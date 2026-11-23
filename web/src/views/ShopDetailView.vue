<script setup>
import { ref, computed, watch } from 'vue'
import { getShop } from '../data/provider'
import EmptyState from '../components/EmptyState.vue'

const props = defineProps({
  slug: { type: String, required: true },
  id: { type: String, required: true },
})

const shop = ref(null)
const loading = ref(true)

watch(
  () => [props.slug, props.id],
  async () => {
    loading.value = true
    shop.value = await getShop({ slug: props.slug, id: props.id })
    loading.value = false
  },
  { immediate: true }
)

const annotated = computed(
  () => shop.value?.dataStatus === 'annotated' && shop.value?.localScore != null
)

const isEstimatedCost = computed(() => shop.value?.costSource === 'district-median')

/** 跳转高德看位置：不内嵌地图，零 Key 依赖 */
const amapUri = computed(() => {
  const s = shop.value
  if (!s) return '#'
  const params = new URLSearchParams({
    position: `${s.lng},${s.lat}`,
    name: s.name ?? '',
    coordinate: 'gaode',
    callnative: '1',
  })
  return `https://uri.amap.com/marker?${params.toString()}`
})
</script>

<template>
  <RouterLink v-if="shop" :to="`/explore/${shop.slug}`" class="back">← 返回 {{ shop.district }}</RouterLink>
  <RouterLink v-else to="/" class="back">← 返回首页</RouterLink>

  <div v-if="loading" class="grid">
    <div class="skeleton" style="height: 28px; width: 60%" />
    <div class="skeleton" style="height: 180px" />
  </div>

  <template v-else-if="shop">
    <h1>{{ shop.name }}</h1>

    <div class="badge-row">
      <span v-if="shop.keytag" class="chip">{{ shop.keytag }}</span>
      <span v-if="shop.distBand" class="chip">{{ shop.distBand }}</span>
      <span v-if="shop.isChain" class="chip">连锁</span>
      <span v-if="annotated" class="chip badge-real">已标注</span>
      <span v-else class="chip badge-pending">高德数据 · 未核验</span>
    </div>

    <!-- 主指标 -->
    <div class="primary">
      <div class="primary-label">本地认可度</div>
      <div v-if="annotated" class="primary-value">
        {{ shop.localScore }}<span class="unit">/5</span>
      </div>
      <div v-else class="primary-pending">
        待采集
        <p class="primary-note">
          这一项需要实地观察才能填。我们刻意不用平台评分顶替它 ——
          否则这个网站就变成了它要反对的东西。
        </p>
      </div>
    </div>

    <blockquote v-if="shop.localEvidence" class="evidence">
      {{ shop.localEvidence }}
    </blockquote>

    <div class="section-title"><h2>店铺信息</h2></div>
    <dl class="kv card">
      <dt>平台评分</dt>
      <dd>{{ shop.rating ?? '—' }}<span class="text-faint text-xs">（来自高德，未核验）</span></dd>

      <dt>人均消费</dt>
      <dd>
        <template v-if="shop.cost != null">
          ¥{{ shop.cost }}
          <span v-if="isEstimatedCost" class="text-xs text-faint">（片区中位数估算）</span>
        </template>
        <template v-else>—</template>
      </dd>

      <dt>营业时间</dt>
      <dd>{{ shop.opentimeWeek ?? '未提供' }}</dd>

      <dt>地址</dt>
      <dd>{{ shop.address ?? '—' }}</dd>

      <dt>电话</dt>
      <dd>
        <template v-if="shop.tel">
          <a :href="`tel:${shop.tel}`">{{ shop.tel }}</a>
        </template>
        <template v-else>—</template>
      </dd>

      <dt>距核心区</dt>
      <dd>{{ shop.distToWuyiM }} 米（距五一广场直线距离）</dd>

      <dt>推荐标签</dt>
      <dd>{{ shop.rectag ?? '—' }}</dd>
    </dl>

    <div class="actions">
      <a :href="amapUri" target="_blank" rel="noopener" class="btn btn-primary">在高德地图中打开</a>
      <RouterLink :to="`/explore/${shop.slug}`" class="btn">看同片区的店</RouterLink>
    </div>
  </template>

  <EmptyState
    v-else
    icon="◌"
    title="找不到这家店"
    desc="可能是数据还没导出，或者这个链接的店铺 ID 不在当前数据集里。"
  >
    <RouterLink to="/" class="btn">回首页</RouterLink>
  </EmptyState>
</template>

<style scoped>
.back {
  display: inline-block;
  font-size: 13px;
  color: var(--ink-2);
  margin-bottom: 12px;
}

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 4px 0 16px;
}

.primary {
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 16px;
  background: var(--bg-soft);
}
.primary-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.primary-value {
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
  color: var(--ok);
  font-variant-numeric: tabular-nums;
}
.primary-value .unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 2px;
}
.primary-pending {
  font-size: 20px;
  font-weight: 700;
  color: var(--warn);
}
.primary-note {
  font-size: 12px;
  font-weight: 400;
  color: var(--ink-2);
  line-height: 1.6;
  margin: 8px 0 0;
  max-width: 34em;
}

.evidence {
  margin: 12px 0 0;
  padding: 10px 14px;
  border-left: 3px solid var(--accent);
  background: var(--accent-soft);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  font-size: 14px;
  color: var(--ink-2);
}

.kv {
  margin: 0;
  padding: 14px 16px;
}
.kv dd {
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 18px;
}
</style>
