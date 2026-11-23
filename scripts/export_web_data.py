#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1 · 把离线 CSV 导出成前端用的静态 JSON

    输入：data/cleaned_all.csv, data/scenic/poi_all.csv, data/hotel/poi_all.csv
    输出：web/public/data/*.json

设计要点
--------
1. 空值一律 JSON `null`。**判空只能用 pd.isna()** ——
   pandas 3.0 的 str dtype 下 `str(pd.NA)` 会产出字符串 "nan"，
   前端就会把 "nan" 当电话号码显示出来。
2. cost 缺失用本片区中位数填补，并置 costSource="district-median"，
   前端据此标「估算」。不标出来就等于伪造数据。
3. 输出按 id 升序稳定排序；generatedAt 取输入文件的最新修改时间
   （不是当前时间），因此同输入必得逐字节相同的输出。
4. 停业/装修中的店不导出。

用法：
    python scripts/export_web_data.py
"""

import gzip
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "web" / "public" / "data"

SCHEMA_VERSION = 1
CST = timezone(timedelta(hours=8))

# 片区 → ASCII slug（文件名与 URL 用）
SLUG = {
    "五一广场坡子街": "wuyi",
    "南门口": "nanmenkou",
    "冬瓜山": "dongguashan",
    "四方坪": "sifangping",
    "开福北辰": "kaifu",
    "河西大学城": "hexi",
}

FOOD_REQUIRED = [
    "id", "name", "district", "lng", "lat", "rating", "cost", "keytag",
    "rectag", "opentime_week", "tel", "address", "dist_to_wuyi_m",
    "dist_band", "is_chain", "status_flag",
]
POI_REQUIRED = ["id", "name", "district", "lng", "lat", "rating", "cost",
                "keytag", "opentime_week", "address", "tel"]


# --------------------------------------------------------------------------
# 取值助手：所有空值统一成 None
# --------------------------------------------------------------------------

def as_str(v):
    """空值 → None；字符串 "nan"/"None"/空白 也当空值处理。"""
    if v is None or pd.isna(v):
        return None
    t = str(v).strip()
    if t == "" or t.lower() in ("nan", "none", "null"):
        return None
    return t


def as_float(v, nd=6):
    if v is None or pd.isna(v):
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def as_int(v):
    if v is None or pd.isna(v):
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def as_bool(v):
    if v is None or pd.isna(v):
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "是")


def slug_of(district):
    return SLUG.get(district, "other")


# --------------------------------------------------------------------------
# 导出
# --------------------------------------------------------------------------

def export_shops():
    path = DATA / "cleaned_all.csv"
    df = pd.read_csv(path)
    missing = [c for c in FOOD_REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"❌ cleaned_all.csv 缺字段：{missing}\n   请检查 make_sample.py 的清洗输出。")

    total = len(df)
    df = df[df["status_flag"].isna()].copy()
    closed = total - len(df)

    # cost 缺失 → 片区中位数（标记来源）
    medians = df.groupby("district")["cost"].median()
    filled = 0

    shops = []
    for r in df.itertuples(index=False):
        district = as_str(r.district)
        cost = as_float(r.cost, 2)
        if cost is None:
            m = medians.get(district)
            if m is not None and not pd.isna(m):
                cost = round(float(m), 2)
                cost_source = "district-median"
                filled += 1
            else:
                cost_source = None
        else:
            cost_source = "amap"

        shops.append({
            "id": as_str(r.id),
            "name": as_str(r.name),
            "district": district,
            "slug": slug_of(district),
            "lng": as_float(r.lng),
            "lat": as_float(r.lat),
            "rating": as_float(r.rating, 1),
            "cost": cost,
            "costSource": cost_source,
            "keytag": as_str(r.keytag),
            "rectag": as_str(r.rectag),
            "opentimeWeek": as_str(r.opentime_week),
            "tel": as_str(r.tel),
            "address": as_str(r.address),
            "distToWuyiM": as_int(r.dist_to_wuyi_m),
            "distBand": as_str(r.dist_band),
            "isChain": as_bool(r.is_chain),
            # —— 以下两项需人工标注后才有值，故意留空 ——
            "localScore": None,
            "localEvidence": None,
            "dataStatus": "amap-only",
        })

    shops.sort(key=lambda x: (x["id"] or ""))
    return shops, closed, filled


def export_poi(path, label):
    df = pd.read_csv(path)
    missing = [c for c in POI_REQUIRED if c not in df.columns]
    if missing:
        sys.exit(f"❌ {path.name} 缺字段：{missing}")
    rows = []
    for r in df.itertuples(index=False):
        district = as_str(r.district)
        rows.append({
            "id": as_str(r.id),
            "name": as_str(r.name),
            "district": district,
            "slug": slug_of(district),
            "lng": as_float(r.lng),
            "lat": as_float(r.lat),
            "rating": as_float(r.rating, 1),
            # 景点/住宿的 cost 缺失率极高（97.7% / 99.8%），不做填补：
            # 填了就是伪造房价和门票，宁可留 null 让前端显示「未提供」。
            "cost": as_float(r.cost, 2),
            "keytag": as_str(r.keytag),
            "opentimeWeek": as_str(r.opentime_week),
            "address": as_str(r.address),
            "tel": as_str(r.tel),
        })
    rows.sort(key=lambda x: (x["id"] or ""))
    return rows


def snapshot_time(*paths):
    ts = max(p.stat().st_mtime for p in paths)
    return datetime.fromtimestamp(ts, CST).isoformat(timespec="seconds")


def dump(obj, path):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    path.write_text(text, encoding="utf-8")
    raw = len(text.encode("utf-8"))
    gz = len(gzip.compress(text.encode("utf-8"), 6))
    return raw, gz


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 62)
    print("导出前端数据 →", OUT)
    print("=" * 62)

    shops, closed, filled = export_shops()
    print(f"\n餐饮：{len(shops)} 家（已排除停业 {closed} 家）")
    print(f"  cost 用片区中位数填补：{filled} 家")

    # 按片区拆分
    by_slug = {}
    for s in shops:
        by_slug.setdefault(s["slug"], []).append(s)

    index_fields = ("id", "name", "slug", "district", "lng", "lat", "rating",
                    "cost", "distBand", "distToWuyiM", "keytag", "isChain", "dataStatus")
    shop_index = [{k: s[k] for k in index_fields} for s in shops]

    print("\n" + "-" * 62)
    print(f"{'文件':<28}{'条数':>7}{'原始':>11}{'gzip':>9}")
    print("-" * 62)

    total_raw = total_gz = 0
    r, g = dump(shop_index, OUT / "shops-index.json")
    total_raw += r; total_gz += g
    print(f"{'shops-index.json':<28}{len(shop_index):>7}{r/1024:>9.0f} KB{g/1024:>7.0f} KB")

    district_meta = []
    for slug in [SLUG[k] for k in SLUG]:
        rows = by_slug.get(slug, [])
        if not rows:
            continue
        r, g = dump(rows, OUT / f"shops-{slug}.json")
        total_raw += r; total_gz += g
        name = rows[0]["district"]
        district_meta.append({"slug": slug, "name": name, "count": len(rows)})
        print(f"{'shops-' + slug + '.json':<28}{len(rows):>7}{r/1024:>9.0f} KB{g/1024:>7.0f} KB")

    scenics = export_poi(DATA / "scenic" / "poi_all.csv", "scenic")
    r, g = dump(scenics, OUT / "scenics.json")
    total_raw += r; total_gz += g
    print(f"{'scenics.json':<28}{len(scenics):>7}{r/1024:>9.0f} KB{g/1024:>7.0f} KB")

    hotels = export_poi(DATA / "hotel" / "poi_all.csv", "hotel")
    r, g = dump(hotels, OUT / "hotels.json")
    total_raw += r; total_gz += g
    print(f"{'hotels.json':<28}{len(hotels):>7}{r/1024:>9.0f} KB{g/1024:>7.0f} KB")

    meta = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": snapshot_time(
            DATA / "cleaned_all.csv",
            DATA / "scenic" / "poi_all.csv",
            DATA / "hotel" / "poi_all.csv",
        ),
        "source": "amap place/around v5",
        "attribution": "数据来源：高德地图",
        "counts": {"shops": len(shops), "scenics": len(scenics), "hotels": len(hotels)},
        "districts": district_meta,
        "note": "localScore 需人工实地标注，当前全部为 null；dataStatus 全为 amap-only。",
    }
    dump(meta, OUT / "meta.json")

    print("-" * 62)
    print(f"{'合计':<28}{'':>7}{total_raw/1024/1024:>7.2f} MB{total_gz/1024:>6.0f} KB(gz)")

    # ---------- 自检 ----------
    print("\n自检：")
    problems = []
    for f in OUT.glob("*.json"):
        text = f.read_text(encoding="utf-8")
        for bad in ('"nan"', '"None"', "NaN"):
            if bad in text:
                problems.append(f"{f.name} 含脏值 {bad}")
    if problems:
        for p in problems:
            print("  ❌", p)
        sys.exit(1)
    print("  ✅ 无 \"nan\" / \"None\" / NaN 脏值")

    sample = shops[0]
    assert pd.isna(pd.NA)  # sanity
    print(f"  ✅ 抽样记录字段完整：{sample['name']} · localScore={sample['localScore']} "
          f"· dataStatus={sample['dataStatus']}")

    null_tel = sum(1 for s in shops if s["tel"] is None)
    print(f"  ✅ tel 为 null 的 {null_tel} 家（前端会显示「—」而不是 nan）")
    print(f"\n完成：{OUT}")


if __name__ == "__main__":
    main()
