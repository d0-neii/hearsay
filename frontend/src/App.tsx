import { useState, useEffect } from 'react'
import { StockSidebar } from './components/StockSidebar'
import { SentimentChart } from './components/SentimentChart'
import { StatCards } from './components/StatCard'
import { PostFeed } from './components/PostFeed'
import { AskPanel } from './components/AskPanel'
import { useStockList, usePostFeed, useSentimentChart } from './hooks/useStockQueries'
import { useAskQuestion } from './hooks/useAskQuestion'
import type { StockSummary } from './types'

export default function App() {
  const [manuallySelectedStock, setManuallySelectedStock] = useState<StockSummary | null>(null)

  const { data: stockList = [], isLoading: isStockListLoading, isError: isStockListError } = useStockList()

  // 사용자가 직접 고른 종목이 있으면 그것을, 아니면 목록의 첫 번째 종목을 기본값으로 사용
  const selectedStock = manuallySelectedStock ?? stockList[0] ?? null

  const { data: postFeed = [] } = usePostFeed(selectedStock?.stockCode)
  const { data: sentimentChartData = [] } = useSentimentChart(selectedStock?.stockCode)
  const { mutate: askQuestion, isPending: isAsking, data: askResult, reset: resetAsk } = useAskQuestion(selectedStock?.stockCode)

  useEffect(() => {
    resetAsk()
  }, [selectedStock?.stockCode, resetAsk])

  const positiveRatio = selectedStock
    ? Math.round(selectedStock.todayPositiveRatio ?? selectedStock.positiveRatio)
    : 50

  return (
    <div className="grid grid-cols-[220px_1fr_300px] h-screen overflow-hidden">
      <StockSidebar
        stockList={stockList}
        selectedStockCode={selectedStock?.stockCode ?? ''}
        onSelectStock={setManuallySelectedStock}
      />

      <main className="overflow-y-auto px-7 py-6 bg-base flex flex-col gap-5 [scrollbar-width:thin] [scrollbar-color:var(--color-border)_transparent]">
        {isStockListLoading && (
          <p className="py-10 text-center text-[13px] text-muted">불러오는 중...</p>
        )}

        {isStockListError && (
          <p className="py-10 text-center text-[13px] text-negative">데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.</p>
        )}

        {selectedStock && (
          <>
            <div className="flex justify-between items-start">
              <h2 className="text-[22px] font-bold text-primary tracking-[-0.5px] flex items-baseline gap-2">
                {selectedStock.stockName}
                <span className="text-[13px] font-normal text-muted font-mono">{selectedStock.stockCode}</span>
              </h2>
              <span className="text-xs text-muted pt-1.5">{selectedStock.totalPostCount}개 게시글</span>
            </div>

            <div className="flex items-center gap-2.5">
              <span className="text-xs font-semibold whitespace-nowrap text-positive">
                매수 {positiveRatio}%
              </span>
              <div className="flex-1 flex h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-positive-bar transition-[width] duration-[400ms] ease-in-out"
                  style={{ width: `${positiveRatio}%` }}
                />
                <div
                  className="h-full bg-negative-bar transition-[width] duration-[400ms] ease-in-out"
                  style={{ width: `${100 - positiveRatio}%` }}
                />
              </div>
              <span className="text-xs font-semibold whitespace-nowrap text-negative">
                매도 {100 - positiveRatio}%
              </span>
            </div>

            <StatCards stock={selectedStock} askResult={askResult} />

            {sentimentChartData.length > 0 && (
              <SentimentChart data={sentimentChartData} />
            )}

            <AskPanel
              key={selectedStock.stockCode}
              isAsking={isAsking}
              askResult={askResult}
              onAskQuestion={askQuestion}
            />
          </>
        )}
      </main>

      <PostFeed postFeed={postFeed} />
    </div>
  )
}
