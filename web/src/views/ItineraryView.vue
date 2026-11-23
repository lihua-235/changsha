<script setup>
import EmptyState from '../components/EmptyState.vue'

// Step 3 待实现。这里先说明设计意图，避免给出一个假的行程。
const tiers = [
  { label: '50 元 / 天', perMeal: '≤16.7 元', range: '208 – 511 家可选', note: '穷游档' },
  { label: '150 元 / 天', perMeal: '≤50 元', range: '825 – 1,831 家可选', note: '常规档' },
  { label: '400 元 / 天', perMeal: '≤133 元', range: '1,080 – 2,327 家可选', note: '富游档' },
]
</script>

<template>
  <h1>按预算生成行程</h1>
  <p class="page-lead">
    预算是<strong>约束条件</strong>，不是一个开关。我们不提供「穷游模式」，
    而是把三档预算同时算出来，让你看见省下来的钱换回了什么。
  </p>

  <div class="section-title">
    <h2>三档每日餐饮预算</h2>
    <span class="hint">可生成性已验证</span>
  </div>

  <div class="grid tiers">
    <div v-for="t in tiers" :key="t.label" class="tier">
      <div class="tier-top">
        <b>{{ t.label }}</b>
        <span class="chip">{{ t.note }}</span>
      </div>
      <div class="tier-meta text-sm text-muted">
        单餐预算 {{ t.perMeal }} ・ 各片区 {{ t.range }}
      </div>
    </div>
  </div>

  <p class="text-xs text-faint verify-note">
    这组数字来自对六个片区现有数据的实测：即使是最紧的 50 元/天，
    每个片区仍有 44–83 种不同菜品类型可供组餐。所以这一档不是凑出来的。
  </p>

  <div class="section-title"><h2>生成的行程会是什么样</h2></div>
  <ol class="plan">
    <li>每天分配一个片区，从生活区递进到游客核心区</li>
    <li>按单餐预算筛店，同一天不出现重复的菜品类型</li>
    <li>按营业时间匹配早市 / 午市 / 夜市</li>
    <li>按距离排出走访顺序，并给出步行时间</li>
    <li>同一批店跑三档预算，输出并排对比</li>
  </ol>

  <EmptyState
    icon="◔"
    title="行程生成还没实现"
    desc="这是 Step 3 的内容，规则算法本身不复杂。之所以先留空，是因为一旦把逻辑写死在前端，等真实信号接入时就要重写第二遍。"
  >
    <RouterLink to="/" class="btn">先去看店</RouterLink>
  </EmptyState>
</template>

<style scoped>
.tiers {
  grid-template-columns: 1fr;
}
.tier {
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 13px 15px;
  background: #fff;
}
.tier-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.tier-top b {
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}
.tier-meta {
  font-variant-numeric: tabular-nums;
}

.verify-note {
  margin: 8px 0 0;
  line-height: 1.6;
}

.plan {
  margin: 0;
  padding-left: 1.3em;
  color: var(--ink-2);
  font-size: 14px;
}
.plan li {
  margin-bottom: 6px;
}
</style>
