import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { SentimentPoint } from '../types'
import { Card } from './Card'

type Props = {
  data: SentimentPoint[]
}

const formatHour = (hourStr: string) =>
  new Date(hourStr).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })

export const SentimentChart = ({ data }: Props) => {
  const chartData = data.map((point) => ({
    time: formatHour(point.hour),
    score: parseFloat((point.avgSentimentScore * 100).toFixed(1)),
    postCount: point.postCount,
  }))

  return (
    <Card>
      <p className="text-[11px] font-semibold text-muted mb-3 uppercase tracking-[0.5px]">시간대별 여론 추이</p>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 8 }}>
          <defs>
            <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-positive-bar)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--color-positive-bar)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: 'var(--color-chart-tick)' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--color-chart-tick)' }}
            tickLine={false}
            axisLine={false}
          />
          <ReferenceLine y={0} stroke="var(--color-chart-zero)" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              background: 'var(--color-chart-tooltip)',
              border: 'none',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: 'var(--color-chart-tick)' }}
            formatter={(value) => [`${Number(value) > 0 ? '+' : ''}${value}`, '여론 점수']}
          />
          <Area
            type="linear"
            dataKey="score"
            stroke="var(--color-positive-bar)"
            strokeWidth={2}
            fill="url(#sentimentGradient)"
            baseValue="dataMin"
            dot={false}
            activeDot={{ r: 4, fill: 'var(--color-positive-bar)' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  )
}
