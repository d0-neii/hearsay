import { z } from 'zod'

// ===== Zod Schemas (백엔드 snake_case 응답 파싱 + camelCase 변환) =====

export const stockSummarySchema = z
  .object({
    stock_code: z.string(),
    stock_name: z.string(),
    total: z.number(),
    positive: z.number(),
    negative: z.number(),
    avg_score: z.number(),
    positive_ratio: z.number(),
  })
  .transform((raw) => ({
    stockCode: raw.stock_code,
    stockName: raw.stock_name,
    totalPostCount: raw.total,
    positivePostCount: raw.positive,
    negativePostCount: raw.negative,
    avgSentimentScore: raw.avg_score,
    positiveRatio: raw.positive_ratio,
  }))

export const postItemSchema = z
  .object({
    id: z.number(),
    title: z.string(),
    author: z.string(),
    views: z.number(),
    likes: z.number(),
    sentiment_score: z.number().nullable(),
    posted_at: z.string(),
  })
  .transform((raw) => ({
    id: raw.id,
    title: raw.title,
    author: raw.author,
    viewCount: raw.views,
    likeCount: raw.likes,
    sentimentScore: raw.sentiment_score,
    postedAt: raw.posted_at,
  }))

export const sentimentPointSchema = z
  .object({
    hour: z.string(),
    count: z.number(),
    avg_score: z.number(),
  })
  .transform((raw) => ({
    hour: raw.hour,
    postCount: raw.count,
    avgSentimentScore: raw.avg_score,
  }))

const askSourceSchema = z
  .object({
    id: z.number(),
    stock_name: z.string(),
    stock_code: z.string(),
    title: z.string(),
    posted_at: z.string(),
    distance: z.number(),
  })
  .transform((raw) => ({
    id: raw.id,
    stockName: raw.stock_name,
    stockCode: raw.stock_code,
    title: raw.title,
    postedAt: raw.posted_at,
    distance: raw.distance,
  }))

export const askResultSchema = z.object({
  answer: z.string(),
  sources: z.array(askSourceSchema),
})

// ===== 추론 타입 (스키마의 단일 소스) =====

export type StockSummary = z.infer<typeof stockSummarySchema>
export type PostItem = z.infer<typeof postItemSchema>
export type SentimentPoint = z.infer<typeof sentimentPointSchema>
export type AskResult = z.infer<typeof askResultSchema>
export type AskSource = z.infer<typeof askSourceSchema>
