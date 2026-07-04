import { useMutation } from '@tanstack/react-query'
import { askQuestion } from '../api/index'

export const useAskQuestion = (stockCode: string | undefined) => {
  return useMutation({
    mutationFn: (query: string) => askQuestion(query, stockCode),
  })
}
