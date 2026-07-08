"""
pykrx를 이용한 실제 매수/매도 비율 조회.

KRX 투자자별 거래금액 기반으로 매수세/매도세를 계산한다.
- 개인 / 기관합계 / 외국인합계 세 그룹의 순매수 방향을 집계
- buy_ratio: 매수 우세 그룹 비율 (0~100)
  예) 3그룹 중 2그룹이 순매수 → 67%, 1그룹만 순매수 → 33%
- 당일 장 중·직후에는 데이터가 없을 수 있어 전일로 fallback
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_KEY_INVESTORS = ["개인", "기관합계", "외국인합계"]


def _fetch_ratio(stock_code: str, target_date: str) -> dict | None:
    """단일 날짜에 대해 매수/매도 비율을 조회."""
    try:
        from pykrx import stock  # 지연 임포트 (서버 기동 시 로드 비용 회피)

        df = stock.get_market_trading_value_by_investor(
            target_date, target_date, stock_code
        )
        if df is None or df.empty:
            return None

        # 누락된 투자자 그룹 제외
        available = [inv for inv in _KEY_INVESTORS if inv in df.index]
        if not available:
            return None

        buy_count = sum(
            1 for inv in available if df.loc[inv, "순매수"] > 0
        )
        sell_count = len(available) - buy_count
        total = len(available)

        buy_ratio = round(buy_count / total * 100)

        # 개인/기관/외국인 순매수 금액도 함께 반환 (UI 확장용)
        detail = {
            inv: int(df.loc[inv, "순매수"])
            for inv in available
        }

        return {
            "buy_ratio": buy_ratio,
            "sell_ratio": 100 - buy_ratio,
            "detail": detail,   # 예: {"개인": -1200000000, "기관합계": 500000000, ...}
            "date": target_date,
        }
    except Exception as e:
        logger.warning(f"[trading] {stock_code} ({target_date}) 조회 실패: {e}")
        return None


def get_buy_sell_ratio(stock_code: str) -> dict | None:
    """
    오늘 KRX 투자자별 매수/매도 데이터를 가져와 비율을 계산한다.
    당일 데이터 미수록 시 전일 데이터로 fallback.

    반환 예시:
    {
        "buy_ratio": 67,
        "sell_ratio": 33,
        "detail": {"개인": 1200000000, "기관합계": -800000000, "외국인합계": 600000000},
        "date": "20260708",
    }
    """
    today = date.today().strftime("%Y%m%d")
    result = _fetch_ratio(stock_code, today)
    if result:
        return result

    # 전일 fallback (주말·공휴일 고려해 최대 3일 전까지)
    for days_ago in range(1, 4):
        prev_date = (date.today() - timedelta(days=days_ago)).strftime("%Y%m%d")
        result = _fetch_ratio(stock_code, prev_date)
        if result:
            logger.info(f"[trading] {stock_code}: {prev_date} fallback 사용")
            return result

    return None
