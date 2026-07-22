import { useState, useEffect, useRef, useMemo } from 'react'
import { useAddStock, useDeleteStock } from '../hooks/useStockMutations'
import { useStockSearch } from '../hooks/useStockQueries'
import type { StockSummary } from '../types'
import type { StockSearchResult } from '../api'
import SearchIcon from '../assets/icons/search.svg?react'
import ClearIcon from '../assets/icons/clear.svg?react'

type Props = {
  stockList: StockSummary[]
  onBack: () => void
}

const SearchResultRow = ({
  stock,
  isAdded,
  isLoading,
  onToggle,
}: {
  stock: StockSearchResult
  isAdded: boolean
  isLoading: boolean
  onToggle: () => void
}) => (
  <div className="flex items-center justify-between p-2 rounded-md hover:bg-sidebar-hover transition-colors">
    <div className="flex flex-col gap-0.5">
      <span className="text-[12px] text-sidebar-fg">{stock.stock_name}</span>
      <span className="text-[10px] text-sidebar-muted font-mono">{stock.stock_code}</span>
    </div>
    <button
      onClick={onToggle}
      disabled={isLoading}
      className={`text-[11px] px-2.5 py-1 rounded transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
        isAdded
          ? 'bg-positive-bar/15 text-positive-bar hover:bg-positive-bar/25'
          : 'bg-sidebar-hover text-sidebar-muted hover:text-sidebar-fg'
      }`}
    >
      {isLoading ? '…' : isAdded ? '✓ 추가됨' : '+ 추가'}
    </button>
  </div>
)

const ManagedStockChip = ({
  stock,
  isLoading,
  onDelete,
}: {
  stock: StockSummary
  isLoading: boolean
  onDelete: () => void
}) => (
  <div className="flex items-center gap-1 bg-sidebar-hover rounded-full px-2.5 py-1">
    <span className="text-[11px] text-sidebar-fg">{stock.stockName}</span>
    <button
      onClick={onDelete}
      disabled={isLoading}
      className="text-sidebar-muted hover:text-negative-bar transition-colors cursor-pointer text-[12px] leading-none"
      aria-label="삭제"
    >
      {isLoading ? '…' : '×'}
    </button>
  </div>
)

const SearchStatusMessage = ({
  text,
  tone = 'muted',
}: {
  text: string
  tone?: 'muted' | 'negative'
}) => (
  <p
    className={`px-2 py-4 text-center text-[12px] ${
      tone === 'negative' ? 'text-negative-bar' : 'text-sidebar-muted'
    }`}
  >
    {text}
  </p>
)

export const AddStockView = ({ stockList, onBack }: Props) => {
  const addMutation = useAddStock()
  const deleteMutation = useDeleteStock()
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const searchQuery = useStockSearch(submittedQuery)
  const results = searchQuery.data ?? null
  const isSearching = searchQuery.isFetching
  const searchError = searchQuery.isError

  const managedCodes = useMemo(
    () => new Set(stockList.map((s) => s.stockCode)),
    [stockList]
  )

  const isItemLoading = (stockCode: string) =>
    (addMutation.isPending && addMutation.variables?.stock_code === stockCode) ||
    (deleteMutation.isPending && deleteMutation.variables === stockCode)

  const actionError = addMutation.isError
    ? '종목 추가에 실패했어요'
    : deleteMutation.isError
    ? '종목 삭제에 실패했어요'
    : null

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSearch = () => {
    if (!query.trim() || isSearching) return
    setSubmittedQuery(query.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handleClear = () => {
    setQuery('')
    setSubmittedQuery('')
    inputRef.current?.focus()
  }

  const handleAdd = (stock: StockSearchResult) => addMutation.mutate(stock)
  const handleDelete = (stockCode: string) => deleteMutation.mutate(stockCode)

  return (
    <>
      {/* 헤더 */}
      <div className="p-4 border-b border-sidebar-hover flex items-center gap-2">
        <button
          onClick={onBack}
          className="text-sidebar-muted hover:text-sidebar-fg transition-colors cursor-pointer text-lg leading-none"
          aria-label="뒤로가기"
        >
          ←
        </button>
        <span className="text-[14px] font-medium text-sidebar-fg">종목 추가</span>
      </div>

      {/* 검색창 */}
      <div className="mx-3 mt-3">
        <div className="flex items-center gap-2 p-2 bg-sidebar-search rounded-md">
          <button
            onClick={handleSearch}
            className="shrink-0 text-sidebar-muted hover:text-sidebar-fg transition-colors cursor-pointer"
            aria-label="검색"
          >
            <SearchIcon className="w-3.5 h-3.5" />
          </button>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="종목명 입력 후 Enter"
            className="bg-transparent outline-none w-full text-sidebar-fg placeholder:text-sidebar-muted text-xs"
          />
          {query && (
            <button
              onClick={handleClear}
              className="shrink-0 text-sidebar-muted hover:text-sidebar-fg transition-colors cursor-pointer"
            >
              <ClearIcon className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <p className="mx-3 mt-2 text-[11px] text-negative-bar">{actionError}</p>
      )}

      <div className="flex-1 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {/* 검색 결과 */}
        {submittedQuery !== '' && (
          <>
            <p className="p-3 text-[10px] font-semibold text-sidebar-muted tracking-[0.8px]">
              검색 결과
            </p>
            <div className="flex flex-col gap-0.5 px-2">
              {isSearching && <SearchStatusMessage text="검색 중…" />}
              {!isSearching && searchError && (
                <SearchStatusMessage text="검색 중 오류가 발생했어요" tone="negative" />
              )}
              {!isSearching && !searchError && (results?.length ?? 0) === 0 && (
                <SearchStatusMessage text="결과가 없어요" />
              )}
              {!isSearching && !searchError && results?.map((stock) => {
                const isAdded = managedCodes.has(stock.stock_code)
                return (
                  <SearchResultRow
                    key={stock.stock_code}
                    stock={stock}
                    isAdded={isAdded}
                    isLoading={isItemLoading(stock.stock_code)}
                    onToggle={() => isAdded ? handleDelete(stock.stock_code) : handleAdd(stock)}
                  />
                )
              })}
            </div>
          </>
        )}

        {/* 관리 중인 종목 */}
        <p className="p-3 text-[10px] font-semibold text-sidebar-muted tracking-[0.8px]">
          관리 중인 종목 · {stockList.length}
        </p>
        <div className="flex flex-wrap gap-1.5 px-3 pb-3">
          {stockList.map((stock) => (
            <ManagedStockChip
              key={stock.stockCode}
              stock={stock}
              isLoading={isItemLoading(stock.stockCode)}
              onDelete={() => handleDelete(stock.stockCode)}
            />
          ))}
        </div>
      </div>
    </>
  )
}