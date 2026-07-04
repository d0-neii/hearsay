from sqlalchemy import text
from app.database import SessionLocal

# 긍정/부정 키워드 (주식 커뮤니티 특화)
POSITIVE_KEYWORDS = [
    "상승", "급등", "오른다", "올랐", "올라", "매수", "강세", "반등", "돌파",
    "신고가", "기대", "호재", "좋다", "좋은", "긍정", "추천", "사자", "담아",
    "가즈아", "ㄱㄱ", "불장", "목표가", "익절", "수익", "흑자", "성장",
]

NEGATIVE_KEYWORDS = [
    "하락", "급락", "떨어진", "떨어져", "매도", "약세", "하한가", "손절",
    "악재", "위험", "걱정", "불안", "팔자", "버려", "폭락", "최저", "적자",
    "손실", "물렸", "물타기", "탈출", "지옥", "망했", "ㅠ", "ㅜ", "개망",
]


def compute_sentiment(title: str) -> float:
    """
    제목 키워드 기반 단순 감성 점수 계산
    반환값: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
    """
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)

    total = pos + neg
    if total == 0:
        return 0.0

    return round((pos - neg) / total, 2)


def score_all_posts():
    """sentiment_score가 없는 게시글 전체에 감성 점수 부여"""
    db = SessionLocal()
    try:
        result = db.execute(text(
            "SELECT id, title FROM posts WHERE sentiment_score IS NULL"
        ))
        posts = result.fetchall()

        print(f"{len(posts)}개 게시글 감성 분석 중...")
        for post_id, title in posts:
            score = compute_sentiment(title)
            db.execute(text(
                "UPDATE posts SET sentiment_score = :score WHERE id = :id"
            ), {"score": score, "id": post_id})

        db.commit()
        print("감성 분석 완료!")
    finally:
        db.close()


if __name__ == "__main__":
    score_all_posts()
