import { useMutation, useQueryClient } from '@tanstack/react-query'
import { askQuestion, addStock, deleteStock } from '../api/index'

export const useAskQuestion = (stockCode: string | undefined) => {
  return useMutation({
    mutationFn: (query: string) => askQuestion(query, stockCode),
  })
}

export const useAddStock = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (stock: { stock_code: string; stock_name: string }) =>
      addStock(stock.stock_code, stock.stock_name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stockList'] }),
  })
}

export const useDeleteStock = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (stockCode: string) => deleteStock(stockCode),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stockList'] }),
  })
}
