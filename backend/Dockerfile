# Hearsay 백엔드 — 서빙(API) 전용 이미지
#
# requirements.txt(서빙용)만 설치하므로 torch/transformers가 들어가지 않는다.
# 크롤링·감성분석은 GitHub Actions 배치(scripts/run_batch.py)가 담당한다.
#
# 빌드:  docker build -t hearsay-api ./backend
# 실행:  docker run -p 8000:8000 --env-file backend/.env hearsay-api

# ---------- builder ----------
# 빌드 도구는 여기서만 쓰고 최종 이미지에는 남기지 않는다.
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- runtime ----------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# libpq5: psycopg2 런타임 의존성 / curl: 헬스체크용
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app
COPY scripts ./scripts

# 서빙 전용 기본값. 로컬에서 한 프로세스로 다 돌리고 싶으면 실행 시 덮어쓴다.
ENV ENABLE_SCHEDULER=false \
    ENABLE_STARTUP_CRAWL=false \
    PRELOAD_SENTIMENT_MODEL=false

# 루트로 돌리지 않는다
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

# PaaS(Fly.io, Railway 등)는 PORT를 주입한다. 없으면 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
