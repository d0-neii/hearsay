from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.api.routes import api_router
from app.core.config import settings
from app.crawler import crawl_all
from app.crawler.community import crawl_quick_all

_scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)


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
        # 테이블이 완전히 비어있을 때(최초 실행)만 기본 종목 시드
        if db.query(Stock).count() == 0:
            for code, name in STOCK_LIST.items():
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

    # 서버 시작 시 빠른 초기 크롤링 (백그라운드)
    import threading
    threading.Thread(target=crawl_quick_all, daemon=True).start()
    print("초기 빠른 크롤링 시작 (백그라운드)...")

    _scheduler.add_job(crawl_all, "interval", minutes=settings.crawl_interval_minutes)
    _scheduler.start()
    print(f"스케줄러 시작 — {settings.crawl_interval_minutes}분마다 전체 크롤링 반복합니다.")
    yield
    _scheduler.shutdown()
    print("스케줄러 종료.")


app = FastAPI(title="Hearsay API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
