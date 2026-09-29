// 报告 / 建议 / 时间轴 / 班次共用同一套状态文案与配色。
// 偏离（deviation）与串车（bunching）互斥：偏离班绝不再被标成串车。
export type EventStatus = 'bunching' | 'large_gap' | 'deviation' | 'normal'

export function unifyStatusLabel(status: string): string {
  if (status === 'bunching') return '串车'
  if (status === 'large_gap') return '大间隔'
  if (status === 'deviation') return '偏离'
  return '正常'
}

export function stripClass(status: string): string {
  if (status === 'bunching') return 'bg-bunch'
  if (status === 'large_gap') return 'bg-large'
  if (status === 'deviation') return 'bg-deviate'
  return ''
}

export function badgeClass(status: string): string {
  if (status === 'bunching') return 'badge-bad'
  if (status === 'large_gap') return 'badge-warn'
  if (status === 'deviation') return 'badge-deviate'
  return 'badge-ok'
}

export function markColor(status: string): string {
  if (status === 'bunching') return 'var(--bg-red)'
  if (status === 'large_gap') return 'var(--bg-amber)'
  if (status === 'deviation') return 'var(--bg-violet)'
  return 'var(--bg-cyan)'
}
