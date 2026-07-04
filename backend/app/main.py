import re
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from app.rag import ask
from app.database import SessionLocal
from app.crawler import crawl_all

# 키워드 추출용 불용어
_STOP_WORDS = {
    '있는', '없는', '이건', '그냥', '진짜', '완전', '너무', '정말', '이제', '근데',
    '그래', '다시', '지금', '오늘', '어제', '이거', '그거', '이게', '그게', '뭔가',
    '이렇게', '저렇게', '어떻게', '왜냐면', '그래서', '하지만', '그런데', '그리고',
    '합니다', '입니다', '있습니다', '없습니다', '했습니다', '됩니다', '같습니다',
}

def _extract_hot_keyword(titles: list[str], exclude: set[str] = frozenset()) -> str | None:
    if not titles:
        return None

    base_exclude = _STOP_WORDS | exclude | {w for name in exclude for w in name.split()}

    # 문서 빈도(DF) 계산: 전체 제목의 50% 이상에 등장하면 종목명 변형으로 간주하고 자동 제외
    # → "NAVER" stock에서 "네이버"처럼 stock_name과 표기가 다른 경우도 처리
    doc_freq: Counter = Counter()
    token_list: list[str] = []
    for title in titles:
        tokens = re.findall(r'[가-힣]{2,}|[A-Za-z]{2,}', title)
        doc_freq.update(set(tokens))   # 문서당 1번만 카운트
        token_list.extend(tokens)

    # DF 1위 단어 = 종목명 표기 변형일 가능성이 가장 높으므로 무조건 제외
    # (예: stock_name이 "NAVER"여도 제목엔 "네이버"로 등장)
    top_by_df = {w for w, _ in doc_freq.most_common(2) if w not in base_exclude}
    exclude_words = base_exclude | top_by_df

    filtered = [w for w in token_list if w not in exclude_words]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.add_job(crawl_all, "interval", minutes=10, next_run_time=datetime.now())
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


class AskRequest(BaseModel):
    query: str
    stock_code: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask_endpoint(body: AskRequest):
    try:
        result = ask(body.query, stock_code=body.stock_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stocks")
def get_stocks():
    """종목별 통계 (게시글 수, 감성 비율, 어제 대비, 언급량 비교, 핫키워드)"""
    db = SessionLocal()
    try:
        # 1. 종목별 통계 집계 — 오늘/어제/7일 분리
        result = db.execute(text("""
            SELECT
                stock_code,
                stock_name,
                COUNT(*) as total,
                SUM(CASE WHEN sentiment_score > 0.1 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment_score < -0.1 THEN 1 ELSE 0 END) as negative,
                AVG(sentiment_score) as avg_score,
                -- 오늘
                SUM(CASE WHEN DATE(posted_at) = CURRENT_DATE THEN 1 ELSE 0 END)
                    as today_total,
                SUM(CASE WHEN DATE(posted_at) = CURRENT_DATE AND sentiment_score > 0.1 THEN 1 ELSE 0 END)
                    as today_positive,
                -- 어제
                SUM(CASE WHEN DATE(posted_at) = CURRENT_DATE - INTERVAL '1 day' THEN 1 ELSE 0 END)
                    as yesterday_total,
                SUM(CASE WHEN DATE(posted_at) = CURRENT_DATE - INTERVAL '1 day' AND sentiment_score > 0.1 THEN 1 ELSE 0 END)
                    as yesterday_positive,
                -- 최근 7일(오늘 제외) 합계 — 일평균 계산용
                SUM(CASE WHEN DATE(posted_at) >= CURRENT_DATE - INTERVAL '7 days' AND DATE(posted_at) < CURRENT_DATE THEN 1 ELSE 0 END)
                    as week_total
            FROM posts
            GROUP BY stock_code, stock_name
            ORDER BY today_total DESC NULLS LAST, total DESC
        """))
        rows = result.fetchall()

        # 2. 오늘 제목 목록 — 핫키워드 추출용
        title_result = db.execute(text("""
            SELECT stock_code, title
            FROM posts
            WHERE DATE(posted_at) = CURRENT_DATE
        """))
        titles_by_stock: dict[str, list[str]] = {}
        for t in title_result.fetchall():
            titles_by_stock.setdefault(t.stock_code, []).append(t.title or "")

        def _ratio(pos, total) -> int | None:
            return round(pos / total * 100) if total else None

        return [
            {
                # 기존 필드 (사이드바용 — 전체 기간)
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "total": row.total,
                "positive": row.positive,
                "negative": row.negative,
                "avg_score": round(float(row.avg_score or 0), 3),
                "positive_ratio": _ratio(row.positive, row.total) or 0,
                # 카드용 신규 필드
                "today_total": row.today_total or 0,
                "today_positive_ratio": _ratio(row.today_positive, row.today_total),
                "prev_positive_ratio": _ratio(row.yesterday_positive, row.yesterday_total),
                "post_count_ratio": round(row.today_total / (row.week_total / 7), 1)
                    if row.week_total and row.today_total else None,
                "hot_keyword": _extract_hot_keyword(
                    titles_by_stock.get(row.stock_code, []),
                    exclude={row.stock_name, row.stock_code},
                ),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/stocks/{stock_code}/posts")
def get_posts(stock_code: str, limit: int = 20):
    """종목별 최근 게시글"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT id, title, author, views, likes, sentiment_score, posted_at
            FROM posts
            WHERE stock_code = :code
            ORDER BY posted_at DESC
            LIMIT :limit
        """), {"code": stock_code, "limit": limit})
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "title": row.title,
                "author": row.author,
                "views": row.views,
                "likes": row.likes,
                "sentiment_score": row.sentiment_score,
                "posted_at": str(row.posted_at),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/stocks/{stock_code}/timeseries")
def get_timeseries(stock_code: str):
    """시간대별 게시글 수 + 평균 감성 점수"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                DATE_TRUNC('hour', posted_at) as hour,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score
            FROM posts
            WHERE stock_code = :code AND posted_at IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        """), {"code": stock_code})
        rows = result.fetchall()
        return [
            {
                "hour": str(row.hour),
                "count": row.count,
                "avg_score": round(float(row.avg_score or 0), 3),
            }
            for row in rows
        ]
    finally:
        db.close()
