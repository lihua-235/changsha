<script setup>
import { ref, onMounted } from 'vue'
import { getMeta, getDemoItinerary } from '../data/provider'
import EmptyState from '../components/EmptyState.vue'

const meta = ref(null)
const demo = ref(null)
const loading = ref(true)

onMounted(async () => {
  const [m, d] = await Promise.all([getMeta(), getDemoItinerary()])
  meta.value = m
  demo.value = d
  loading.value = false
})

const fmt = (n) => (n == null ? '—' : n.toLocaleString('zh-CN'))
</script>

<template>
  <section class="hero">
    <h1>长沙，不按评分吃</h1>
    <p class="page-lead">
      平台评分高的店，往往只是更贵。我们换一个判断依据：
      <strong>本地人是不是真的在吃</strong>。先定每天去哪玩，再在景点周边就近吃。
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
        <b>{{ fmt(meta.counts.anchors) }}</b>
        <span>个景点锚点</span>
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

    <!-- 行程预览 -->
    <section v-if="demo" class="demo">
      <div class="section-title">
        <h2>行程长这样</h2>
        <span class="hint">
          {{ demo.params.days }} 天 · {{ demo.params.dailyBudget }} 元/天 ·
          {{ demo.params.paceLabel }}
        </span>
      </div>

      <div class="demo-card">
        <div class="demo-meta">
          <span>共 ¥{{ demo.summary.totalCost }}</span>
          <span>{{ demo.summary.anchorCount }} 个景点锚点</span>
          <span>移动 {{ (demo.summary.totalLegMeters / 1000).toFixed(1) }} km</span>
        </div>

        <div v-for="day in demo.days" :key="day.dayIndex" class="demo-day">
          <div class="demo-day-head">
            第 {{ day.dayIndex + 1 }} 天 · {{ day.district }}
            <span class="demo-day-leg">{{ (day.legMeters / 1000).toFixed(1) }} km</span>
          </div>
          <ol class="stops">
            <li v-for="(s, i) in day.stops" :key="i" :class="s.kind">
              <span class="stop-label">{{ s.label }}</span>
              <span class="stop-name">{{ s.name }}</span>
              <span class="stop-detail">{{ s.detail }}</span>
            </li>
          </ol>
        </div>

        <RouterLink to="/itinerary" class="btn demo-cta">
          换成你的预算和天数 →
        </RouterLink>
      </div>
    </section>

    <div class="section-title">
      <h2>从哪个片区开始</h2>
      <span class="hint">标签由数据算出，不是写死的</span>
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
        <span v-if="d.tags && d.tags.length" class="district-tags">
          <span v-for="t in d.tags" :key="t.text" class="dtag" :title="t.why">{{ t.text }}</span>
        </span>
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
.district-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.dtag {
  font-size: 10px;
  line-height: 1.6;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid #fed7aa;
  white-space: nowrap;
}

/* ---------------- 行程预览 ---------------- */

.demo-card {
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: #fff;
  padding: 14px 15px;
}

.demo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--ink-2);
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
  font-variant-numeric: tabular-nums;
}

.demo-day {
  padding-top: 12px;
}
.demo-day-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-2);
  margin-bottom: 6px;
}
.demo-day-leg {
  margin-left: auto;
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.stops {
  margin: 0;
  padding: 0;
  list-style: none;
}
.stops li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 5px 0 5px 12px;
  border-left: 2px solid var(--line);
  margin-left: 3px;
  font-size: 13px;
}
.stops li.anchor {
  border-left-color: var(--accent);
}
.stop-label {
  flex: 0 0 2.6em;
  font-size: 11px;
  color: var(--muted);
}
.stop-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
}
.stops li.anchor .stop-name {
  font-weight: 600;
}
.stop-detail {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
}

.demo-cta {
  margin-top: 12px;
  width: 100%;
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
