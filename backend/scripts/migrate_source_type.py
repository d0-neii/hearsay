"""
DB 마이그레이션: posts 테이블에 source_type 컬럼 추가

실행: python migrate_source_type.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE posts
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'community'
    """))
    conn.execute(text("""
        UPDATE posts SET source_type = 'community' WHERE source_type IS NULL
    """))
    conn.commit()

print("✅ 마이그레이션 완료 — source_type 컬럼 추가됨")
