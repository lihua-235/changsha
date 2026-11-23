# 前端数据契约

> 由 `scripts/export_web_data.py` 生成，前端 `src/data/provider.js` 消费。
> **改动字段必须同时改这两处，并把 `schemaVersion` 加 1。**

## 文件清单（`web/public/data/`）

| 文件 | 内容 | 约体积 |
|---|---|---|
| `meta.json` | 版本、生成时间、各层条数、片区清单 | < 1 KB |
| `shops-index.json` | 跨片区轻量索引（搜索、详情定位用） | 760 KB |
| `shops-<slug>.json` | 单片区完整店铺记录 × 6 | 每片 60–200 KB（gzip） |
| `scenics.json` | 景点 | 176 KB |
| `hotels.json` | 住宿 | 916 KB |

## meta.json

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-11-23T13:20:00+08:00",
  "source": "amap place/around v5",
  "attribution": "数据来源：高德地图",
  "counts": { "shops": 9519, "scenics": 643, "hotels": 3612 },
  "districts": [{ "slug": "wuyi", "name": "五一广场坡子街", "count": 2600 }]
}
```

## Shop（`shops-*.json` 完整记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 高德 POI ID |
| `name` | string | 店名 |
| `district` | string | 片区中文名 |
| `slug` | string | 片区 ASCII 标识 |
| `lng` `lat` | number | 坐标，6 位小数 |
| `rating` | number \| null | 平台评分 |
| `cost` | number \| null | 人均消费 |
| `costSource` | `"amap"` \| `"district-median"` \| null | **填补过的必须标出来** |
| `keytag` | string \| null | 主标签 |
| `rectag` | string \| null | 推荐标签 |
| `opentimeWeek` | string \| null | 营业时间原文 |
| `tel` | string \| null | 电话 |
| `address` | string \| null | 地址 |
| `distToWuyiM` | number | 距五一广场直线距离（米） |
| `distBand` | string | `核心区(0-1km)` / `中间带(1-3km)` / `生活区(3km+)` |
| `isChain` | boolean | 是否连锁（本地多店经营口径） |
| `localScore` | number \| null | **本地认可度 1–5，标注后方有值，现为 `null`** |
| `localEvidence` | string \| null | 标注时的判断依据句 |
| `dataStatus` | `"amap-only"` \| `"annotated"` | 前端据此决定显示「待采集」还是真实分数 |

## shops-index.json（轻量索引）

同上，但只保留：
`id, name, slug, district, lng, lat, rating, cost, distBand, distToWuyiM, keytag, isChain, dataStatus`

## Scenic / Hotel

`id, name, district, slug, lng, lat, rating, cost, keytag, opentimeWeek, address, tel`

## 硬性约束（导出脚本负责保证）

1. **空值一律是 JSON `null`**，绝不能出现字符串 `"nan"`、`"None"`、`""`。
2. `cost` 缺失时用**本片区中位数**填补，并置 `costSource = "district-median"`。
3. 坐标统一保留 6 位小数。
4. 输出按 `id` 升序稳定排序 —— 同样输入必须得到逐字节相同的输出。
5. `status_flag` 非空（停业/装修中）的店铺**不导出**。
