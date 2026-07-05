"""
BM25 인덱스 모듈

역할:
- DB의 posts 전체를 읽어 BM25 인덱스를 메모리에 빌드
- 크롤링이 끝날 때마다 rebuild_index()로 갱신
- search()로 BM25 점수 기반 유사 post_id 목록 반환
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from rank_bm25 import BM25Okapi
from sqlalchemy import text
from app.core.database import SessionLocal


def _tokenize(text: str) -> list[str]:
    """
    한국어 + 영문/숫자 단순 토크나이저.
    konlpy 없이 정규식만으로 처리.
    예) "삼성전자 배당 발표" → ["삼성전자", "배당", "발표"]
    """
    if not text:
        return []
    tokens = re.findall(r'[가-힣]+|[A-Za-z0-9]+', text)
    return [t.lower() for t in tokens if len(t) > 1]


# 앱 수명 동안 메모리에 유지되는 인덱스 상태
_bm25: Optional[BM25Okapi] = None
_post_ids: list[int] = []       # _bm25의 i번째 문서 → 실제 post.id
_post_meta: dict[int, dict] = {}  # post_id → {stock_name, stock_code, title, posted_at}


def rebuild_index() -> int:
    """
    DB에서 전체 posts를 읽어 BM25 인덱스를 (재)빌드.
    반환값: 인덱싱된 게시글 수
    """
    global _bm25, _post_ids, _post_meta

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT id, stock_name, stock_code, title, posted_at, source_type
            FROM posts
            WHERE title IS NOT NULL
            ORDER BY id
        """)).fetchall()
    finally:
        db.close()

    if not rows:
        print("[bm25] 인덱싱할 게시글 없음")
        return 0

    corpus: list[list[str]] = []
    ids: list[int] = []
    meta: dict[int, dict] = {}

    for row in rows:
        tokens = _tokenize(row.title or "")
        corpus.append(tokens)
        ids.append(row.id)
        meta[row.id] = {
            "stock_name": row.stock_name,
            "stock_code": row.stock_code,
            "title": row.title,
            "posted_at": str(row.posted_at),
            "source_type": row.source_type or "community",
        }

    _bm25 = BM25Okapi(corpus)
    _post_ids = ids
    _post_meta = meta

    print(f"[bm25] 인덱스 빌드 완료 — {len(ids)}개 게시글")
    return len(ids)


def search(
    query: str,
    top_k: int = 20,
    stock_code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """
    BM25 점수 기준 상위 top_k 게시글 반환.
    stock_code, date_from, date_to 지정 시 필터링.

    반환: [{"post_id", "stock_name", "stock_code", "title", "posted_at", "source_type", "bm25_score"}, ...]
    """
    if _bm25 is None:
        rebuild_index()

    if not _post_ids:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scores: list[float] = _bm25.get_scores(query_tokens)

    # (score, post_id) 내림차순 정렬
    ranked = sorted(
        zip(scores, _post_ids),
        key=lambda x: x[0],
        reverse=True,
    )

    results = []
    for score, post_id in ranked:
        if score <= 0:
            break
        meta = _post_meta.get(post_id, {})
        if stock_code and meta.get("stock_code") != stock_code:
            continue

        # 날짜 필터
        if date_from or date_to:
            posted_at_str = meta.get("posted_at", "")
            try:
                posted_at = datetime.fromisoformat(posted_at_str[:19])
                if date_from and posted_at < date_from:
                    continue
                if date_to and posted_at >= date_to:
                    continue
            except (ValueError, TypeError):
                continue

        results.append({
            "post_id": post_id,
            "stock_name": meta.get("stock_name"),
            "stock_code": meta.get("stock_code"),
            "title": meta.get("title"),
            "posted_at": meta.get("posted_at"),
            "source_type": meta.get("source_type", "community"),
            "bm25_score": round(float(score), 4),
        })
        if len(results) >= top_k:
            break

    return results
