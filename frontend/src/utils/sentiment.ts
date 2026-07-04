export type SentimentLabel = 'positive' | 'negative' | 'neutral'

const POSITIVE_THRESHOLD = 0.1
const NEGATIVE_THRESHOLD = -0.1

export const classifySentiment = (score: number | null): SentimentLabel => {
  if (score === null) return 'neutral'
  if (score > POSITIVE_THRESHOLD) return 'positive'
  if (score < NEGATIVE_THRESHOLD) return 'negative'
  return 'neutral'
}

export const SENTIMENT_LABEL_KO: Record<SentimentLabel, string> = {
  positive: '긍정',
  negative: '부정',
  neutral: '중립',
}
