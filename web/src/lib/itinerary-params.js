/**
 * 行程参数的 URL 序列化 / 反序列化
 * ---------------------------------------------------------------
 * 为什么需要它：
 *   行程页的状态原本只活在组件内存里，切到首页再回来就丢了。
 *   而算法是确定性的 —— 给定 (天数, 预算, 节奏, 种子) 结果是唯一的，
 *   所以**这组参数本身就是行程的存档**，几十字节，不必存整份结果。
 *
 * 两个存储位：
 *   · URL query  → 刷新不丢、可分享、可复现（给别人的链接）
 *   · localStorage → 站内跳走再回来不丢（给自己的"继续上次"）
 */

import { BUDGET_TIERS, PACES } from './itinerary.js'

export const PARAM_DEFAULTS = { days: 2, budget: 150, pace: 'normal', seed: 0 }
export const MAX_DAYS = 30

export const STORAGE_KEY = 'cs-itinerary-params'

function clampDays(v) {
  const n = Math.floor(Number(v))
  if (!Number.isFinite(n)) return PARAM_DEFAULTS.days
  return Math.min(MAX_DAYS, Math.max(1, n))
}

/**
 * 从 query（或 localStorage 里的对象）解析参数。
 * 解析不出来就返回默认值并标记 restored=false —— 调用方据此决定是否展示「还没生成」。
 */
export function parseParams(input = {}) {
  const rawDays = input.days
  const rawBudget = Number(input.budget)
  const rawPace = String(input.pace ?? '')
  const rawSeed = Number(input.seed)

  // 天数缺失就认为是「没有参数」，不要用默认值假装恢复成功
  if (rawDays == null || rawDays === '' || !Number.isFinite(Number(rawDays))) {
    return { ...PARAM_DEFAULTS, restored: false }
  }

  const days = clampDays(rawDays)
  const budget = BUDGET_TIERS.some((t) => t.value === rawBudget)
    ? rawBudget
    : PARAM_DEFAULTS.budget
  const pace = PACES.some((p) => p.key === rawPace) ? rawPace : PARAM_DEFAULTS.pace
  const seed = Number.isFinite(rawSeed) ? Math.max(0, Math.floor(rawSeed)) : 0

  return { days, budget, pace, seed, restored: true }
}

/** 参数 → query 对象（一律写全，链接才自解释） */
export function toQuery({ days, budget, pace, seed }) {
  return {
    days: String(clampDays(days)),
    budget: String(budget),
    pace: String(pace),
    seed: String(Math.max(0, Math.floor(Number(seed) || 0))),
  }
}

/** 参数是否与默认值一致（用于决定要不要写 URL） */
export function isDefault(params) {
  return (
    params.days === PARAM_DEFAULTS.days &&
    params.budget === PARAM_DEFAULTS.budget &&
    params.pace === PARAM_DEFAULTS.pace &&
    params.seed === PARAM_DEFAULTS.seed
  )
}
