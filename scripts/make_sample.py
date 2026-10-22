#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 · 数据清洗 + 分层抽样

输入：data/poi_all.csv（amap_poi_collect.py 的产出）
输出：
    data/cleaned_all.csv    清洗后全量（供 Phase 2 算信号用）
    data/sample_150.csv     实地核验清单 —— 你的扫街路线表（带标注空列）
    data/sample_report.md   抽样说明（写进论文"数据采集"一节）

用法：
    python make_sample.py
    python make_sample.py --n 180 --seed 42

设计要点（答辩时会被问，先想清楚）：
 1. 连锁判定口径 = "在本次采集范围内同名主品牌 >= 3 家"，即"长沙本地多店经营"，
    而非全国连锁。这正好对应"本地商业化程度"这个信号。
 2. 分层 = 距离带（**均分名额**）→ 片区（按比例）→ 评分档（按配额）。
    距离带刻意均分：核心区在全量只占约 12%，按比例抽不足以检验核心假设。
    评分档刻意抬高低分比例：对比度全在这里，全抽高分店模型学不到东西。
    这两处都是实验设计，不是抽样错误，论文里必须主动解释。
 3. 随机种子固定，结果可复现。
"""

import argparse
import math
import re
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

DATA = Path(__file__).resolve().parents[1] / "data"

# 与采集脚本保持一致的片区中心
DISTRICTS = {
    "五一广场坡子街": (112.9820, 28.1945),
    "南门口": (112.9775, 28.1840),
    "冬瓜山": (112.9860, 28.1710),
    "四方坪": (113.0010, 28.2340),
    "河西大学城": (112.9360, 28.1780),
    "开福北辰": (112.9770, 28.2380),
}
WUYI = (112.9820, 28.1945)          # 游客核心基准点

DIST_BINS = [0, 1000, 3000, 10**9]
DIST_LABELS = ["核心区(0-1km)", "中间带(1-3km)", "生活区(3km+)"]

RATING_BINS = [0, 3.5, 4.3, 5.01]
RATING_LABELS = ["低(<3.5)", "中(3.5-4.3)", "高(>=4.3)"]
# 层内配额比例：低分刻意多留，因为对比度就在这里
RATING_QUOTA = {"低(<3.5)": 0.30, "中(3.5-4.3)": 0.40, "高(>=4.3)": 0.30}

MIN_PER_CELL = 4       # 层内最少抽几家（防止某片区被抽空）
MAX_PER_CELL = 22      # 层内上限，防止某一片区吃掉全部名额

ANN_COLS = [
    "本地认可度(1-5)",
    "游客浓度(1-5)",
    "是否网红店(是/否/疑似)",
    "判断依据(一句话)",
    "是否已停业(是/否)",
    "标注备注",
]


# ---------------------------------------------------------------------------

def dist_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    lat_deg = 110540.0
    lng_deg = 111320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lng1 - lng2) * lng_deg, (lat1 - lat2) * lat_deg)


def main_brand(name: str) -> str:
    """剥掉括号里的分店后缀，得到主品牌名。

    高德店名形如「蜜雪冰城(中天国际店)」「茶颜悦色（坡子街店）」，
    不剥离就会把同一品牌当成不同店。中英文括号都要处理。
    """
    if not isinstance(name, str):
        return ""
    s = re.sub(r"[（(【\[][^）)】\]]*[）)】\]]", "", name)
    s = re.sub(r"\s+", "", s)
    # 再剥掉结尾的"店/分店/总店"等无信息后缀
    s = re.sub(r"(分店|总店|旗舰店|门店)$", "", s)
    return s.strip()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 坐标
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df = df.dropna(subset=["lng", "lat"])
    df = df[df["name"].notna() & (df["name"].astype(str).str.strip() != "")]

    # 高德会把营业状态写进店名，如「XX店(暂停营业)」。这类店实地核验是白跑，
    # 抽出来单独标记并排除出抽样池。
    status_pat = r"[（(]([^）)]*(?:暂停营业|已停业|已关闭|歇业|装修中|搬迁)[^）)]*)[）)]"
    df["status_flag"] = (
        df["name"].astype(str).str.extract(status_pat, expand=False).fillna("")
    )

    # 只保留确实和餐饮相关的（typecode 05 开头，或类型里明确写了餐饮）
    # 注意：有 122 条是「购物+餐饮」复合类型，但主体确实是餐饮店，不能一刀切删掉
    tc = df["typecode"].astype(str)
    tp = df["type"].astype(str)
    df = df[tc.str.startswith("05") | tp.str.contains("餐饮", na=False)]

    # 评分
    df["rating_num"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating_band"] = pd.cut(
        df["rating_num"], RATING_BINS, labels=RATING_LABELS, right=True
    )

    # 人均
    df["cost_num"] = pd.to_numeric(df["cost"], errors="coerce")
    df["cost_missing"] = df["cost_num"].isna().astype(int)

    # 到游客核心区距离
    df["dist_to_wuyi_m"] = [
        dist_m(WUYI[0], WUYI[1], a, b) for a, b in zip(df["lng"], df["lat"])
    ]
    df["dist_band"] = pd.cut(
        df["dist_to_wuyi_m"], DIST_BINS, labels=DIST_LABELS, right=False
    )

    # 连锁判定：同名主品牌 >= 3 家
    df["main_brand"] = df["name"].map(main_brand)
    brand_n = df["main_brand"].value_counts()
    df["brand_store_count"] = df["main_brand"].map(brand_n).fillna(0).astype(int)
    df["is_chain"] = (df["brand_store_count"] >= 3).astype(int)

    # 营业时间是否可得（行程生成需要）
    df["has_opentime"] = df["opentime_week"].notna().astype(int)

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------

def allocate(counts: dict, total: int, min_per: int = 1,
             max_per: int = 10 ** 9) -> dict:
    """在给定各层可用量内按比例分配名额，带上下限，总和精确等于 total。"""
    tot = max(sum(counts.values()), 1)
    targets = {
        k: min(max_per, max(min_per, int(round(total * c / tot))))
        for k, c in counts.items()
    }
    guard = 0
    while sum(targets.values()) > total and guard < 10000:
        guard += 1
        k = max(targets, key=lambda x: targets[x])
        if targets[k] <= 1:
            break
        targets[k] -= 1
    guard = 0
    while sum(targets.values()) < total and guard < 10000:
        guard += 1
        # 优先补给可用量剩余最多的层
        cand = [k for k in counts if targets[k] < counts[k]]
        if not cand:
            break
        k = max(cand, key=lambda x: counts[x] - targets[x])
        targets[k] += 1
    return targets


def allocate_even(total: int, avail: dict) -> dict:
    """把 total 尽量均分到各层，样本不足的层按可用量封顶。"""
    keys = list(avail)
    t = {k: 0 for k in keys}
    remaining = total
    guard = 0
    while remaining > 0 and guard < 10000:
        guard += 1
        cand = [k for k in keys if t[k] < avail[k]]
        if not cand:
            break
        share = max(1, remaining // len(cand))
        for k in cand:
            if remaining <= 0:
                break
            add = min(share, avail[k] - t[k], remaining)
            t[k] += add
            remaining -= add
    return t


def _pick_in_cell(pool: pd.DataFrame, quota: int, seed: int) -> pd.DataFrame:
    """层内按评分档配额抽，保证低分店有足够比例。"""
    if pool.empty or quota <= 0:
        return pool.iloc[0:0]

    picks = []
    for band, ratio in RATING_QUOTA.items():
        sub = pool[pool["rating_band"].astype(str) == band]
        q = max(1, int(round(quota * ratio)))
        take = min(q, len(sub))
        if take > 0:
            picks.append(sub.sample(n=take, random_state=seed))

    got = pd.concat(picks) if picks else pool.iloc[0:0]
    if len(got) < quota:
        rest = pool.drop(index=got.index, errors="ignore")
        need = min(quota - len(got), len(rest))
        if need > 0:
            got = pd.concat([got, rest.sample(n=need, random_state=seed)])
    if len(got) > quota:
        got = got.sample(n=quota, random_state=seed)
    return got


def stratify(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """两段分层抽样。

    第一段：距离带 **均分** 名额（刻意不按比例）。
        原因：核心区(0-1km)在全量里只占约 12%，若按比例抽只剩十几家，
        根本无法检验「核心区 vs 生活区」这个核心假设。
        对距离带过度抽样是实验设计需要，不是抽样偏差 —— 论文里要主动写清楚。

    第二段：带内按片区比例分配，片区内部再按评分档配额抽。
    """
    df = df.copy()
    df["district"] = df["district"].astype(str)
    df["dist_band"] = df["dist_band"].astype(str)

    bands = [b for b in DIST_LABELS if (df["dist_band"] == b).any()]
    avail = {b: int((df["dist_band"] == b).sum()) for b in bands}
    band_target = allocate_even(n, avail)

    picked = []
    for band, bt in band_target.items():
        if bt <= 0:
            continue
        bdf = df[df["dist_band"] == band]
        dcounts = bdf["district"].value_counts().to_dict()
        for d, dt in allocate(dcounts, bt).items():
            if dt <= 0:
                continue
            pool = bdf[bdf["district"] == d]
            picked.append(_pick_in_cell(pool, dt, seed))

    out = pd.concat(picked).drop_duplicates(subset=["id"])

    # 某些层样本不足时从整体剩余补齐
    if len(out) < n:
        rest = df.drop(index=out.index, errors="ignore")
        need = min(n - len(out), len(rest))
        if need > 0:
            out = pd.concat([out, rest.sample(n=need, random_state=seed)])

    return out.iloc[:n] if len(out) > n else out


# ---------------------------------------------------------------------------

SAMPLE_COLS = [
    "id", "name", "main_brand", "district", "dist_band", "dist_to_wuyi_m",
    "rating", "rating_band", "cost", "cost_missing", "is_chain",
    "brand_store_count", "business_area", "typecode", "type",
    "opentime_week", "keytag", "tag", "rectag", "tel", "address", "lng", "lat",
]


def build_report(df_all: pd.DataFrame, samp: pd.DataFrame, n: int,
                 seed: int, path: Path) -> None:
    lines = [
        "# 抽样说明（Phase 1 验收物之一）",
        "",
        f"- 抽样池（清洗后、已排除营业异常）：**{len(df_all)}** 条",
        f"- 抽样数量：**{len(samp)}** 条（目标 {n}）",
        f"- 随机种子：`{seed}`（固定，结果可复现）",
        "- 抽样方式：距离带**均分名额** → 片区内按比例 → 评分档配额",
        "",
        "## 一、距离带构成（刻意均分，用于检验核心假设）",
        "",
        "| 距离带 | 全量条数 | 全量占比 | 抽样条数 | 抽样占比 |",
        "|---|---|---|---|---|",
    ]
    for b in DIST_LABELS:
        a = int((df_all["dist_band"].astype(str) == b).sum())
        s = int((samp["dist_band"].astype(str) == b).sum())
        lines.append(
            f"| {b} | {a} | {a / max(len(df_all), 1):.1%} | {s} | {s / max(len(samp), 1):.1%} |"
        )

    lines += [
        "",
        "> 距离带抽样占比明显高于全量占比，这是**刻意过度抽样**，",
        "> 目的是让「游客核心区 / 中间带 / 本地生活区」三组样本量可比。",
        "> 写论文时把它当作分层设计的理由，不要当成抽错。",
        "",
        "## 二、各层配额与评分档构成",
        "",
        "| 片区 | 距离带 | 抽中 | 低分 | 中间 | 高分 | 评分缺失 | 连锁占比 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (d, band), g in samp.groupby(["district", "dist_band"], observed=True):
        rb = g["rating_band"].value_counts()
        lines.append(
            f"| {d} | {band} | {len(g)} | "
            f"{rb.get('低(<3.5)', 0)} | {rb.get('中(3.5-4.3)', 0)} | "
            f"{rb.get('高(>=4.3)', 0)} | {int(g['rating_band'].isna().sum())} | "
            f"{g['is_chain'].mean():.0%} |"
        )

    lines += [
        "",
        "## 三、与全量的分布对比（检验抽样是否失真）",
        "",
        "| 指标 | 全量 | 抽样 |",
        "|---|---|---|",
        f"| 条数 | {len(df_all)} | {len(samp)} |",
        f"| 评分中位数 | {df_all['rating_num'].median():.2f} | {samp['rating_num'].median():.2f} |",
        f"| 人均中位数 | {df_all['cost_num'].median():.0f} | {samp['cost_num'].median():.0f} |",
        f"| 连锁占比 | {df_all['is_chain'].mean():.0%} | {samp['is_chain'].mean():.0%} |",
        f"| 评分<3.5 占比 | {(df_all['rating_num'] < 3.5).mean():.0%} | {(samp['rating_num'] < 3.5).mean():.0%} |",
        f"| 到核心区距离中位数 | {df_all['dist_to_wuyi_m'].median():.0f}m | {samp['dist_to_wuyi_m'].median():.0f}m |",
        "",
        "> 关键判断：**评分<3.5 的占比，抽样应高于全量**。",
        "> 因为全量本身被高德权重排序偏向高分店，抽样刻意提高低分店配额，",
        "> 这是为了拿到对比度，不是抽样偏误——写论文时要主动解释这一点。",
        "",
        "## 四、已知局限",
        "",
        "1. 候选池受高德单次查询 200 条上限影响，密集商圈存在欠采样；",
        "   因此「抽中概率」并非各店均等，样本对超密集区域仍有偏。",
        "2. 连锁判定只覆盖本次采集范围（长沙 6 片区），是「本地多店经营」口径。",
        "3. 停业店铺无法从 API 判断，需实地核验后在标注列中标注。",
        "",
        "## 五、怎么用这份清单",
        "",
        "1. 打开 `sample_150.csv`，按 `片区 → 距离带 → 距离` 排序，规划扫街路线；",
        "2. 每到一个片区，先打附近 3-5 家的电话确认是否营业（`tel` 字段 68% 有值）；",
        "3. 现场填 6 个标注列，**当天填完**，别靠回忆；",
        "4. `判断依据` 那一列哪怕只写一句「老板和顾客都说长沙话，12 点满座」，",
        "   答辩时就是你最硬的证据。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"    抽样说明：{path}")


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150, help="抽样数量，默认 150")
    ap.add_argument("--seed", type=int, default=20261021, help="随机种子")
    ap.add_argument("--input", default=str(DATA / "poi_all.csv"))
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"找不到 {src}，请先跑 amap_poi_collect.py")

    print(f"读取 {src}")
    raw = pd.read_csv(src)
    print(f"  原始 {len(raw)} 条")

    df = clean(raw)
    print(f"  清洗后 {len(df)} 条"
          f"（移除 {len(raw) - len(df)} 条：坐标缺失 / 名称空 / 非餐饮）")
    print(f"  其中连锁店 {int(df['is_chain'].sum())} 条，"
          f"评分缺失 {int(df['rating_num'].isna().sum())} 条，"
          f"人均缺失 {int(df['cost_missing'].sum())} 条")

    DATA.mkdir(exist_ok=True)
    df.to_csv(DATA / "cleaned_all.csv", index=False, encoding="utf-8-sig")
    print(f"    已写 data/cleaned_all.csv")

    pool = df[df["status_flag"] == ""]
    excluded = len(df) - len(pool)
    if excluded:
        print(f"  排除营业异常（暂停营业/装修中）{excluded} 条，不纳入抽样池")
    print(f"  抽样池 {len(pool)} 条")

    samp = stratify(pool, args.n, args.seed)
    samp = samp.sort_values(
        ["district", "dist_band", "dist_to_wuyi_m"]
    ).reset_index(drop=True)

    for c in ANN_COLS:
        samp[c] = ""
    out_cols = [c for c in SAMPLE_COLS if c in samp.columns] + ANN_COLS
    samp_out = samp[out_cols]

    sample_path = DATA / "sample_150.csv"
    samp_out.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"\n抽样结果：{len(samp_out)} 条 -> {sample_path}")

    print("\n=== 片区分布 ===")
    print(samp_out["district"].value_counts().to_string())
    print("\n=== 距离带分布 ===")
    print(samp_out["dist_band"].value_counts().to_string())
    print("\n=== 评分档（对比度检查）===")
    print(samp_out["rating_band"].value_counts(dropna=False).to_string())

    build_report(pool, samp, args.n, args.seed, DATA / "sample_report.md")

    print("\n" + "=" * 62)
    print("Phase 1 抽样完成。清单在你的扫街路线表里：")
    print(f"  {sample_path.resolve()}")
    print("=" * 62)


if __name__ == "__main__":
    main()
