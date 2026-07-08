import type { StockSummary, TradingData } from '../types'

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
  compute: (stock: StockSummary, tradingData: TradingData | undefined) => CardValue
}

/** 개인/기관/외국인 순매수 방향을 한 줄 텍스트로 요약 */
const buildTradingSubText = (detail: Record<string, number> | null): string | undefined =>
  detail
    ? Object.entries(detail)
        .map(([investor, net]) => `${investor.replace('합계', '')}${net > 0 ? '↑' : '↓'}`)
        .join('  ')
    : undefined

const STAT_CARD_DEFINITIONS: CardDefinition[] = [
  {
    label: '수급',
    compute: (_stock, tradingData) => {
      // KRX 실제 거래 데이터가 있으면 사용
      if (tradingData?.buyRatio != null) {
        const isSell = tradingData.buyRatio < 50
        const ratio = isSell ? tradingData.sellRatio! : tradingData.buyRatio
        return {
          value: `${isSell ? '매도' : '매수'} ${ratio}%`,
          valueClassName: isSell ? 'text-negative' : 'text-positive',
          sub: buildTradingSubText(tradingData.detail),
          subClassName: 'text-muted',
        }
      }

      // 데이터 없음 (장외시간 or pykrx 오류)
      return {
        value: '—',
        sub: '장 마감 후 제공',
        subClassName: 'text-muted',
      }
    },
  },
  {
    label: '여론',
    compute: (stock) => {
      // 커뮤니티 감성 비율 (긍정 게시글 비율)
      const ratio = Math.round(stock.todayPositiveRatio ?? stock.positiveRatio)
      const isMaedo = ratio < 50
      const displayRatio = isMaedo ? 100 - ratio : ratio
      return {
        value: `${isMaedo ? '부정' : '긍정'} ${displayRatio}%`,
        valueClassName: isMaedo ? 'text-negative' : 'text-positive',
        sub: '커뮤니티 감성',
        subClassName: 'text-muted',
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
]

type StatCardsProps = {
  stock: StockSummary
  tradingData: TradingData | undefined
}

export const StatCards = ({ stock, tradingData }: StatCardsProps) => (
  <div className="grid grid-cols-4 gap-3">
    {STAT_CARD_DEFINITIONS.map(({ label, compute }) => (
      <StatCard key={label} label={label} {...compute(stock, tradingData)} />
    ))}
  </div>
)
