<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel } from '../viewHints'
const tips = ref<any[]>([])
onMounted(async () => { tips.value = (await api('/reports/suggestions?line_id=1')).suggestions })
function label(s: string) {
  return unifyStatusLabel(s)
}
</script>
<template>
  <h1>建议</h1>
  <p class="sub">针对串车、大间隔与偏离班次的调班提示</p>
  <div class="card" v-for="(t,i) in tips" :key="i">
    <div v-if="t.status === 'deviation'">
      <strong>{{ t.stop_name }}</strong> · {{ t.trip_no }} · 偏差 {{ t.deviation_min }} 分
      <span class="badge badge-deviate">{{ label(t.status) }}</span>
    </div>
    <div v-else><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分
      <span class="badge" :class="t.status === 'bunching' ? 'badge-bad' : 'badge-warn'">{{ label(t.status) }}</span>
    </div>
    <p class="muted">{{ t.suggestion }}</p>
  </div>
  <p v-if="!tips.length" class="muted">暂无异常建议</p>
</template>
