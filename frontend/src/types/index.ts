import { z } from 'zod'

// ===== Zod Schemas (백엔드 snake_case 응답 파싱 + camelCase 변환) =====

export const stockSummarySchema = z
  .object({
    stock_code: z.string(),
    stock_name: z.string(),
    total: z.number(),
    avg_score: z.number(),
    positive_ratio: z.number(),
    // 카드용 신규 필드 — optional: 백엔드 미배포 시에도 파싱 오류 없이 graceful degradation
    today_total: z.number().optional(),
    today_positive_ratio: z.number().nullable().optional(),
    post_count_ratio: z.number().nullable().optional(),
    hot_keyword: z.string().nullable().optional(),
  })
  .transform((raw) => ({
    stockCode: raw.stock_code,
    stockName: raw.stock_name,
    totalPostCount: raw.total,
    avgSentimentScore: raw.avg_score,
    positiveRatio: raw.positive_ratio,
    // 카드용 신규 필드
    todayTotalCount: raw.today_total ?? null,
    todayPositiveRatio: raw.today_positive_ratio ?? null,
    postCountRatio: raw.post_count_ratio ?? null,
    hotKeyword: raw.hot_keyword ?? null,
  }))

export const postItemSchema = z
  .object({
    id: z.number(),
    title: z.string(),
    content: z.string().nullable().optional(),
    author: z.string(),
    views: z.number(),
    likes: z.number(),
    sentiment_score: z.number().nullable(),
    posted_at: z.string(),
  })
  .transform((raw) => ({
    id: raw.id,
    title: raw.title,
    content: raw.content ?? null,
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

export const askResultSchema = z.object({
  answer: z.string(),
})

export const dailySummarySchema = z.object({
  items: z.array(z.object({
    type: z.enum(['이슈', '호재', '악재']),
    text: z.string(),
  })),
  generated_at: z.string(),
})

// ===== 추론 타입 (스키마의 단일 소스) =====

export type StockSummary = z.infer<typeof stockSummarySchema>
export type PostItem = z.infer<typeof postItemSchema>
export type SentimentPoint = z.infer<typeof sentimentPointSchema>
export type AskResult = z.infer<typeof askResultSchema>
export type DailySummary = z.infer<typeof dailySummarySchema>

// ===== 실제 매수/매도 거래 비율 (KRX 투자자별 데이터) =====

export const tradingDataSchema = z
  .object({
    buy_ratio: z.number().nullable(),
    sell_ratio: z.number().nullable(),
    detail: z.record(z.string(), z.number()).nullable().optional(),
  })
  .transform((raw) => ({
    buyRatio: raw.buy_ratio,
    sellRatio: raw.sell_ratio,
    detail: raw.detail ?? null,  // 예: { "개인": 1200000000, "기관합계": -800000000 }
  }))

export type TradingData = z.infer<typeof tradingDataSchema>
