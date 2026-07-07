from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.crawler import crawl_all
from app.api.routes import api_router

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 테이블 자동 생성 + stocks 초기 데이터
    import app.models  # noqa: F401 — Base에 모든 모델 등록
    from app.core.database import Base, engine, SessionLocal
    from app.models.stock import Stock
    from app.crawler.community import STOCK_LIST
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for code, name in STOCK_LIST.items():
            if not db.query(Stock).filter(Stock.stock_code == code).first():
                db.add(Stock(stock_code=code, stock_name=name))
        db.commit()
    finally:
        db.close()

    # 감성 분석 모델 선(先)로드 — 첫 크롤링 전에 준비
    from app.sentiment import get_pipeline
    get_pipeline()

    # BM25 인덱스 초기 빌드 — 기존 게시글 대상
    from app.rag.bm25_index import rebuild_index
    rebuild_index()

    _scheduler.add_job(crawl_all, "interval", minutes=10)
    _scheduler.start()
    print("스케줄러 시작 — 즉시 크롤링 후 10분마다 반복합니다.")
    yield
    _scheduler.shutdown()
    print("스케줄러 종료.")


app = FastAPI(title="Hearsay API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
