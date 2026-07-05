from sqlalchemy import text
from openai import OpenAI
from app.database import SessionLocal
from app.embedder import get_embedding
from app.bm25_index import search as bm25_search
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# RRF 상수: 순위 충격 완화용
_RRF_K = 60


def _vector_search(query: str, stock_code: str | None, top_k: int) -> list[dict]:
    """벡터 유사도 기반 검색. 거리(distance) 오름차순 top_k 반환."""
    query_vector = get_embedding(query)
    db = SessionLocal()
    try:
        if stock_code:
            result = db.execute(text("""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                WHERE p.stock_code = :stock_code
                ORDER BY distance ASC
                LIMIT :top_k
            """), {"query_vector": str(query_vector), "stock_code": stock_code, "top_k": top_k})
        else:
            result = db.execute(text("""
                SELECT
                    p.id,
                    p.stock_name,
                    p.stock_code,
                    p.title,
                    p.posted_at,
                    pe.embedding <=> CAST(:query_vector AS vector) AS distance
                FROM post_embeddings pe
                JOIN posts p ON pe.post_id = p.id
                ORDER BY distance ASC
                LIMIT :top_k
            """), {"query_vector": str(query_vector), "top_k": top_k})

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "stock_name": row.stock_name,
                "stock_code": row.stock_code,
                "title": row.title,
                "posted_at": str(row.posted_at),
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
                "distance": None,
            }

    # 점수 내림차순 정렬 후 top_k 슬라이싱
    sorted_ids = sorted(rrf_scores, key=lambda pid: rrf_scores[pid], reverse=True)
    return [meta_map[pid] for pid in sorted_ids[:top_k]]


def search_similar_posts(query: str, stock_code: str = None, top_k: int = 5) -> list[dict]:
    """
    Hybrid Search (BM25 + Vector) + RRF 기반 유사 게시글 검색.

    1. 벡터 검색으로 후보 top-20 추출
    2. BM25 검색으로 후보 top-20 추출
    3. RRF로 두 결과 합산 → 최종 top_k 반환
    """
    CANDIDATE_K = 20  # 각 검색에서 뽑을 후보 수

    vector_results = _vector_search(query, stock_code=stock_code, top_k=CANDIDATE_K)
    bm25_results = bm25_search(query, top_k=CANDIDATE_K, stock_code=stock_code)

    return _reciprocal_rank_fusion(vector_results, bm25_results, top_k=top_k)


def ask(query: str, stock_code: str = None) -> dict:
    """RAG 기반 질의응답"""

    # 1. 유사 게시글 검색
    similar_posts = search_similar_posts(query, stock_code=stock_code, top_k=5)

    if not similar_posts:
        return {
            "answer": "관련 게시글을 찾을 수 없습니다.",
            "sources": [],
        }

    # 2. 게시글 목록을 컨텍스트로 정리
    context = "\n".join([
        f"- [{post['stock_name']}] {post['title']} ({post['posted_at'][:10]})"
        for post in similar_posts
    ])

    # 3. Claude에게 여론 요약 요청
    prompt = f"""당신은 주식 커뮤니티 여론을 요약해주는 분석가입니다.
아래는 사용자 질문과 관련된 주식 커뮤니티 게시글 제목들입니다.

[질문]
{query}

[관련 게시글]
{context}

위 게시글들을 바탕으로 커뮤니티의 전반적인 여론과 분위기를 2~3문장으로 요약해주세요.
중요: 이것은 사실 분석이 아니라 커뮤니티 여론 요약입니다. 팩트체크가 아닌 분위기를 전달해주세요."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": similar_posts,
    }


if __name__ == "__main__":
    result = ask("요즘 분위기 어때?", stock_code="005930")  # 삼성전자
    print("=== 답변 ===")
    print(result["answer"])
    print("\n=== 참고 게시글 ===")
    for post in result["sources"]:
        print(f"  [{post['stock_name']}] {post['title']}")
