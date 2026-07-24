import { useState } from 'react'
import type { PostItem } from '../types'
import { classifySentiment, SENTIMENT_LABEL_KO } from '../utils/sentiment'
import { formatTimeAgo } from '../utils/time'

type Props = {
  postFeed: PostItem[]
  isLoading?: boolean
}

const SentimentBadge = ({ sentimentScore }: { sentimentScore: number | null }) => {
  const label = classifySentiment(sentimentScore)
  const styleMap = {
    positive: 'bg-positive-bg text-positive',
    negative: 'bg-negative-bg text-negative',
    neutral: 'bg-neutral-bg text-muted',
  }
  return (
    <span className={`text-[10px] font-semibold px-[7px] py-[2px] rounded-[10px] ${styleMap[label]}`}>
      {SENTIMENT_LABEL_KO[label]}
    </span>
  )
}

const PostCard = ({ post }: { post: PostItem }) => {
  const [expanded, setExpanded] = useState(false)
  const hasContent = !!post.content

  return (
    <div
      className={`px-4 py-3 border-b border-border-light transition-colors duration-[120ms] ${hasContent ? 'cursor-pointer hover:bg-surface-hover' : ''}`}
      onClick={() => hasContent && setExpanded((prev) => !prev)}
    >
      <div className="flex items-center justify-between mb-1.5">
        <SentimentBadge sentimentScore={post.sentimentScore} />
        <span className="text-[11px] text-muted">{formatTimeAgo(post.postedAt)}</span>
      </div>

      <p className={`text-xs text-primary leading-[1.5] ${expanded ? '' : 'line-clamp-2'}`}>
        {post.title}
      </p>

      {expanded && post.content && (
        <p className="mt-2 text-[11px] text-secondary leading-[1.6] line-clamp-6 whitespace-pre-line">
          {post.content}
        </p>
      )}

      <div className="flex items-center gap-2.5 mt-1.5">
        <span className="text-[10px] text-muted">조회 {post.viewCount.toLocaleString()}</span>
        {post.likeCount > 0 && (
          <span className="text-[10px] text-muted">👍 {post.likeCount}</span>
        )}
        {hasContent && (
          <span className="text-[10px] text-muted ml-auto">{expanded ? '접기 ↑' : '본문 보기 ↓'}</span>
        )}
      </div>
    </div>
  )
}

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center h-full gap-2 pb-8">
    <span className="text-2xl">🔍</span>
    <p className="text-[12px] text-muted text-center leading-relaxed">
      아직 수집된 게시글이 없어요
    </p>
  </div>
)

export const PostFeed = ({ postFeed, isLoading = false }: Props) => {
  return (
    <aside className="bg-surface border-l border-border flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 p-4 border-b border-border-light">
        <span className="w-[7px] h-[7px] bg-positive-bar rounded-full animate-blink" />
        <span className="text-xs font-semibold text-secondary tracking-[0.5px]">실시간 게시글</span>
      </div>
      <div className="flex-1 overflow-y-auto [scrollbar-width:thin] [scrollbar-color:var(--color-border)_transparent]">
        {isLoading ? (
          <p className="py-10 text-center text-[12px] text-muted">불러오는 중...</p>
        ) : postFeed.length === 0 ? (
          <EmptyState />
        ) : (
          postFeed.map((post) => (
            <PostCard key={post.id} post={post} />
          ))
        )}
      </div>
    </aside>
  )
}
