import { useState, useEffect } from 'react'
import { StockSidebar } from './components/StockSidebar'
import { SentimentChart } from './components/SentimentChart'
import { StatCards } from './components/StatCard'
import { PostFeed } from './components/PostFeed'
import { AskPanel } from './components/AskPanel'
import { DailySummary } from './components/DailySummary'
import { useStockList, usePostFeed, useSentimentChart, useDailySummary } from './hooks/useStockQueries'
import { useAskQuestion } from './hooks/useAskQuestion'
import type { StockSummary } from './types'

export default function App() {
  const [manuallySelectedStock, setManuallySelectedStock] = useState<StockSummary | null>(null)

  const { data: stockList = [], isLoading: isStockListLoading, isError: isStockListError } = useStockList()

  // 사용자가 직접 고른 종목이 있으면 그것을, 아니면 목록의 첫 번째 종목을 기본값으로 사용
  const selectedStock = manuallySelectedStock ?? stockList[0] ?? null

  const { data: postFeed = [] } = usePostFeed(selectedStock?.stockCode)
  const { data: sentimentChartData = [] } = useSentimentChart(selectedStock?.stockCode)
  const { data: dailySummary, isLoading: isDailySummaryLoading } = useDailySummary(selectedStock?.stockCode)
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

      <main className="overflow-y-auto px-7 py-6 bg-base flex flex-col gap-3 [scrollbar-width:thin] [scrollbar-color:var(--color-border)_transparent]">
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

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-center gap-2 text-sm font-semibold">
                <span className="text-positive">{positiveRatio}% 매수</span>
                <span className="text-border-strong">|</span>
                <span className="text-negative">매도 {100 - positiveRatio}%</span>
              </div>
              <div className="flex h-2 rounded-full border border-border overflow-hidden">
                {/* 매수: 오른쪽 정렬 (중심 방향) */}
                <div className="flex-1 overflow-hidden flex justify-end">
                  <div
                    className="h-full bg-positive-bar transition-[width] duration-[400ms] ease-in-out"
                    style={{ width: `${Math.min(positiveRatio * 2, 100)}%` }}
                  />
                </div>
                {/* 매도: 왼쪽 정렬 (중심 방향) */}
                <div className="flex-1 overflow-hidden flex justify-start">
                  <div
                    className="h-full bg-negative-bar transition-[width] duration-[400ms] ease-in-out"
                    style={{ width: `${Math.min((100 - positiveRatio) * 2, 100)}%` }}
                  />
                </div>
              </div>
            </div>

            <DailySummary data={dailySummary} isLoading={isDailySummaryLoading} />

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
