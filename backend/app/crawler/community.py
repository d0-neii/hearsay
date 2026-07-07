import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
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


def _extract_nid(source_url: str) -> str | None:
    """source_url에서 nid 파라미터 추출. 예: ...&nid=424636515 → '424636515'"""
    import re
    match = re.search(r"nid=(\d+)", source_url)
    return match.group(1) if match else None


def fetch_post_detail(source_url: str) -> dict:
    """
    네이버 종토방 API로 전체 제목 + 본문 가져오기
    """
    nid = _extract_nid(source_url)
    if not nid:
        return {"title": None, "content": None}

    try:
        api_url = f"https://m.stock.naver.com/front-api/discussion/detail?id={nid}"
        res = requests.get(api_url, headers=HEADERS, timeout=10)
        data = res.json()

        result = data.get("result", {})
        title = result.get("title")

        # contentHtml에서 텍스트만 추출
        content_html = result.get("contentHtml", "")
        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")
            content = soup.get_text(separator="\n", strip=True)
        else:
            content = None

        return {"title": title, "content": content}

    except Exception as e:
        print(f"  [detail] 요청 실패 (nid={nid}): {e}")
        return {"title": None, "content": None}


def fetch_posts_quick(stock_code: str, stock_name: str) -> list[dict]:
    """
    빠른 초기 수집용 — 1페이지만, 상세 요청 없이 목록 제목만 사용.
    종목 추가 시 즉시 호출용.
    """
    posts = []
    url = f"https://finance.naver.com/item/board.naver?code={stock_code}&page=1"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-kr")
    except Exception as e:
        print(f"[{stock_name}] 빠른 수집 실패: {e}")
        return posts

    for row in soup.select("table.type2 tr"):
        cols = row.select("td")
        if len(cols) < 5:
            continue
        title_tag = cols[1].select_one("a")
        if not title_tag:
            continue
        list_title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        source_url = f"https://finance.naver.com{href}" if href else None
        if not source_url or not list_title:
            continue
        author = cols[3].get_text(strip=True)
        try:
            posted_at = datetime.strptime(cols[0].get_text(strip=True), "%Y.%m.%d %H:%M")
        except ValueError:
            posted_at = None
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
            "title": list_title,
            "content": None,
            "author": author,
            "views": views,
            "likes": likes,
            "source_url": source_url,
            "posted_at": posted_at,
        })
    return posts


def fetch_posts(stock_code: str, stock_name: str, pages: int = 3, sleep: bool = True) -> list[dict]:
    """
    종토방 게시글 목록 수집 → 상세 페이지 병렬 요청으로 전체 제목 + 본문 저장.
    sleep=True 이면 순차 요청 (정기 크롤링용), False 이면 병렬 요청 (초기 크롤링용).
    """
    # 1단계: 목록 페이지에서 기본 정보 수집
    raw_posts = []

    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/item/board.naver?code={stock_code}&page={page}"

        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-kr")
        except Exception as e:
            print(f"[{stock_name}] 페이지 {page} 요청 실패: {e}")
            continue

        for row in soup.select("table.type2 tr"):
            cols = row.select("td")
            if len(cols) < 5:
                continue

            title_tag = cols[1].select_one("a")
            if not title_tag:
                continue

            list_title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            source_url = f"https://finance.naver.com{href}" if href else None

            if not source_url or not list_title:
                continue

            author = cols[3].get_text(strip=True)

            try:
                posted_at = datetime.strptime(cols[0].get_text(strip=True), "%Y.%m.%d %H:%M")
            except ValueError:
                posted_at = None

            try:
                views = int(cols[2].get_text(strip=True).replace(",", ""))
            except ValueError:
                views = 0

            try:
                likes = int(cols[4].get_text(strip=True).replace(",", ""))
            except ValueError:
                likes = 0

            raw_posts.append({
                "stock_code": stock_code,
                "stock_name": stock_name,
                "list_title": list_title,
                "author": author,
                "views": views,
                "likes": likes,
                "source_url": source_url,
                "posted_at": posted_at,
            })

    # 2단계: 상세 요청 (순차 or 병렬)
    if sleep:
        # 정기 크롤링 — 순차 + sleep (네이버 서버 부하 방지)
        details = []
        for p in raw_posts:
            details.append(fetch_post_detail(p["source_url"]))
            time.sleep(0.3)
    else:
        # 초기 크롤링 — ThreadPoolExecutor로 병렬 요청
        from concurrent.futures import ThreadPoolExecutor
        urls = [p["source_url"] for p in raw_posts]
        with ThreadPoolExecutor(max_workers=10) as ex:
            details = list(ex.map(fetch_post_detail, urls))

    # 3단계: 목록 정보 + 상세 정보 합치기
    posts = []
    for p, detail in zip(raw_posts, details):
        posts.append({
            "stock_code": p["stock_code"],
            "stock_name": p["stock_name"],
            "title": detail["title"] or p["list_title"],
            "content": detail["content"],
            "author": p["author"],
            "views": p["views"],
            "likes": p["likes"],
            "source_url": p["source_url"],
            "posted_at": p["posted_at"],
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


def get_stock_list() -> dict[str, str]:
    """DB에서 종목 목록을 읽어 {code: name} 딕셔너리 반환. DB 연결 실패 시 하드코딩 폴백."""
    try:
        from app.models.stock import Stock
        db = SessionLocal()
        try:
            stocks = db.query(Stock).all()
            if stocks:
                return {s.stock_code: s.stock_name for s in stocks}
        finally:
            db.close()
    except Exception as e:
        print(f"[경고] DB에서 종목 목록 로드 실패, 하드코딩 사용: {e}")
    return STOCK_LIST


def crawl_quick_all():
    """서버 시작 시 초기 크롤링 — 2페이지, sleep 없이 본문까지 수집"""
    from app.sentiment import score_all_posts

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 초기 크롤링 시작...")
    total = 0

    stock_list = get_stock_list()

    for code, name in stock_list.items():
        posts = fetch_posts(code, name, pages=2, sleep=False)
        saved = save_posts(posts)
        print(f"  {name}({code}): {len(posts)}개 수집, {saved}개 저장")
        total += saved

    print(f"초기 크롤링 완료 — 총 {total}개 저장")

    scored = score_all_posts()
    print(f"감성 분석 완료 — {scored}개 채점\n")


def crawl_all():
    """전체 종목 크롤링 + 감성 분석 파이프라인 실행"""
    from app.sentiment import score_all_posts
    from app.crawler.news import crawl_news_all

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 크롤링 시작...")
    total = 0

    stock_list = get_stock_list()

    # 종토방 게시글
    for code, name in stock_list.items():
        posts = fetch_posts(code, name, pages=3)
        saved = save_posts(posts)
        print(f"  {name}({code}): {len(posts)}개 수집, {saved}개 저장")
        total += saved

    print(f"종토방 크롤링 완료 — 총 {total}개 저장")

    # 뉴스 기사
    news_saved = crawl_news_all()
    total += news_saved

    # 새로 저장된 게시글/뉴스 감성 분석
    scored = score_all_posts()
    print(f"감성 분석 완료 — {scored}개 채점")

    # 새로 저장된 게시글/뉴스 임베딩
    from app.embedder import embed_unprocessed_posts
    embed_unprocessed_posts()

    # BM25 인덱스 갱신 (새 게시글 반영)
    from app.rag.bm25_index import rebuild_index
    rebuild_index()
    print()


if __name__ == "__main__":
    crawl_all()
