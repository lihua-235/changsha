<script setup>
import { computed } from 'vue'
import { distanceMeters } from '../lib/itinerary.js'
import MealCard from './MealCard.vue'

const props = defineProps({
  day: { type: Object, required: true },
})

/** 每餐到下一餐的距离，挂在当前这餐下面显示 */
const legs = computed(() =>
  props.day.meals.map((_, i) => {
    if (i === 0) return null
    return distanceMeters(props.day.meals[i - 1].shop, props.day.meals[i].shop)
  })
)

const legTotal = computed(() => {
  if (props.day.legMeters) return props.day.legMeters
  return Math.round(legs.value.filter((x) => x != null).reduce((a, b) => a + b, 0))
})

const legLabel = computed(() => {
  const m = legTotal.value
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`
})

const dayCost = computed(() =>
  props.day.meals.reduce((sum, m) => sum + (m.cost ?? 0), 0)
)
</script>

<template>
  <section class="day">
    <header class="day-head">
      <div class="day-index">第 {{ day.dayIndex + 1 }} 天</div>
      <div class="day-district">{{ day.district }}</div>
      <div class="day-stats">
        <span>{{ day.meals.length }} 餐</span>
        <span>¥{{ dayCost }}</span>
        <span>餐间 {{ legLabel }}</span>
      </div>
    </header>

    <div v-if="day.meals.length" class="timeline">
      <MealCard
        v-for="(meal, i) in day.meals"
        :key="meal.shop.id"
        :meal="meal"
        :leg-meters="legs[i + 1] ?? null"
      />
    </div>

    <p v-else class="empty-day">这一天没有可安排的店</p>

    <ul v-if="day.notes.length" class="notes">
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
  padding: 14px 15px 6px;
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
}
</style>
