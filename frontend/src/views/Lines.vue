<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const saving = ref<number | null>(null)
const savedId = ref<number | null>(null)
onMounted(async () => { rows.value = await api('/lines') })
async function save(r: any) {
  saving.value = r.id
  try {
    const updated = await api(`/lines/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        early_tolerance_min: Number(r.early_tolerance_min) || 0,
        late_tolerance_min: Number(r.late_tolerance_min) || 0,
      }),
    })
    Object.assign(r, updated)
    savedId.value = r.id
    setTimeout(() => { if (savedId.value === r.id) savedId.value = null }, 2000)
  } finally { saving.value = null }
}
</script>
<template>
  <h1>线路</h1>
  <p class="sub">运营线路与串车 / 大间隔判定阈值 · 允许早到 / 晚到带宽可编辑保存，两带宽为 0 时只判间隔</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>计划间隔(分)</th><th>串车阈值</th><th>大间隔阈值</th><th>允许早到(分)</th><th>允许晚到(分)</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td>
          <td>{{ r.planned_headway_min }}</td><td>{{ r.bunch_threshold }}</td><td>{{ r.large_threshold }}</td>
          <td><input class="band-input" type="number" min="0" step="0.5" v-model.number="r.early_tolerance_min" /></td>
          <td><input class="band-input" type="number" min="0" step="0.5" v-model.number="r.late_tolerance_min" /></td>
          <td>
            <button class="btn" :disabled="saving === r.id" @click="save(r)">保存</button>
            <span v-if="savedId === r.id" class="muted"> 已保存</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
