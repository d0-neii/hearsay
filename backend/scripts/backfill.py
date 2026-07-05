"""
기존 게시글 백필 스크립트

content가 NULL인 기존 게시글들을 source_url로 방문해서
전체 제목 + 본문을 업데이트
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.crawler.community import fetch_post_detail


# content 비어있는 게시글 하나씩 돌면서 원문 긁어와서 채워줌
def backfill():
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT id, source_url
            FROM posts
            WHERE content IS NULL AND source_url IS NOT NULL
            ORDER BY id
        """)).fetchall()
    finally:
        db.close()

    total = len(rows)
    if not total:
        print("백필할 게시글 없음 (content가 이미 모두 채워져 있음)")
        return

    print(f"백필 대상: {total}개\n")

    for i, row in enumerate(rows, start=1):
        detail = fetch_post_detail(row.source_url)
        full_title = detail["title"]
        content = detail["content"]

        # 게시글마다 새 세션 열어서 커밋 (하나 실패해도 나머지는 계속 진행)
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE posts
                SET
                    title   = COALESCE(:title, title),
                    content = :content
                WHERE id = :id
            """), {"title": full_title, "content": content, "id": row.id})
            db.commit()
        finally:
            db.close()

        status = "✅" if content else "⚠️ 본문 없음"
        print(f"  [{i}/{total}] id={row.id} {status}")

        time.sleep(0.3)  # 네이버 서버 부하 방지

    print(f"\n백필 완료 — {total}개 처리")


if __name__ == "__main__":
    backfill()
