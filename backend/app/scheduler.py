from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import settings
from app.crawler import crawl_all

scheduler = BlockingScheduler(timezone=settings.scheduler_timezone)

scheduler.add_job(crawl_all, "interval", minutes=settings.crawl_interval_minutes)

if __name__ == "__main__":
    print(f"스케줄러 시작 — {settings.crawl_interval_minutes}분마다 크롤링합니다. (Ctrl+C로 종료)")
    crawl_all()  # 시작하자마자 1회 즉시 실행
    scheduler.start()
