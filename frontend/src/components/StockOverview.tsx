import type { StockSummary, TradingData } from '../types'

type Props = {
  stock: StockSummary
  tradingData: TradingData | undefined
}

export const StockOverview = ({ stock, tradingData }: Props) => {
  // 실제 KRX 매수/매도 비율 우선 사용, 없으면 커뮤니티 감성 비율로 fallback
  const buyRatio = tradingData?.buyRatio ?? Math.round(stock.todayPositiveRatio ?? stock.positiveRatio)
  const sellRatio = 100 - buyRatio
  const isEstimated = tradingData?.buyRatio == null

  return (
    <>
      <div className="flex justify-between items-start">
        <h2 className="text-[22px] font-bold text-primary tracking-[-0.5px] flex items-baseline gap-2">
          {stock.stockName}
          <span className="text-[13px] font-normal text-muted font-mono">{stock.stockCode}</span>
        </h2>
        <span className="text-xs text-muted pt-1.5">{stock.totalPostCount}개 게시글</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-center gap-2 text-sm font-semibold">
          <span className="text-positive">{buyRatio}% 매수</span>
          <span className="text-border-strong">|</span>
          <span className="text-negative">매도 {sellRatio}%</span>
          {isEstimated && (
            <span className="text-[10px] font-normal text-muted">(커뮤니티 추정)</span>
          )}
        </div>
        <div className="flex h-2 rounded-full border border-border overflow-hidden">
          {/* 매수: 오른쪽 정렬 (중심 방향) */}
          <div className="flex-1 overflow-hidden flex justify-end">
            <div
              className="h-full bg-positive-bar transition-[width] duration-[400ms] ease-in-out"
              style={{ width: `${Math.min(buyRatio * 2, 100)}%` }}
            />
          </div>
          {/* 매도: 왼쪽 정렬 (중심 방향) */}
          <div className="flex-1 overflow-hidden flex justify-start">
            <div
              className="h-full bg-negative-bar transition-[width] duration-[400ms] ease-in-out"
              style={{ width: `${Math.min(sellRatio * 2, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </>
  )
}
