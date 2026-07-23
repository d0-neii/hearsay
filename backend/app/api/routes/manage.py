import threading
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.stock import Stock

router = APIRouter()


class StockIn(BaseModel):
    stock_code: str
    stock_name: str


_KRX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDCConsole.jsp",
}


@router.get("/stocks/search")
def search_stocks(q: str):
    """KRX 공식 데이터포털 종목 검색 (data.krx.co.kr)"""
    if not q.strip():
        return []
    try:
        res = requests.post(
            "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
            data={
                "bld": "dbms/comm/finder/finder_stkisu",
                "market_abrv": "",
                "searchText": q,
                "pagePath": "/contents/MDCConsole.jsp",
            },
            headers=_KRX_HEADERS,
            timeout=5,
        )
        res.raise_for_status()
        block = res.json().get("block1", [])
        return [
            {"stock_code": item["short_code"], "stock_name": item["codeName"]}
            for item in block
            if item.get("short_code", "").isdigit() and len(item["short_code"]) == 6
        ][:10]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {e}")


@router.get("/stocks/manage")
def list_managed_stocks(db: Session = Depends(get_db)):
    """현재 관리 중인 종목 목록"""
    stocks = db.query(Stock).order_by(Stock.created_at).all()
    return [{"stock_code": s.stock_code, "stock_name": s.stock_name} for s in stocks]


def _crawl_single(stock_code: str, stock_name: str):
    """추가된 종목 즉시 크롤링 (백그라운드 실행) — 빠른 버전"""
    try:
        from app.crawler.community import fetch_posts_quick, save_posts
        from app.sentiment import score_all_posts

        posts = fetch_posts_quick(stock_code, stock_name)
        save_posts(posts)
        score_all_posts()
        print(f"[즉시 크롤링 완료] {stock_name}({stock_code}): {len(posts)}개")
    except Exception as e:
        print(f"[즉시 크롤링 실패] {stock_name}({stock_code}): {e}")


@router.post("/stocks/manage", status_code=201)
def add_stock(body: StockIn, db: Session = Depends(get_db)):
    """종목 추가 + 즉시 크롤링"""
    existing = db.query(Stock).filter(Stock.stock_code == body.stock_code).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 추가된 종목입니다.")
    db.add(Stock(stock_code=body.stock_code, stock_name=body.stock_name))
    db.commit()
    # 응답은 바로 반환하고, 크롤링은 백그라운드에서
    threading.Thread(
        target=_crawl_single,
        args=(body.stock_code, body.stock_name),
        daemon=True,
    ).start()
    return {"stock_code": body.stock_code, "stock_name": body.stock_name}


@router.delete("/stocks/manage/{stock_code}", status_code=204)
def delete_stock(stock_code: str, db: Session = Depends(get_db)):
    """종목 삭제"""
    stock = db.query(Stock).filter(Stock.stock_code == stock_code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    db.delete(stock)
    db.commit()
