<script setup>
import { ref, onMounted } from 'vue'
import { getMeta } from '../data/provider'
import EmptyState from '../components/EmptyState.vue'

const meta = ref(null)
const loading = ref(true)

onMounted(async () => {
  meta.value = await getMeta()
  loading.value = false
})

const fmt = (n) => (n == null ? '—' : n.toLocaleString('zh-CN'))
</script>

<template>
  <section class="hero">
    <h1>长沙，不按评分吃</h1>
    <p class="page-lead">
      平台评分高的店，往往只是更贵。我们换一个判断依据：
      <strong>本地人是不是真的在吃</strong>。然后按你的预算生成行程 ——
      包括每天 50 元的那种。
    </p>
    <div class="hero-actions">
      <RouterLink to="/itinerary" class="btn btn-primary">按预算生成行程</RouterLink>
      <RouterLink to="/about" class="btn">这个判断怎么来的</RouterLink>
    </div>
  </section>

  <div v-if="loading" class="stat-row">
    <div v-for="i in 3" :key="i" class="skeleton" style="height: 58px" />
  </div>

  <template v-else-if="meta">
    <div class="stat-row">
      <div class="stat">
        <b>{{ fmt(meta.counts.shops) }}</b>
        <span>家餐饮</span>
      </div>
      <div class="stat">
        <b>{{ fmt(meta.counts.scenics) }}</b>
        <span>个景点</span>
      </div>
      <div class="stat">
        <b>{{ fmt(meta.counts.hotels) }}</b>
        <span>处住宿</span>
      </div>
    </div>

    <p class="text-xs text-faint data-note">
      以上为高德数据，<strong>未经实地核验</strong>；
      「本地认可度」需人工标注，当前为空。
    </p>

    <div class="section-title">
      <h2>从哪个片区开始</h2>
      <span class="hint">按距游客核心区分层</span>
    </div>

    <div class="grid districts">
      <RouterLink
        v-for="d in meta.districts"
        :key="d.slug"
        :to="`/explore/${d.slug}`"
        class="district-card"
      >
        <span class="district-name">{{ d.name }}</span>
        <span class="district-count">{{ fmt(d.count) }} 家</span>
      </RouterLink>
    </div>
  </template>

  <EmptyState
    v-else
    icon="◌"
    title="还没有数据"
    desc="先运行导出脚本生成数据文件，刷新本页就会有内容。骨架本身是完整的，只是还没喂数据。"
  >
    <code class="cmd">python scripts/export_web_data.py</code>
  </EmptyState>
</template>

<style scoped>
.hero {
  padding: 8px 0 4px;
}
.hero h1 {
  font-size: 26px;
  letter-spacing: -0.03em;
}
.hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 24px 0 0;
}
.stat {
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat b {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.stat span {
  font-size: 12px;
  color: var(--ink-2);
}

.data-note {
  margin: 10px 0 0;
  line-height: 1.6;
}

.districts {
  grid-template-columns: repeat(2, 1fr);
}
.district-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  color: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.district-card:hover {
  text-decoration: none;
  border-color: #d6d3d1;
  box-shadow: var(--shadow);
}
.district-name {
  font-weight: 600;
  font-size: 14px;
}
.district-count {
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.cmd {
  display: inline-block;
  background: #1c1917;
  color: #fafaf9;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
