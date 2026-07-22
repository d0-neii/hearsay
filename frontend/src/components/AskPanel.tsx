import { useState } from 'react'
import { Card } from './Card'

type ChatMessage = { question: string; answer: string }

type Props = {
  isAsking: boolean
  messages: ChatMessage[]
  onAskQuestion: (query: string) => void
}

const QUICK_QUERIES = ['오늘 왜 올랐어?', '실적 이후 반응은?', '지금 분위기 어때?']

export const AskPanel = ({ isAsking, messages, onAskQuestion }: Props) => {
  const [inputQuery, setInputQuery] = useState('')
  const [lastQuery, setLastQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputQuery.trim()) return
    setLastQuery(inputQuery)
    onAskQuestion(inputQuery)
    setInputQuery('')
  }

  const handleQuickQuery = (query: string) => {
    setLastQuery(query)
    onAskQuestion(query)
    setInputQuery('')
  }

  return (
    <Card>
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

      {(messages.length > 0 || isAsking) && (
        <div className="flex flex-col gap-3">
          {messages.map((msg, i) => (
            <div key={i} className="flex flex-col gap-1.5">
              <p className="text-[12px] text-muted font-medium">Q. {msg.question}</p>
              <div className="bg-base rounded-md px-4 py-3.5 border-l-[3px] border-l-primary">
                <p className="text-[13px] leading-[1.7] text-primary">{msg.answer}</p>
              </div>
            </div>
          ))}
          {isAsking && (
            <div className="flex flex-col gap-1.5">
              <p className="text-[12px] text-muted font-medium">Q. {lastQuery}</p>
              <div className="bg-base rounded-md px-4 py-3.5 border-l-[3px] border-l-primary opacity-50">
                <p className="text-[13px] text-muted">분석 중...</p>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
