"""
배치 파이프라인 진입점 — 수집 → 감성분석 → 임베딩
"""

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    started = time.time()
    print(f"=== 배치 시작: {datetime.now().isoformat(timespec='seconds')} ===")

    from sqlalchemy import text

    import app.models  # noqa: F401 — Base에 모든 모델 등록
    from app.core.config import settings
    from app.core.database import Base, engine

    print(f"[설정] 감성 분석 모델: {settings.sentiment_model_path}")

    # 빈 DB에서도 바로 돌 수 있도록 확장/테이블을 먼저 준비한다.
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    # 종목 시드 — 비어 있을 때만
    from app.core.database import SessionLocal
    from app.models.stock import Stock
    from app.crawler.community import STOCK_LIST

    db = SessionLocal()
    try:
        if db.query(Stock).count() == 0:
            for code, name in STOCK_LIST.items():
                db.add(Stock(stock_code=code, stock_name=name))
            db.commit()
            print(f"[초기화] 기본 종목 {len(STOCK_LIST)}개 시드 완료")
    finally:
        db.close()

    # 크롤링 → 감성분석 → 임베딩
    from app.crawler.community import crawl_all
    crawl_all()

    elapsed = time.time() - started
    print(f"=== 배치 완료 ({elapsed:.1f}s) ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[배치 실패] {type(e).__name__}: {e}", file=sys.stderr)
        raise
