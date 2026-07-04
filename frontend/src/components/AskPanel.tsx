import { useState } from 'react'
import type { AskResult } from '../types'

type Props = {
  isAsking: boolean
  askResult: AskResult | undefined
  onAskQuestion: (query: string) => void
}

const QUICK_QUERIES = ['오늘 왜 올랐어?', '실적 이후 반응은?', '지금 분위기 어때?']

export const AskPanel = ({ isAsking, askResult, onAskQuestion }: Props) => {
  const [inputQuery, setInputQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputQuery.trim()) return
    onAskQuestion(inputQuery)
  }

  const handleQuickQuery = (query: string) => {
    setInputQuery(query)
    onAskQuestion(query)
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <p className="text-[13px] font-semibold text-primary mb-3.5">✦ 커뮤니티에 물어보기</p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {QUICK_QUERIES.map((query) => (
          <button
            key={query}
            className="px-2.5 py-1.5 bg-base border border-border rounded-[20px] text-xs text-secondary cursor-pointer transition-colors duration-150 hover:bg-base-hover hover:border-border-strong hover:text-primary"
            onClick={() => handleQuickQuery(query)}
          >
            {query} ↗
          </button>
        ))}
      </div>

      <form className="flex gap-2 mb-4" onSubmit={handleSubmit}>
        <input
          type="text"
          className="flex-1 p-3 bg-base border border-border rounded-md text-[13px] text-primary outline-none transition-colors focus:border-border-focus"
          placeholder="커뮤니티 여론을 물어보세요..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2.5 bg-primary text-white rounded-md text-xs font-semibold cursor-pointer transition-opacity duration-150 disabled:opacity-40 disabled:cursor-not-allowed enabled:hover:opacity-80"
          disabled={isAsking || !inputQuery.trim()}
        >
          {isAsking ? '분석 중...' : '질문'}
        </button>
      </form>

      {askResult && (
        <div className="bg-base rounded-md px-4 py-3.5 border-l-[3px] border-l-primary">
          <p className="text-[13px] leading-[1.7] text-primary">{askResult.answer}</p>
        </div>
      )}
    </div>
  )
}
