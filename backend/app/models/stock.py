from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    stock_code = Column(String(20), primary_key=True)  # 종목 코드 (예: 005930)
    stock_name = Column(String(100), nullable=False)   # 종목명 (예: 삼성전자)
    created_at = Column(DateTime, server_default=func.now())
