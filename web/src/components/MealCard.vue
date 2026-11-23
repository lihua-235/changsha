<script setup>
import { computed } from 'vue'

const props = defineProps({
  meal: { type: Object, required: true },
  legMeters: { type: Number, default: null },
})

const shop = computed(() => props.meal.shop ?? null)
/** 吃+逛复合体占掉的餐次：没有具体店铺，这一餐就是那个景点 */
const diningAnchor = computed(() =>
  props.meal.fromAnchor ? props.meal.anchor ?? null : null
)

const title = computed(() => shop.value?.name ?? diningAnchor.value?.name ?? '—')

const priceLabel = computed(() => {
  if (props.meal.cost == null) return diningAnchor.value ? '人均见景点说明' : '价格未知'
  return `¥${props.meal.cost}`
})

const distLabel = computed(() => {
  const m = shop.value?.distToWuyiM
  if (m == null) return null
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`
})

const legLabel = computed(() => {
  if (props.legMeters == null) return null
  return props.legMeters >= 1000
    ? `${(props.legMeters / 1000).toFixed(1)} km`
    : `${Math.round(props.legMeters)} m`
})
</script>

<template>
  <div class="meal">
    <div class="slot">{{ meal.slotLabel }}</div>

    <div class="body">
      <RouterLink v-if="shop" :to="`/shop/${shop.slug}/${shop.id}`" class="name">
        {{ title }}
      </RouterLink>
      <span v-else class="name name-static">{{ title }}</span>

      <div class="meta">
        <span v-if="diningAnchor" class="chip dining">吃+逛 · 不另配餐</span>
        <span class="cost" :class="{ faint: meal.cost == null }">{{ priceLabel }}</span>
        <span v-if="meal.dishGroup && meal.dishGroup !== 'dining'" class="chip">
          {{ meal.dishGroup }}
        </span>
        <span v-if="distLabel" class="chip">距核心区 {{ distLabel }}</span>
        <span v-if="shop?.isChain" class="chip">连锁</span>
      </div>

      <div v-if="meal.estimatedCost || !meal.hoursKnown || meal.relaxed" class="flags">
        <span v-if="meal.estimatedCost" class="chip badge-pending">价格为片区估算</span>
        <span v-if="!meal.hoursKnown" class="chip badge-pending">营业时间未知</span>
        <span v-if="meal.relaxed" class="chip badge-pending">该价位无可选，已放宽</span>
      </div>
    </div>

    <div v-if="legLabel" class="leg">↓ {{ legLabel }}</div>
  </div>
</template>

<style scoped>
.meal {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 10px;
  position: relative;
  padding-bottom: 4px;
}

.slot {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  padding-top: 3px;
  text-align: right;
}

.body {
  border-left: 2px solid var(--line);
  padding: 0 0 12px 14px;
  position: relative;
}
.body::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--accent);
}

.name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}
.name:hover {
  color: var(--accent);
}
.name-static {
  color: var(--ink);
}
.chip.dining {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
  font-weight: 600;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
}

.cost {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.cost.faint {
  font-size: 13px;
  font-weight: 400;
  color: var(--muted);
}

.flags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 6px;
}

.leg {
  grid-column: 2;
  font-size: 11px;
  color: var(--muted);
  padding: 0 0 8px 14px;
  margin-top: -8px;
}
</style>
