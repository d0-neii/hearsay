from apscheduler.schedulers.blocking import BlockingScheduler
from app.crawler import crawl_all

scheduler = BlockingScheduler(timezone="Asia/Seoul")

# 10분마다 크롤링 실행
scheduler.add_job(crawl_all, "interval", minutes=10)

if __name__ == "__main__":
    print("스케줄러 시작 — 10분마다 크롤링합니다. (Ctrl+C로 종료)")
    crawl_all()  # 시작하자마자 1회 즉시 실행
    scheduler.start()
