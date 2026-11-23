/**
 * 行程算法测试 —— 用 Node 内置 test runner，零新增依赖
 *   运行：npm test
 *
 * 注意：这里有一条测试是专门为了防住第一版的 bug ——
 * 当时 150 与 400 档生成了完全相同的行程（因为排序主键是距离降序，
 * 而最远的店恰好最便宜），但所有结构性断言都通过了。
 * 所以「三档必须真的不同」必须写成断言。
 */

import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import {
  BUDGET_TIERS,
  MEAL_SLOTS,
  buildItinerary,
  compareTiers,
  dishGroup,
  dishTag,
  distanceMeters,
  openInSlot,
  parseOpeningHours,
} from './itinerary.js'

/* ---------------- 真实数据 ---------------- */

function loadDistrict(slug) {
  const p = fileURLToPath(new URL(`../../public/data/shops-${slug}.json`, import.meta.url))
  return JSON.parse(readFileSync(p, 'utf8'))
}

const DISTRICTS = ['wuyi', 'hexi', 'nanmenkou']
const SHOPS = DISTRICTS.flatMap(loadDistrict)

/* ---------------- 营业时间解析 ---------------- */

describe('parseOpeningHours：对抗实测的 12 种脏格式', () => {
  const cases = [
    ['周一至周日 09:00-23:00', { known: true, count: 1 }],
    ['周一至周日 10:30-13:30,16:30-20:30', { known: true, count: 2 }],
    ['10:00-21:30', { known: true, count: 1 }],
    ['周一至周日 11:00-14:00，17:00-20:00', { known: true, count: 2 }],
    ['周一至周日 10:00-23:00 最晚点餐22:30', { known: true, count: 1 }],
    ['周一至周日 07:00-22:00 10-01至10-07 周一至周日 07:00-22:00', { known: true, count: 2 }],
    ['周一至周日 09:00-23:00 2026-03-02至2026-03-03 周一至周日 09:00-21:00', { known: true, count: 2 }],
    ['周一至周日 11:30-14:00,17:00-20:00 2026-02-15至2026-02-16 周一至周日 全天关闭', { known: true, count: 2 }],
    ['周一至周日 16:30-02:00 2026-02-10至2026-03-04 周一至周日 全天关闭', { known: true, count: 1 }],
    ['24小时营业', { known: true, allDay: true }],
    [null, { known: false }],
    ['', { known: false }],
  ]

  for (const [raw, expect] of cases) {
    test(JSON.stringify(raw), () => {
      const r = parseOpeningHours(raw)
      assert.equal(r.known, expect.known, `known 不符: ${raw}`)
      if (expect.count != null) assert.equal(r.segments.length, expect.count, `段数不符: ${raw}`)
      if (expect.allDay != null) assert.equal(r.allDay, expect.allDay)
    })
  }

  test('跨午夜 16:30-02:00 的结束时间要加一天', () => {
    const r = parseOpeningHours('周一至周日 16:30-02:00')
    assert.equal(r.segments[0].open, 16 * 60 + 30)
    assert.equal(r.segments[0].close, 26 * 60)
  })

  test('「全天关闭」要标记为临时闭店，但仍能解析出正常时段', () => {
    const r = parseOpeningHours('周一至周日 11:30-14:00,17:00-20:00 2026-02-15至2026-02-16 全天关闭')
    assert.equal(r.tempClosed, true)
    assert.ok(r.segments.length >= 1)
  })
})

describe('openInSlot', () => {
  const dinner = MEAL_SLOTS.find((s) => s.key === 'dinner')

  test('跨午夜店算作晚餐营业', () => {
    assert.equal(openInSlot(parseOpeningHours('周一至周日 16:30-02:00'), dinner), true)
  })

  test('只做早餐的店不算晚餐营业', () => {
    assert.equal(openInSlot(parseOpeningHours('周一至周日 06:00-10:00'), dinner), false)
  })

  test('无数据返回 unknown（不是 false）', () => {
    assert.equal(openInSlot(parseOpeningHours(null), dinner), 'unknown')
  })

  test('24 小时恒为 true', () => {
    assert.equal(openInSlot(parseOpeningHours('24小时营业'), dinner), true)
  })
})

/* ---------------- 菜品分类 ---------------- */

describe('dishTag / dishGroup', () => {
  test('正常菜品保留', () => {
    assert.equal(dishTag({ keytag: '米粉' }), '米粉')
    assert.equal(dishTag({ keytag: '奶茶/茶饮' }), '奶茶/茶饮')
  })

  test('类目兜底值返回 null', () => {
    assert.equal(dishTag({ keytag: '餐饮服务,餐饮相关场所,餐饮相关' }), null)
    assert.equal(dishTag({ keytag: '餐饮相关' }), null)
    assert.equal(dishTag({}), null)
  })

  test('米粉 / 牛肉粉 / 面馆 归为同一粗类，否则一天会吃三顿粉', () => {
    assert.equal(dishGroup({ keytag: '米粉' }), '粉面')
    assert.equal(dishGroup({ keytag: '牛肉粉' }), '粉面')
    assert.equal(dishGroup({ keytag: '面馆' }), '粉面')
  })

  test('饮品与火锅各自成类', () => {
    assert.equal(dishGroup({ keytag: '奶茶/茶饮' }), '饮品')
    assert.equal(dishGroup({ keytag: '咖啡' }), '饮品')
    assert.equal(dishGroup({ keytag: '火锅' }), '火锅烧烤')
  })
})

/* ---------------- 行程生成（真实数据） ---------------- */

describe('buildItinerary：三档预算 × 三个片区', () => {
  for (const tier of BUDGET_TIERS) {
    for (const slug of DISTRICTS) {
      test(`${tier.label} × ${slug} 能生成完整三餐`, () => {
        const r = buildItinerary({ days: 1, dailyBudget: tier.value, districtSlugs: [slug] }, SHOPS)
        assert.equal(r.plan.length, 1)
        assert.equal(r.plan[0].meals.length, 3, `应有三餐，实际 ${r.plan[0].meals.length}`)
      })
    }
  }

  test('严格命中的餐次总价不超过每日预算', () => {
    for (const value of [150, 400]) {
      const r = buildItinerary({ days: 1, dailyBudget: value, districtSlugs: ['wuyi'] }, SHOPS)
      assert.ok(r.summary.totalCost <= value, `总价 ${r.summary.totalCost} 超过预算 ${value}`)
    }
  })

  test('同一天不出现重复的菜品粗类', () => {
    for (const slug of DISTRICTS) {
      for (const tier of BUDGET_TIERS) {
        const r = buildItinerary({ days: 1, dailyBudget: tier.value, districtSlugs: [slug] }, SHOPS)
        const groups = r.plan[0].meals.map((m) => m.dishGroup).filter(Boolean)
        assert.equal(new Set(groups).size, groups.length, `${slug}/${tier.value} 出现重复粗类: ${groups}`)
      }
    }
  })

  test('晚餐不安排饮品', () => {
    for (const slug of DISTRICTS) {
      for (const tier of BUDGET_TIERS) {
        const r = buildItinerary({ days: 1, dailyBudget: tier.value, districtSlugs: [slug] }, SHOPS)
        const dinner = r.plan[0].meals.find((m) => m.slot === 'dinner')
        assert.notEqual(dinner?.dishGroup, '饮品', `${slug}/${tier.value} 晚餐是饮品`)
      }
    }
  })

  test('整份行程不重复使用同一家店', () => {
    const r = buildItinerary({ days: 3, dailyBudget: 150, districtSlugs: ['wuyi'] }, SHOPS)
    const ids = r.plan.flatMap((p) => p.meals.map((m) => m.shop.id))
    assert.equal(new Set(ids).size, ids.length, '出现了重复店铺')
  })

  test('确定性：同样输入跑两次结果完全一致', () => {
    const params = { days: 2, dailyBudget: 150, districtSlugs: ['wuyi', 'hexi'] }
    assert.deepEqual(buildItinerary(params, SHOPS), buildItinerary(params, SHOPS))
  })

  test('天数多于片区数时会循环使用片区，但不重复店铺', () => {
    const r = buildItinerary({ days: 4, dailyBudget: 150, districtSlugs: ['wuyi'] }, SHOPS)
    assert.equal(r.plan.length, 4)
    const ids = r.plan.flatMap((p) => p.meals.map((m) => m.shop.id))
    assert.equal(new Set(ids).size, ids.length)
  })

  test('单日行程要可执行：餐间总距离不能超过两段上限', () => {
    for (const slug of DISTRICTS) {
      for (const tier of BUDGET_TIERS) {
        const r = buildItinerary({ days: 1, dailyBudget: tier.value, districtSlugs: [slug] }, SHOPS)
        assert.ok(
          r.summary.totalLegMeters <= 2 * 2200 + 1,
          `${slug}/${tier.value} 当天餐间 ${r.summary.totalLegMeters}m，超过可执行上限`
        )
      }
    }
  })
})

/* ---------------- 三档必须真的不同（回归测试） ---------------- */

describe('compareTiers：三档必须产生实质差异', () => {
  const rows = compareTiers({ days: 2, districtSlugs: ['wuyi', 'hexi'] }, SHOPS)
  const [cheap, mid, rich] = rows

  test('返回三档', () => {
    assert.equal(rows.length, 3)
  })

  test('花费随档位单调递增', () => {
    const costs = rows.map((r) => r.summary.totalCost)
    assert.ok(
      costs[0] < costs[1] && costs[1] < costs[2],
      `花费未严格递增: ${costs.join(' / ')} ← 这条断言就是为了防住第一版的 bug`
    )
  })

  test('平均每餐花费随档位递增', () => {
    const avg = rows.map((r) => r.summary.avgPerMeal)
    assert.ok(avg[0] < avg[1] && avg[1] < avg[2], `人均未递增: ${avg.join(' / ')}`)
  })

  test('150 与 400 档不能选出同一批店', () => {
    const names = (r) => r.shops.flatMap((d) => d.names).join('|')
    assert.notEqual(names(mid), names(rich), '中档与高档选出了完全相同的店 —— 分档失效')
  })

  test('便宜档的餐次数不应少于贵档（预算不是删减菜品，是换选择）', () => {
    const counts = rows.map((r) => r.summary.mealCount)
    assert.equal(new Set(counts).size, 1, `餐次数不一致: ${counts}`)
  })

  test('便宜档的人均不超过其单餐预算', () => {
    assert.ok(cheap.summary.avgPerMeal <= cheap.summary.perMealBudget + 0.01)
  })
})

/* ---------------- 锚点模式（anchor-first） ---------------- */

const ANCHORS = (() => {
  const p = fileURLToPath(new URL('../../public/data/anchors.json', import.meta.url))
  return JSON.parse(readFileSync(p, 'utf8'))
})()

describe('锚点模式：先去哪玩，再就近吃', () => {
  const usable = ANCHORS.filter((a) => a.foodAvailable)

  test('锚点数据里至少有一批可用锚点', () => {
    assert.ok(usable.length >= 15, `可用锚点只有 ${usable.length} 个`)
  })

  test('每天都有锚点，且都是可排程锚点', () => {
    const r = buildItinerary({ days: 2, dailyBudget: 150, anchors: ANCHORS }, SHOPS)
    for (const day of r.plan) {
      assert.ok(day.anchors.length >= 1, `第 ${day.dayIndex + 1} 天没有锚点`)
      for (const a of day.anchors) {
        assert.equal(a.anchor.foodAvailable, true, `${a.anchor.name} 不可排程却被选中`)
      }
    }
  })

  test('整份行程内锚点不重复', () => {
    const r = buildItinerary({ days: 3, dailyBudget: 150, anchors: ANCHORS }, SHOPS)
    const ids = r.plan.flatMap((p) => p.anchors.map((a) => a.anchor.id))
    assert.equal(new Set(ids).size, ids.length, '出现重复锚点')
  })

  test('吃+逛复合体占掉对应餐次，不再额外配店', () => {
    const r = buildItinerary({ days: 3, dailyBudget: 400, anchors: ANCHORS }, SHOPS)
    const fromAnchor = r.plan
      .flatMap((p) => p.meals)
      .filter((m) => m.fromAnchor)
    for (const m of fromAnchor) {
      assert.equal(m.shop, null, '复合体餐次不应再配一家店')
      assert.equal(m.anchor.kind, 'dining')
      assert.equal(m.anchor.mealHint, m.slot, '复合体应占自己该占的餐次')
    }
  })

  test('午餐落在上午锚点 3 km 内', () => {
    const r = buildItinerary({ days: 2, dailyBudget: 150, anchors: ANCHORS }, SHOPS)
    for (const day of r.plan) {
      const morning = day.anchors.find((a) => a.part === 'morning')?.anchor
      const lunch = day.meals.find((m) => m.slot === 'lunch' && m.shop)
      if (!morning || !lunch) continue
      const d = distanceMeters(morning, lunch.shop)
      assert.ok(d <= 3000, `${morning.name} 到午餐 ${d.toFixed(0)}m，超过 3km`)
    }
  })

  test('确定性：同样输入跑两次结果一致', () => {
    const params = { days: 2, dailyBudget: 150, anchors: ANCHORS }
    assert.deepEqual(buildItinerary(params, SHOPS), buildItinerary(params, SHOPS))
  })

  test('三档预算在锚点模式下依然产生不同花费', () => {
    const rows = [50, 150, 400].map((dailyBudget) =>
      buildItinerary({ days: 2, dailyBudget, anchors: ANCHORS }, SHOPS)
    )
    const costs = rows.map((r) => r.summary.totalCost)
    assert.ok(costs[0] < costs[1] && costs[1] < costs[2], `花费未递增: ${costs.join(' / ')}`)
  })

  test('锚点用完后给出提示，而不是静默乱排', () => {
    // 可用锚点 23 个，每天最多 3 个 → 12 天必然用尽
    const r = buildItinerary({ days: 12, dailyBudget: 150, anchors: ANCHORS }, SHOPS)
    const used = r.plan.flatMap((p) => p.anchors).length
    assert.ok(used <= usable.length, '锚点使用数超过可用数')
    const hasHint = r.plan.some((p) => p.notes.some((n) => n.includes('锚点已用完')))
    assert.ok(hasHint, '锚点用尽时应给出提示')
  })

  test('summary 区分景点数与吃逛数', () => {
    const r = buildItinerary({ days: 3, dailyBudget: 150, anchors: ANCHORS }, SHOPS)
    const s = r.summary
    assert.equal(s.anchorCount, s.attractionCount + s.diningAnchorCount)
    assert.ok(s.anchorCount > 0)
  })
})
