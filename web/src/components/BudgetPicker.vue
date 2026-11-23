<script setup>
import { BUDGET_TIERS } from '../lib/itinerary.js'

defineProps({
  modelValue: { type: Number, required: true },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="picker" role="radiogroup" aria-label="每日餐饮预算">
    <button
      v-for="t in BUDGET_TIERS"
      :key="t.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === t.value"
      class="tier"
      :class="{ active: modelValue === t.value }"
      @click="$emit('update:modelValue', t.value)"
    >
      <span class="price">{{ t.label }}</span>
      <span class="headline">{{ t.headline }}</span>
      <span class="desc">{{ t.desc }}</span>
    </button>
  </div>
</template>

<style scoped>
.picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.tier {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 12px 14px;
  border: 1.5px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, transform 0.1s ease;
}
.tier:hover {
  border-color: #d6d3d1;
  background: var(--bg-soft);
}
.tier:active {
  transform: translateY(1px);
}
.tier.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.price {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.tier.active .price {
  color: var(--accent);
}

.headline {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-2);
}

.desc {
  font-size: 11px;
  line-height: 1.5;
  color: var(--muted);
}

@media (max-width: 420px) {
  .price {
    font-size: 13px;
  }
  .headline {
    font-size: 12px;
  }
  .desc {
    display: none;
  }
}
</style>
