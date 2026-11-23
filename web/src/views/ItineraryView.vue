<script setup>
import { ref, computed, onMounted } from 'vue'
import { listDistricts, listShops } from '../data/provider.js'
import { BUDGET_TIERS, buildItinerary } from '../lib/itinerary.js'
import BudgetPicker from '../components/BudgetPicker.vue'
import DayTimeline from '../components/DayTimeline.vue'
import TierCompare from '../components/TierCompare.vue'
import EmptyState from '../components/EmptyState.vue'

const districts = ref([])
const allShops = ref([])
const loading = ref(true)
const loadError = ref('')

const days = ref(2)
const budget = ref(150)
const selectedSlugs = ref([])
const hasGenerated = ref(false)

onMounted(async () => {
  districts.value = await listDistricts()
  if (!districts.value.length) {
    loading.value = false
    loadError.value = '没有片区数据，先运行 scripts/export_web_data.py'
    return
  }
  selectedSlugs.value = districts.value.map((d) => d.slug)
  const lists = await Promise.all(
    districts.value.map((d) => listShops({ districtSlug: d.slug }))
  )
  allShops.value = lists.flat()
  loading.value = false
})

const DAY_OPTIONS = [1, 2, 3, 4, 5]

function toggleDistrict(slug) {
  const set = new Set(selectedSlugs.value)
  if (set.has(slug)) {
    if (set.size === 1) return // 至少留一个片区
    set.delete(slug)
  } else {
    set.add(slug)
  }
  selectedSlugs.value = districts.value.map((d) => d.slug).filter((s) => set.has(s))
}

const poolShops = computed(() =>
  allShops.value.filter((s) => selectedSlugs.value.includes(s.slug))
)

/** 三档一起算：切换档位是纯切换，不重新计算 */
const built = computed(() => {
  if (!hasGenerated.value || !poolShops.value.length) return []
  return BUDGET_TIERS.map((tier) => ({
    tier,
    it: buildItinerary(
      { days: days.value, dailyBudget: tier.value, districtSlugs: selectedSlugs.value },
      poolShops.value
    ),
  }))
})

const current = computed(
  () => built.value.find((b) => b.tier.value === budget.value) ?? built.value[0] ?? null
)

function generate() {
  hasGenerated.value = true
}
</script>

<template>
  <h1>按预算排行程</h1>
  <p class="page-lead">
    预算是<strong>约束条件</strong>，不是模式开关。三档同时算出来，
    你能看见少花 350 元到底少掉了什么。
  </p>

  <div v-if="loading" class="grid">
    <div class="skeleton" style="height: 88px" />
    <div class="skeleton" style="height: 120px" />
  </div>

  <EmptyState v-else-if="loadError" icon="◌" title="没有可用数据" :desc="loadError" />

  <template v-else>
    <section class="controls">
      <div class="ctrl-row">
        <span class="ctrl-label">天数</span>
        <div class="days">
          <button
            v-for="d in DAY_OPTIONS"
            :key="d"
            type="button"
            class="day-btn"
            :class="{ active: days === d }"
            @click="days = d"
          >
            {{ d }} 天
          </button>
        </div>
      </div>

      <div class="ctrl-row">
        <span class="ctrl-label">每日餐饮预算</span>
        <BudgetPicker v-model="budget" />
      </div>

      <div class="ctrl-row">
        <span class="ctrl-label">片区</span>
        <div class="districts">
          <button
            v-for="d in districts"
            :key="d.slug"
            type="button"
            class="dist-chip"
            :class="{ active: selectedSlugs.includes(d.slug) }"
            @click="toggleDistrict(d.slug)"
          >
            {{ d.name }}
          </button>
        </div>
      </div>

      <div class="ctrl-row actions">
        <button type="button" class="btn btn-primary" @click="generate">
          {{ hasGenerated ? '重新生成' : '生成行程' }}
        </button>
        <span class="pool-hint">
          候选 {{ poolShops.length.toLocaleString('zh-CN') }} 家 ·
          {{ selectedSlugs.length }} 个片区
        </span>
      </div>
    </section>

    <template v-if="current">
      <div class="section-title">
        <h2>三档对比</h2>
        <span class="hint">点任意一档看明细</span>
      </div>
      <TierCompare v-model="budget" :built="built" />

      <p class="insight">
        {{ built[0].tier.label }} 吃 {{ built[0].it.summary.dishTypeCount }} 类菜、
        人均 ¥{{ built[0].it.summary.avgPerMeal }}；{{ built[2].tier.label }}
        人均 ¥{{ built[2].it.summary.avgPerMeal }}。
        <template v-if="built[2].it.summary.chainRate > built[0].it.summary.chainRate">
          贵的那一档连锁店占比更高（{{ built[2].it.summary.chainRate }}% vs
          {{ built[0].it.summary.chainRate }}%）—— 多花的钱有一部分花在了连锁品牌上。
        </template>
        <template v-else>
          这份数据里贵的那一档并没有更多连锁店，多花的钱主要花在菜价本身上。
        </template>
      </p>

      <div class="section-title">
        <h2>{{ current.tier.label }} 的行程</h2>
        <span class="hint">
          {{ current.it.summary.days }} 天 · {{ current.it.summary.mealCount }} 餐
        </span>
      </div>

      <div class="grid days-list">
        <DayTimeline v-for="day in current.it.plan" :key="day.dayIndex" :day="day" />
      </div>

      <div class="disclaimer">
        <p v-for="(n, i) in current.it.notes" :key="i">{{ n }}</p>
        <p>价格为片区中位数填补的餐次已标「估算」；营业时间缺失的店标「未核验」。出行前请电话确认。</p>
      </div>
    </template>

    <EmptyState
      v-else
      icon="◔"
      title="还没生成行程"
      desc="选好天数、预算和片区，点「生成行程」。三档预算会一起算出来，方便对比。"
    />
  </template>
</template>

<style scoped>
.controls {
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: var(--bg-soft);
  padding: 14px 15px;
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.ctrl-row {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.ctrl-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
}

.days {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.day-btn {
  padding: 6px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  font-size: 13px;
  font-family: inherit;
  color: var(--ink-2);
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.day-btn.active {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
  font-weight: 600;
}

.districts {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.dist-chip {
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  font-size: 12px;
  font-family: inherit;
  color: var(--muted);
  cursor: pointer;
}
.dist-chip.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}

.actions {
  flex-direction: row;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 2px;
}
.pool-hint {
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.insight {
  margin: 12px 0 0;
  padding: 11px 14px;
  border-left: 3px solid var(--accent);
  background: var(--accent-soft);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ink-2);
}

.days-list {
  grid-template-columns: 1fr;
  gap: 12px;
}

.disclaimer {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  line-height: 1.7;
  color: var(--muted);
}
.disclaimer p {
  margin: 0 0 6px;
}
</style>
