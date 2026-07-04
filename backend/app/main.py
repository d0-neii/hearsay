from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from app.rag import ask
from app.database import SessionLocal

app = FastAPI(title="Hearsay API")

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
    """종목별 통계 (게시글 수, 감성 비율)"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                stock_code,
                stock_name,
                COUNT(*) as total,
                SUM(CASE WHEN sentiment_score > 0.1 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment_score < -0.1 THEN 1 ELSE 0 END) as negative,
                AVG(sentiment_score) as avg_score
            FROM posts
            GROUP BY stock_code, stock_name
            ORDER BY total DESC
        """))
        rows = result.fetchall()
        return [
            {
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "total": row.total,
                "positive": row.positive,
                "negative": row.negative,
                "avg_score": round(float(row.avg_score or 0), 3),
                "positive_ratio": round(row.positive / row.total * 100) if row.total else 0,
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
