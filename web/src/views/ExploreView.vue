<script setup>
import { ref, computed, watch } from 'vue'
import { listShops, listDistricts } from '../data/provider'
import ShopCard from '../components/ShopCard.vue'
import EmptyState from '../components/EmptyState.vue'

const props = defineProps({
  district: { type: String, required: true },
})

const shops = ref([])
const districtName = ref('')
const loading = ref(true)
const keyword = ref('')
const SHOW_LIMIT = 60

async function load() {
  loading.value = true
  keyword.value = ''
  const ds = await listDistricts()
  districtName.value = ds.find((d) => d.slug === props.district)?.name ?? props.district
  shops.value = await listShops({ districtSlug: props.district })
  loading.value = false
}

watch(() => props.district, load, { immediate: true })

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return shops.value
  return shops.value.filter(
    (s) =>
      s.name?.toLowerCase().includes(kw) ||
      s.keytag?.toLowerCase().includes(kw) ||
      s.rectag?.toLowerCase().includes(kw)
  )
})

const shown = computed(() => filtered.value.slice(0, SHOW_LIMIT))
</script>

<template>
  <RouterLink to="/" class="back">← 返回片区列表</RouterLink>

  <h1 class="district-title">{{ districtName }}</h1>
  <p v-if="!loading" class="page-lead">
    共 <b class="mono">{{ shops.length }}</b> 家餐饮。
    平台评分与人均来自高德，<strong>本地认可度待实地标注</strong>。
  </p>

  <div v-if="loading" class="grid">
    <div v-for="i in 6" :key="i" class="skeleton" style="height: 118px" />
  </div>

  <template v-else-if="shops.length">
    <input
      v-model="keyword"
      class="search"
      type="search"
      placeholder="搜店名或菜品，例如「米粉」「小龙虾」"
      aria-label="搜索店铺"
    />

    <p class="text-xs text-faint result-hint">
      匹配 {{ filtered.length }} 家<template v-if="filtered.length > SHOW_LIMIT">
        ，先显示前 {{ SHOW_LIMIT }} 家</template>
    </p>

    <div v-if="filtered.length" class="grid shop-list">
      <ShopCard v-for="s in shown" :key="s.id" :shop="s" />
    </div>
    <EmptyState v-else icon="⌕" title="没有匹配的店" desc="换个关键词试试，或者清空搜索框。" />
  </template>

  <EmptyState
    v-else
    icon="◌"
    title="这个片区还没有数据"
    desc="数据文件没生成，或者片区标识不对。先运行导出脚本，再刷新。"
  />
</template>

<style scoped>
.back {
  display: inline-block;
  font-size: 13px;
  color: var(--ink-2);
  margin-bottom: 12px;
}
.district-title {
  font-size: 22px;
  margin-bottom: 4px;
}

.search {
  width: 100%;
  padding: 11px 14px;
  font-size: 15px;
  font-family: inherit;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: #fff;
  color: var(--ink);
  margin: 4px 0 8px;
}
.search:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.result-hint {
  margin: 0 0 10px;
}

.shop-list {
  grid-template-columns: 1fr;
}
</style>
