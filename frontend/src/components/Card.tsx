import type { HTMLAttributes } from 'react'

const PAD = {
  md: 'px-5 py-4', // 큰 카드 표준
  sm: 'px-4 py-3.5', // 조밀한 타일 (StatCard)
} as const

type Props = HTMLAttributes<HTMLDivElement> & {
  pad?: keyof typeof PAD
}

/** 카드 껍데기 단일 소스: bg + border + radius + 표준 패딩 */
export const Card = ({ pad = 'md', className = '', ...props }: Props) => (
  <div
    className={`bg-surface border border-border rounded-lg ${PAD[pad]} ${className}`}
    {...props}
  />
)
