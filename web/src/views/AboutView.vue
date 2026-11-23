<template>
  <h1>关于本项目</h1>
  <p class="page-lead">
    一句话：<strong>在网红城市里，平台评分已经不能代表「本地人觉得好吃」</strong>，
    而这个偏差是可测量的。本站试图用别的依据重做一次推荐。
  </p>

  <div class="section-title"><h2>为什么不信评分</h2></div>
  <p>
    采集长沙 6 个片区 9,560 家餐饮 POI 后，对其中 8,021 家同时有评分与人均价的店做相关分析：
  </p>
  <div class="card evidence-card">
    <dl class="kv">
      <dt>相关系数</dt>
      <dd>评分与人均价的 Spearman ρ = <b class="mono">0.469</b></dd>
      <dt>高分店</dt>
      <dd>评分 ≥ 4.5 的店，人均中位数 <b class="mono">55 元</b></dd>
      <dt>低分店</dt>
      <dd>评分 &lt; 3.5 的店，人均中位数 <b class="mono">19 元</b></dd>
    </dl>
  </div>
  <p class="text-sm text-muted">
    也就是说，按「评分排序」做攻略，预算有限的人会被系统性地推离真正值得吃的低价好店。
    这正是本项目最想服务的场景。
  </p>

  <div class="section-title"><h2>所以本站怎么排序</h2></div>
  <p>
    目标是引入一个不依赖评分的指标：<strong>本地认可度</strong>（1–5 分），
    由实地观察得出 —— 听口音、看菜单、看有没有行李箱、看老板是否招呼熟客。
  </p>
  <p class="text-sm text-muted">
    指标现在<strong>是空的</strong>。标注要在寒假集中完成 150 家店，之后才会逐步填上。
    在那之前，本站只展示高德数据，并明确标注「未核验」。
  </p>

  <div class="section-title"><h2>数据来源与限制</h2></div>
  <dl class="kv card limits">
    <dt>数据来源</dt>
    <dd>高德开放平台 Web 服务 API（POI 周边搜索 v5），个人开发者额度</dd>

    <dt>采集范围</dt>
    <dd>长沙 6 个片区：五一广场坡子街、南门口、冬瓜山、四方坪、河西大学城、开福北辰</dd>

    <dt>数据规模</dt>
    <dd>餐饮 9,519 家（已排除停业）・景点 643 个 ・住宿 3,612 处</dd>

    <dt>不采集</dt>
    <dd>需登录的数据、平台禁止抓取的内容、用户评论正文、任何个人身份信息</dd>
  </dl>

  <p class="text-sm text-muted limits-note">已知的数据缺陷，老实写在这里：</p>
  <ul class="text-sm text-muted limits-list">
    <li>接口单次查询最多返回 200 条，密集商圈存在欠采样，非全量覆盖</li>
    <li>人均消费 16.1% 缺失，缺的用片区中位数估算，并在卡片上标了「估算」</li>
    <li>营业时间 20.2% 缺失，展示为「未提供」</li>
    <li>住宿房价字段缺失 99.8%，因此住宿无法做真实价格分层</li>
    <li>景点类目标注有噪声，部分零售店被归入风景名胜</li>
  </ul>

  <div class="section-title"><h2>这个站的原则</h2></div>
  <ol class="principles">
    <li><strong>宁可缺一块，也不编数据。</strong>「本地认可度」没标注就是空的，不用评分冒充。</li>
    <li><strong>估算是要说出来的。</strong>凡是用中位数填补的价格，卡片上都标「估算」。</li>
    <li><strong>预算不是开关，是约束。</strong>三档同时算，让你看见取舍。</li>
  </ol>

  <p class="text-xs text-faint foot">
    数据版权归原数据提供方。本项目仅用于学术研究与技术演示。
  </p>
</template>

<style scoped>
.evidence-card {
  margin-bottom: 12px;
}
.evidence-card .kv {
  margin: 0;
}

.limits {
  margin-bottom: 8px;
}
.limits-note {
  margin: 14px 0 6px;
}
.limits-list {
  margin: 0 0 8px;
  padding-left: 1.2em;
}
.limits-list li {
  margin-bottom: 5px;
}

.principles {
  margin: 0;
  padding-left: 1.3em;
  color: var(--ink-2);
  font-size: 14px;
}
.principles li {
  margin-bottom: 8px;
}

.foot {
  margin-top: 28px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}
</style>
