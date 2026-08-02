"""
배치 파이프라인 진입점 — 수집 → 감성분석 → 임베딩.

서빙 인스턴스(API 서버)는 DB를 읽기만 하고, 데이터를 채우는 일은 전부 여기서 한다.
GitHub Actions에서 하루 1회 실행하는 것을 기본으로 하며, 로컬에서도 같은 명령으로
돌릴 수 있다.

이렇게 나눠 두면 서빙 쪽에 torch/transformers를 설치하지 않아도 되고,
배치가 끝나면 별도 배포 없이 다음 요청부터 새 데이터가 보인다.

실행:
    cd backend
    python scripts/run_batch.py

필요한 환경변수:
    DATABASE_URL, OPENAI_API_KEY
    (선택) SENTIMENT_MODEL_FALLBACK — 파인튜닝 모델의 HuggingFace repo id
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
