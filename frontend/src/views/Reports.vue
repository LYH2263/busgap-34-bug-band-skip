<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, stripClass, badgeClass } from '../viewHints'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const loading = ref(false)
async function run() {
  loading.value = true
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } finally { loading.value = false }
}
onMounted(async () => {
  trips.value = await api('/trips')
  await run()
})
function label(s: string) {
  return unifyStatusLabel(s)
}
function hhmm(iso: string) {
  return typeof iso === 'string' && iso.length >= 16 ? iso.slice(11, 16) : iso
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">按实际到站间隔对照计划发车间隔 · 出带先标偏离（紫），偏离班不再参与串车 / 大间隔配对</p>
  <button class="btn" :disabled="loading" @click="run">重新检测</button>
  <div class="bg-split" style="margin-top:1rem">
    <aside class="bg-trip-col">
      <h2>关联班次</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">{{ r.vehicle_no }}</div>
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
          <span class="badge" :class="badgeClass(e.status)">{{ label(e.status) }}</span>
        </div>
        <div v-else class="bg-gap-body">
          <div class="bg-gap-val">{{ e.gap_min }}′</div>
          <div>计划 {{ e.planned_headway_min }}′</div>
          <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
          <span class="badge" :class="badgeClass(e.status)">{{ label(e.status) }}</span>
        </div>
      </article>
    </div>
  </div>
</template>
