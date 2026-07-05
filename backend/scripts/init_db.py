import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text
import app.models  # 모델 임포트해야 Base에 테이블 등록됨
from app.core.database import Base


def init():
    # pgvector 익스텐션 활성화
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ 테이블 생성 완료!")


if __name__ == "__main__":
    init()
