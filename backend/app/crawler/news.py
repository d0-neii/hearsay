import time
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.models import Post
from app.crawler.community import STOCK_LIST, HEADERS


def _parse_date(date_str: str) -> datetime | None:
    """
    네이버 뉴스 날짜 파싱.
    형식 예: '2025.01.15 오전 09:30' / '2025.01.15 오후 03:45'
    """
    try:
        date_str = date_str.strip()
        date_str = date_str.replace('오전', 'AM').replace('오후', 'PM')
        return datetime.strptime(date_str, "%Y.%m.%d %p %I:%M")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str[:10], "%Y.%m.%d")
    except ValueError:
        return None


def fetch_news(stock_code: str, stock_name: str, pages: int = 2) -> list[dict]:
    """
    네이버 금융 뉴스 탭에서 기사 목록 수집.
    """
    news_list = []

    for page in range(1, pages + 1):
        url = (
            f"https://finance.naver.com/item/news_news.naver"
            f"?code={stock_code}&page={page}&sm=title_entity_id.basic&clusterId="
        )

        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-kr")
        except Exception as e:
            print(f"[{stock_name}] 뉴스 페이지 {page} 요청 실패: {e}")
            continue

        rows = soup.select("table.type5 tr")

        for row in rows:
            title_tag = row.select_one("td.title a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")

            # 상대 경로 → 절대 경로
            if href.startswith("/"):
                source_url = f"https://finance.naver.com{href}"
            else:
                source_url = href

            if not title or not source_url:
                continue

            # 언론사
            info_td = row.select_one("td.info")
            press = info_td.get_text(strip=True) if info_td else ""

            # 날짜
            date_td = row.select_one("td.date")
            date_str = date_td.get_text(strip=True) if date_td else ""
            posted_at = _parse_date(date_str)

            news_list.append({
                "stock_code": stock_code,
                "stock_name": stock_name,
                "title": title,
                "content": None,       # 뉴스 본문은 외부 사이트 → 제목만 활용
                "author": press,       # author 필드에 언론사명 저장
                "views": 0,
                "likes": 0,
                "source_url": source_url,
                "posted_at": posted_at,
                "source_type": "news",
            })

        time.sleep(0.3)

    return news_list


def save_news(news_list: list[dict]) -> int:
    """뉴스 기사를 posts 테이블에 저장. 중복은 스킵."""
    db = SessionLocal()
    saved = 0
    try:
        for item in news_list:
            post = Post(**item)
            db.add(post)
            try:
                db.commit()
                saved += 1
            except IntegrityError:
                db.rollback()  # source_url 중복 → 스킵
    finally:
        db.close()
    return saved


def crawl_news_all():
    """전체 종목 뉴스 크롤링"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 뉴스 크롤링 시작...")
    total = 0

    for code, name in STOCK_LIST.items():
        news = fetch_news(code, name, pages=2)
        saved = save_news(news)
        print(f"  {name}({code}): {len(news)}개 수집, {saved}개 저장")
        total += saved

    print(f"뉴스 크롤링 완료 — 총 {total}개 저장")
    return total
