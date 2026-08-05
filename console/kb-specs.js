/**
 * Agent 知识库规范（自 yitech/待整理文件 迁入）
 * - 分类：知识库建设与评分体系完整报告 v6.0 · §1.1 + 三层架构
 * - 评分：战略委员会 10.评分体系 · COVER / FOACA / L1–L5 v3.1
 */
const KbSpecs = (() => {
  const META = {
    taxonomySource:
      "yitech/待整理文件/99-旧版本/05-知识库/…/知识库建设与评分体系完整报告v6.0.md + 知识库管理员/01-架构设计标准.md",
    scoringSource:
      "yitech/待整理文件/05-知识库/战略委员会/10.评分体系/00-框架总纲-COVER-FOACA-L1L5.md（v3.1）",
  };

  /** 顶层知识库分类（AgentKnowledge 全景） */
  const TAXONOMY = [
    {
      id: "role-db",
      name: "角色数据库",
      desc: "数字员工核心角色（CEO / CTO / CMO 等）",
      note: "含 SOUL / IDENTITY / 能力域",
    },
    {
      id: "role-kb",
      name: "角色知识库",
      desc: "传统岗位角色（产品 / 项目 / 开发等）",
      note: "按岗位沉淀方法论",
    },
    {
      id: "company",
      name: "公司知识库",
      desc: "公司特定信息、流程、产品",
      note: "更新频率高 · 不宜灌入角色 COVER",
    },
    {
      id: "industry",
      name: "行业知识库",
      desc: "行业垂直知识与竞争情报",
      note: "按行业定制，不重复写通用层",
    },
    {
      id: "special",
      name: "专项知识库",
      desc: "技术 / 产品专项（如框架、OPC）",
      note: "可跨角色挂载",
    },
    {
      id: "brand",
      name: "品牌专项",
      desc: "品牌项目与对外叙事资产",
      note: "示例：LridiumStone / 公司介绍定稿",
    },
  ];

  /** 三层架构（建设规范） */
  const LAYERS = [
    {
      id: "00",
      name: "通用层",
      prefix: "00-",
      cadence: "低（半年+）",
      content: "任何公司都适用的方法论 / 框架 / 工具",
      example: "BCG 矩阵、SWOT、SOLID",
    },
    {
      id: "01",
      name: "行业层",
      prefix: "01-",
      cadence: "中（季度）",
      content: "特定行业的知识 / 法规 / 竞争格局",
      example: "AI 行业分析、制造业流程",
    },
    {
      id: "02",
      name: "公司层",
      prefix: "02-",
      cadence: "高（月度）",
      content: "本公司特定的信息 / 流程 / 产品",
      example: "产品 PRD、客户案例、内部流程",
    },
  ];

  /** 归档库顶部分类（OneDrive 待整理 00–07）——公司资料落盘用 */
  const ARCHIVE = [
    { id: "00", name: "00-战略与治理", use: "战略、制度、评分决策" },
    { id: "01", name: "01-主营业务", use: "三条业务线 + 品牌共用资产" },
    { id: "02", name: "02-客户与项目", use: "按客户归档的正式项目" },
    { id: "03", name: "03-运营与市场", use: "营销、渠道、官网" },
    { id: "04", name: "04-财务与法务", use: "合同、报价、发票（敏感）" },
    { id: "05", name: "05-知识库", use: "角色知识库、方法论（战略委员会）" },
    { id: "06", name: "06-人力与行政", use: "招聘、会议纪要" },
    { id: "07", name: "07-媒体与资产", use: "图片、视频、PPT 模板（定稿）" },
    { id: "99", name: "99-旧版本", use: "全库旧版唯一入口" },
  ];

  const COVER = {
    formula: "COVER = C×0.30 + O×0.25 + U×0.20 + R×0.15 + F×0.10",
    dims: [
      { key: "C", name: "Coverage 覆盖度", w: 30, mean: "该角色必备知识领域是否齐全" },
      { key: "O", name: "Accuracy 准确性", w: 25, mean: "内容可靠、时效、风险标注" },
      { key: "U", name: "Usability 可用性", w: 20, mean: "模板 / 索引 / 场景映射 / Agent 可调用" },
      { key: "R", name: "Richness 深度", w: 15, mean: "案例、实操、避坑、附录" },
      { key: "F", name: "Fairness 一致性", w: 10, mean: "术语、格式、逻辑连贯" },
    ],
    grades: [
      { range: "9.0–10.0", level: "卓越", tone: "green" },
      { range: "7.5–8.9", level: "健康", tone: "green" },
      { range: "6.0–7.4", level: "良好", tone: "orange" },
      { range: "4.5–5.9", level: "需改进", tone: "orange" },
      { range: "<4.5", level: "严重不足", tone: "" },
    ],
  };

  const FOACA = {
    dims: [
      { key: "F", name: "Findability 可检索", w: 20 },
      { key: "O", name: "Organization 结构化", w: 20 },
      { key: "A", name: "Accuracy 准确性", w: 25 },
      { key: "C", name: "Completeness 完整性", w: 20 },
      { key: "Ap", name: "Applicability 实用性", w: 15 },
    ],
    gates: [
      { range: "8.5–10", action: "可直接入库" },
      { range: "7.0–8.4", action: "修订后入库" },
      { range: "5.5–6.9", action: "大幅修订" },
      { range: "<5.5", action: "暂不入库" },
    ],
  };

  const LADDER = [
    { lv: "L1", name: "认知期", feat: "基础概念、术语、职责定义" },
    { lv: "L2", name: "学习期", feat: "方法论与框架系统学习" },
    { lv: "L3", name: "应用期", feat: "模板、工具、检查清单可实操" },
    { lv: "L4", name: "精通期", feat: "深度案例、失败教训、最佳实践" },
    { lv: "L5", name: "创新期", feat: "前沿趋势、原创洞察、战略建议" },
  ];

  const FLOW = [
    "季度：全库 COVER + L1–L5 复评，写入评分报告",
    "入库前：新文档 FOACA ≥ 7.0 方可入库",
    "抽查：每月随机 3 篇 FOACA 复核",
    "整改：COVER < 7.5 的维度列入待办",
  ];

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderTaxonomy() {
    return `<div class="kb-spec-body">
      <div class="fb-story">
        <div class="fb-story-kicker">知识库分类</div>
        <p>Agent 挂载前先归类：顶层六类决定「这是谁的知识」；三层架构决定「通用 / 行业 / 公司」边界；归档 00–07 决定公司定稿落盘位置。</p>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">顶层分类 · AgentKnowledge</h2>
        <div class="meta" style="margin-bottom:12px">来源：知识库建设报告 v6.0 §1.1</div>
        <div class="fb-variant-list">
          ${TAXONOMY.map(
            (t, i) => `<div class="fb-variant">
              <div class="fb-variant-row">
                <div>
                  <div class="row-title">${i + 1}. ${esc(t.name)}</div>
                  <div class="row-desc">${esc(t.desc)}</div>
                  <div class="meta" style="margin-top:4px">${esc(t.note)}</div>
                </div>
                <span class="tag blue">${esc(t.id)}</span>
              </div>
            </div>`
          ).join("")}
        </div>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">三层架构</h2>
        <div class="meta" style="margin-bottom:12px">知识 = 通用能力 + 行业认知 + 公司上下文 · 来源：架构设计标准</div>
        <div class="fb-split">
          ${LAYERS.map(
            (l) => `<div class="fb-variant">
              <div class="tags" style="margin-bottom:8px"><span class="tag">${esc(l.prefix)}</span><span class="tag orange">${esc(
                l.cadence
              )}</span></div>
              <div class="row-title">${esc(l.name)}</div>
              <div class="row-desc" style="margin-top:6px">${esc(l.content)}</div>
              <div class="meta" style="margin-top:8px">例：${esc(l.example)}</div>
            </div>`
          ).join("")}
        </div>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">公司归档分类 · 00–07</h2>
        <div class="meta" style="margin-bottom:12px">来源：yitech/待整理文件 README · 只收定稿</div>
        <div class="fb-variant-list">
          ${ARCHIVE.map(
            (a) => `<div class="fb-variant">
              <div class="fb-variant-row">
                <div>
                  <div class="row-title mono">${esc(a.name)}</div>
                  <div class="row-desc">${esc(a.use)}</div>
                </div>
              </div>
            </div>`
          ).join("")}
        </div>
      </div>

      <div class="meta" style="margin-top:12px">出处：${esc(META.taxonomySource)}</div>
    </div>`;
  }

  function renderScoring() {
    return `<div class="kb-spec-body">
      <div class="fb-story">
        <div class="fb-story-kicker">知识库评分体系 · v3.1</div>
        <p>COVER 评整库健康度；FOACA 评单篇能否入库；L1–L5 标成熟度阶段。旧版 COVER-G / 仅作历史参考。</p>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">COVER · 整库健康度</h2>
        <div class="fb-insight" style="margin:10px 0"><code class="mono">${esc(COVER.formula)}</code></div>
        ${COVER.dims
          .map(
            (d) => `<div class="fb-score-row">
              <span class="fb-score-label">${esc(d.key)} · ${esc(d.name)}</span>
              <div class="fb-score-track"><i style="width:${d.w * 3}%"></i></div>
              <span class="fb-score-num mono">${d.w}%</span>
            </div>
            <div class="meta" style="margin:2px 0 10px 0">${esc(d.mean)}</div>`
          )
          .join("")}
        <div class="tags" style="margin-top:8px">
          ${COVER.grades
            .map((g) => `<span class="tag ${g.tone}">${esc(g.range)} · ${esc(g.level)}</span>`)
            .join("")}
        </div>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">FOACA · 单篇入库</h2>
        <div class="meta" style="margin-bottom:10px">门槛：FOACA ≥ 7.0 方可入库（第二个 A 写作 Ap）</div>
        ${FOACA.dims
          .map(
            (d) => `<div class="fb-score-row">
              <span class="fb-score-label">${esc(d.key)} · ${esc(d.name)}</span>
              <div class="fb-score-track"><i style="width:${d.w * 3.5}%"></i></div>
              <span class="fb-score-num mono">${d.w}%</span>
            </div>`
          )
          .join("")}
        <div class="fb-variant-list" style="margin-top:14px">
          ${FOACA.gates
            .map(
              (g) => `<div class="fb-variant">
                <div class="fb-variant-row">
                  <div class="row-title">${esc(g.range)}</div>
                  <span class="tag">${esc(g.action)}</span>
                </div>
              </div>`
            )
            .join("")}
        </div>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">L1–L5 · 成熟度阶梯</h2>
        <div class="fb-variant-list" style="margin-top:10px">
          ${LADDER.map(
            (l) => `<div class="fb-variant">
              <div class="fb-variant-row">
                <div>
                  <div class="row-title">${esc(l.lv)} · ${esc(l.name)}</div>
                  <div class="row-desc">${esc(l.feat)}</div>
                </div>
              </div>
            </div>`
          ).join("")}
        </div>
        <div class="meta" style="margin-top:10px">取达标最高连续阶段为「当前阶段」。</div>
      </div>

      <div class="card fb-panel" style="margin-top:14px">
        <h2 style="margin:0 0 6px;font-size:18px">评分流程</h2>
        <div class="fb-variant-list" style="margin-top:10px">
          ${FLOW.map(
            (s, i) => `<div class="fb-variant"><div class="row-title">${i + 1}. ${esc(s)}</div></div>`
          ).join("")}
        </div>
        <div class="fb-insight" style="margin-top:12px">
          角色 KB 只评角色专业内容；公司事实 / 项目交付不计入 COVER。Agent 底层知识库独立维护，不并入各角色 COVER 汇总。
        </div>
      </div>

      <div class="meta" style="margin-top:12px">出处：${esc(META.scoringSource)}</div>
    </div>`;
  }

  function render(tab) {
    const t = tab === "manage" ? "manage" : tab === "scoring" ? "scoring" : "taxonomy";
    const main =
      t === "manage"
        ? typeof KbManage !== "undefined"
          ? KbManage.render()
          : `<div class="pad"><div class="card"><div class="empty">知识库管理脚本未加载</div></div></div>`
        : `<div class="pad fb-page">
            <div class="card fb-hero">
              <div class="tags" style="margin-bottom:10px">
                <span class="tag orange">知识库规范</span>
                <span class="tag">自待整理迁入</span>
              </div>
              <h2>${t === "scoring" ? "评分体系" : "分类体系"}</h2>
              <div class="meta">规范口径只读；文档入库与可视化请用「知识库管理」。</div>
            </div>
            ${t === "scoring" ? renderScoring() : renderTaxonomy()}
          </div>`;
    return `
      <div class="wb-shell kb-editor-shell">
        <aside class="wb-side" aria-label="知识库">
          <div class="wb-side-head">知识库</div>
          <button class="wb-side-item ${t === "manage" ? "active" : ""}" type="button" data-kb-editor-tab="manage">
            <span class="wb-side-label">知识库管理</span>
            <span class="wb-side-desc">MD · SQLite · 可视化</span>
          </button>
          <button class="wb-side-item ${t === "taxonomy" ? "active" : ""}" type="button" data-kb-editor-tab="taxonomy">
            <span class="wb-side-label">分类体系</span>
            <span class="wb-side-desc">顶层 · 三层 · 归档</span>
          </button>
          <button class="wb-side-item ${t === "scoring" ? "active" : ""}" type="button" data-kb-editor-tab="scoring">
            <span class="wb-side-label">评分体系</span>
            <span class="wb-side-desc">COVER · FOACA · L1–L5</span>
          </button>
        </aside>
        <div class="wb-main">${main}</div>
      </div>`;
  }

  return {
    META,
    TAXONOMY,
    LAYERS,
    ARCHIVE,
    COVER,
    FOACA,
    LADDER,
    render,
  };
})();
