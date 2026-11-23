/**
 * 行程生成 · 规则版（Step 3）
 * ---------------------------------------------------------------
 * 纯函数，不依赖 Vue，可直接用 `node --test` 跑。
 *
 * 设计立场：
 *   预算是**约束条件**，不是模式开关。三档预算各自覆盖一个价格区间，
 *   用户能看见"多花 350 元，换来的到底是什么"。
 *
 * 排序为什么以价格为主键：
 *   第一版用「距核心区最远优先」当主键，结果 150 与 400 档生成了
 *   完全相同的行程 —— 因为最远的店恰好最便宜，抬高预算不改变选择。
 *   改为价格优先后，每档在自己的区间里选"能负担的较贵的一餐"，
 *   三档才真正可比。
 *
 * 当前局限（必须在 UI 上说明）：
 *   没有 localScore，本地店倾向用「距核心区距离」代理，不是真实信号。
 */

/* ---------------- 常量 ---------------- */

export const MEAL_SLOTS = [
  { key: 'breakfast', label: '早餐', from: 7 * 60, to: 10 * 60, exclude: ['火锅烧烤', '饮品'] },
  { key: 'lunch', label: '午餐', from: 11 * 60, to: 14 * 60, exclude: ['饮品'] },
  { key: 'dinner', label: '晚餐', from: 17 * 60, to: 20 * 60, exclude: ['饮品'] },
]

/** 相邻两餐最大直线距离：超过就不算"可执行的一天"了 */
const MAX_LEG_M = 2200

export const BUDGET_TIERS = [
  {
    value: 50,
    label: '50 元 / 天',
    headline: '粉面小吃',
    desc: '单人三餐，以粉面和小吃为主',
  },
  {
    value: 150,
    label: '150 元 / 天',
    headline: '可进馆子',
    desc: '含一顿正经湘菜或招牌菜',
  },
  {
    value: 400,
    label: '400 元 / 天',
    headline: '含高价店',
    desc: '招牌菜与网红店都可以安排',
  },
]

/** 预算是上限，也要有下限，否则 400 档会退化成"最便宜的店" */
const PRICE_FLOOR_RATIO = 0.4

/** keytag 里这些值是类目兜底，不是菜品 */
const NON_DISH_MARKERS = ['餐饮', ',', '，']

/**
 * 菜品粗分类：用于"同一天不重复"。
 * 不做这层聚合，"米粉 / 牛肉粉 / 面馆"会被当成三种不同菜，
 * 结果一天吃三顿粉。
 */
const DISH_GROUPS = [
  { key: '粉面', test: /粉|面|米线|馄饨|饺|抄手/ },
  { key: '饮品', test: /奶茶|茶饮|咖啡|茶座|果汁|饮料|酒吧/ },
  { key: '火锅烧烤', test: /火锅|烧烤|烤肉|串|小龙虾|口味虾/ },
  { key: '湘菜', test: /湘菜|湖南菜|本帮/ },
  { key: '米饭快餐', test: /快餐|盖码|煲仔|饭|粥/ },
  { key: '小吃卤味', test: /小吃|卤味|炸|饼|包|臭豆腐|糖油/ },
  { key: '西餐烘焙', test: /西餐|意面|披萨|牛排|糕点|烘焙|汉堡/ },
]

/* ---------------- 营业时间解析 ---------------- */

/**
 * 把 `opentimeWeek` 原文解析成可判断的时间段。
 * 实测有 12 种结构，这里只做保守提取：抓所有 HH:MM-HH:MM。
 */
export function parseOpeningHours(raw) {
  const result = { known: false, allDay: false, segments: [], tempClosed: false }
  if (typeof raw !== 'string' || !raw.trim()) return result

  const text = raw.trim()
  result.tempClosed = /全天关闭|暂停营业/.test(text)

  if (/24\s*小时|全天营业/.test(text)) {
    return { ...result, known: true, allDay: true }
  }

  const re = /(\d{1,2}):(\d{2})\s*[-–—~至]\s*(\d{1,2}):(\d{2})/g
  let m
  while ((m = re.exec(text)) !== null) {
    const open = Number(m[1]) * 60 + Number(m[2])
    let close = Number(m[3]) * 60 + Number(m[4])
    if (close <= open) close += 24 * 60 // 跨午夜，例如 16:30-02:00
    if (open >= 0 && open < 24 * 60) result.segments.push({ open, close })
  }

  result.known = result.segments.length > 0
  return result
}

/** 该店是否在某个时段内营业。'unknown' 表示无数据，由调用方决定 */
export function openInSlot(parsed, slot) {
  if (!parsed.known) return 'unknown'
  if (parsed.allDay) return true
  return parsed.segments.some((s) => s.open < slot.to && s.close > slot.from)
}

/* ---------------- 菜品分类 ---------------- */

/** 原始菜品标签；类目兜底值返回 null */
export function dishTag(shop) {
  const t = (shop.keytag || '').trim()
  if (!t) return null
  if (NON_DISH_MARKERS.some((m) => t.includes(m))) return null
  if (t.length > 8) return null
  return t
}

/** 粗分类，用于去重与餐次适配 */
export function dishGroup(shop) {
  const tag = dishTag(shop)
  if (!tag) return null
  for (const g of DISH_GROUPS) {
    if (g.test.test(tag)) return g.key
  }
  return tag
}

/* ---------------- 工具 ---------------- */

/** 两点间直线距离（米）。也用在前端展示"上一餐到这餐多远" */
export function distanceMeters(a, b) {
  const latDeg = 110540
  const lngDeg = 111320 * Math.cos((((a.lat ?? 0) + (b.lat ?? 0)) / 2) * (Math.PI / 180))
  return Math.hypot(((a.lng ?? 0) - (b.lng ?? 0)) * lngDeg, ((a.lat ?? 0) - (b.lat ?? 0)) * latDeg)
}

/* ---------------- 核心：生成一天 ---------------- */

function buildDay(pool, perMeal, usedIds) {
  const meals = []
  const notes = []
  const usedGroups = new Set()
  const floor = perMeal * PRICE_FLOOR_RATIO

  for (const slot of MEAL_SLOTS) {
    const base = pool.filter((s) => !usedIds.has(s.id))

    // 逐级放宽，每一级都记录，诚实告诉用户"这里降级了"
    const attempts = [
      {
        level: 'strict',
        test: (s) => {
          const c = s.cost ?? Infinity
          return c <= perMeal && c >= floor
        },
      },
      { level: 'no-floor', test: (s) => (s.cost ?? Infinity) <= perMeal },
      { level: 'any', test: () => true },
    ]

    let picked = null
    let level = null

    for (const attempt of attempts) {
      const byBudget = base.filter(attempt.test)
      const byGroup = byBudget.filter((s) => {
        const g = dishGroup(s)
        if (g === null) return true
        if (usedGroups.has(g)) return false
        return !(slot.exclude || []).includes(g)
      })
      const byHours = byGroup.filter((s) => {
        const r = openInSlot(parseOpeningHours(s.opentimeWeek), slot)
        return r === true || r === 'unknown'
      })

      // 时段的菜品适配优先，其次才退回只看预算
      let finalPool = byHours.length ? byHours : byGroup
      if (!finalPool.length) continue

      // 路线可行性：优先选离上一餐不远的店，避免一天跑十几公里。
      // 找不到落点时才放宽，这样"可执行"是被优先保证的。
      const prev = meals[meals.length - 1]
      if (prev) {
        const near = finalPool.filter((s) => distanceMeters(prev.shop, s) <= MAX_LEG_M)
        if (near.length) finalPool = near
      }

      // 价格降序：在本档区间内"能负担的较贵的一餐"
      // 距离降序：同价时优先离核心区更远（本地店代理）
      // id 升序：保证确定性
      const sorted = [...finalPool].sort((a, b) => {
        const ca = a.cost ?? -1
        const cb = b.cost ?? -1
        if (cb !== ca) return cb - ca
        const da = a.distToWuyiM ?? -1
        const db = b.distToWuyiM ?? -1
        if (db !== da) return db - da
        return String(a.id).localeCompare(String(b.id))
      })

      picked = sorted[0]
      level = attempt.level
      break
    }

    if (!picked) {
      notes.push(`${slot.label}：该片区已无可安排的店`)
      continue
    }

    if (level !== 'strict') {
      notes.push(
        `${slot.label}：该片区在 ${Math.round(floor)}–${Math.round(perMeal)} 元区间内无可选，已放宽`
      )
    }

    const parsed = parseOpeningHours(picked.opentimeWeek)
    if (!parsed.known) notes.push(`${slot.label}：${picked.name} 营业时间未知`)
    if (parsed.tempClosed) notes.push(`${slot.label}：${picked.name} 有临时闭店公告，请电话确认`)

    const group = dishGroup(picked)
    if (group) usedGroups.add(group)
    usedIds.add(picked.id)

    meals.push({
      slot: slot.key,
      slotLabel: slot.label,
      shop: picked,
      dishTag: dishTag(picked),
      dishGroup: group,
      cost: picked.cost ?? null,
      estimatedCost: picked.costSource === 'district-median',
      hoursKnown: parsed.known,
      relaxed: level !== 'strict',
    })
  }

  let legMeters = 0
  for (let i = 1; i < meals.length; i += 1) {
    const leg = distanceMeters(meals[i - 1].shop, meals[i].shop)
    if (leg > MAX_LEG_M) {
      notes.push(
        `${meals[i].slotLabel}：距上一餐 ${(leg / 1000).toFixed(1)} km，当天路线偏散，建议打车`
      )
    }
    legMeters += leg
  }

  return { meals, notes, legMeters }
}

/* ---------------- 对外：生成整份行程 ---------------- */

export function buildItinerary({ days, dailyBudget, districtSlugs }, shops) {
  const nDays = Math.max(1, Math.floor(days || 1))
  const budget = Number(dailyBudget) || 50
  const perMeal = budget / 3

  const slugs = districtSlugs?.length
    ? districtSlugs
    : [...new Set(shops.map((s) => s.slug))].sort()

  const usedIds = new Set()
  const plan = []
  const notes = []

  for (let d = 0; d < nDays; d += 1) {
    const slug = slugs[d % slugs.length]
    const pool = shops.filter((s) => s.slug === slug)
    if (!pool.length) {
      notes.push(`第 ${d + 1} 天：片区「${slug}」没有数据`)
      plan.push({ dayIndex: d, slug, district: slug, meals: [], notes: [], legMeters: 0 })
      continue
    }
    const day = buildDay(pool, perMeal, usedIds)
    plan.push({
      dayIndex: d,
      slug,
      district: pool[0]?.district ?? slug,
      meals: day.meals,
      notes: day.notes,
      legMeters: Math.round(day.legMeters),
    })
  }

  const allMeals = plan.flatMap((p) => p.meals)
  const totalCost = allMeals.reduce((sum, m) => sum + (m.cost ?? 0), 0)
  const chainCount = allMeals.filter((m) => m.shop.isChain).length
  const localProxyCount = allMeals.filter((m) => (m.shop.distToWuyiM ?? 0) >= 2000).length

  const summary = {
    days: nDays,
    dailyBudget: budget,
    perMealBudget: Math.round(perMeal * 100) / 100,
    priceFloor: Math.round(perMeal * PRICE_FLOOR_RATIO),
    mealCount: allMeals.length,
    totalCost: Math.round(totalCost),
    avgPerMeal: allMeals.length ? Math.round((totalCost / allMeals.length) * 10) / 10 : 0,
    dishTypeCount: new Set(allMeals.map((m) => m.dishGroup).filter(Boolean)).size,
    chainCount,
    chainRate: allMeals.length ? Math.round((chainCount / allMeals.length) * 100) : 0,
    localProxyCount,
    estimatedCostCount: allMeals.filter((m) => m.estimatedCost).length,
    unknownHoursCount: allMeals.filter((m) => !m.hoursKnown).length,
    relaxedCount: allMeals.filter((m) => m.relaxed).length,
    totalLegMeters: plan.reduce((sum, p) => sum + p.legMeters, 0),
  }

  return {
    plan,
    summary,
    notes: [
      ...notes,
      '排序暂用「距核心区距离」作本地店代理，不是真实的本地认可度 —— 该指标需实地标注后才能启用。',
    ],
  }
}

/** 同一批参数跑三档预算，用于并排对比 */
export function compareTiers({ days, districtSlugs }, shops, tiers = BUDGET_TIERS.map((t) => t.value)) {
  return tiers.map((dailyBudget) => {
    const r = buildItinerary({ days, dailyBudget, districtSlugs }, shops)
    return {
      tier:
        BUDGET_TIERS.find((t) => t.value === dailyBudget) ?? {
          value: dailyBudget,
          label: `${dailyBudget} 元 / 天`,
        },
      summary: r.summary,
      shops: r.plan.map((p) => ({
        dayIndex: p.dayIndex,
        district: p.district,
        names: p.meals.map((m) => m.shop.name),
      })),
    }
  })
}
