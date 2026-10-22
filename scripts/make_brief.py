#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《项目说明与导师支持申请》DOCX，用于提交辅导员/院系申请分配指导教师。"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "advisor-brief.docx"

BODY_CN = "宋体"
BODY_EN = "Times New Roman"
HEAD_CN = "黑体"
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)


# ---------------------------------------------------------------- 样式工具

def set_style_font(style, cn, en, size, bold=False, color=None):
    style.font.name = en
    style.font.size = Pt(size)
    style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), cn)


def para(doc, text, size=11, bold=False, cn=BODY_CN, en=BODY_EN,
         align=None, space_after=6, space_before=0, indent=None,
         line=1.45, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = line
    if indent is not None:
        pf.first_line_indent = Cm(indent)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), cn)
    return p


def h1(doc, text):
    return para(doc, text, size=13, bold=True, cn=HEAD_CN, en="Arial",
                space_before=14, space_after=6, color=ACCENT)


def h2(doc, text):
    return para(doc, text, size=11.5, bold=True, cn=HEAD_CN, en="Arial",
                space_before=9, space_after=4)


def bullet(doc, text, size=11):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.space_after = Pt(3)
    pf.line_spacing = 1.4
    pf.left_indent = Cm(0.75)
    run = p.add_run(text)
    run.font.name = BODY_EN
    run.font.size = Pt(size)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), BODY_CN)
    return p


def table(doc, headers, rows, widths, font=9.5, header_shade="DCE6F1"):
    # A4 减去左右各 2.4cm 边距后正文宽 16.2cm；
    # 表格统一缩到 15.6cm 留安全余量，避免 Word 里轻微溢出。
    _t = sum(widths)
    widths = [w * 15.6 / _t for w in widths]

    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    hdr = t.rows[0].cells
    for i, htxt in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        r = p.add_run(htxt)
        r.font.bold = True
        r.font.size = Pt(font)
        r.font.name = BODY_EN
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), HEAD_CN)

    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(str(val))
            r.font.size = Pt(font)
            r.font.name = BODY_EN
            r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), BODY_CN)

    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    return t


# ---------------------------------------------------------------- 正文

def build():
    doc = Document()

    sec = doc.sections[0]
    sec.page_width = Cm(21.0)      # A4
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.4)

    set_style_font(doc.styles["Normal"], BODY_CN, BODY_EN, 11)

    # ---------------- 标题区
    para(doc, "长沙美食可信度评估与个性化行程生成系统",
         size=18, bold=True, cn=HEAD_CN, en="Arial",
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4, color=ACCENT)
    para(doc, "项 目 说 明   ·   导 师 支 持 申 请",
         size=11, cn=HEAD_CN, en="Arial",
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    para(doc, "姓名：___________　　专业：计算机／软件工程　　年级：大三（上）　　"
              "日期：2026 年 10 月",
         size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
         color=RGBColor(0x55, 0x55, 0x55))

    # 分隔线
    pline = doc.add_paragraph()
    pline.paragraph_format.space_after = Pt(8)
    pbdr = pline._p.get_or_add_pPr()
    from docx.oxml import OxmlElement
    pbd = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:color"), "1F3A5F")
    pbd.append(bottom)
    pbdr.append(pbd)

    # ---------------- 一
    h1(doc, "一、项目背景")
    para(doc, "在长沙这类「网红城市」中，游客量与本地生活高度重叠，主流平台的餐饮评分"
              "已明显偏离本地居民的真实判断。评分高的店往往是装修好、会运营、客单价高的店，"
              "而本地人天天光顾、人均十几元的粉店和小炒馆，评分反而偏低、排名靠后。", indent=0.74)
    para(doc, "本项目希望以长沙为单城试点，构建一套「本地偏好信号」，在不依赖平台评分的"
              "前提下识别真正值得吃的店铺，并据此生成可执行、可分预算档位的旅行行程。", indent=0.74)

    # ---------------- 二
    h1(doc, "二、核心问题与已有数据发现")
    para(doc, "为验证问题是否真实存在，我已自行搭建数据管线，采集长沙 6 个片区（五一广场坡子街、"
              "南门口、冬瓜山、四方坪、河西大学城、开福北辰）的高德地图 POI 数据，"
              "共获得餐饮 9,560 条、景点 643 条、住宿 3,612 条，累计调用接口 852 次。（见表 1）", indent=0.74)

    para(doc, "表 1　已完成的数据采集情况", size=9.5, bold=True, cn=HEAD_CN, en="Arial",
         align=WD_ALIGN_PARAGRAPH.CENTER, space_before=4, space_after=3)
    table(doc,
          ["数据层", "类目", "条数", "在项目中的定位"],
          [["餐饮店铺", "050000 餐饮服务", "9,560", "研究对象：需人工标注、建信号、做实验"],
           ["景点", "110000 风景名胜", "643", "约束数据：仅用于行程排程"],
           ["住宿", "100000 住宿服务", "3,612", "约束数据：仅用于预算分层"]],
          [3.2, 4.6, 2.6, 5.8])

    h2(doc, "2.1　一项关键实证发现")
    para(doc, "对 8,021 家同时具备评分与人均消费的店铺做相关分析，结果为：", indent=0.74)
    bullet(doc, "评分与人均价的 Spearman 相关系数 ρ = 0.469，呈明显正相关。")
    bullet(doc, "评分 ≥ 4.5 的店铺，人均消费中位数为 55 元；评分 < 3.5 的店铺，人均中位数仅 19 元。")
    bullet(doc, "按价位分组，评分中位数依次为：人均 15 元以下 3.9 分、15–30 元 4.0 分、"
                "30–60 元 4.3 分、60–120 元 4.5 分。")
    para(doc, "这说明：现有平台的评分体系系统性偏向中高价店铺。若按「评分排序」生成攻略，"
              "预算有限的旅行者会被系统性地推离真正值得吃的低价好店。"
              "这也构成了本项目最直接的应用价值——服务于对价格敏感的用户。", indent=0.74)

    # ---------------- 三
    h1(doc, "三、研究假设")
    bullet(doc, "H1：在游客占比高的城市，店铺公开评分与「本地人认可度」呈弱相关。")
    bullet(doc, "H2：由地理分层、结构特征、时段热度等构造的复合信号，对本地人认可度的预测"
                "能力显著优于评分基线。")
    bullet(doc, "H3：在低预算区间（人均 ≤ 30 元），评分与本地认可度的背离程度显著大于"
                "高预算区间（人均 ≥ 60 元）。")

    # ---------------- 四
    h1(doc, "四、方法与技术路线")
    para(doc, "整体思路是「先用可观测信号逼近不可直接观测的构念，再用人工标注验证」。", indent=0.74)
    table(doc,
          ["环节", "做法", "产出"],
          [["信号构造", "地理位置（距游客核心区距离）、片区属性、是否连锁、"
                        "开业年限、人均价、标签丰富度", "店铺特征表"],
           ["可信度模型", "加权／学习排序，输出可信度分与排序", "排序服务"],
           ["对比实验", "与「评分排序」「热度排序」双基线对比，"
                        "指标 Precision@10、NDCG@10，并做消融", "实验结果"],
           ["行程生成", "带约束多目标排程：时间窗、营业时间、距离、口味多样性、"
                        "预算上限（重点）", "帕累托前沿行程"],
           ["事实校验", "对生成结果逐条校验营业状态、营业时间、距离合理性", "校验报告"]],
          [2.6, 9.4, 4.2])

    para(doc, "系统实现采用 Java 17 + Spring Boot 3 + PostgreSQL/PostGIS + Redis，"
              "数据处理用 Python 离线计算后落库，前后端分离，容器化部署。"
              "选择 Java 技术栈是有意为之：与本项目的目标岗位方向一致。", indent=0.74, space_before=6)

    # ---------------- 五
    h1(doc, "五、目前已完成的阶段性工作")
    para(doc, "截至目前，项目已完成数据与标注两个基础环节，所有脚本可复现：", indent=0.74)
    table(doc,
          ["序号", "已完成工作", "说明"],
          [["1", "数据采集管线", "自适应网格平铺策略，绕开接口单次 200 条返回上限"],
           ["2", "数据可得性分析", "评分填充率 99.9%、人均 83.9%、营业时间 79.7%，"
                                    "并明确记录三项不可得字段"],
           ["3", "分层抽样设计", "按「距离带均分 → 片区 → 评分档」抽出 150 家待核验店铺，"
                                "随机种子固定、结果可复现"],
           ["4", "标注规范 v1.0", "6 个核心字段 + 2 个预算字段的打分锚点、"
                                "时段规范、一致性自检方案"],
           ["5", "约束数据采集", "景点 643 条、住宿 3,612 条，独立存储、不进入实验"],
           ["6", "初步实证分析", "评分与价格相关性 ρ = 0.469，支撑 H1／H3"]],
          [1.4, 4.4, 10.4])

    h2(doc, "5.1　已识别的数据限制（拟写入论文局限性一节）")
    bullet(doc, "高德接口单次查询最多返回 200 条，密集商圈存在欠采样，已用网格平铺缓解但非 100% 覆盖。")
    bullet(doc, "评论正文与历史客流无法通过接口获取，需以人工采样与实地观测替代。")
    bullet(doc, "住宿房价字段缺失率 99.8%，拟改用酒店类别／星级作为价格代理指标。")

    # ---------------- 六
    h1(doc, "六、希望获得的指导")
    para(doc, "本项目已具备可运行的数据基础与明确的技术路线，目前主要的短板不在动手能力，"
              "而在方法层面的把关。希望能获得一位方向匹配的指导教师（导师），具体需要：", indent=0.74)
    bullet(doc, "方向建议：数据挖掘、机器学习、自然语言处理或知识图谱方向。")
    bullet(doc, "方法指导：信号设计与评价指标是否合理，实验设计能否支撑结论。")
    bullet(doc, "合规意见：数据采集边界的把握（当前方案已规避需登录数据与明令禁止抓取的平台）。")
    bullet(doc, "论文层面：是否具备整理为会议／期刊论文的可能性与时间点建议。")
    para(doc, "项目不需要额外经费与设备支持，地图开放平台个人开发者额度可覆盖全部采集需求。",
         indent=0.74, space_before=4)

    # ---------------- 七
    h1(doc, "七、时间计划")
    table(doc,
          ["时间", "阶段目标", "阶段成果"],
          [["2026.10–12", "标注规范落地、春节前工具链就绪", "30 家标注 + 一致性自检报告"],
           ["2027.01–02", "寒假实地核验 150 家，覆盖春节客流峰值", "完整标注数据集"],
           ["2027.03", "信号验证与对比实验", "可演示原型 Demo"],
           ["2027.04–08", "Java 后端开发与迭代", "试用版 v0.1，含真实用户反馈"],
           ["2027.09–12", "实验补全：消融、H3 检验、用户研究", "完整实验章节"],
           ["2028.01–04", "系统完善与论文撰写", "毕业设计成品"],
           ["2028.05", "答辩", "—"]],
          [3.0, 7.6, 5.6])

    # ---------------- 八
    h1(doc, "八、投入承诺")
    para(doc, "本人已持续投入约两周完成数据管线与抽样设计，后续计划保持每周 10–12 小时"
              "的稳定投入（寒暑假集中投入）。项目代码、数据与文档同步归档，"
              "可按月向指导教师汇报进度。恳请考虑分配指导教师，不胜感激。", indent=0.74)

    doc.save(OUT)
    print(f"已生成：{OUT}")


if __name__ == "__main__":
    build()
