import type { StockSummary, AskResult } from '../types'

type Props = {
  label: string
  value: React.ReactNode
  valueClassName?: string
  sub?: string
  subClassName?: string
}

export const StatCard = ({
  label,
  value,
  valueClassName = 'text-primary',
  sub,
  subClassName = 'text-muted',
}: Props) => (
  <div className="bg-surface border border-border rounded-lg px-4 py-3.5 flex flex-col gap-2 min-w-0">
    <span className="text-[10px] font-semibold text-muted tracking-[0.6px]">
      {label}
    </span>
    <span className={`text-[20px] font-bold leading-none truncate ${valueClassName}`}>
      {value}
    </span>
    {sub && (
      <span className={`text-[11px] leading-none ${subClassName}`}>
        {sub}
      </span>
    )}
  </div>
)

type CardValue = Omit<Props, 'label'>

type CardDefinition = {
  label: string
  compute: (stock: StockSummary, askResult: AskResult | undefined) => CardValue
}

// 매도면 비율을 뒤집어서 "매도 비율"로 표시 (예: 긍정 30% → 매도 70%)
const toDisplayRatio = (ratio: number, isMaedo: boolean) => Math.round(isMaedo ? 100 - ratio : ratio)

const STAT_CARD_DEFINITIONS: CardDefinition[] = [
  {
    label: '여론',
    compute: (stock) => {
      const todayRatio = stock.todayPositiveRatio ?? stock.positiveRatio
      const isMaedo = todayRatio < 50
      const displayRatio = toDisplayRatio(todayRatio, isMaedo)

      const delta =
        stock.prevPositiveRatio !== null
          ? displayRatio - toDisplayRatio(stock.prevPositiveRatio, isMaedo)
          : null
      const deltaText = delta !== null ? `어제 대비 ${delta >= 0 ? '+' : ''}${delta}%` : undefined

      // 매도면 delta<0, 매수면 delta>0일 때가 좋은 신호(초록)
      const isGoodDelta = delta !== null && (isMaedo ? delta < 0 : delta > 0)
      const deltaColor = !delta ? 'text-muted' : isGoodDelta ? 'text-positive' : 'text-negative'

      return {
        value: `${isMaedo ? '매도' : '매수'} ${displayRatio}%`,
        valueClassName: isMaedo ? 'text-negative' : 'text-positive',
        sub: deltaText,
        subClassName: deltaColor,
      }
    },
  },
  {
    label: '오늘 언급량',
    compute: (stock) => ({
      value: stock.todayTotalCount !== null ? `${stock.todayTotalCount}개` : '—',
      sub: stock.postCountRatio !== null ? `평소 대비 ${stock.postCountRatio}배` : undefined,
    }),
  },
  {
    label: '핫 키워드',
    compute: (stock) => ({
      value: stock.hotKeyword ?? '—',
    }),
  },
  {
    label: '분석 근거',
    compute: (_stock, askResult) => {
      const sourceCount = askResult?.sources.length
      return {
        value: sourceCount !== undefined ? `${sourceCount}개` : '—',
        sub: sourceCount !== undefined ? '참고 게시글' : '질문 후 표시',
      }
    },
  },
]

type StatCardsProps = {
  stock: StockSummary
  askResult: AskResult | undefined
}

export const StatCards = ({ stock, askResult }: StatCardsProps) => (
  <div className="grid grid-cols-4 gap-3">
    {STAT_CARD_DEFINITIONS.map(({ label, compute }) => (
      <StatCard key={label} label={label} {...compute(stock, askResult)} />
    ))}
  </div>
)
