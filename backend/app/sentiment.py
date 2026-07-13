from __future__ import annotations

from transformers import pipeline
from sqlalchemy import text
from app.core.database import SessionLocal

import os
from pathlib import Path

_FINETUNED = Path(__file__).parent.parent / "finetuned_model"
MODEL_NAME = str(_FINETUNED) if _FINETUNED.exists() else "snunlp/KR-FinBert-SC"

# 앱 수명 동안 1회만 로드 (get_pipeline() 첫 호출 시)
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        print(f"[sentiment] 모델 로드 중: {MODEL_NAME}")
        _pipeline = pipeline(
            "text-classification",
            model=MODEL_NAME,
            top_k=None,       # 전체 라벨 확률 반환
            truncation=True,
            max_length=512,
        )
        print("[sentiment] 모델 로드 완료")
    return _pipeline


# neutral 확률이 이 값 이상이면 점수를 0.0으로 확정
_NEUTRAL_DOMINANCE = 0.5


def _score_from_probs(probs: dict[str, float]) -> float:
    """
    라벨별 확률 딕셔너리 → 감성 점수 변환.

    - P(neutral) >= 0.5: 모델이 중립으로 확신 → 0.0 반환
    - 그 외: P(positive) - P(negative)  →  -1.0 ~ 1.0
    """
    if probs.get("neutral", 0.0) >= _NEUTRAL_DOMINANCE:
        return 0.0
    return round(probs.get("positive", 0.0) - probs.get("negative", 0.0), 3)


def compute_sentiment(text: str) -> float:
    """
    KR-FinBert-SC 기반 감성 점수.
    반환값: -1.0 ~ 1.0 (neutral 확률 >= 0.5이면 0.0 고정)
    """
    if not text or not text.strip():
        return 0.0

    pipe = get_pipeline()
    results = pipe(text)[0]   # [{"label": "positive", "score": 0.9}, ...]

    probs = {r["label"]: r["score"] for r in results}
    return _score_from_probs(probs)


def score_all_posts(batch_size: int = 32) -> int:
    """
    sentiment_score가 NULL인 게시글을 배치로 분석해서 업데이트.
    반환값: 채점된 게시글 수
    """
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT id, title, content FROM posts WHERE sentiment_score IS NULL"
        )).fetchall()

        if not rows:
            return 0

        print(f"[sentiment] {len(rows)}개 게시글 감성 분석 시작...")
        pipe = get_pipeline()

        # 배치 단위 추론 (메모리 안전)
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            # 제목 + 본문 합산 (본문 없으면 제목만). 512토큰 내에서 truncation됨.
            texts = [
                f"{row.title or ''} {row.content or ''}".strip() or " "
                for row in batch
            ]

            batch_results = pipe(texts, batch_size=batch_size)

            for row, result in zip(batch, batch_results):
                probs = {r["label"]: r["score"] for r in result}
                score = _score_from_probs(probs)
                db.execute(
                    text("UPDATE posts SET sentiment_score = :s WHERE id = :id"),
                    {"s": score, "id": row.id},
                )

            db.commit()
            print(f"[sentiment]  {min(i + batch_size, len(rows))}/{len(rows)} 완료")

        print("[sentiment] 감성 분석 완료")
        return len(rows)
    finally:
        db.close()
