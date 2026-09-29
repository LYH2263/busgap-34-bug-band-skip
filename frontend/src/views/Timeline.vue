<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel } from '../viewHints'
const data = ref<{ stop_name: string; marks: any[] }>({ stop_name: '', marks: [] })
onMounted(async () => { data.value = await api('/reports/timeline?line_id=1') })
function markColor(m: any) {
  if (m.status === 'deviation') return 'var(--bg-violet)'
  if (m.status === 'bunching') return 'var(--bg-red)'
  if (m.status === 'large_gap') return 'var(--bg-amber)'
  return 'var(--bg-cyan)'
}
function label(s: string) {
  return unifyStatusLabel(s)
}
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布（顶部已展示发车间隔轴）· 偏离班次不参与配对</p>
  <div class="card">
    <div class="tl-track">
      <div v-for="m in data.marks" :key="m.trip_no" class="tl-mark"
        :style="{ left: m.pct + '%', background: markColor(m) }"
        :title="m.trip_no + ' ' + m.actual_arrive + ' ' + label(m.status)" />
    </div>
    <table>
      <thead><tr><th>班次</th><th>到站时间</th><th>相对位置</th><th>状态</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td><td>{{ m.actual_arrive }}</td><td>{{ m.pct }}%</td>
          <td>
            <span class="badge" :class="m.status === 'bunching' ? 'badge-bad' : m.status === 'large_gap' ? 'badge-warn' : m.status === 'deviation' ? 'badge-deviate' : 'badge-ok'">{{ label(m.status) }}</span>
            <span v-if="!m.paired && m.status !== 'deviation'" class="muted"> 未配对</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
