from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Enum
import enum
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), index=True)   # 종목 코드 (예: 005930)
    stock_name = Column(String(100), index=True)  # 종목명 (예: 삼성전자)
    title = Column(Text)                           # 게시글 제목
    content = Column(Text)                         # 게시글 본문
    author = Column(String(100))                   # 작성자
    views = Column(Integer, default=0)             # 조회수
    likes = Column(Integer, default=0)             # 좋아요
    sentiment_score = Column(Float, nullable=True) # 감성 점수 (-1 ~ 1)
    source_type = Column(String(20), default="community")  # 'community' | 'news'
    source_url = Column(Text, unique=True)         # 원본 URL (중복 방지)
    posted_at = Column(DateTime)                   # 게시글 작성 시각
    crawled_at = Column(DateTime, server_default=func.now())  # 크롤링 시각


class PostEmbedding(Base):
    __tablename__ = "post_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, index=True)          # posts.id 참조
    embedding = Column(Vector(1536))               # 임베딩 벡터 (OpenAI 기준 1536차원)
    created_at = Column(DateTime, server_default=func.now())
