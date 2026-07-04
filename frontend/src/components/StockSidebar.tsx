import type { StockSummary } from '../types'
import Logo from '../assets/logo.svg?react'

type Props = {
  stockList: StockSummary[]
  selectedStockCode: string
  onSelectStock: (stock: StockSummary) => void
}

const SentimentMiniBar = ({ positiveRatio }: { positiveRatio: number }) => (
  <div className="flex h-[3px] rounded-[2px] overflow-hidden bg-sidebar-hover">
    <div className="h-full bg-positive-bar" style={{ width: `${positiveRatio}%` }} />
    <div className="h-full bg-negative-bar" style={{ width: `${100 - positiveRatio}%` }} />
  </div>
)

export const StockSidebar = ({ stockList, selectedStockCode, onSelectStock }: Props) => {
  return (
    <aside className="bg-sidebar flex flex-col overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="p-4 border-b border-sidebar-hover">
        <Logo className="h-9 w-auto block" aria-label="Hearsay" />
      </div>

      <div className="flex items-center gap-2 mx-3 mt-3 p-2 bg-sidebar-search rounded-md text-sidebar-muted text-xs cursor-pointer">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
        </svg>
        <span>종목 검색</span>
      </div>

      <p className="p-3 text-[10px] font-semibold text-sidebar-muted tracking-[0.8px]">
        인기 종목
      </p>

      <div className="flex flex-col gap-0.5 px-2">
        {stockList.map((stock) => (
          <button
            key={stock.stockCode}
            className={`w-full rounded-md p-2 cursor-pointer text-left transition-colors duration-150 hover:bg-sidebar-hover ${
              selectedStockCode === stock.stockCode ? 'bg-sidebar-active' : 'bg-transparent'
            }`}
            onClick={() => onSelectStock(stock)}
          >
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-[13px] font-medium text-sidebar-fg">{stock.stockName}</span>
              <span className={`text-xs font-semibold font-mono ${stock.avgSentimentScore >= 0 ? 'text-positive-bar' : 'text-negative-bar'}`}>
                {stock.avgSentimentScore >= 0 ? '+' : ''}{(stock.avgSentimentScore * 10).toFixed(1)}%
              </span>
            </div>
            <SentimentMiniBar positiveRatio={stock.positiveRatio} />
            <span className={`text-[10px] mt-1 block ${stock.positiveRatio >= 50 ? 'text-positive-bar' : 'text-negative-bar'}`}>
              {stock.positiveRatio >= 50 ? '매수 우세' : '매도 우세'}
            </span>
          </button>
        ))}
      </div>
    </aside>
  )
}
