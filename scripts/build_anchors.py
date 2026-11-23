#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补全锚点台账：把 data/anchors.csv 的「名称 + 我的估计值」
用高德关键字搜索补上**权威的**坐标、地址、营业时间、电话、评分。

    data/anchors.csv  ──查询──▶  data/raw_anchors/*.json（缓存）
                              └──▶  data/anchors_enriched.csv

设计原则
--------
- 时长、票价、「为什么值得去」是**人的判断**，脚本不改。
- 坐标、营业时间、电话是**事实**，只从接口取，不手写。
- 结果带缓存，重跑不重复消耗配额；`--refresh` 强制重取。
- 每条都记录数据来源，出问题时能追溯。

用法：
    python scripts/build_anchors.py
    python scripts/build_anchors.py --refresh      # 忽略缓存重新查询
"""

import argparse
import csv
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC = DATA / "anchors.csv"
CACHE = DATA / "raw_anchors"
OUT_CSV = DATA / "anchors_enriched.csv"

CST = timezone(timedelta(hours=8))
INTERVAL = 0.35

DISTRICTS = {
    "五一广场坡子街": (112.9820, 28.1945),
    "南门口": (112.9775, 28.1840),
    "冬瓜山": (112.9860, 28.1710),
    "四方坪": (113.0010, 28.2340),
    "河西大学城": (112.9360, 28.1780),
    "开福北辰": (112.9770, 28.2380),
}

# 只认景区/科教文化两类，避免把「湖南省博物馆(公交站)」当成景点
GOOD_TYPECODE_PREFIX = ("11", "14")


def read_key():
    env = __import__("os").environ.get("AMAP_KEY", "").strip()
    if env:
        return env
    f = ROOT / "key.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            k = line.replace("\ufeff", "").strip().strip('"').strip("'").strip()
            if k:
                return k
    sys.exit("未找到 Key：请放 key.txt 或设置 AMAP_KEY 环境变量")


def dist_m(a, b):
    lat_deg = 110540.0
    lng_deg = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * lng_deg, (a[1] - b[1]) * lat_deg)


def nearest_district(lng, lat):
    p = (lng, lat)
    return min(DISTRICTS.items(), key=lambda kv: dist_m(kv[1], p))[0]


def search(keyword, key):
    params = {
        "key": key,
        "keywords": keyword,
        "region": "长沙",
        "city_limit": "true",
        "page_size": "10",
        "page_num": "1",
        "show_fields": "business",
    }
    url = "https://restapi.amap.com/v5/place/text?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pick(pois, keyword):
    """在候选里选最像「那个景点」的一条

    踩过的坑（都是实测）：
      · 搜「烈士公园」会返回 62 公里外一个同名地物
      · 搜「湖南第一师范」会优先返回学校校区，而不是旧址纪念馆
    所以：名字完全一致 > 前缀一致 > 含关键词；并对校区/公交站等后缀重罚。
    """
    if not pois:
        return None

    def score(p):
        tc = str(p.get("typecode") or "")
        name = str(p.get("name") or "")
        s = 0

        # 类目质量优先：风景名胜 / 科教文化 才是真正的景点类目。
        # 只按名字完全一致去选，会把「岳麓山」选成地名地址、把「新民学会旧址」
        # 选成「职工宿舍楼」—— 两个都是实测踩到的坑。
        if tc.startswith(GOOD_TYPECODE_PREFIX):
            s += 150

        if name == keyword:
            s += 100
        elif name.startswith(keyword):
            s += 50
        elif keyword in name:
            s += 25

        for bad in ("公交站", "停车场", "地铁站", "售票", "厕所", "派出所", "小学",
                    "附小", "校区", "宿舍", "游客中心", "文创中心", "分店"):
            if bad in name:
                s -= 200
        return s

    return max(pois, key=score)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="忽略缓存，重新查询")
    args = ap.parse_args()

    if not SRC.exists():
        sys.exit(f"找不到 {SRC}")
    CACHE.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    print(f"锚点台账 {len(rows)} 条\n")

    key = None
    out = []
    stats = {"cache": 0, "api": 0, "miss": 0}

    for r in rows:
        name = r["name"]
        query = r["query"] or name
        # 缓存键带上检索词：改了 query 就会自然重新查询，不会读到旧结果
        cache_file = CACHE / f"{name}__{query.replace('/', '_')}.json"

        if cache_file.exists() and not args.refresh:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            stats["cache"] += 1
        else:
            if key is None:
                key = read_key()
            try:
                data = search(query, key)
            except Exception as exc:  # noqa: BLE001
                print(f"  ❌ {name}: 请求失败 {exc}")
                data = {"status": "0", "pois": []}
            cache_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            time.sleep(INTERVAL)
            stats["api"] += 1

        poi = pick(data.get("pois") or [], query)
        if not poi:
            stats["miss"] += 1
            print(f"  ❌ {name}: 没搜到（query={query}）")
            continue

        loc = str(poi.get("location") or "")
        try:
            lng, lat = (float(x) for x in loc.split(","))
        except ValueError:
            stats["miss"] += 1
            print(f"  ❌ {name}: 坐标异常 {loc!r}")
            continue

        biz = poi.get("business") or {}
        rating = biz.get("rating")

        out.append({
            "name": name,
            "poiName": poi.get("name"),
            "poiId": poi.get("id"),
            "typecode": poi.get("typecode"),
            "type": poi.get("type"),
            "lng": round(lng, 6),
            "lat": round(lat, 6),
            "district": nearest_district(lng, lat),
            "address": poi.get("address") or "",
            "opentimeWeek": biz.get("opentime_week") or "",
            "tel": poi.get("tel") or "",
            "rating": rating,
            "durationMin": r["duration_min"],
            "ticketCny": r["ticket_cny"],
            "mustSee": r["must_see"],
            "why": r["why"],
            # 纯景点 / 吃+逛复合体（文和友这类，自身就占掉一个餐次）
            "kind": r.get("kind") or "attraction",
            "mealHint": r.get("meal_hint") or "",
            "durationSource": r["duration_source"],
            "ticketSource": r["ticket_source"],
            "verified": r["verified"],
        })
        print(f"  ✅ {name:<22} → {poi.get('name'):<26} [{nearest_district(lng, lat)}]  tc={poi.get('typecode')}")

    fields = list(out[0].keys())
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    print(f"\n写出 {OUT_CSV}（{len(out)} 条）")
    print(f"命中统计：缓存 {stats['cache']} · 实查 {stats['api']} · 未找到 {stats['miss']}")

    # 分布检查
    from collections import Counter

    print("\n片区分布：")
    for d, n in Counter(x["district"] for x in out).most_common():
        print(f"  {d:<12} {n}")

    no_hours = sum(1 for x in out if not x["opentimeWeek"])
    no_ticket_api = sum(1 for x in out if x["ticketCny"] in ("", None))
    print(f"\n营业时间缺失 {no_hours}/{len(out)}")
    print(f"必去标记 {sum(1 for x in out if x['mustSee'] == '1')} 个")
    print("\n提醒：durationMin / ticketCny 仍是我的估计值（verified=否），寒假需实地核验。")


if __name__ == "__main__":
    main()
