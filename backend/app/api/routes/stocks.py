import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from sqlalchemy import text
from dotenv import load_dotenv
import os

from app.core.database import SessionLocal
from app.api.keywords import extract_hot_keyword

load_dotenv()
_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()


@router.get("/stocks")
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
                "hot_keyword": extract_hot_keyword(
                    titles_by_stock.get(row.stock_code, []),
                    exclude={row.stock_name, row.stock_code},
                ),
            }
            for row in rows
        ]
    finally:
        db.close()


@router.get("/stocks/{stock_code}/daily-summary")
def get_daily_summary(stock_code: str):
    """오늘 게시글 기반 자동 요약 (이슈/호재/악재)"""
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT title
            FROM posts
            WHERE stock_code = :code AND DATE(posted_at) = CURRENT_DATE
            ORDER BY posted_at DESC
            LIMIT 40
        """), {"code": stock_code}).fetchall()

        if not rows:
            return {"items": [], "generated_at": datetime.now().isoformat()}

        titles = "\n".join(f"- {r.title}" for r in rows)

        response = _openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": f"""주식 커뮤니티 게시글 제목들을 분석해서 오늘의 주요 내용을 2~3개로 요약하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{"items": [{{"type": "이슈|호재|악재", "text": "한 줄 요약"}}]}}

- 이슈: 중립적 주요 사건
- 호재: 긍정적 내용
- 악재: 부정적 내용

게시글 제목:
{titles}"""
            }]
        )

        result = json.loads(response.choices[0].message.content)
        return {
            "items": result.get("items", []),
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/stocks/{stock_code}/posts")
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


@router.get("/stocks/{stock_code}/timeseries")
def get_timeseries(stock_code: str):
    """시간대별 게시글 수 + 평균 감성 점수"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                DATE_TRUNC('hour', posted_at) as hour,
                COUNT(*) as count,
                -- 조회수 가중 평균: views 없으면 단순 AVG로 폴백
                CASE WHEN SUM(views) > 0
                     THEN SUM(sentiment_score * views) / SUM(views)
                     ELSE AVG(sentiment_score)
                END as avg_score
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
