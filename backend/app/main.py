from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

_scheduler = None


def _seed_initial_data() -> None:
    """테이블 생성 + 최초 실행 시 기본 종목 시드."""
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


def _start_scheduler() -> None:
    """주기적 크롤링 스케줄러 기동 (배치를 앱 안에서 돌릴 때만)."""
    global _scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.crawler import crawl_all

    _scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    _scheduler.add_job(crawl_all, "interval", minutes=settings.crawl_interval_minutes)
    _scheduler.start()
    print(f"스케줄러 시작 — {settings.crawl_interval_minutes}분마다 전체 크롤링 반복합니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_initial_data()

    # 감성 분석 모델 선(先)로드 — 앱 안에서 크롤링을 돌릴 때만 의미가 있다.
    # 서빙 전용 모드에서는 이 블록을 타지 않으므로 transformers/torch가 필요 없다.
    if settings.preload_sentiment_model:
        from app.sentiment import get_pipeline
        get_pipeline()

    import threading

    def _build_index_background() -> None:
        try:
            from app.rag.bm25_index import rebuild_index
            rebuild_index()
        except Exception as e:  # 인덱스 실패로 서버 전체가 죽지 않도록
            print(f"[bm25] 초기 인덱스 빌드 실패 — {type(e).__name__}: {e}")

    threading.Thread(target=_build_index_background, daemon=True).start()
    print("BM25 인덱스 백그라운드 빌드 시작...")

    if settings.enable_startup_crawl:
        import threading
        from app.crawler.community import crawl_quick_all

        threading.Thread(target=crawl_quick_all, daemon=True).start()
        print("초기 빠른 크롤링 시작 (백그라운드)...")

    if settings.enable_scheduler:
        _start_scheduler()
    else:
        print("서빙 전용 모드 — 크롤링/스케줄러 비활성화 (배치에서 수집합니다).")

    yield

    if _scheduler is not None:
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
