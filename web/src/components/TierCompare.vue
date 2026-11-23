<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** [{ tier, it }]，it 是 buildItinerary 的返回 */
  built: { type: Array, required: true },
  modelValue: { type: Number, required: true },
})
defineEmits(['update:modelValue'])

const maxCost = computed(() => Math.max(...props.built.map((b) => b.it.summary.totalCost), 1))

function pct(v) {
  return `${Math.round((v / maxCost.value) * 100)}%`
}
</script>

<template>
  <div class="compare" role="radiogroup" aria-label="预算档位对比">
    <button
      v-for="row in built"
      :key="row.tier.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === row.tier.value"
      class="col"
      :class="{ active: modelValue === row.tier.value }"
      @click="$emit('update:modelValue', row.tier.value)"
    >
      <div class="col-head">
        <span class="col-label">{{ row.tier.label }}</span>
        <span class="col-sub">{{ row.tier.headline }}</span>
      </div>

      <div class="col-cost">
        <b>¥{{ row.it.summary.totalCost }}</b>
        <span>总计</span>
      </div>

      <div class="bar" aria-hidden="true">
        <div class="bar-fill" :style="{ width: pct(row.it.summary.totalCost) }" />
      </div>

      <dl class="col-stats">
        <dt>人均每餐</dt>
        <dd>¥{{ row.it.summary.avgPerMeal }}</dd>
        <dt>菜品类型</dt>
        <dd>{{ row.it.summary.dishTypeCount }}</dd>
        <dt>连锁占比</dt>
        <dd>{{ row.it.summary.chainRate }}%</dd>
        <dt>餐间距离</dt>
        <dd>
          {{ row.it.summary.totalLegMeters >= 1000
            ? (row.it.summary.totalLegMeters / 1000).toFixed(1) + ' km'
            : row.it.summary.totalLegMeters + ' m' }}
        </dd>
      </dl>
    </button>
  </div>
</template>

<style scoped>
.compare {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 12px 14px;
  border: 1.5px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.col:hover {
  border-color: #d6d3d1;
}
.col.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.col-head {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.col-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
.col.active .col-label {
  color: var(--accent);
}
.col-sub {
  font-size: 11px;
  color: var(--muted);
}

.col-cost {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.col-cost b {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.col-cost span {
  font-size: 10px;
  color: var(--muted);
}

.bar {
  height: 4px;
  border-radius: 2px;
  background: var(--line);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.col-stats {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 6px;
  margin: 2px 0 0;
  font-size: 11px;
}
.col-stats dt {
  color: var(--muted);
}
.col-stats dd {
  margin: 0;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--ink-2);
}

@media (max-width: 420px) {
  .col-cost b {
    font-size: 16px;
  }
  .col-stats {
    font-size: 10px;
  }
}
</style>
