import axios from 'axios'
import { z } from 'zod'
import {
  stockSummarySchema,
  postItemSchema,
  sentimentPointSchema,
  askResultSchema,
  dailySummarySchema,
  tradingDataSchema,
} from '../types'
import type { StockSummary, PostItem, SentimentPoint, AskResult, DailySummary, TradingData } from '../types'

// 로컬 개발에서는 값을 비워두고 vite dev server의 proxy(/api → localhost:8000)를
// 그대로 쓴다. 배포본에는 proxy가 존재하지 않으므로 VITE_API_BASE_URL에
// 백엔드 주소(예: https://api.example.com)를 넣어야 요청이 나간다.
const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

export const fetchStockList = async (): Promise<StockSummary[]> => {
  const { data } = await httpClient.get('/stocks')
  return z.array(stockSummarySchema).parse(data)
}

export const fetchPostFeed = async (stockCode: string): Promise<PostItem[]> => {
  const { data } = await httpClient.get(`/stocks/${stockCode}/posts`)
  return z.array(postItemSchema).parse(data)
}

export const fetchSentimentChart = async (stockCode: string): Promise<SentimentPoint[]> => {
  const { data } = await httpClient.get(`/stocks/${stockCode}/timeseries`)
  return z.array(sentimentPointSchema).parse(data)
}

export const fetchDailySummary = async (stockCode: string): Promise<DailySummary> => {
  const { data } = await httpClient.get(`/stocks/${stockCode}/daily-summary`)
  return dailySummarySchema.parse(data)
}

export type StockSearchResult = { stock_code: string; stock_name: string }

export const searchStocks = async (q: string): Promise<StockSearchResult[]> => {
  const { data } = await httpClient.get('/stocks/search', { params: { q } })
  return data
}

export const addStock = async (stock_code: string, stock_name: string): Promise<void> => {
  await httpClient.post('/stocks/manage', { stock_code, stock_name })
}

export const deleteStock = async (stock_code: string): Promise<void> => {
  await httpClient.delete(`/stocks/manage/${stock_code}`)
}

export const fetchTradingData = async (stockCode: string): Promise<TradingData> => {
  const { data } = await httpClient.get(`/stocks/${stockCode}/trading`)
  return tradingDataSchema.parse(data)
}

export const askQuestion = async (query: string, stockCode?: string): Promise<AskResult> => {
  const { data } = await httpClient.post('/ask', {
    query,
    stock_code: stockCode ?? null,
  })
  return askResultSchema.parse(data)
}
