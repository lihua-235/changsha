<script setup>
import { ref, computed, onMounted } from 'vue'
import { listAnchors } from '../data/provider.js'
import EmptyState from '../components/EmptyState.vue'

const anchors = ref([])
const loading = ref(true)
const filter = ref('all')

onMounted(async () => {
  anchors.value = await listAnchors()
  loading.value = false
})

const stats = computed(() => ({
  total: anchors.value.length,
  must: anchors.value.filter((a) => a.mustSee).length,
  schedulable: anchors.value.filter((a) => a.foodAvailable).length,
}))

const FILTERS = computed(() => [
  { key: 'all', label: '全部', count: stats.value.total },
  { key: 'must', label: '必去', count: stats.value.must },
  { key: 'schedulable', label: '可排程', count: stats.value.schedulable },
  { key: 'display', label: '仅展示', count: stats.value.total - stats.value.schedulable },
])

const shown = computed(() => {
  let list = anchors.value
  if (filter.value === 'must') list = list.filter((a) => a.mustSee)
  if (filter.value === 'schedulable') list = list.filter((a) => a.foodAvailable)
  if (filter.value === 'display') list = list.filter((a) => !a.foodAvailable)

  return [...list].sort((a, b) => {
    if (a.mustSee !== b.mustSee) return a.mustSee ? -1 : 1
    if (a.foodAvailable !== b.foodAvailable) return a.foodAvailable ? -1 : 1
    if ((a.district || '') !== (b.district || '')) {
      return String(a.district).localeCompare(String(b.district), 'zh')
    }
    return String(a.name).localeCompare(String(b.name), 'zh')
  })
})

function durationLabel(min) {
  if (min == null) return '时长未知'
  if (min < 60) return `${min} 分钟`
  const h = min / 60
  return Number.isInteger(h) ? `${h} 小时` : `${h.toFixed(1)} 小时`
}

function ticketLabel(cny) {
  if (cny == null) return '票价未知'
  return cny === 0 ? '免费' : `¥${cny}`
}

function hoursText(hint) {
  if (hint === 'breakfast') return '早餐'
  if (hint === 'lunch') return '午餐'
  if (hint === 'dinner') return '晚餐'
  return ''
}

function partText(part) {
  if (part === 'morning') return '上午'
  if (part === 'afternoon') return '下午'
  if (part === 'night') return '夜间'
  return ''
}

function amapUri(a) {
  const params = new URLSearchParams({
    position: `${a.lng},${a.lat}`,
    name: a.poiName || a.name,
    coordinate: 'gaode',
    callnative: '1',
  })
  return `https://uri.amap.com/marker?${params.toString()}`
}
</script>

<template>
  <h1>景点清单</h1>
  <p class="page-lead">
    这份清单是<strong>人工整理</strong>的 {{ stats.total }} 个锚点，不是从接口自动抓的。
    原因：高德把岳麓山拆成「飞来石」「翊武亭」等子景点，而湖南省博物馆这类
    <strong>根本不在</strong>我们的采集类目里。
  </p>
  <p class="page-lead note">
    其中标着「<strong>吃+逛</strong>」的是复合体（文和友、火宫殿）——它们既是景点，
    本身就是一顿饭，排程时不能再额外配餐。
  </p>

  <div v-if="loading" class="grid">
    <div v-for="i in 5" :key="i" class="skeleton" style="height: 108px" />
  </div>

  <EmptyState
    v-else-if="!anchors.length"
    icon="◌"
    title="还没有锚点数据"
    desc="先运行 python scripts/build_anchors.py 再运行 python scripts/export_web_data.py"
  />

  <template v-else>
    <div class="filters">
      <button
        v-for="f in FILTERS"
        :key="f.key"
        type="button"
        class="filter"
        :class="{ active: filter === f.key }"
        @click="filter = f.key"
      >
        {{ f.label }} <span class="n">{{ f.count }}</span>
      </button>
    </div>

    <div class="grid list">
      <article v-for="a in shown" :key="a.id" class="anchor">
        <header class="head">
          <h3 class="name">
            {{ a.name }}
            <span v-if="a.mustSee" class="chip must">必去</span>
          </h3>
          <span class="district">{{ a.district }}</span>
        </header>

        <div class="meta">
          <span v-if="a.kind === 'dining'" class="chip dining">
            吃+逛<span v-if="hoursText(a.mealHint)"> · 建议{{ hoursText(a.mealHint) }}</span>
          </span>
          <span class="chip">{{ durationLabel(a.durationMin) }}·估</span>
          <span class="chip">{{ ticketLabel(a.ticketCny) }}·估</span>
          <span v-if="a.dayPart" class="chip night">宜{{ partText(a.dayPart) }}</span>
          <span v-if="a.foodAvailable" class="chip badge-real">
            周边 {{ a.foodCount800m }} 家餐饮 · 可排程
          </span>
          <span v-else class="chip badge-pending">
            周边无餐饮数据 · 仅展示
          </span>
        </div>

        <p v-if="a.notice" class="notice">⚠ {{ a.notice }}</p>

        <p class="why">{{ a.why }}</p>

        <div class="foot">
          <a :href="amapUri(a)" target="_blank" rel="noopener" class="link">在高德地图中打开 →</a>
          <span v-if="a.opentimeWeek" class="hours">{{ a.opentimeWeek }}</span>
          <span v-else class="hours faint">营业时间未知</span>
        </div>
      </article>
    </div>

    <p class="disclaimer">
      标注「·估」的时长与票价是<strong>人工估计值</strong>，还没有实地核验（共 52 个数字）。
      这是本站唯一没有数据来源的部分，寒假会逐条核实。<br />
      「仅展示」的锚点在六个采集片区之外，周边没有餐饮数据，因此暂时无法排进自动行程。
    </p>
  </template>
</template>

<style scoped>
.filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.note {
  margin-top: -8px;
  font-size: 13px;
}
.filter {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  font-size: 13px;
  font-family: inherit;
  color: var(--ink-2);
  cursor: pointer;
}
.filter.active {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
  font-weight: 600;
}
.filter .n {
  font-size: 11px;
  opacity: 0.75;
  font-variant-numeric: tabular-nums;
}

.list {
  grid-template-columns: 1fr;
  gap: 10px;
}

.anchor {
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  padding: 13px 15px;
}
.anchor:hover {
  border-color: #d6d3d1;
  box-shadow: var(--shadow);
}

.head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.chip.must {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: #fed7aa;
  font-weight: 600;
}
.chip.dining {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
  font-weight: 600;
}
.chip.night {
  background: #eef2ff;
  color: #4338ca;
  border-color: #c7d2fe;
}
.district {
  margin-left: auto;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.notice {
  margin: 9px 0 0;
  padding: 6px 10px;
  border-radius: var(--r-sm);
  background: var(--warn-soft);
  color: var(--warn);
  font-size: 12px;
  line-height: 1.5;
}

.why {
  margin: 9px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--ink-2);
}

.foot {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px dashed var(--line);
}
.link {
  font-size: 12px;
  font-weight: 600;
}
.hours {
  font-size: 11px;
  color: var(--muted);
  margin-left: auto;
}
.hours.faint {
  color: var(--muted);
  opacity: 0.7;
}

.disclaimer {
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  line-height: 1.75;
  color: var(--muted);
}
</style>
