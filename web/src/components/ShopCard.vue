<script setup>
import { computed } from 'vue'

const props = defineProps({
  shop: { type: Object, required: true },
})

// D1 数据诚实标记：只有真正标注过的店才显示「本地认可度」，
// 否则明确显示「待采集」，绝不用平台评分顶替。
const annotated = computed(
  () => props.shop.dataStatus === 'annotated' && props.shop.localScore != null
)

const costLabel = computed(() => {
  if (props.shop.cost == null) return null
  return `¥${props.shop.cost}`
})

const isEstimatedCost = computed(() => props.shop.costSource === 'district-median')

const distLabel = computed(() => {
  const m = props.shop.distToWuyiM
  if (m == null) return null
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`
})
</script>

<template>
  <RouterLink :to="`/shop/${shop.slug}/${shop.id}`" class="shop-card">
    <div class="shop-head">
      <span class="shop-name">{{ shop.name }}</span>
      <span v-if="shop.isChain" class="chip">连锁</span>
    </div>

    <div class="shop-tags">
      <span v-if="shop.keytag" class="chip">{{ shop.keytag }}</span>
      <span v-if="shop.distBand" class="chip">{{ shop.distBand }}</span>
      <span v-if="distLabel" class="chip">距核心区 {{ distLabel }}</span>
    </div>

    <!-- 主指标：本地认可度 / 待采集 -->
    <div class="shop-metric">
      <template v-if="annotated">
        <span class="metric-label">本地认可度</span>
        <span class="metric-value">{{ shop.localScore }}<span class="metric-unit">/5</span></span>
        <span class="chip badge-real">已标注</span>
      </template>
      <template v-else>
        <span class="metric-label">本地认可度</span>
        <span class="metric-pending">待采集</span>
        <span class="chip badge-pending">高德数据 · 未核验</span>
      </template>
    </div>

    <!-- 次指标：平台数据，弱化显示 -->
    <div class="shop-sub">
      <span v-if="shop.rating != null">平台评分 <b class="mono">{{ shop.rating }}</b></span>
      <span v-if="costLabel">
        人均 <b class="mono">{{ costLabel }}</b>
        <span v-if="isEstimatedCost" class="text-xs text-faint">（估算）</span>
      </span>
      <span v-if="shop.rating == null && costLabel == null" class="text-faint">无平台评分与人均</span>
    </div>

    <div v-if="shop.opentimeWeek" class="shop-hours text-xs text-faint">
      {{ shop.opentimeWeek }}
    </div>
  </RouterLink>
</template>

<style scoped>
.shop-card {
  display: block;
  padding: 13px 15px;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  color: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.shop-card:hover {
  text-decoration: none;
  border-color: #d6d3d1;
  box-shadow: var(--shadow);
}

.shop-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.shop-name {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.shop-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin: 7px 0 0;
}

.shop-metric {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.metric-label {
  font-size: 12px;
  color: var(--muted);
}
.metric-value {
  font-size: 19px;
  font-weight: 700;
  color: var(--ok);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.metric-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 1px;
}
.metric-pending {
  font-size: 14px;
  font-weight: 600;
  color: var(--warn);
  letter-spacing: 0.02em;
}

.shop-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 6px;
  font-size: 13px;
  color: var(--ink-2);
}
.shop-sub b {
  font-weight: 600;
  color: var(--ink);
}

.shop-hours {
  margin-top: 5px;
}
</style>
