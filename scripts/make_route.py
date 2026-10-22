#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1.5 · 生成扫街路线表（Excel）

把 data/sample_150.csv 的 150 家店，按「片区 → 距离带 → 最近邻路线」重排，
输出成一份可以直接拿在手上跑的实地核验表：

    data/route-plan.xlsx

包含：
    总览              分批计划与进度
    各片区 sheet       按行走路线排序的店铺清单 + 可直接填写的标注列
    标注速查           一页速查规则（离线用，不用翻文档）

用法：
    python scripts/make_route.py
"""

import math
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "route-plan.xlsx"

WUYI = (112.9820, 28.1945)              # 游客核心基准点（五一广场）

# 片区中心（与采集脚本一致）+ 批次安排
# 顺序即建议执行顺序：先近、先本地生活区，核心区留到寒假两次
PLAN = [
    # 片区,            中心(lng,lat),          批次,      计划时间,            说明
    ("南门口",         (112.9775, 28.1840),   "第一批",  "10.21–11.05", "起步区，本地店密集，标准在这里定死"),
    ("冬瓜山",         (112.9860, 28.1710),   "第一批",  "10.21–11.05", "夜宵聚集，注意晚间时段"),
    ("开福北辰",       (112.9770, 28.2380),   "第三批",  "11.21–12.31", "本地生活区，补充样本"),
    ("四方坪",         (113.0010, 28.2340),   "第三批",  "11.21–12.31", "本地生活区，补充样本"),
    ("河西大学城",     (112.9360, 28.1780),   "第三批",  "11.21–12.31", "学生客群为主，注意区分学生≠本地居民"),
    ("五一广场坡子街", (112.9820, 28.1945),   "第四批",  "2027.1 寒假初", "游客核心区，先取本地日常基线"),
]

ANN_COLS = [
    ("已电话确认", "是/否", 11),
    ("本地认可度", "1-5", 13),
    ("游客浓度", "1-5", 11),
    ("是否网红店", "是/否/疑似", 13),
    ("是否停业", "是/否", 11),
    ("判断依据", None, 42),
    ("备注", None, 22),
]

HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
HEAD_FONT = Font(bold=True, color="FFFFFF", size=10, name="微软雅黑")
BODY_FONT = Font(size=10, name="微软雅黑")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BAND_FILL = {
    "核心区(0-1km)": PatternFill("solid", fgColor="FCE4E4"),
    "中间带(1-3km)": PatternFill("solid", fgColor="FFF2CC"),
    "生活区(3km+)": PatternFill("solid", fgColor="E2EFDA"),
}


def dist_m(a, b):
    lat_deg = 110540.0
    lng_deg = 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * lng_deg, (a[1] - b[1]) * lat_deg)


def order_by_route(df, center):
    """最近邻排序：从片区中心出发，每次走向离当前点最近的下一家。"""
    remaining = [(i, (r.lng, r.lat)) for i, r in zip(df.index, df.itertuples())]
    cur = center
    order = []
    while remaining:
        best_i, best_d = 0, None
        for i, (_, pt) in enumerate(remaining):
            d = dist_m(cur, pt)
            if best_d is None or d < best_d:
                best_i, best_d = i, d
        idx, pt = remaining.pop(best_i)
        order.append(idx)
        cur = pt
    return df.loc[order]


def suggest_slot(row):
    """按标签猜一个建议到店时段（只是建议，现场以实际营业时间为准）。"""
    blob = " ".join(str(row.get(c, "")) for c in ("keytag", "rectag", "tag", "type"))
    if any(k in blob for k in ("夜宵", "烧烤", "小龙虾", "酒吧", "口味虾")):
        return "夜市"
    if any(k in blob for k in ("米粉", "早餐", "包子", "面馆", "早点", "饼")):
        return "早市/午市"
    return "午市"


def style_header(ws, ncol, row=1):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 34


def build_district_sheet(wb, name, df, center, batch, when, note):
    ws = wb.create_sheet(name)
    headers = ["序", "店名", "距离带", "距核心区(m)", "平台评分", "平台人均",
               "电话", "营业时间", "地址", "建议时段"] + [c[0] for c in ANN_COLS]
    widths = [4, 30, 14, 11, 9, 9, 15, 20, 34, 10] + [c[2] for c in ANN_COLS]

    # 标题区先写死，避免后插行导致数据验证范围错位
    ws["A1"] = f"{name}　{batch}　{when}　共 {len(df)} 家"
    ws["A1"].font = Font(bold=True, size=12, name="微软雅黑", color="1F3A5F")
    ws["A2"] = note + "　｜　按路线顺序走访，同一片区一次跑完，减少往返"
    ws["A2"].font = Font(size=9, name="微软雅黑", color="595959")

    HEAD_ROW = 3
    FIRST = HEAD_ROW + 1
    for i, h in enumerate(headers, 1):
        ws.cell(row=HEAD_ROW, column=i, value=h)
    style_header(ws, len(headers), row=HEAD_ROW)

    df = order_by_route(df, center)
    for k, (_, r) in enumerate(df.iterrows()):
        row = FIRST + k
        vals = [
            k + 1,
            r["name"],
            r["dist_band"],
            round(float(r["dist_to_wuyi_m"])),
            float(r["rating"]) if pd.notna(r["rating"]) else None,
            float(r["cost"]) if pd.notna(r["cost"]) else None,
            str(r["tel"]) if pd.notna(r["tel"]) else "",
            str(r["opentime_week"]) if pd.notna(r["opentime_week"]) else "",
            str(r["address"]) if pd.notna(r["address"]) else "",
            suggest_slot(r),
        ] + [""] * len(ANN_COLS)

        fill = BAND_FILL.get(r["dist_band"])
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.font = BODY_FONT
            cell.border = BORDER
            # 店名 / 营业时间 / 地址 / 判断依据 / 备注 左对齐并换行
            if c in (2, 8, 9, 16, 17):
                cell.alignment = Alignment(vertical="center", wrap_text=True,
                                           horizontal="left")
            else:
                cell.alignment = Alignment(vertical="center", horizontal="center")
            if fill is not None:
                cell.fill = fill

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"C{FIRST}"

    # 下拉选项：手机上点选比打字快得多
    last = FIRST + len(df) - 1
    dv_yn = DataValidation(type="list", formula1='"是,否"', allow_blank=True)
    dv_wh = DataValidation(type="list", formula1='"是,否,疑似"', allow_blank=True)
    dv_15 = DataValidation(type="list", formula1='"1,2,3,4,5,NA"', allow_blank=True)
    for dv in (dv_yn, dv_wh, dv_15):
        ws.add_data_validation(dv)
    col_of = {c[0]: get_column_letter(11 + k) for k, c in enumerate(ANN_COLS)}
    dv_yn.add(f"{col_of['已电话确认']}{FIRST}:{col_of['已电话确认']}{last}")
    dv_15.add(f"{col_of['本地认可度']}{FIRST}:{col_of['本地认可度']}{last}")
    dv_15.add(f"{col_of['游客浓度']}{FIRST}:{col_of['游客浓度']}{last}")
    dv_wh.add(f"{col_of['是否网红店']}{FIRST}:{col_of['是否网红店']}{last}")
    dv_yn.add(f"{col_of['是否停业']}{FIRST}:{col_of['是否停业']}{last}")
    return ws


def build_overview(wb, per_district):
    ws = wb.create_sheet("总览", 0)
    ws["A1"] = "长沙扫街路线表 · 150 家实地核验"
    ws["A1"].font = Font(bold=True, size=14, name="微软雅黑", color="1F3A5F")
    ws["A2"] = "每店建议：15 分钟现场观察 + 电话预确认；每天 12–14 家，约 11 个工作日跑完。"
    ws["A2"].font = Font(size=9, name="微软雅黑", color="595959")
    ws["A3"] = ("春节窗口（2027.2 上旬）不要新标新店，只复访「核心区」50 家，"
                "重点更新游客浓度与判断依据 —— 同一批店的两个时点对比，才是 H1/H3 的证据。")
    ws["A3"].font = Font(size=9, name="微软雅黑", color="C00000")

    HEAD = 5
    FIRST = HEAD + 1
    headers = ["批次", "计划时间", "片区", "家数", "建议天数", "完成家数", "备注"]
    for i, h in enumerate(headers, 1):
        ws.cell(row=HEAD, column=i, value=h)
    style_header(ws, 7, row=HEAD)

    r = FIRST
    for name, center, batch, when, note in PLAN:
        n = per_district.get(name, 0)
        vals = [batch, when, name, n, max(1, math.ceil(n / 14)), "", note]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=(c == 7))
        r += 1

    total = sum(per_district.get(p[0], 0) for p in PLAN)
    days = sum(max(1, math.ceil(per_district.get(p[0], 0) / 14)) for p in PLAN)
    for c, v in enumerate(["合计", "", "", total, days, "", f"约 {days} 个工作日"], 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = Font(size=10, name="微软雅黑", bold=True)
        cell.border = BORDER
        cell.alignment = Alignment(vertical="center")

    for i, w in enumerate([10, 16, 18, 8, 10, 10, 44], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"A{FIRST}"


def build_cheatsheet(wb):
    ws = wb.create_sheet("标注速查")
    lines = [
        ("字段", "打分要点"),
        ("本地认可度", "5=本地人天天吃、非餐点也满座 ｜ 3=本地与游客各半 ｜ 1=基本只有游客 ｜ NA=不确定，写原因"),
        ("怎么判断", "①听口音 ②看菜单有无网红/打卡字样 ③看有无行李箱自拍杆 ④看吃完速度快慢 ⑤看老板是否招呼熟客 ⑥看做不做早餐夜宵"),
        ("游客浓度", "5=几乎全是游客 1=几乎全是本地人 ｜ 记的是本次观察时段，不是全年"),
        ("是否网红", "有排队栏杆/叫号机/网红字样/打卡墙/旅游大巴 = 是；线索不明确 = 疑似"),
        ("判断依据", "必填，写证据不写结论。例：12:10满座，8桌里6桌长沙话，菜单只有9个菜"),
        ("时段代号", "WD-L 工作日午市 ｜ WD-D 工作日夜市 ｜ WE-L 周末午市 ｜ WE-D 周末夜市 ｜ CNY 春节"),
        ("实际人均", "现场看菜单估，不要抄平台人均——你可能正在纠正它"),
        ("穷游友好", "一个人 50 元内能吃饱吃好 = 是（用来验证 H3 假设，必须记）"),
        ("红线", "只去一次不下结论；只坐 5 分钟不下结论；拿平台评分当参照 = 污染，绝对不要"),
    ]
    for r in lines:
        ws.append(list(r))
    style_header(ws, 2)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=2):
        for cell in row:
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 100
    ws.freeze_panes = "A2"


def main():
    src = DATA / "sample_150.csv"
    if not src.exists():
        sys.exit(f"找不到 {src}，请先运行 scripts/make_sample.py")

    df = pd.read_csv(src)
    print(f"读取 {src}：{len(df)} 家")

    wb = Workbook()
    wb.remove(wb.active)

    per_district = df["district"].value_counts().to_dict()
    order = [p[0] for p in PLAN]
    for name, center, batch, when, note in PLAN:
        sub = df[df["district"] == name]
        if sub.empty:
            print(f"  跳过 {name}（无样本）")
            continue
        build_district_sheet(wb, name, sub, center, batch, when, note)
        print(f"  {name:<14} {len(sub):>3} 家  →  工作表已生成")

    # 兜底：不在 PLAN 里的片区
    for name in per_district:
        if name not in order:
            print(f"  [!] 片区「{name}」不在计划表里，已忽略")

    build_overview(wb, per_district)
    build_cheatsheet(wb)
    wb._sheets = [wb["总览"]] + [wb[p[0]] for p in PLAN if p[0] in wb.sheetnames] + [wb["标注速查"]]

    wb.save(OUT)
    print(f"\n已生成：{OUT}")
    print(f"工作表：{', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
