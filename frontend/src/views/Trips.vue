<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { badgeClass, stripClass, unifyStatusLabel } from '../viewHints'
const trips = ref<any[]>([])
const events = ref<any[]>([])
onMounted(async () => {
  trips.value = await api('/trips')
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } catch { events.value = [] }
})
function hhmm(iso: string) {
  return typeof iso === 'string' && iso.length >= 16 ? iso.slice(11, 16) : iso
}
</script>
<template>
  <h1>班次 · 间隔条带</h1>
  <p class="sub">左侧班次清单，右侧串车 / 大间隔 / 偏离竖直条带，与报告同一套参与集</p>
  <div class="bg-split">
    <aside class="bg-trip-col">
      <h2>班次列表</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">线路 {{ r.line_id }} · 车 {{ r.vehicle_no }}</div>
        </div>
        <div class="bg-trip-meta">{{ r.planned_depart }}</div>
      </div>
    </aside>
    <div class="bg-strip-col">
      <article
        v-for="(e, i) in events"
        :key="i"
        class="bg-gap-strip"
        :class="stripClass(e.status)"
      >
        <header>{{ e.stop_name }}</header>
        <div v-if="e.status === 'deviation'" class="bg-gap-body">
          <div class="bg-gap-val">{{ e.deviation_min }}′</div>
          <div>{{ e.trip_no }} 偏离{{ e.status_kind === 'early' ? '（早到）' : '（晚到）' }}</div>
          <div>计划 {{ hhmm(e.planned_arrive) }} · 实际 {{ hhmm(e.actual_arrive) }}</div>
          <span class="badge" :class="badgeClass(e.status)">{{ unifyStatusLabel(e.status) }}</span>
        </div>
        <div v-else class="bg-gap-body">
          <div class="bg-gap-val">{{ e.gap_min }}′</div>
          <div>计划 {{ e.planned_headway_min }}′</div>
          <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
          <span class="badge" :class="badgeClass(e.status)">{{ unifyStatusLabel(e.status) }}</span>
        </div>
      </article>
      <p v-if="!events.length" class="muted">暂无间隔事件</p>
    </div>
  </div>
</template>
