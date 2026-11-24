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
  {
    key: 'breakfast',
    label: '早餐',
    from: 7 * 60,
    to: 10 * 60,
    exclude: ['火锅烧烤', '饮品'],
    // 早餐偏好：粉面、粥饭、小吃。不设这条会排出「酱板鸭当早餐」
    prefer: ['粉面', '米饭快餐', '小吃卤味'],
  },
  { key: 'lunch', label: '午餐', from: 11 * 60, to: 14 * 60, exclude: ['饮品', '甜品烘焙'] },
  { key: 'dinner', label: '晚餐', from: 17 * 60, to: 20 * 60, exclude: ['饮品', '甜品烘焙'] },
]

/** 名字里带这些的是内部餐饮，不是给游客的 */
const UNWANTED_NAME = /员工餐厅|职工餐厅|员工食堂|内部|食堂/

function isUnwanted(shop) {
  return UNWANTED_NAME.test(shop?.name || '')
}

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

/**
 * 每日预算的分配：早餐占比小且封顶，其余给午晚餐。
 * 之前三餐平分导致 150 元档排出 47 元的早餐 —— 没人这么吃早饭。
 */
const BREAKFAST_SHARE = 0.2
const BREAKFAST_CAP = 25

export function mealBudgets(dailyBudget) {
  const bf = Math.min(dailyBudget * BREAKFAST_SHARE, BREAKFAST_CAP)
  const rest = Math.max(0, dailyBudget - bf)
  return { breakfast: bf, lunch: rest / 2, dinner: rest / 2 }
}

/** 单日移动上限（各段直线距离合计） */
const MAX_DAY_LEG_M = 12000

/**
 * 节奏档位 —— 抄穷游的三选一，它问的是「一天想玩多久」，
 * 这个比「每天花多少钱」更容易回答。
 */
export const PACES = [
  { key: 'relaxed', label: '宽松安排', desc: '每天游览 4–6 小时', maxAnchors: 1, maxAnchorMinutes: 360 },
  { key: 'normal', label: '适中安排', desc: '每天游览 6–10 小时', maxAnchors: 2, maxAnchorMinutes: 600 },
  { key: 'tight', label: '紧凑安排', desc: '每天游览 11–16 小时', maxAnchors: 3, maxAnchorMinutes: 960 },
]

export const DEFAULT_PACE = 'normal'

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
  { key: '正餐西式', test: /西餐|意面|披萨|牛排|汉堡/ },
  // 甜品单独成类：它出现在午晚餐里就是错的（实测排出过「蛋糕店当午餐」）
  { key: '甜品烘焙', test: /糕点|烘焙|蛋糕|甜品|冰淇淋|布丁/ },
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

/* ---------------- 换一批：种子 + top-K 抽样 ----------------
 *
 * 为什么需要它：算法原本完全确定，同样的参数永远排出同一份行程，
 * 但界面上写着「重新生成」，用户会以为会变 —— 这是 UI 在撒谎。
 *
 * 做法：先按原有标准排好序（质量下限有保证），再在**前 K 名**里
 * 按 seed 选一个。这样：
 *   · 给定 (参数, seed) 结果依然唯一 —— 论文的「可复现」不受影响
 *   · 换个 seed 得到不同但同样合格的安排
 *   · 永远不会为了"不同"而排出烂店
 *
 * seed = 0 时直接取第一名，保持原有行为（旧测试与示例行程不受影响）。
 */

/** FNV-1a，纯为打散用，不需要密码学强度 */
function hash32(str) {
  let h = 2166136261
  for (let i = 0; i < str.length; i += 1) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

/** 在前 K 名里按种子挑一个 */
export function pickFromTopK(sorted, k, seed, magic) {
  if (!sorted.length) return null
  if (!seed) return sorted[0]
  const n = Math.min(k, sorted.length)
  return sorted[hash32(`${seed}|${magic}`) % n]
}

/** 抽样池的大小：越大越随机，越小越稳。5 是个折中 */
const TOP_K = 5

/* ---------------- 核心：生成一天 ---------------- */

function buildDay(pool, budgets, usedIds, seed) {
  const meals = []
  const notes = []
  const usedGroups = new Set()

  for (const slot of MEAL_SLOTS) {
    const perMeal = budgets[slot.key] ?? 0
    const floor = perMeal * PRICE_FLOOR_RATIO
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
        if (isUnwanted(s)) return false
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

      picked = pickFromTopK(sorted, TOP_K, seed, `district|${slot.key}|${attempt.level}`)
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

/** 片区模式：按片区轮转选三餐（没有锚点时用这个） */
function buildDistrictItinerary({ days, dailyBudget, districtSlugs, seed = 0 }, shops) {
  const nDays = Math.max(1, Math.floor(days || 1))
  const budget = Number(dailyBudget) || 50
  const budgets = mealBudgets(budget)
  const perMeal = budget / 3
  const seedNum = Math.max(0, Math.floor(Number(seed) || 0))

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
    const day = buildDay(pool, budgets, usedIds, seedNum)
    if (day.legMeters > MAX_DAY_LEG_M) {
      day.notes.push(
        `当天移动 ${(day.legMeters / 1000).toFixed(1)} km，超过 ${MAX_DAY_LEG_M / 1000} km 上限，建议打车或换近一点的店`
      )
    }
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
    budgets: {
      breakfast: Math.round(budgets.breakfast),
      lunch: Math.round(budgets.lunch),
      dinner: Math.round(budgets.dinner),
    },
    priceFloor: Math.round(perMeal * PRICE_FLOOR_RATIO),
    seed: seedNum,
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
export function compareTiers(params, shops, tiers = BUDGET_TIERS.map((t) => t.value)) {
  return tiers.map((dailyBudget) => {
    const r = buildItinerary({ ...params, dailyBudget }, shops)
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
        names: p.meals.map((m) => m.shop?.name ?? m.anchor?.name ?? '—'),
      })),
      anchors: r.plan.map((p) => ({
        dayIndex: p.dayIndex,
        names: (p.anchors ?? []).map((a) => a.anchor.name),
      })),
    }
  })
}

/* =================================================================
   锚点模式（anchor-first）
   -----------------------------------------------------------------
   真实旅游是「先去哪玩，再就近吃」，不是「先定吃哪家，再跑过去」。
   所以这里换成：先定当天 1–2 个景点锚点（+ 可选的夜间锚点），
   三餐就在锚点周边找，找不够再逐级放宽半径。

   吃+逛复合体（文和友、火宫殿）特殊处理：它本身就是一顿饭，
   占掉对应餐次，不再额外配餐，否则会出现「逛文和友 + 在文和友吃」的重复。
   ================================================================= */

const ANCHOR_MEAL_RADIUS = [800, 1500, 3000]
/** 同一天两个锚点最远 9km：跨江（岳麓山 ↔ 五一广场 约 6km）还算合理 */
const MAX_ANCHOR_LEG_M = 9000

function usableAnchors(anchors) {
  return (anchors ?? []).filter((a) => a.foodAvailable && a.lng != null && a.lat != null)
}

function pickAnchor(candidates, used, filter, seed, magic = 'anchor') {
  const pool = candidates.filter((a) => !used.has(a.id)).filter(filter)
  if (!pool.length) return null
  const sorted = [...pool].sort((a, b) => {
    if (a.mustSee !== b.mustSee) return a.mustSee ? -1 : 1
    // 离市中心近的先排，减少跨城
    const da = Math.abs((a.lng ?? 0) - 112.982) + Math.abs((a.lat ?? 0) - 28.1945)
    const db = Math.abs((b.lng ?? 0) - 112.982) + Math.abs((b.lat ?? 0) - 28.1945)
    if (da !== db) return da - db
    return String(a.id).localeCompare(String(b.id))
  })
  return pickFromTopK(sorted, TOP_K, seed, magic)
}

/** 在锚点周边找一家店：半径逐级放宽，价格档由宽到窄 */
function pickMealNear(pool, center, perMeal, slot, usedIds, usedGroups, seed) {
  const floor = perMeal * PRICE_FLOOR_RATIO
  const attempts = [
    {
      level: 'strict',
      test: (s) => (s.cost ?? Infinity) <= perMeal && (s.cost ?? Infinity) >= floor,
    },
    { level: 'no-floor', test: (s) => (s.cost ?? Infinity) <= perMeal },
    { level: 'any', test: () => true },
  ]

  for (const radius of ANCHOR_MEAL_RADIUS) {
    const near = pool.filter((s) => !usedIds.has(s.id) && distanceMeters(center, s) <= radius)
    if (!near.length) continue

    for (const attempt of attempts) {
      const byBudget = near.filter(attempt.test)
      const byGroup = byBudget.filter((s) => {
        if (isUnwanted(s)) return false
        const g = dishGroup(s)
        if (g === null) return true
        if (usedGroups.has(g)) return false
        return !(slot.exclude || []).includes(g)
      })
      // 时段偏好（如早餐偏粉面）先筛一遍，筛空了再退回
      let preferMissed = false
      if (slot.prefer) {
        const pref = byGroup.filter((s) => slot.prefer.includes(dishGroup(s)))
        if (!pref.length && !byGroup.length) continue
        if (pref.length) {
          byGroup.splice(0, byGroup.length, ...pref)
        } else {
          preferMissed = true
        }
      }
      const byHours = byGroup.filter((s) => {
        const r = openInSlot(parseOpeningHours(s.opentimeWeek), slot)
        return r === true || r === 'unknown'
      })
      const finalPool = byHours.length ? byHours : byGroup
      if (!finalPool.length) continue

      // 与片区模式的关键差别：这里**离锚点越近越优先**，
      // 因为「顺路」才是锚点模式要保证的，而不是「离核心区远 = 本地店」
      const sorted = [...finalPool].sort((a, b) => {
        const ca = a.cost ?? -1
        const cb = b.cost ?? -1
        if (cb !== ca) return cb - ca
        const da = distanceMeters(center, a)
        const db = distanceMeters(center, b)
        if (da !== db) return da - db
        return String(a.id).localeCompare(String(b.id))
      })
      return {
        shop: pickFromTopK(sorted, TOP_K, seed, `meal|${slot.key}|${radius}|${attempt.level}`),
        level: attempt.level,
        radius,
        preferMissed,
      }
    }
  }
  return null
}

function buildAnchorDay(dayIndex, anchors, shops, budgets, usedAnchorIds, usedShopIds, pace, seed) {
  const notes = []
  const usedGroups = new Set()
  const candidates = usableAnchors(anchors)
  const P = PACES.find((p) => p.key === pace) ?? PACES[1]

  // 按节奏档位决定一天排几个锚点、游览时间上限多少
  const picks = []
  const taken = new Set(usedAnchorIds)

  function tryPick(part, filter) {
    if (picks.length >= P.maxAnchors) return
    const usedMin = picks.reduce((sum, p) => sum + (p.anchor.durationMin ?? 90), 0)
    // 把游览时长上限放进筛选条件：否则可能选中一个太长的锚点，
    // 发现超时后被丢弃，白白浪费一个名额
    const a = pickAnchor(
      candidates,
      taken,
      (x) => filter(x) && usedMin + (x.durationMin ?? 90) <= P.maxAnchorMinutes,
      seed,
      part
    )
    if (!a) return
    picks.push({ part, anchor: a })
    taken.add(a.id)
  }

  tryPick('morning', (a) => a.dayPart !== 'night')
  tryPick('afternoon', picks.length ? (a) => distanceMeters(picks[0].anchor, a) <= MAX_ANCHOR_LEG_M : () => true)
  tryPick('night', (a) => a.dayPart === 'night')

  for (const p of picks) usedAnchorIds.add(p.anchor.id)

  const dayAnchors = picks
  const morning = picks.find((p) => p.part === 'morning')?.anchor ?? null
  const afternoon = picks.find((p) => p.part === 'afternoon')?.anchor ?? null
  const night = picks.find((p) => p.part === 'night')?.anchor ?? null
  const chosen = [morning, afternoon, night].filter(Boolean)

  const morningCenter = morning ?? afternoon ?? night ?? null
  const dinnerCenter = afternoon ?? morning ?? night ?? null

  const meals = []
  for (const slot of MEAL_SLOTS) {
    const perMeal = budgets[slot.key] ?? 0

    // 吃+逛复合体先占位：它就是这一餐
    const dining = chosen.find((a) => a.kind === 'dining' && a.mealHint === slot.key)
    if (dining) {
      usedGroups.add('dining')
      meals.push({
        slot: slot.key,
        slotLabel: slot.label,
        shop: null,
        anchor: dining,
        dishTag: null,
        dishGroup: 'dining',
        cost: null,
        estimatedCost: false,
        hoursKnown: Boolean(dining.opentimeWeek),
        relaxed: false,
        fromAnchor: true,
      })
      continue
    }

    const center = slot.key === 'dinner' ? dinnerCenter : morningCenter
    if (!center) {
      notes.push(`${slot.label}：当天没有可用锚点，无法就近安排`)
      continue
    }

    const picked = pickMealNear(shops, center, perMeal, slot, usedShopIds, usedGroups, seed)
    if (!picked) {
      notes.push(`${slot.label}：锚点周边 3 km 内没有可选餐厅`)
      continue
    }

    if (picked.level !== 'strict') {
      notes.push(`${slot.label}：锚点周边该价位无可选，已放宽到 ${Math.round(perMeal)} 元以内`)
    }
    if (picked.radius > 800) {
      notes.push(`${slot.label}：锚点 800 m 内不够选，已放宽到 ${picked.radius} m 内`)
    }
    if (picked.preferMissed) {
      notes.push(`${slot.label}：周边没有${slot.prefer.join('/')}类的店，品类已放宽`)
    }

    const parsed = parseOpeningHours(picked.shop.opentimeWeek)
    if (!parsed.known) notes.push(`${slot.label}：${picked.shop.name} 营业时间未知`)

    const group = dishGroup(picked.shop)
    if (group) usedGroups.add(group)
    usedShopIds.add(picked.shop.id)

    meals.push({
      slot: slot.key,
      slotLabel: slot.label,
      shop: picked.shop,
      anchor: null,
      dishTag: dishTag(picked.shop),
      dishGroup: group,
      cost: picked.shop.cost ?? null,
      estimatedCost: picked.shop.costSource === 'district-median',
      hoursKnown: parsed.known,
      relaxed: picked.level !== 'strict',
      fromAnchor: false,
      searchRadius: picked.radius,
    })
  }

  if (picks.length < P.maxAnchors) {
    notes.push(
      `「${P.label}」应排 ${P.maxAnchors} 个锚点，实际只有 ${picks.length} 个 —— 锚点不够了，建议缩短天数或补充清单`
    )
  }

  // 当天走过的路径：锚点 → 午餐 → 锚点 → 晚餐 → 夜间锚点
  const path = []
  if (morning) path.push(morning)
  const lunch = meals.find((m) => m.slot === 'lunch')
  if (lunch?.shop) path.push(lunch.shop)
  if (afternoon) path.push(afternoon)
  const dinner = meals.find((m) => m.slot === 'dinner')
  if (dinner?.shop) path.push(dinner.shop)
  if (night) path.push(night)

  let legMeters = 0
  for (let i = 1; i < path.length; i += 1) {
    legMeters += distanceMeters(path[i - 1], path[i])
  }

  if (legMeters > MAX_DAY_LEG_M) {
    notes.push(
      `当天移动 ${(legMeters / 1000).toFixed(1)} km，超过 ${MAX_DAY_LEG_M / 1000} km 上限，建议打车`
    )
  }

  return { anchors: dayAnchors, meals, notes, legMeters }
}

/** 锚点模式：先定每天的锚点，再就近安排三餐 */
function buildAnchorItinerary({ days, dailyBudget, anchors, pace = DEFAULT_PACE, seed = 0 }, shops) {
  const nDays = Math.max(1, Math.floor(days || 1))
  const budget = Number(dailyBudget) || 50
  const perMeal = budget / 3
  const budgets = mealBudgets(budget)
  const paceKey = PACES.some((p) => p.key === pace) ? pace : DEFAULT_PACE
  const seedNum = Math.max(0, Math.floor(Number(seed) || 0))

  const usedAnchorIds = new Set()
  const usedShopIds = new Set()
  const plan = []
  const notes = []

  for (let d = 0; d < nDays; d += 1) {
    const day = buildAnchorDay(
      d, anchors, shops, budgets, usedAnchorIds, usedShopIds, paceKey, seedNum
    )
    plan.push({
      dayIndex: d,
      district: day.anchors[0]?.anchor.district ?? '',
      anchors: day.anchors,
      meals: day.meals,
      notes: day.notes,
      legMeters: Math.round(day.legMeters),
    })
  }

  const allMeals = plan.flatMap((p) => p.meals)
  const shopMeals = allMeals.filter((m) => m.shop)
  const anchorMeals = allMeals.filter((m) => m.fromAnchor)
  const totalCost = shopMeals.reduce((sum, m) => sum + (m.cost ?? 0), 0)
  const chainCount = shopMeals.filter((m) => m.shop.isChain).length
  const allAnchors = plan.flatMap((p) => p.anchors.map((a) => a.anchor))

  const summary = {
    days: nDays,
    dailyBudget: budget,
    perMealBudget: Math.round(perMeal * 100) / 100,
    budgets: {
      breakfast: Math.round(budgets.breakfast),
      lunch: Math.round(budgets.lunch),
      dinner: Math.round(budgets.dinner),
    },
    priceFloor: Math.round(perMeal * PRICE_FLOOR_RATIO),
    mealCount: allMeals.length,
    totalCost: Math.round(totalCost),
    avgPerMeal: shopMeals.length
      ? Math.round((totalCost / shopMeals.length) * 10) / 10
      : 0,
    dishTypeCount: new Set(shopMeals.map((m) => m.dishGroup).filter(Boolean)).size,
    chainCount,
    chainRate: shopMeals.length ? Math.round((chainCount / shopMeals.length) * 100) : 0,
    localProxyCount: shopMeals.filter((m) => (m.shop.distToWuyiM ?? 0) >= 2000).length,
    estimatedCostCount: shopMeals.filter((m) => m.estimatedCost).length,
    unknownHoursCount: allMeals.filter((m) => !m.hoursKnown).length,
    relaxedCount: allMeals.filter((m) => m.relaxed).length,
    totalLegMeters: plan.reduce((sum, p) => sum + p.legMeters, 0),
    anchorCount: allAnchors.length,
    diningAnchorCount: allAnchors.filter((a) => a.kind === 'dining').length,
    attractionCount: allAnchors.filter((a) => a.kind !== 'dining').length,
    pace: paceKey,
    paceLabel: PACES.find((p) => p.key === paceKey)?.label ?? '',
    seed: seedNum,
    anchorMinutes: allAnchors.reduce((sum, a) => sum + (a.durationMin ?? 0), 0),
  }

  return {
    plan,
    summary,
    notes: [
      ...notes,
      '锚点来自人工整理的清单；游览时长与票价为估计值，尚未实地核验。',
      '餐厅在锚点周边 800 m 内优先，不够时逐级放宽 —— 每条放宽都会单独提示。',
    ],
  }
}

/**
 * 对外入口：给了 anchors 就走锚点模式，否则维持片区模式。
 * 保持向后兼容，旧调用方不用改。
 */
export function buildItinerary(params, shops) {
  const anchors = params?.anchors
  if (Array.isArray(anchors) && anchors.length) {
    return buildAnchorItinerary(params, shops)
  }
  return buildDistrictItinerary(params, shops)
}
