/**
 * 数据入口（唯一）
 * ---------------------------------------------------------------
 * 前端**只**通过本文件取数。页面组件不允许直接 fetch。
 *
 * 这样做的目的：现在数据来自离线导出的静态 JSON，
 * 将来换成 Java 后端 API 时，只改这一个文件，页面一行都不用动。
 *
 * 数据文件位置：web/public/data/（由 scripts/export_web_data.py 生成）
 * 字段契约见同目录 schema.md
 */

const BASE = import.meta.env.BASE_URL + 'data/'

/** 期望的 schema 版本，与导出脚本保持一致；不一致时控制台告警 */
export const EXPECTED_SCHEMA_VERSION = 1

const cache = new Map()

async function loadJSON(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`${path} 加载失败：HTTP ${res.status}`)
  return res.json()
}

/** 带缓存；失败不留脏缓存，下次可重试 */
function once(path) {
  if (!cache.has(path)) {
    const p = loadJSON(path).catch((err) => {
      cache.delete(path)
      throw err
    })
    cache.set(path, p)
  }
  return cache.get(path)
}

/** 数据缺失时返回兜底值而不是抛错 —— 空站点也要能正常渲染 */
async function tryOnce(path, fallback) {
  try {
    return await once(path)
  } catch (err) {
    console.warn('[provider]', err.message)
    return fallback
  }
}

/* ---------------- 元信息 ---------------- */

export async function getMeta() {
  const meta = await tryOnce('meta.json', null)
  if (meta && meta.schemaVersion !== EXPECTED_SCHEMA_VERSION) {
    console.warn(
      `[provider] schema 版本不匹配：数据为 ${meta.schemaVersion}，前端期望 ${EXPECTED_SCHEMA_VERSION}。` +
        '请重跑 scripts/export_web_data.py，或同步更新前端字段。'
    )
  }
  return meta
}

export async function listDistricts() {
  const meta = await getMeta()
  return meta?.districts ?? []
}

/* ---------------- 餐饮店铺 ---------------- */

/** 跨片区轻量索引（id / 片名 / 基础字段），用于搜索与详情定位 */
export async function getShopIndex() {
  return tryOnce('shops-index.json', [])
}

/** 某片区的完整店铺列表 */
export async function listShops({ districtSlug } = {}) {
  if (!districtSlug) return []
  return tryOnce(`shops-${districtSlug}.json`, [])
}

/** 单店详情：给了片区 slug 就只加载那一个文件；没给才回退到索引查找 */
export async function getShop({ slug, id } = {}) {
  if (!id) return null
  let target = slug
  if (!target) {
    const index = await getShopIndex()
    target = index.find((s) => s.id === id)?.slug
    if (!target) return null
  }
  const list = await listShops({ districtSlug: target })
  return list.find((s) => s.id === id) ?? null
}

/** 跨片区按店名/标签搜索 */
export async function searchShops(keyword, limit = 60) {
  const kw = String(keyword ?? '').trim()
  if (!kw) return []
  const index = await getShopIndex()
  const lower = kw.toLowerCase()
  const out = []
  for (const s of index) {
    if (
      s.name?.toLowerCase().includes(lower) ||
      s.keytag?.toLowerCase().includes(lower)
    ) {
      out.push(s)
      if (out.length >= limit) break
    }
  }
  return out
}

/* ---------------- 约束数据（只用于行程排程） ---------------- */

export async function listScenics() {
  return tryOnce('scenics.json', [])
}

export async function listHotels() {
  return tryOnce('hotels.json', [])
}

/* ---------------- 行程生成 ---------------- */

/**
 * Step 3 实现（规则版）。
 * 故意先留空：行程逻辑一旦写死在前端，等真实信号接入后要重写第二遍。
 */
export async function buildItinerary(_params) {
  return null
}
