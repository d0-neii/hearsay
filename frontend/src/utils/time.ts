const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

export const formatTimeAgo = (isoString: string, suffix = ''): string => {
  const diff = Date.now() - new Date(isoString).getTime()
  if (diff < MINUTE) return `방금${suffix}`
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)}분 전${suffix}`
  if (diff < DAY) return `${Math.floor(diff / HOUR)}시간 전${suffix}`
  return `${Math.floor(diff / DAY)}일 전${suffix}`
}
