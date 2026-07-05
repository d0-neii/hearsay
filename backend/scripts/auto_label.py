"""
GPT 자동 레이블링 스크립트 (Silver Labeling)

- DB에서 아직 레이블링 안 된 게시글을 배치로 뽑아
- GPT-4o-mini로 긍정/부정/중립 판단
- labeled_data.csv에 누적 저장

실행: python auto_label.py
"""

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from sqlalchemy import text
from app.core.database import SessionLocal
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_FILE = Path(__file__).parent.parent / "labeled_data.csv"
BATCH_SIZE = 20   # GPT에 한 번에 넘길 게시글 수
SLEEP_SEC = 1.0   # 배치 간 딜레이 (rate limit 방지)


# 이미 라벨링한 post_id 목록 (중복 방지용)
def _load_labeled_ids() -> set[int]:
    if not OUTPUT_FILE.exists():
        return set()
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {int(row["post_id"]) for row in reader}


# 아직 라벨링 안 된 게시글만 골라서 가져옴
def _fetch_unlabeled(labeled_ids: set[int], limit: int) -> list[dict]:
    db = SessionLocal()
    try:
        # 필터링하다 보면 부족할 수 있어서 넉넉하게 3배로 뽑아둠
        rows = db.execute(text("""
            SELECT id, stock_name, stock_code, title, content, sentiment_score
            FROM posts
            WHERE title IS NOT NULL
            ORDER BY id
            LIMIT :limit
        """), {"limit": limit * 3}).fetchall()
    finally:
        db.close()

    return [
        {
            "post_id": row.id,
            "stock_name": row.stock_name,
            "stock_code": row.stock_code,
            "title": row.title or "",
            "content": (row.content or "")[:300],  # 본문 300자 제한
            "model_score": row.sentiment_score,
        }
        for row in rows
        if row.id not in labeled_ids
    ][:limit]


def _gpt_label_batch(posts: list[dict]) -> dict[int, str]:
    """
    GPT-4o-mini로 배치 레이블링.
    반환: {post_id: "positive" | "negative" | "neutral"}
    """
    items = "\n".join([
        f'[{i+1}] 제목: {p["title"]} / 본문: {p["content"][:150]}'
        for i, p in enumerate(posts)
    ])

    prompt = f"""당신은 한국 주식 커뮤니티(종토방) 게시글의 감성을 분류하는 전문가입니다.

아래 게시글들을 읽고 각각의 투자 감성을 판단하세요.

기준:
- positive: 주가 상승 기대, 호재, 매수 추천, 낙관적 전망
- negative: 주가 하락 우려, 악재, 매도 추천, 비관적 전망, 손실 언급
- neutral: 단순 정보 공유, 중립적 분석, 질문, 주식과 무관한 내용

반드시 아래 JSON 형식으로만 응답하세요:
{{"results": [{{"id": 1, "label": "positive"}}, ...]}}

게시글:
{items}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    data = json.loads(response.choices[0].message.content)
    results = data.get("results", [])

    return {
        posts[item["id"] - 1]["post_id"]: item["label"]
        for item in results
        if 1 <= item["id"] <= len(posts)
    }


# 라벨링 결과를 csv에 이어서 저장 (헤더는 처음 한 번만)
def _append_rows(posts: list[dict], labels: dict[int, str]) -> int:
    is_new = not OUTPUT_FILE.exists()
    saved = 0
    with OUTPUT_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["post_id", "stock_name", "stock_code", "title", "label", "model_score"]
        )
        if is_new:
            writer.writeheader()
        for post in posts:
            label = labels.get(post["post_id"])
            if not label:
                continue
            writer.writerow({
                "post_id": post["post_id"],
                "stock_name": post["stock_name"],
                "stock_code": post["stock_code"],
                "title": post["title"],
                "label": label,
                "model_score": post["model_score"],
            })
            saved += 1
    return saved


# target개 채울 때까지 배치 단위로 GPT 호출 반복
def main(target: int = 500):
    print(f"GPT 자동 레이블링 시작 — 목표: {target}개\n")

    labeled_ids = _load_labeled_ids()
    already = len(labeled_ids)
    print(f"기존 레이블: {already}개")

    posts = _fetch_unlabeled(labeled_ids, limit=target)
    total = len(posts)
    print(f"새로 레이블링할 게시글: {total}개\n")

    if not posts:
        print("레이블링할 게시글이 없습니다.")
        return

    done = 0
    for i in range(0, total, BATCH_SIZE):
        batch = posts[i: i + BATCH_SIZE]
        try:
            labels = _gpt_label_batch(batch)
            saved = _append_rows(batch, labels)
            done += saved
            print(f"  [{i + len(batch)}/{total}] {saved}개 저장 — 누적 {already + done}개")
        except Exception as e:
            print(f"  [{i}] 배치 실패: {e}")

        time.sleep(SLEEP_SEC)

    print(f"\n완료 — 총 {already + done}개 레이블링됨")
    print(f"저장 위치: {OUTPUT_FILE}")


if __name__ == "__main__":
    # 인자로 목표 개수 지정 가능: python auto_label.py 1000
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(target)
