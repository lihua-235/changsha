/**
 * 构建时预生成「示例行程」→ public/data/demo-itinerary.json
 *
 * 为什么预生成：首页要展示一段真实行程，但完整生成需要加载 9,519 家店铺（约 1.4 MB gzip）。
 * 首页不该为此付出这个代价，所以把结果固化成一个几 KB 的 JSON。
 *
 * 用同一份 itinerary.js 生成，不重复实现算法。
 *   npm run build:demo     手动重生成
 *   npm run build          构建前自动重生成
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { PACES, buildItinerary } from '../src/lib/itinerary.js'

const DATA = fileURLToPath(new URL('../public/data/', import.meta.url))
const SLUGS = ['wuyi', 'nanmenkou', 'dongguashan', 'sifangping', 'kaifu', 'hexi']

const PARAMS = { days: 2, dailyBudget: 150, pace: 'normal' }

const PART_LABEL = { morning: '上午', afternoon: '下午', night: '夜间' }

function readJSON(name) {
  return JSON.parse(readFileSync(`${DATA}${name}`, 'utf8'))
}

/** 把一天摊平成有先后顺序的「站点」序列
 *  正确顺序：早餐 → 上午锚点 → 午餐 → 下午锚点 → 晚餐 → 夜间锚点
 */
function toStops(day) {
  const stops = []
  const anchorOf = (part) => day.anchors.find((a) => a.part === part)?.anchor
  const mealOf = (slot) => day.meals.find((m) => m.slot === slot)

  const anchorStop = (a, label) => ({
    kind: 'anchor',
    label,
    name: a.name,
    detail:
      a.durationMin >= 60
        ? `${(a.durationMin / 60).toFixed(1)} 小时`
        : `${a.durationMin} 分钟`,
  })

  const mealStop = (m, label) => ({
    kind: 'meal',
    label,
    name: m.shop?.name ?? m.anchor?.name ?? '—',
    detail: m.cost != null ? `¥${m.cost}` : m.fromAnchor ? '吃+逛' : '',
  })

  const bf = mealOf('breakfast')
  if (bf) stops.push(mealStop(bf, '早餐'))

  const morning = anchorOf('morning')
  if (morning) stops.push(anchorStop(morning, '上午'))

  const lunch = mealOf('lunch')
  if (lunch) stops.push(mealStop(lunch, '午餐'))

  const afternoon = anchorOf('afternoon')
  if (afternoon) stops.push(anchorStop(afternoon, '下午'))

  const dinner = mealOf('dinner')
  if (dinner) stops.push(mealStop(dinner, '晚餐'))

  const night = anchorOf('night')
  if (night) stops.push(anchorStop(night, '夜间'))

  return stops
}

function main() {
  const shops = SLUGS.flatMap((s) => readJSON(`shops-${s}.json`))
  const anchors = readJSON('anchors.json')

  const r = buildItinerary({ ...PARAMS, anchors }, shops)
  const s = r.summary

  const out = {
    schemaVersion: 1,
    params: {
      days: PARAMS.days,
      dailyBudget: PARAMS.dailyBudget,
      pace: PARAMS.pace,
      paceLabel: PACES.find((p) => p.key === PARAMS.pace)?.label ?? '',
    },
    summary: {
      totalCost: s.totalCost,
      avgPerMeal: s.avgPerMeal,
      anchorCount: s.anchorCount,
      attractionCount: s.attractionCount,
      diningAnchorCount: s.diningAnchorCount,
      totalLegMeters: s.totalLegMeters,
      mealCount: s.mealCount,
    },
    days: r.plan.map((d) => ({
      dayIndex: d.dayIndex,
      district: d.district,
      legMeters: d.legMeters,
      stops: toStops(d),
      noteCount: d.notes.length,
    })),
  }

  writeFileSync(
    `${DATA}demo-itinerary.json`,
    JSON.stringify(out, null, 0),
    'utf8'
  )
  console.log(
    `demo-itinerary.json：${PARAMS.days} 天 / ${PARAMS.dailyBudget} 元 / ` +
      `${out.params.paceLabel} / ${s.anchorCount} 个锚点 / ¥${s.totalCost}`
  )
}

main()
