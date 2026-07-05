import { useState } from 'react'
import type { StockSummary } from '../types'
import Logo from '../assets/logo.svg?react'
import SearchIcon from '../assets/icons/search.svg?react'
import ClearIcon from '../assets/icons/clear.svg?react'

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

const sentimentColorClass = (isPositive: boolean) => (isPositive ? 'text-positive-bar' : 'text-negative-bar')

export const StockSidebar = ({ stockList, selectedStockCode, onSelectStock }: Props) => {
  const [searchKeyword, setSearchKeyword] = useState('')

  const trimmedSearchKeyword = searchKeyword.trim()
  const filteredStockList = trimmedSearchKeyword
    ? stockList.filter(
        (stock) =>
          stock.stockName.includes(trimmedSearchKeyword) ||
          stock.stockCode.includes(trimmedSearchKeyword)
      )
    : stockList

  return (
    <aside className="bg-sidebar flex flex-col overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="p-4 border-b border-sidebar-hover">
        <Logo className="h-9 w-auto block" aria-label="Hearsay" />
      </div>

      <div className="flex items-center gap-2 mx-3 mt-3 px-2 py-1.5 bg-sidebar-search rounded-md text-sidebar-muted text-xs">
        <SearchIcon className="w-3.5 h-3.5 shrink-0" />
        <input
          type="text"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          placeholder="종목 검색"
          className="bg-transparent outline-none w-full text-sidebar-fg placeholder:text-sidebar-muted"
        />
        {searchKeyword && (
          <button onClick={() => setSearchKeyword('')} className="shrink-0 hover:text-sidebar-fg transition-colors">
            <ClearIcon className="w-3 h-3" />
          </button>
        )}
      </div>

      <p className="p-3 text-[10px] font-semibold text-sidebar-muted tracking-[0.8px]">
        {trimmedSearchKeyword ? `검색 결과 ${filteredStockList.length}건` : '인기 종목'}
      </p>

      <div className="flex flex-col gap-0.5 px-2">
        {filteredStockList.length === 0 && (
          <p className="p-4 text-center text-[12px] text-sidebar-muted">종목을 찾을 수 없어요</p>
        )}
        {filteredStockList.map((stock) => (
          <button
            key={stock.stockCode}
            className={`w-full rounded-md p-2 cursor-pointer text-left transition-colors duration-150 hover:bg-sidebar-hover ${
              selectedStockCode === stock.stockCode ? 'bg-sidebar-active' : 'bg-transparent'
            }`}
            onClick={() => onSelectStock(stock)}
          >
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-[13px] font-medium text-sidebar-fg">{stock.stockName}</span>
              <span className={`text-xs font-semibold font-mono ${sentimentColorClass(stock.avgSentimentScore >= 0)}`}>
                {stock.avgSentimentScore >= 0 ? '+' : ''}{(stock.avgSentimentScore * 10).toFixed(1)}%
              </span>
            </div>
            <SentimentMiniBar positiveRatio={stock.positiveRatio} />
            <span className={`text-[10px] mt-1 block ${sentimentColorClass(stock.positiveRatio >= 50)}`}>
              {stock.positiveRatio >= 50 ? '매수 우세' : '매도 우세'}
            </span>
          </button>
        ))}
      </div>
    </aside>
  )
}
