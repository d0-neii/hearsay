import { useState, useEffect } from 'react'
import { StockSidebar } from './components/StockSidebar'
import { StockOverview } from './components/StockOverview'
import { SentimentChart } from './components/SentimentChart'
import { StatCards } from './components/StatCard'
import { PostFeed } from './components/PostFeed'
import { AskPanel } from './components/AskPanel'
import { DailySummary } from './components/DailySummary'
import { useStockList, usePostFeed, useSentimentChart, useDailySummary, useTradingData } from './hooks/useStockQueries'
import { useAskQuestion } from './hooks/useAskQuestion'
import type { StockSummary } from './types'

type ChatMessage = { question: string; answer: string }

export default function App() {
  const [manuallySelectedStock, setManuallySelectedStock] = useState<StockSummary | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const { data: stockList = [], isLoading: isStockListLoading, isError: isStockListError } = useStockList()

  // 사용자가 직접 고른 종목이 있으면 그것을, 아니면 목록의 첫 번째 종목을 기본값으로 사용
  const selectedStock = manuallySelectedStock ?? stockList[0] ?? null

  const { data: postFeed = [] } = usePostFeed(selectedStock?.stockCode)
  const { data: sentimentChartData = [] } = useSentimentChart(selectedStock?.stockCode)
  const { data: dailySummary, isLoading: isDailySummaryLoading } = useDailySummary(selectedStock?.stockCode)
  const { data: tradingData } = useTradingData(selectedStock?.stockCode)
  const { mutate: askQuestionMutate, isPending: isAsking, reset: resetAsk } = useAskQuestion(selectedStock?.stockCode)

  const handleAskQuestion = (query: string) => {
    if (!selectedStock) return
    askQuestionMutate(query, {
      onSuccess: (result) => {
        setMessages((prev) => [...prev, { question: query, answer: result.answer }])
      },
    })
  }

  useEffect(() => {
    resetAsk()
    setMessages([])
  }, [selectedStock?.stockCode, resetAsk])

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
            <StockOverview stock={selectedStock} tradingData={tradingData} />

            <DailySummary data={dailySummary} isLoading={isDailySummaryLoading} />

            <StatCards stock={selectedStock} tradingData={tradingData} />

            {sentimentChartData.length > 0 && (
              <SentimentChart data={sentimentChartData} />
            )}

            <AskPanel
              isAsking={isAsking}
              messages={messages}
              onAskQuestion={handleAskQuestion}
            />
          </>
        )}
      </main>

      <PostFeed postFeed={postFeed} />
    </div>
  )
}
