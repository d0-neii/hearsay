"""
BM25 인덱스 모듈

역할:
- DB의 posts를 읽어 BM25 인덱스를 메모리에 빌드
- 크롤링이 끝날 때마다 rebuild_index()로 갱신
- search()로 BM25 점수 기반 유사 post_id 목록 반환
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from rank_bm25 import BM25Okapi
from sqlalchemy import text

from app.core.config import settings
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


# 앱 수명 동안 메모리에 유지되는 인덱스 상태.
# _post_ids / _corpus / _posted_at 은 같은 인덱스를 공유하는 병렬 리스트다.
_bm25: Optional[BM25Okapi] = None
_post_ids: list[int] = []                    # i번째 문서 → 실제 post.id
_corpus: list[list[str]] = []                # i번째 문서의 토큰 (증분 갱신용 캐시)
_posted_at: list[Optional[datetime]] = []    # i번째 문서의 작성 시각 (윈도우 판정용)
_post_meta: dict[int, dict] = {}             # post_id → {stock_name, stock_code, ...}
_max_indexed_id: int = 0                     # 지금까지 인덱싱한 최대 post.id


def _window_cutoff() -> Optional[datetime]:
    """인덱싱 하한 시각. bm25_window_days가 0 이하면 제한 없음(None)."""
    days = settings.bm25_window_days
    if not days or days <= 0:
        return None
    return datetime.now() - timedelta(days=days)


def _fetch_rows(after_id: int, cutoff: Optional[datetime]) -> list:
    """after_id보다 큰 id 중 윈도우 안에 드는 게시글만 조회."""
    sql = """
        SELECT id, stock_name, stock_code, title, posted_at, source_type
        FROM posts
        WHERE title IS NOT NULL
          AND id > :after_id
    """
    params: dict = {"after_id": after_id}
    if cutoff is not None:
        # posted_at이 비어있는 레코드는 버리지 않고 남긴다.
        sql += " AND (posted_at IS NULL OR posted_at >= :cutoff)"
        params["cutoff"] = cutoff
    sql += " ORDER BY id"

    db = SessionLocal()
    try:
        return db.execute(text(sql), params).fetchall()
    finally:
        db.close()


def _evict_outside_window(cutoff: Optional[datetime]) -> int:
    """윈도우를 벗어난 문서를 인덱스 상태에서 제거. 반환값: 제거된 문서 수."""
    global _post_ids, _corpus, _posted_at, _post_meta

    if cutoff is None or not _post_ids:
        return 0

    keep = [i for i, dt in enumerate(_posted_at) if dt is None or dt >= cutoff]
    if len(keep) == len(_post_ids):
        return 0

    kept_ids = [_post_ids[i] for i in keep]
    for pid in set(_post_ids) - set(kept_ids):
        _post_meta.pop(pid, None)

    _corpus = [_corpus[i] for i in keep]
    _posted_at = [_posted_at[i] for i in keep]
    removed = len(_post_ids) - len(kept_ids)
    _post_ids = kept_ids
    return removed


def rebuild_index(full: bool = False) -> int:
    """
    BM25 인덱스를 갱신한다.

    full=False (기본): 증분. 새 게시글만 읽어 추가하고 윈도우 밖 문서를 덜어낸다.
    full=True: 캐시를 버리고 처음부터 다시 빌드한다.

    반환값: 인덱싱된 게시글 수
    """
    global _bm25, _post_ids, _corpus, _posted_at, _post_meta, _max_indexed_id

    if full:
        _post_ids, _corpus, _posted_at, _post_meta, _max_indexed_id = [], [], [], {}, 0

    cutoff = _window_cutoff()
    removed = _evict_outside_window(cutoff)
    rows = _fetch_rows(_max_indexed_id, cutoff)

    for row in rows:
        _post_ids.append(row.id)
        _corpus.append(_tokenize(row.title or ""))
        _posted_at.append(row.posted_at)
        _post_meta[row.id] = {
            "stock_name": row.stock_name,
            "stock_code": row.stock_code,
            "title": row.title,
            "posted_at": str(row.posted_at),
            "source_type": row.source_type or "community",
        }
        if row.id > _max_indexed_id:
            _max_indexed_id = row.id

    if not _corpus:
        _bm25 = None
        print("[bm25] 인덱싱할 게시글 없음")
        return 0

    # 변화가 있을 때만 재생성. 옛 인덱스를 먼저 놓아줘야 재빌드 중
    # 두 개가 동시에 메모리에 올라가지 않는다.
    if rows or removed or _bm25 is None:
        _bm25 = None
        _bm25 = BM25Okapi(_corpus)

    print(
        f"[bm25] 인덱스 갱신 — 총 {len(_post_ids)}개"
        f" (신규 {len(rows)}, 윈도우 밖 제거 {removed})"
    )
    return len(_post_ids)


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

    if not _post_ids or _bm25 is None:
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
