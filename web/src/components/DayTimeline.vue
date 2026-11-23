<script setup>
import { computed } from 'vue'
import { distanceMeters } from '../lib/itinerary.js'
import MealCard from './MealCard.vue'

const props = defineProps({
  day: { type: Object, required: true },
})

const PART_LABEL = { morning: '上午', afternoon: '下午', night: '夜间' }

function durationLabel(min) {
  if (min == null) return ''
  if (min < 60) return `${min} 分钟`
  const h = min / 60
  return Number.isInteger(h) ? `${h} 小时` : `${h.toFixed(1)} 小时`
}

/**
 * 把当天的锚点和餐次按时间顺序摊平：
 *   早餐 → 上午锚点 → 午餐 → 下午锚点 → 晚餐 → 夜间锚点
 * 之前的版本把锚点和餐分成两段显示，看的人无法判断先后。
 */
const stops = computed(() => {
  const day = props.day
  const out = []
  const anchorOf = (part) => (day.anchors ?? []).find((a) => a.part === part)?.anchor
  const mealOf = (slot) => (day.meals ?? []).find((m) => m.slot === slot)

  const pushMeal = (slot) => {
    const m = mealOf(slot)
    if (!m) return
    const p = m.shop ?? m.anchor
    out.push({ kind: 'meal', key: `m-${slot}`, meal: m, point: p })
  }
  const pushAnchor = (part) => {
    const a = anchorOf(part)
    if (!a) return
    out.push({ kind: 'anchor', key: `a-${part}`, part, anchor: a, point: a })
  }

  pushMeal('breakfast')
  pushAnchor('morning')
  pushMeal('lunch')
  pushAnchor('afternoon')
  pushMeal('dinner')
  pushAnchor('night')
  return out
})

/** 相邻两个站点之间的距离 */
const legs = computed(() =>
  stops.value.map((s, i) => {
    if (i === 0) return null
    const prev = stops.value[i - 1].point
    if (!prev || !s.point) return null
    return distanceMeters(prev, s.point)
  })
)

function legText(m) {
  if (m == null) return ''
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`
}

const legTotal = computed(() => {
  if (props.day.legMeters) return props.day.legMeters
  return Math.round(legs.value.filter((x) => x != null).reduce((a, b) => a + b, 0))
})

const legLabel = computed(() => {
  const m = legTotal.value
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`
})

const dayCost = computed(() =>
  (props.day.meals ?? []).reduce((sum, m) => sum + (m.shop?.cost ?? 0), 0)
)

const anchorCount = computed(() => (props.day.anchors ?? []).length)
</script>

<template>
  <section class="day">
    <header class="day-head">
      <div class="day-index">第 {{ day.dayIndex + 1 }} 天</div>
      <div class="day-district">{{ day.district || '—' }}</div>
      <div class="day-stats">
        <span v-if="anchorCount">{{ anchorCount }} 个景点</span>
        <span>¥{{ Math.round(dayCost) }}</span>
        <span>移动 {{ legLabel }}</span>
      </div>
    </header>

    <div v-if="stops.length" class="timeline">
      <template v-for="(s, i) in stops" :key="s.key">
        <div v-if="i > 0 && legs[i] != null" class="leg">↓ {{ legText(legs[i]) }}</div>

        <div v-if="s.kind === 'anchor'" class="anchor-stop">
          <div class="stop-part">{{ PART_LABEL[s.part] }}</div>
          <div class="anchor-body">
            <div class="anchor-title">
              <span class="anchor-name">{{ s.anchor.name }}</span>
              <span v-if="s.anchor.kind === 'dining'" class="chip dining">吃+逛</span>
            </div>
            <div class="anchor-meta">
              <span v-if="durationLabel(s.anchor.durationMin)">
                游览 {{ durationLabel(s.anchor.durationMin) }}
              </span>
              <span v-if="s.anchor.ticketCny != null">
                {{ s.anchor.ticketCny ? `门票 ¥${s.anchor.ticketCny}` : '免费' }}·估
              </span>
              <span v-if="s.anchor.district" class="faint">{{ s.anchor.district }}</span>
            </div>
            <p v-if="s.anchor.why" class="anchor-why">{{ s.anchor.why }}</p>
            <p v-if="s.anchor.notice" class="anchor-notice">⚠ {{ s.anchor.notice }}</p>
          </div>
        </div>

        <MealCard v-else :meal="s.meal" />
      </template>
    </div>

    <p v-else class="empty-day">这一天没有可安排的内容</p>

    <ul v-if="day.notes && day.notes.length" class="notes">
      <li v-for="(n, i) in day.notes" :key="i">{{ n }}</li>
    </ul>
  </section>
</template>

<style scoped>
.day {
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  overflow: hidden;
}

.day-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 12px 15px;
  background: var(--bg-soft);
  border-bottom: 1px solid var(--line);
}
.day-index {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.day-district {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.day-stats {
  margin-left: auto;
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.timeline {
  padding: 12px 15px 10px;
}

/* ---------------- 景点锚点 ---------------- */

.anchor-stop {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 10px;
  padding: 2px 0 6px;
}
.stop-part {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  padding-top: 3px;
  text-align: right;
}
.anchor-body {
  border-left: 2px solid var(--accent);
  padding: 0 0 8px 14px;
  position: relative;
}
.anchor-body::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 5px;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: var(--accent);
}
.anchor-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.anchor-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}
.chip.dining {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
  font-weight: 600;
}
.anchor-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
.anchor-meta .faint {
  color: var(--muted);
}
.anchor-why {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-2);
}
.anchor-notice {
  margin: 5px 0 0;
  font-size: 11px;
  color: var(--warn);
}

/* ---------------- 站间距离 ---------------- */

.leg {
  font-size: 11px;
  color: var(--muted);
  padding: 0 0 4px 54px;
}

.empty-day {
  padding: 20px 15px;
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.notes {
  margin: 0;
  padding: 10px 15px 14px 32px;
  border-top: 1px dashed var(--line);
  font-size: 12px;
  color: var(--ink-2);
  line-height: 1.6;
}
.notes li {
  margin-bottom: 3px;
}

@media (max-width: 420px) {
  .day-stats {
    gap: 7px;
    font-size: 10px;
  }
  .leg {
    padding-left: 54px;
  }
}
</style>
