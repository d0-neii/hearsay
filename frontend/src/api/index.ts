import axios from 'axios'
import { z } from 'zod'
import {
  stockSummarySchema,
  postItemSchema,
  sentimentPointSchema,
  askResultSchema,
} from '../types'
import type { StockSummary, PostItem, SentimentPoint, AskResult } from '../types'

const httpClient = axios.create({ baseURL: '/api' })

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

export const askQuestion = async (query: string, stockCode?: string): Promise<AskResult> => {
  const { data } = await httpClient.post('/ask', {
    query,
    stock_code: stockCode ?? null,
  })
  return askResultSchema.parse(data)
}
