import re
from datetime import datetime, timedelta
from sqlalchemy import text
from openai import OpenAI
from dotenv import load_dotenv
import os
from app.core.database import SessionLocal
from app.embedder import get_embedding
from .bm25_index import search as bm25_search

load_dotenv()
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# RRF 상수: 순위 충격 완화용
_RRF_K = 60


def _generate_hypothetical_document(query: str) -> str:
    """
    HyDE (Hypothetical Document Embeddings):
    사용자 쿼리를 받아 실제로 DB에 있을 법한 게시글 제목을 LLM으로 생성.

    일반 쿼리 임베딩 대신 이 가상 문서를 임베딩해서 벡터 검색에 사용하면,
    쿼리(짧고 추상적) vs 문서(구체적 제목) 간 분포 차이를 줄일 수 있다.

    예) "삼성전자 요즘 분위기 어때?" →
        "삼성전자, 반도체 수요 회복 기대감에 커뮤니티 긍정 여론 증가"
    """
    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=80,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 주식 커뮤니티 게시글 제목을 작성하는 봇입니다. "
                        "사용자 질문을 받으면, 그 질문에 대한 답이 담겼을 법한 "
                        "실제 커뮤니티 게시글 제목을 딱 한 줄만 출력하세요. "
                        "다른 말은 절대 하지 마세요."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        hypothetical = response.choices[0].message.content.strip()
        print(f"[HyDE] '{query}' → '{hypothetical}'")
        return hypothetical
    except Exception as e:
        print(f"[HyDE] 가상 문서 생성 실패, 원본 쿼리 사용: {e}")
        return query


def _parse_date_range(query: str) -> tuple[datetime | None, datetime | None]:
    """
    쿼리 텍스트에서 날짜 의도를 파싱해 (date_from, date_to) 반환.

    오늘  → 오늘 00:00 ~ 내일 00:00
    어제  → 어제 00:00 ~ 오늘 00:00
    이번 주 / 최근 → 7일 전 ~ 내일
    명시 없음 → 최근 3일 (기본값)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    q = query.lower()

    if re.search(r'오늘|today', q):
        return today, tomorrow

    if re.search(r'어제|yesterday', q):
        return today - timedelta(days=1), today

    if re.search(r'이번\s*주|지난\s*7일|일주일|한\s*주', q):
        return today - timedelta(days=7), tomorrow

    if re.search(r'이번\s*달|지난\s*달|한\s*달', q):
        return today - timedelta(days=30), tomorrow

    # 기본값: 최근 3일
    return today - timedelta(days=3), tomorrow


def _vector_search(
    query: str,
    stock_code: str | None,
    top_k: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """벡터 유사도 기반 검색. 거리(distance) 오름차순 top_k 반환.
    HyDE: 쿼리 → 가상 문서 생성 → 가상 문서 임베딩으로 검색.
    """
    hypothetical_doc = _generate_hypothetical_document(query)
    query_vector = get_embedding(hypothetical_doc)
    db = SessionLocal()
    try:
        # 날짜 필터 조건 동적 생성
        date_clause = ""
        params: dict = {"query_vector": str(query_vector), "top_k": top_k}
        if date_from:
            date_clause += " AND p.posted_at >= :date_from"
            params["date_from"] = date_from
        if date_to:
            date_clause += " AND p.posted_at < :date_to"
            params["date_to"] = date_to

        if stock_code:
            params["stock_code"] = stock_code
            result = db.execute(text(f"""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    p.source_type,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                WHERE p.stock_code = :stock_code{date_clause}
                ORDER BY distance ASC
                LIMIT :top_k
            """), params)
        else:
            result = db.execute(text(f"""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    p.source_type,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                WHERE 1=1{date_clause}
                ORDER BY distance ASC
                LIMIT :top_k
            """), params)

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "stock_name": row.stock_name,
                "stock_code": row.stock_code,
                "title": row.title,
                "posted_at": str(row.posted_at),
                "source_type": row.source_type or "community",
                "distance": row.distance,
            }
            for row in rows
        ]
    finally:
        db.close()


def _reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    top_k: int,
) -> list[dict]:
    """
    RRF (Reciprocal Rank Fusion)로 두 검색 결과를 합산
    """
    rrf_scores: dict[int, float] = {}
    meta_map: dict[int, dict] = {}

    # 벡터 검색 결과 반영
    for rank, post in enumerate(vector_results, start=1):
        pid = post["id"]
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 1.0 / (_RRF_K + rank)
        meta_map[pid] = post

    # BM25 검색 결과 반영 (post_id 키가 "post_id"임에 주의)
    for rank, post in enumerate(bm25_results, start=1):
        pid = post["post_id"]
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 1.0 / (_RRF_K + rank)
        if pid not in meta_map:
            meta_map[pid] = {
                "id": pid,
                "stock_name": post["stock_name"],
                "stock_code": post["stock_code"],
                "title": post["title"],
                "posted_at": post["posted_at"],
                "source_type": post.get("source_type", "community"),
                "distance": None,
            }

    # 점수 내림차순 정렬 후 top_k 슬라이싱
    sorted_ids = sorted(rrf_scores, key=lambda pid: rrf_scores[pid], reverse=True)
    return [meta_map[pid] for pid in sorted_ids[:top_k]]


def search_similar_posts(query: str, stock_code: str = None, top_k: int = 5) -> list[dict]:
    """
    Hybrid Search (BM25 + Vector) + RRF 기반 유사 게시글 검색.

    1. 쿼리에서 날짜 의도 파싱 (오늘/어제/이번주 등)
    2. HyDE로 가상 문서 생성 후 벡터 검색 후보 top-20 추출
    3. BM25 검색으로 후보 top-20 추출
    4. RRF로 두 결과 합산 → 최종 top_k 반환
    """
    CANDIDATE_K = 20

    date_from, date_to = _parse_date_range(query)

    vector_results = _vector_search(
        query, stock_code=stock_code, top_k=CANDIDATE_K,
        date_from=date_from, date_to=date_to,
    )
    bm25_results = bm25_search(
        query, top_k=CANDIDATE_K, stock_code=stock_code,
        date_from=date_from, date_to=date_to,
    )

    return _reciprocal_rank_fusion(vector_results, bm25_results, top_k=top_k)
