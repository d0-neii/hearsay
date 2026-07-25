"""
애플리케이션 설정 중앙화 모듈
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",          # .env의 PYTHONPATH 등 무관한 키 무시
        case_sensitive=False,
    )

    # --- 필수 (없으면 기동 실패) ---
    database_url: str
    openai_api_key: str

    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    # --- 크롤러 ---
    crawl_interval_minutes: int = 10
    crawl_pages: int = 3              # 정기 크롤링 시 수집할 종토방 페이지 수
    crawl_quick_pages: int = 2        # 서버 시작 직후 빠른 크롤링 페이지 수
    crawl_news_pages: int = 2         # 뉴스 크롤링 페이지 수
    crawl_detail_delay: float = 0.3   # 상세 요청 간 sleep (초)
    crawl_max_workers: int = 10       # 병렬 상세 요청 워커 수
    scheduler_timezone: str = "Asia/Seoul"

    # --- 감성 분석 ---
    sentiment_model_fallback: str = "snunlp/KR-FinBert-SC"
    sentiment_batch_size: int = 32
    # neutral 확률이 이 값 이상이면 감성 점수를 0.0으로 확정
    sentiment_neutral_dominance: float = 0.5
    # 통계 집계 시 긍정/부정을 가르는 임계값
    sentiment_positive_threshold: float = 0.1

    # --- 임베딩 / LLM ---
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_batch_size: int = 100
    llm_model: str = "gpt-4o-mini"

    # --- 검색 ---
    rrf_k: int = 60               # RRF 순위 충격 완화 상수
    search_candidate_k: int = 20  # 각 검색기에서 뽑을 후보 수
    search_top_k: int = 5         # 최종 반환 개수

    @property
    def cors_origins(self) -> list[str]:
        """콤마 구분 문자열 → 리스트"""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def sentiment_model_path(self) -> str:
        """파인튜닝 모델이 있으면 그 경로를, 없으면 허브 모델명을 반환."""
        finetuned = BASE_DIR / "finetuned_model"
        return str(finetuned) if finetuned.exists() else self.sentiment_model_fallback


settings = Settings()  # type: ignore[call-arg]
