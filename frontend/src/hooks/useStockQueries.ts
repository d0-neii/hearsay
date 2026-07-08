import { useQuery } from '@tanstack/react-query'
import { fetchStockList, fetchPostFeed, fetchSentimentChart, fetchDailySummary, searchStocks, fetchTradingData } from '../api/index'

const STALE_TIME = 1000 * 60 * 5 // 5분

export const useStockList = () => {
  return useQuery({
    queryKey: ['stockList'],
    queryFn: fetchStockList,
    staleTime: STALE_TIME,
  })
}

export const usePostFeed = (stockCode: string | undefined) => {
  return useQuery({
    queryKey: ['postFeed', stockCode],
    queryFn: () => fetchPostFeed(stockCode!),
    enabled: !!stockCode,
    staleTime: STALE_TIME,
  })
}

export const useSentimentChart = (stockCode: string | undefined) => {
  return useQuery({
    queryKey: ['sentimentChart', stockCode],
    queryFn: () => fetchSentimentChart(stockCode!),
    enabled: !!stockCode,
    staleTime: STALE_TIME,
  })
}

export const useDailySummary = (stockCode: string | undefined) => {
  return useQuery({
    queryKey: ['dailySummary', stockCode],
    queryFn: () => fetchDailySummary(stockCode!),
    enabled: !!stockCode,
    staleTime: STALE_TIME,
  })
}

export const useTradingData = (stockCode: string | undefined) => {
  return useQuery({
    queryKey: ['tradingData', stockCode],
    queryFn: () => fetchTradingData(stockCode!),
    enabled: !!stockCode,
    staleTime: 1000 * 60 * 30, // 30분 (장중 변동 반영 주기)
  })
}

export const useStockSearch = (query: string) => {
  return useQuery({
    queryKey: ['stockSearch', query],
    queryFn: () => searchStocks(query),
    enabled: query !== '',
  })
}
