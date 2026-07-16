import type { DailySummary as DailySummaryData } from '../types'
import { formatTimeAgo } from '../utils/time'
import { Card } from './Card'

type Props = {
  data: DailySummaryData | undefined
  isLoading: boolean
}

type TagType = DailySummaryData['items'][number]['type']

const TAG_STYLE_MAP: Record<TagType, string> = {
  이슈: 'bg-neutral-bg text-muted',
  호재: 'bg-positive-bg text-positive',
  악재: 'bg-negative-bg text-negative',
}

const Badge = ({ type }: { type: TagType }) => (
  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 mt-0.5 ${TAG_STYLE_MAP[type]}`}>
    {type}
  </span>
)

const Skeleton = () => (
  <Card className="flex flex-col gap-3 animate-pulse">
    <div className="flex items-center justify-between">
      <div className="h-3.5 w-24 bg-positive-bg rounded" />
      <div className="h-3 w-16 bg-positive-bg rounded" />
    </div>
    <div className="flex flex-col gap-2.5">
      {[80, 65, 45].map((w, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="h-4 w-8 bg-positive-bg rounded shrink-0" />
          <div className="h-3 bg-positive-bg rounded" style={{ width: `${w}%` }} />
        </div>
      ))}
    </div>
  </Card>
)

export const DailySummary = ({ data, isLoading }: Props) => {
  if (isLoading) return <Skeleton />
  if (!data || !data.items.length) return null

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-positive flex items-center gap-1.5">
          ✦ 오늘의 요약
        </span>
        <span className="text-[11px] text-muted">{formatTimeAgo(data.generated_at, ' 갱신')}</span>
      </div>

      <div className="flex flex-col gap-2">
        {data.items.map((item, i) => (
          <div key={i} className="flex items-start gap-3">
            <Badge type={item.type} />
            <span className="text-[13px] text-primary leading-snug">{item.text}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}
