import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text
import app.models  # 모델 임포트해야 Base에 테이블 등록됨
from app.core.database import Base


INITIAL_STOCKS = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("035420", "NAVER"),
    ("035720", "카카오"),
    ("051910", "LG화학"),
]


def init():
    # pgvector 익스텐션 활성화
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료!")

    # stocks 초기 데이터 삽입 (이미 있으면 스킵)
    from app.core.database import SessionLocal
    from app.models.stock import Stock
    db = SessionLocal()
    try:
        for code, name in INITIAL_STOCKS:
            if not db.query(Stock).filter(Stock.stock_code == code).first():
                db.add(Stock(stock_code=code, stock_name=name))
        db.commit()
        print("✅ 초기 종목 데이터 삽입 완료!")
    finally:
        db.close()


if __name__ == "__main__":
    init()
