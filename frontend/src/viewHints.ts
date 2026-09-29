// 状态文案：偏离、串车、大间隔各自独立，互不混标
export function unifyStatusLabel(status: string): string {
  if (status === 'deviation') return '偏离'
  if (status === 'bunching') return '串车'
  if (status === 'large_gap') return '大间隔'
  return '正常'
}
