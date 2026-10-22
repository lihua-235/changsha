#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0 · 高德 POI 采集与字段可得性盘点（v2 网格版）

v1 的问题：单点 + 2000m 半径查询，实测高德单次查询最多只返回 200 条，
导致拿到的全是"权重最高的店"——正好偏向网红店，与"找小众本地店"的目标相反。

v2 的解法：把片区切成 600m 半径的小圆网格平铺（步长 900m），
每个小圆内的店铺数通常低于 200 条上限，从而更接近穷尽采集。

用法：
    1. 安装 Python 3.11+（python.org，安装时勾选 Add python.exe to PATH）
    2. 准备 Key（二选一）：
       - 同目录 key.txt，第一行写 Key
       - 或设置环境变量 AMAP_KEY
       注意：Key 必须是【Web服务】类型
    3. 全量采集：      python amap_poi_collect.py
    4. 只重建报告：    python amap_poi_collect.py --report-only
       （不调接口、不消耗配额，直接从 data/raw/ 重新生成 csv 和报告）

产出：
    data/raw/{片区}.json      原始响应（永远不要覆盖，这是你的资产）
    data/poi_all.csv          汇总表，Excel 可直接打开
    data/field_report.md      字段填充率报告 = Phase 0 的验收物
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from pathlib import Path
import urllib.parse
import urllib.request

# Windows 控制台默认 GBK，强制 UTF-8 输出，否则打印中文直接 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_URL = "https://restapi.amap.com/v5/place/around"

# 仓库根目录：所有路径都以此为基准，与当前工作目录无关（换台机器也能直接跑）
ROOT = Path(__file__).resolve().parents[1]

# 数据层：每层用不同类目码，采到不同子目录，互不干扰
#   food   = 研究对象（要标注、要建信号、要进实验）
#   scenic / hotel = 约束数据（只喂给行程生成，不标注、不进实验）
LAYERS = {
    #  层名      typecode  半径(米) 步长(米)  输出目录
    "food":   ("050000",  600,    900,      ROOT / "data"),
    "scenic": ("110000",  2500,   3500,     ROOT / "data" / "scenic"),
    "hotel":  ("100000",  1200,   1600,     ROOT / "data" / "hotel"),
}

TYPE_CODE = "050000"            # 当前层的类目码，由 --layer 决定
PAGE_SIZE = 25                  # v5 单页上限就是 25，改大无效
MAX_PAGE = 8                    # 实测：单次查询最多返回 200 条（第 9 页返回空）
REQUEST_INTERVAL = 0.35         # 请求间隔（秒）
MAX_REQUESTS = 900              # 请求总数硬上限，防止失控吃配额
GRID_RADIUS = 600               # 网格小圆半径（米）
GRID_STEP = 900                 # 网格步长（米），必须小于 2×半径才有重叠
OUT_DIR = ROOT / "data"

# 各片区中心点：大致坐标，请自己在地图上核对后微调
DISTRICTS = [
    # name,             lng,      lat,      radius
    ("五一广场坡子街",  112.9820, 28.1945, 2000),
    ("南门口",          112.9775, 28.1840, 1500),
    ("冬瓜山",          112.9860, 28.1710, 1200),
    ("四方坪",          113.0010, 28.2340, 2000),
    ("河西大学城",      112.9360, 28.1780, 2200),
    ("开福北辰",        112.9770, 28.2380, 2000),
]

_REQ = {"n": 0, "capped": 0, "cells": 0}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict, timeout: int = 20) -> dict:
    """极简 GET，只用标准库，无需安装任何依赖。"""
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{qs}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clean_key(raw: str) -> str:
    """清掉 BOM、引号、空白 —— 手工复制 Key 时最常见的三种污染。"""
    return raw.replace("\ufeff", "").strip().strip('"').strip("'").strip()


def load_key() -> str:
    key = _clean_key(os.environ.get("AMAP_KEY", ""))
    if key:
        return key
    key_file = ROOT / "key.txt"
    if key_file.exists():
        for line in key_file.read_text(encoding="utf-8-sig").splitlines():
            key = _clean_key(line)
            if key:
                return key
    sys.exit(
        f"未找到 Key。请创建 {key_file} 并写入 Key，或设置环境变量 AMAP_KEY。\n"
        "注意：Key 必须是【Web服务】类型，不能是【Web端(JS API)】类型。"
    )


# ---------------------------------------------------------------------------
# 采集：网格平铺
# ---------------------------------------------------------------------------

def grid_points(lng: float, lat: float, district_radius: float) -> list:
    """把片区切成一圈圈网格中心点，用于小半径多点覆盖。"""
    lat_deg = 110540.0                                  # 1 度纬度 ≈ 米
    lng_deg = 111320.0 * math.cos(math.radians(lat))    # 1 度经度 ≈ 米（随纬度收缩）
    n = int(district_radius // GRID_STEP)
    pts = [(lng, lat)]
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            if i == 0 and j == 0:
                continue
            dx, dy = i * GRID_STEP, j * GRID_STEP
            # 只保留落在片区圆内的网格点，外圈放宽半个半径保证边缘覆盖
            if math.hypot(dx, dy) > district_radius + GRID_RADIUS * 0.5:
                continue
            pts.append((lng + dx / lng_deg, lat + dy / lat_deg))
    return pts


def _dist_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """两点平面近似距离（米）。城市尺度足够，不必上路网。"""
    lat_deg = 110540.0
    lng_deg = 111320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lng1 - lng2) * lng_deg, (lat1 - lat2) * lat_deg)


def nearest_district(lng: float, lat: float) -> str:
    """按坐标把 POI 归属到最近的片区中心。"""
    best, best_d = "", float("inf")
    for name, dlng, dlat, _r in DISTRICTS:
        d = _dist_m(lng, lat, dlng, dlat)
        if d < best_d:
            best, best_d = name, d
    return best


def fetch_cell(key: str, lng: float, lat: float, radius: int, label: str) -> list:
    """采一个小圆。返回 POI 列表；若疑似撞到 200 条上限会记录下来。"""
    pois = []
    for page in range(1, MAX_PAGE + 1):
        if _REQ["n"] >= MAX_REQUESTS:
            print("  [!] 已达请求数上限，提前结束")
            return pois

        params = {
            "key": key,
            "location": f"{lng:.6f},{lat:.6f}",
            "radius": radius,
            "types": TYPE_CODE,
            "page_size": PAGE_SIZE,
            "page_num": page,
            "sortrule": "weight",
            # 关键：不带 show_fields=business 就拿不到 rating / cost / opentime
            "show_fields": "business,photos",
        }
        try:
            data = _get_json(BASE_URL, params)
            _REQ["n"] += 1
        except Exception as e:  # noqa: BLE001
            print(f"      [!] {label} p{page} 异常：{e}")
            break

        if str(data.get("status")) != "1":
            print(
                f"      [!] {label} p{page} 失败："
                f"{data.get('info')} / infocode={data.get('infocode')}"
            )
            break

        batch = data.get("pois") or []
        if not batch:
            break
        pois.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(REQUEST_INTERVAL)

    if len(pois) >= MAX_PAGE * PAGE_SIZE:
        _REQ["capped"] += 1
    return pois


def collect_district(key: str, name: str, lng: float, lat: float, radius: int) -> list:
    pts = grid_points(lng, lat, radius)
    print(f"  → {name}：{len(pts)} 个网格点（半径 {GRID_RADIUS}m / 步长 {GRID_STEP}m）")
    pois = []
    for idx, (glng, glat) in enumerate(pts, 1):
        got = fetch_cell(key, glng, glat, GRID_RADIUS, f"{name}#{idx}")
        _REQ["cells"] += 1
        for p in got:
            p["_district"] = name
        pois.extend(got)
        print(f"      网格 {idx}/{len(pts)} +{len(got)}（本区累计 {len(pois)}）")
        time.sleep(REQUEST_INTERVAL)

    uniq = len({p.get("id") for p in pois})
    print(f"     {name} 完成：{len(pois)} 条，去重后 {uniq} 条")
    return pois


def dedup(pois: list) -> list:
    """按 POI id 去重，并用坐标重新归属片区。

    不能沿用「哪个查询先采到就归哪个片区」——那会让先跑的片区吞掉邻区的门店，
    造成片区分布系统性偏斜（v1 实测：南门口采到 1769 条，最后只剩 840）。
    片区归属必须由坐标决定，这样结果才可复现。
    """
    seen, out = {}, []
    for p in pois:
        pid = p.get("id")
        if not pid:
            continue
        if pid in seen:
            prev = seen[pid]
            d = p.get("_district")
            if d and d not in prev.setdefault("_districts", []):
                prev["_districts"].append(d)
            continue

        p["_districts"] = [p.get("_district")] if p.get("_district") else []
        loc = str(p.get("location", "")).split(",")
        if len(loc) == 2:
            try:
                p["_district"] = nearest_district(float(loc[0]), float(loc[1]))
            except ValueError:
                pass
        seen[pid] = p
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# 落盘
# ---------------------------------------------------------------------------

def biz(p: dict, field: str) -> str:
    """安全读取 business 子字段，统一转成字符串。"""
    b = p.get("business")
    if isinstance(b, dict):
        v = b.get(field)
        if isinstance(v, list):
            v = " | ".join(str(x) for x in v if x)
        if v in ("", [], None):
            return ""
        return str(v).strip()
    return ""


def save_raw(pois: list) -> None:
    (OUT_DIR / "raw").mkdir(parents=True, exist_ok=True)
    grouped = {}
    for p in pois:
        grouped.setdefault(p.get("_district", "unknown"), []).append(p)
    for district, items in grouped.items():
        path = OUT_DIR / "raw" / f"{district}.json"
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    原始数据：{path}（{len(items)} 条）")


def load_raw() -> list:
    """从 data/raw/*.json 重新载入，供 --report-only 使用。"""
    files = sorted((OUT_DIR / "raw").glob("*.json"))
    if not files:
        sys.exit("data/raw/ 下没有文件，请先跑一次全量采集。")
    pois = []
    for f in files:
        pois.extend(json.loads(f.read_text(encoding="utf-8")))
    return dedup(pois)


# CSV 列：把真实存在的业务字段都带上
CSV_COLS = [
    "id", "name", "district", "address", "lng", "lat", "typecode", "type",
    "business_area", "rating", "cost",
    "opentime_today", "opentime_week",
    "tag", "keytag", "rectag", "tel",
]


def save_csv(pois: list) -> Path:
    csv_path = OUT_DIR / "poi_all.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for p in pois:
            loc = str(p.get("location", "")).split(",")
            row = {c: biz(p, c) for c in CSV_COLS if c not in
                   ("id", "name", "district", "address", "lng", "lat", "typecode", "type")}
            row.update({
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "district": p.get("_district", ""),
                "address": p.get("address", ""),
                "lng": loc[0] if loc else "",
                "lat": loc[1] if len(loc) > 1 else "",
                "typecode": p.get("typecode", ""),
                "type": p.get("type", ""),
            })
            w.writerow(row)
    print(f"    汇总表：{csv_path}（{len(pois)} 条）")
    return csv_path


# ---------------------------------------------------------------------------
# 字段可得性报告 —— Phase 0 的核心产出
# ---------------------------------------------------------------------------

# 字段中文名对照（没列到的字段会以原始英文名出现）
LABELS = {
    "rating": "评分",
    "cost": "人均消费",
    "opentime_today": "今日营业时间",
    "opentime_week": "每周营业时间",
    "tag": "标签",
    "keytag": "特色标签",
    "rectag": "推荐标签",
    "business_area": "所属商圈",
    "tel": "电话",
    "alias": "别名",
}


def build_report(pois: list) -> Path:
    total = max(len(pois), 1)

    # 动态统计所有 business 子字段（不写死，避免再次漏掉 opentime_week 这类字段）
    counts = {}
    for p in pois:
        b = p.get("business")
        if isinstance(b, dict):
            for k in b:
                if biz(p, k):
                    counts[k] = counts.get(k, 0) + 1

    lines = [
        "# 数据可得性结论（Phase 0 验收物）",
        "",
        f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- POI 总数（去重后）：**{len(pois)}**",
        f"- 覆盖片区：{len({p.get('_district') for p in pois})} 个",
        f"- 采集方式：{GRID_RADIUS}m 半径网格平铺，步长 {GRID_STEP}m",
        "",
        "## 一、business 子字段填充率（按实际返回动态统计）",
        "",
        "| 字段 | 含义 | 有值条数 | 填充率 | 可用性判断 |",
        "|---|---|---|---|---|",
    ]
    for field, c in sorted(counts.items(), key=lambda x: -x[1]):
        rate = c / total
        verdict = "✅ 可用" if rate >= 0.6 else ("⚠️ 部分可用" if rate >= 0.2 else "❌ 不可用")
        lines.append(
            f"| `{field}` | {LABELS.get(field, field)} | {c} | {rate:.1%} | {verdict} |"
        )

    lines += ["", "## 二、各片区样本量", "", "| 片区 | 条数 |", "|---|---|"]
    dc = {}
    for p in pois:
        k = p.get("_district", "unknown")
        dc[k] = dc.get(k, 0) + 1
    for d, c in sorted(dc.items(), key=lambda x: -x[1]):
        lines.append(f"| {d} | {c} |")

    lines += [
        "",
        "## 三、明确拿不到的字段（结论）",
        "",
        "- [ ] 评论正文 —— 高德/百度 API 均不返回，需人工采样或改用公开学术数据集",
        "- [ ] 评论数量 —— 高德无此字段",
        "- [ ] 历史客流 / 时序热度 —— 无历史数据，需周期性采集或实地观测",
        "",
        "## 四、已知局限（写进论文的『数据局限』小节）",
        "",
        f"1. **单次查询上限 200 条**：实测高德 v5 周边搜索第 9 页返回空，"
        f"故单点最多取 200 家。本版用 {GRID_RADIUS}m 网格平铺缓解，但密集商圈内"
        "个别网格仍可能触顶，覆盖率非 100%。",
        "2. **结果受 sortrule=weight 影响**：高德按自身权重排序，"
        "权重与知名度和商业活跃度相关，仍存在向「知名店」偏移的残余偏差。",
        "3. **POI 属性为快照**：rating / cost 是采集时刻的值，无历史序列。",
        "",
        "## 五、下一步",
        "",
        "标 ✅ 的字段就是 Phase 2 能直接用的信号来源。",
        "标 ❌ 的从现在起从方法设计里划掉，不要等写代码时才发现。",
        "",
        "> 本报告由脚本自动生成；请手动补充对每个字段的观感（是否准确、是否有明显脏数据）。",
    ]

    path = OUT_DIR / "field_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"    字段报告：{path}")
    return path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    global TYPE_CODE, GRID_RADIUS, GRID_STEP, OUT_DIR, MAX_REQUESTS

    ap = argparse.ArgumentParser(description="高德 POI 网格采集（分层）")
    ap.add_argument("--layer", default="food", choices=list(LAYERS),
                    help="数据层：food=餐饮 / scenic=景点 / hotel=住宿")
    ap.add_argument("--report-only", action="store_true",
                    help="只从已有 raw 重建报告，不调用接口、不消耗配额")
    ap.add_argument("--radius", type=int, default=None, help="覆盖网格半径（米）")
    ap.add_argument("--step", type=int, default=None, help="覆盖网格步长（米）")
    ap.add_argument("--max-requests", type=int, default=MAX_REQUESTS,
                    help="请求总数上限")
    args = ap.parse_args()

    TYPE_CODE, r_def, s_def, out_dir = LAYERS[args.layer]
    GRID_RADIUS = args.radius or r_def
    GRID_STEP = args.step or s_def
    OUT_DIR = out_dir
    MAX_REQUESTS = args.max_requests
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.report_only:
        print(f"[{args.layer}] 仅重建报告，不调用接口（不消耗配额）\n")
        pois = load_raw()
        print(f"从 {OUT_DIR}/raw/ 载入 {len(pois)} 条（去重后）\n")
        save_csv(pois)
        build_report(pois)
        return

    key = load_key()
    print(f"[{args.layer}] 使用 Key：{key[:6]}...{key[-4:] if len(key) > 10 else ''}")
    print(f"类目 {TYPE_CODE}，网格 {GRID_RADIUS}m / 步长 {GRID_STEP}m，"
          f"请求上限 {MAX_REQUESTS} 次\n")
    print(f"采集 {len(DISTRICTS)} 个片区\n")

    all_pois = []
    for name, lng, lat, radius in DISTRICTS:
        all_pois.extend(collect_district(key, name, lng, lat, radius))

    all_pois = dedup(all_pois)
    print(f"\n去重后共 {len(all_pois)} 条 POI")
    print(f"请求次数 {_REQ['n']} 次，网格 {_REQ['cells']} 个，"
          f"其中疑似触顶（≥200 条）的网格 {_REQ['capped']} 个\n")

    if not all_pois:
        sys.exit("一条数据都没拿到，请检查 Key 平台类型（必须 Web服务）与配额。")

    save_raw(all_pois)
    save_csv(all_pois)
    report = build_report(all_pois)

    print("\n" + "=" * 62)
    print("Phase 0 完成。请打开并补充这个文件：")
    print(f"  {report.resolve()}")
    print("=" * 62)


if __name__ == "__main__":
    main()
