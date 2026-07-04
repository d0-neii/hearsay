import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import Post

# 크롤링할 종목 리스트 (코드: 이름)
STOCK_LIST = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "051910": "LG화학",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_posts(stock_code: str, stock_name: str, pages: int = 3) -> list[dict]:
    """종토방 게시글을 가져와서 딕셔너리 리스트로 반환"""
    posts = []

    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/item/board.naver?code={stock_code}&page={page}"

        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.encoding = "euc-kr"
            soup = BeautifulSoup(res.text, "html.parser")
        except Exception as e:
            print(f"[{stock_name}] 페이지 {page} 요청 실패: {e}")
            continue

        rows = soup.select("table.type2 tr")

        for row in rows:
            cols = row.select("td")
            if len(cols) < 5:
                continue

            # 제목 및 URL
            title_tag = cols[1].select_one("a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            source_url = f"https://finance.naver.com{href}" if href else None

            if not source_url or not title:
                continue

            # 작성자
            author = cols[3].get_text(strip=True)

            # 작성 시각
            date_str = cols[0].get_text(strip=True)
            try:
                posted_at = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
            except ValueError:
                posted_at = None

            # 조회수 / 좋아요
            try:
                views = int(cols[2].get_text(strip=True).replace(",", ""))
            except ValueError:
                views = 0

            try:
                likes = int(cols[4].get_text(strip=True).replace(",", ""))
            except ValueError:
                likes = 0

            posts.append({
                "stock_code": stock_code,
                "stock_name": stock_name,
                "title": title,
                "author": author,
                "views": views,
                "likes": likes,
                "source_url": source_url,
                "posted_at": posted_at,
            })

    return posts


def save_posts(posts: list[dict]) -> int:
    """게시글을 DB에 저장. 중복은 스킵. 저장된 개수 반환"""
    db = SessionLocal()
    saved = 0

    try:
        for post_data in posts:
            post = Post(**post_data)
            db.add(post)
            try:
                db.commit()
                saved += 1
            except IntegrityError:
                db.rollback()  # source_url 중복 → 스킵
    finally:
        db.close()

    return saved


def crawl_all():
    """전체 종목 크롤링 실행"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 크롤링 시작...")
    total = 0

    for code, name in STOCK_LIST.items():
        posts = fetch_posts(code, name, pages=3)
        saved = save_posts(posts)
        print(f"  {name}({code}): {len(posts)}개 수집, {saved}개 저장")
        total += saved

    print(f"크롤링 완료 — 총 {total}개 저장\n")


if __name__ == "__main__":
    crawl_all()
