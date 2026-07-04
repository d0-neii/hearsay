import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export interface Source {
  id: number
  stock_name: string
  stock_code: string
  title: string
  posted_at: string
  distance: number
}

export interface AskResponse {
  answer: string
  sources: Source[]
}

export const askQuestion = async (query: string, stockCode?: string): Promise<AskResponse> => {
  const { data } = await api.post<AskResponse>('/ask', {
    query,
    stock_code: stockCode ?? null,
  })
  return data
}
