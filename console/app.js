const ICO = {
  today: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>`,
  schedule: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M8 14h3M14 14h2M8 17h8"/></svg>`,
  todos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6.2l1.2 1.2L7.8 5"/><path d="M4.5 12.2l1.2 1.2L7.8 11"/><circle cx="5.8" cy="18" r="1.4"/></svg>`,
  chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 16.5V7.8A2.8 2.8 0 0 1 7.8 5h8.4A2.8 2.8 0 0 1 19 7.8v5.4A2.8 2.8 0 0 1 16.2 16H9l-4 3.2z"/></svg>`,
  approvals: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2.2 2.2L15.5 10"/><circle cx="12" cy="12" r="8.5"/></svg>`,
  projects: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h10M4 18h14"/><circle cx="18" cy="12" r="2"/><circle cx="20" cy="18" r="2"/></svg>`,
  progress: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/><path d="M8 6v12M14 12v6"/></svg>`,
  review: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h12l4 4v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/><path d="M14 6v4h4M8 13h6M8 17h4"/></svg>`,
  strategy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/></svg>`,
  org: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="2.2"/><circle cx="6" cy="18" r="2.2"/><circle cx="18" cy="18" r="2.2"/><path d="M12 7.2v4.2M12 11.4H6.5v4.2M12 11.4h5.5v4.2"/></svg>`,
  dna: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 4c4 3 6 5 10 16M17 4c-4 3-6 5-10 16"/><path d="M8.5 8.5h7M8 12h8M8.5 15.5h7"/></svg>`,
  genome: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 3c3.5 2.5 5.5 4.5 10 18M17 3c-3.5 2.5-5.5 4.5-10 18"/><path d="M8 8h8M7.5 12h9M8 16h8"/></svg>`,
  kb: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5V5.5z"/><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20"/></svg>`,
  crm: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="9.5" cy="7" r="3.2"/><path d="M20 8v6M17 11h6"/></svg>`,
  assets: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="8" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 8h.01M7 17h.01"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.3.6.9 1 1.6 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>`,
};

/**
 * 部署门标识（yitech002 五门独立控制台）。
 * 模板默认 opc；各门 console/ 部署时改写本常量。
 */
const SITE_GATE = "yiagent";
const SITE_META = {
  opc: { title: "铱石 OPC · 主控台", brand: "铱石 OPC", you: "主控 · CEO", home: "today", hide: [] },
  yiagent: {
    title: "YiAgent · Agent 编辑台",
    brand: "YiAgent",
    you: "Agent 编辑台",
    home: "chat",
    foot: "单基因 · 基因组 · 目标",
    /** 专属 Agent 编辑：单基因 / 基因组 + 知识库 + 目标拆解 + Provider */
    hide: [
      "today",
      "schedule",
      "todos",
      "approvals",
      "projects",
      "review",
      "strategy",
      "org",
      "dna",
      "crm",
      "assets",
    ],
  },
  erp: {
    title: "ERP · 工作台",
    brand: "ERP",
    you: "客户交付 · CEO",
    home: "today",
    hide: ["dna", "review", "strategy"],
  },
  "founder-ip": {
    title: "创始人 IP · 工作台",
    brand: "创始人 IP",
    you: "影响力 · CEO",
    home: "today",
    hide: ["dna", "review", "assets"],
  },
  cashflow: {
    title: "现金流 · 工作台",
    brand: "现金流",
    you: "经营 · CEO",
    home: "today",
    hide: ["dna", "review", "kb"],
  },
};
const SITE = SITE_META[SITE_GATE] || SITE_META.opc;

/** 产品侧栏：给人用的工作台，不暴露方案仓 01–04 / M 编号 */
const NAV_FULL = [
  {
    sec: "工作",
    items: [
      { id: "today", label: "今日", color: "#007aff" },
      { id: "schedule", label: "日程", color: "#5ac8fa", badge: "todos" },
      { id: "chat", label: "消息", color: "#0a84ff" },
      { id: "approvals", label: "审批", color: "#ff3b30", badge: "approvals" },
      { id: "projects", label: "项目", color: "#64d2ff" },
      { id: "progress", label: "进度表", color: "#30d158" },
      { id: "review", label: "全流程审阅", color: "#ff375f" },
    ],
  },
  {
    sec: "公司",
    items: [
      { id: "strategy", label: "战略", color: "#bf5af2" },
      { id: "org", label: "组织", color: "#5e5ce6" },
      { id: "dna", label: "DNA", color: "#af52de" },
      { id: "kb", label: "知识库", color: "#ff9f0a" },
      { id: "crm", label: "客户", color: "#30d158" },
      { id: "assets", label: "资产", color: "#64d2ff" },
      { id: "settings", label: "设置", color: "#8e8e93" },
    ],
  },
];

/** YiAgent 门：Agent 编辑台（目标拆解 + 单基因 / 基因组 + 知识库） */
const NAV_YIAGENT = [
  {
    sec: "规划",
    items: [{ id: "progress", label: "目标拆解", color: "#30d158" }],
  },
  {
    sec: "编辑",
    items: [
      { id: "chat", label: "单基因工作台", color: "#5ec8ff" },
      { id: "genome", label: "基因组工作台", color: "#3ecfbe" },
    ],
  },
  {
    sec: "资料",
    items: [{ id: "kb", label: "知识库", color: "#ff9f0a" }],
  },
  {
    sec: "系统",
    items: [{ id: "settings", label: "设置", color: "#8e8e93" }],
  },
];

const NAV = SITE_GATE === "yiagent" ? NAV_YIAGENT : NAV_FULL;

const SETTINGS_TABS = [
  { id: "providers", label: "Provider", desc: "模型 / Agent 供应商与密钥" },
];

/** 运行时频道表（由 Agent 管理 roster 同步生成；项目 Develop 可再挂入） */
const CHANNELS = {};

const AGENT_MGMT_LS = "opc-ceo-agent-mgmt-v1";

function ag(id, name, initial, color, opts = {}) {
  return {
    id,
    name,
    initial: initial || name.slice(0, 1),
    color: color || "#8e8e93",
    kind: opts.kind || "agent",
    sub: opts.sub || "",
    developRole: opts.developRole || null,
    system: Boolean(opts.system),
  };
}

/** 种子 Agent 库（审查委席位 system 锁定） */
const AGENT_SEED = [
  ag("ag-tiandao", "天道", "天", "#af52de", { system: true, sub: "审查进化委 · 顶点" }),
  ag("ag-gene", "基因", "基", "#af52de", { system: true, sub: "审查进化委" }),
  ag("ag-protocol", "协议", "协", "#af52de", { system: true, sub: "审查进化委" }),
  ag("ag-skill", "技能", "技", "#af52de", { system: true, sub: "审查进化委" }),
  ag("ag-knowledge", "知识", "知", "#af52de", { system: true, sub: "审查进化委" }),
  ag("ag-boundary", "边界", "边", "#af52de", { system: true, sub: "审查进化委" }),
  ag("ag-ceo", "CEO", "C", "#007aff", { sub: "战略 / 可编入任意频道" }),
  ag("ag-cto", "CTO", "T", "#248a3d", { sub: "技术" }),
  ag("ag-cmo", "CMO", "M", "#b86e00", { sub: "营销 Owner" }),
  ag("ag-cfo", "CFO", "F", "#5e5ce6", { sub: "财务" }),
  ag("ag-ea", "EA", "E", "#8e8e93", { sub: "杂活 / 分发" }),
  ag("ag-product", "Product", "P", "#34c759", { developRole: "Product", sub: "Develop · Product" }),
  ag("ag-pm", "PM", "PM", "#34c759", { developRole: "PM", sub: "Develop · PM" }),
  ag("ag-arch", "Architect", "A", "#34c759", { developRole: "Architect", sub: "Develop · Architect" }),
  ag("ag-dev", "Dev", "D", "#34c759", { developRole: "Dev", sub: "Develop · Dev" }),
  ag("ag-devops", "DevOps", "O", "#34c759", { developRole: "DevOps", sub: "Develop · DevOps" }),
  ag("ag-growth", "Growth", "G", "#ff9f0a", { sub: "增长" }),
  ag("ag-content", "Content", "Ct", "#ff9f0a", { sub: "内容" }),
  ag("ag-brand", "Brand", "B", "#ff9f0a", { sub: "品牌" }),
  ag("ag-fulfill", "Fulfillment", "Fu", "#ff9f0a", { sub: "履约草稿" }),
  ag("ag-legal", "法务", "法", "#8e8e93", { sub: "可编入频道" }),
  ag("ag-risk", "风控", "风", "#636366", { sub: "可编入频道" }),
  ag("ag-intern", "Intern", "实", "#ff375f", { kind: "human", sub: "真人 · 实习" }),
  ag("ag-sales", "Sales", "销", "#64d2ff", { kind: "human", sub: "真人 · 销售" }),
  ag("ag-delivery", "Delivery", "交", "#64d2ff", { kind: "human", sub: "真人 · 交付" }),
];

/** 种子频道：审查委必选；其余为可删起步频道（DEC-046） */
const CHANNEL_SEED = [
  {
    id: "team-review",
    name: "审查进化委员会",
    system: "review",
    badge: "必选·绝密",
    sub: "系统必选 · 不可删除",
    color: "#af52de",
    order: 10,
    kind: "team",
    memberIds: ["ag-tiandao", "ag-gene", "ag-protocol", "ag-skill", "ag-knowledge", "ag-boundary"],
  },
  {
    id: "ch-strategy",
    name: "战略委员会",
    system: false,
    sub: "起步频道 · 可删可改成员",
    color: "#0a84ff",
    order: 20,
    kind: "team",
    memberIds: ["ag-ceo", "ag-cto", "ag-cmo", "ag-cfo", "ag-ea"],
  },
  {
    id: "ch-dev",
    name: "开发编队",
    system: false,
    sub: "起步 · Develop 五席 · 可删",
    color: "#34c759",
    order: 30,
    kind: "team",
    memberIds: ["ag-product", "ag-pm", "ag-arch", "ag-dev", "ag-devops"],
  },
  {
    id: "ch-mkt",
    name: "营销编队",
    system: false,
    sub: "起步频道 · 可删可改成员",
    color: "#ff9f0a",
    order: 40,
    kind: "team",
    memberIds: ["ag-growth", "ag-content", "ag-brand", "ag-fulfill"],
  },
  {
    id: "ch-intern",
    name: "实习生团队",
    system: false,
    sub: "真人起步频道 · 可删",
    color: "#ff375f",
    order: 60,
    kind: "human",
    memberIds: ["ag-intern"],
  },
  {
    id: "ch-sales",
    name: "销售交付",
    system: false,
    sub: "真人起步频道 · 可删",
    color: "#64d2ff",
    order: 70,
    kind: "human",
    memberIds: ["ag-sales", "ag-delivery"],
  },
];

const DNA_SLOT_META = [
  { id: "G1", key: "identity", label: "身份", mutate: "低", note: "我是谁、对外怎么自报" },
  { id: "G2", key: "persona", label: "人设与决策边界", mutate: "中高", note: "能定什么 / 绝不能定什么" },
  { id: "G3", key: "knowledge", label: "知识", mutate: "中", note: "长期挂载哪些已认证材料" },
  { id: "G4", key: "capability", label: "能力与工具", mutate: "高", note: "这班允许用什么手脚" },
  { id: "G5", key: "experience", label: "经验策略", mutate: "高", note: "失败/成功蒸馏的控制信号" },
];

const DNA_PIPELINE = [
  { n: "①", title: "取得目的 DNA", note: "G1–G5 槽与等位 · 可评分分区" },
  { n: "②", title: "构建表达载体", note: "Assemble · G1/G2 必需 · Skill 限注 G3–G5" },
  { n: "③", title: "导入受体", note: "基因 → 可运行配置 · 完整性校验" },
  { n: "④", title: "检测鉴定", note: "裁判打分 · 门禁 · 无鉴定不算基因工程" },
];

const DNA_GOVERNANCE = [
  { agentId: "ag-gene", name: "基因", note: "G1–G5 槽与等位编辑" },
  { agentId: "ag-protocol", name: "协议", note: "协作协议 / 交接契约" },
  { agentId: "ag-skill", name: "技能", note: "技能正文与触发（限注槽）" },
  { agentId: "ag-knowledge", name: "知识", note: "MANIFEST / 切片治理" },
  { agentId: "ag-boundary", name: "边界", note: "越界回收与 denylist" },
  { agentId: "ag-tiandao", name: "天道", note: "审查进化委顶点 · L2 提案" },
];

const DNA_GENOMES = [
  {
    "id": "product",
    "role": "Product",
    "title": "产品 · 边界与优先级",
    "status": "init",
    "path": "AgentTeam/Develop/Product",
    "agentId": "ag-product",
    "slots": {
      "G1": {
        "key": "identity",
        "label": "身份",
        "text": "role_id: product\n显示名: Product\n编队: AgentTeam/Develop\n主责: 产品边界、优先级、对客可讲清的「能做/不做」\n自报: 开发团队 · Product；不自称最终拍板人（编队无 CTO 席；升级走战略委）"
      },
      "G2": {
        "key": "persona",
        "label": "人设与决策边界",
        "text": "语气: 用户向、边界清晰、少黑话\nmay_decide:\n- 需求切片与优先级建议（提交 PM 对齐，重大项升级战略委）\n- Demo/对外话术草案\nmust_not:\n- 擅自扩大范围超出战略与项目源头\n- 用「以后再说」掩盖未定义边界\n- 对外发布未人审的承诺\nhuman_gates:\n- 对外品牌/叙事变更\n- 付费与商务相关表述"
      },
      "G3": {
        "key": "knowledge",
        "label": "知识",
        "text": "挂载优先:\n- 项目信息（源头）与项目调研顶层表述\n- 官网/ASE 对外口径（若任务涉及）\ndenylist: 把内部工程隐喻直接当对客主叙事"
      },
      "G4": {
        "key": "capability",
        "label": "能力与工具",
        "text": "规划: ①一句话问题 ②能做/不做 ③验收口径 ④与工程里程碑对齐\n产出: 边界一页纸、用户故事切片、Demo 脚本要点\n自检: 外人能否 60 秒听懂；是否可测"
      },
      "G5": {
        "key": "experience",
        "label": "经验策略",
        "text": "DO: 每个需求写清「不做清单」。\nDO: Demo 必须对应可点路径或冻结证据。\nAVOID: 功能堆砌无验收。\nAVOID: 与创始人 IP / 开源叙事抢主句。"
      }
    }
  },
  {
    "id": "pm",
    "role": "PM",
    "title": "项目经理 · 节奏与阻塞",
    "status": "init",
    "path": "AgentTeam/Develop/PM",
    "agentId": "ag-pm",
    "slots": {
      "G1": {
        "key": "identity",
        "label": "身份",
        "text": "role_id: pm\n显示名: PM\n编队: AgentTeam/Develop\n主责: 节奏、依赖、阻塞清单、里程碑跟踪\n自报: 开发团队 · PM"
      },
      "G2": {
        "key": "persona",
        "label": "人设与决策边界",
        "text": "语气: 具体、时效、可跟进\nmay_decide:\n- 周计划编排与提醒\n- 阻塞升级建议（不代替战略委拍板）\nmust_not:\n- 隐瞒延期或伪造进度\n- 绕过团队频道共识改优先级\nhuman_gates:\n- 对外承诺的交付日变更"
      },
      "G3": {
        "key": "knowledge",
        "label": "知识",
        "text": "挂载优先:\n- 项目计划.md · 项目登记.md\n- Team 各角色 genome 状态（本目录）\ndenylist: 无来源的「听说进度」"
      },
      "G4": {
        "key": "capability",
        "label": "能力与工具",
        "text": "规划: ①里程碑对照 ②本周任务板 ③阻塞与 owner ④风险预警\n产出: 状态表、阻塞单、评审议程\n工具: 读写 opc 项目夹与看板字段说明\n自检: 每条任务是否有 owner 与截止"
      },
      "G5": {
        "key": "experience",
        "label": "经验策略",
        "text": "DO: 阻塞写「卡什么 / 谁解 / 何时升级」。\nDO: 里程碑只认可验证产出。\nAVOID: 用会议代替决策记录。\nAVOID: 进度条无证据。"
      }
    }
  },
  {
    "id": "architect",
    "role": "Architect",
    "title": "架构 · 边界与可演进",
    "status": "init",
    "path": "AgentTeam/Develop/Architect",
    "agentId": "ag-arch",
    "slots": {
      "G1": {
        "key": "identity",
        "label": "身份",
        "text": "role_id: architect\n显示名: Architect\n编队: AgentTeam/Develop\n主责: 系统边界、模块职责、演进约束、关键接口\n自报: 开发团队 · Architect"
      },
      "G2": {
        "key": "persona",
        "label": "人设与决策边界",
        "text": "语气: 结构化、权衡显式、少口号\nmay_decide:\n- 模块边界与接口草案（提交 CTO 确认）\n- 技术债登记与偿还建议\nmust_not:\n- 无门禁的「大重构」直接合入主路径\n- 把密钥/密钥路径写进仓\n- 违反「部署只许 Docker」\nhuman_gates:\n- 破坏性数据迁移\n- 跨系统权限模型变更"
      },
      "G3": {
        "key": "knowledge",
        "label": "知识",
        "text": "挂载优先:\n- YiAgent docs/architecture.md\n- factory / hof / CLI 模块边界说明\n- opc 工作台挂载与路径约定\ndenylist: 过时副本当正本"
      },
      "G4": {
        "key": "capability",
        "label": "能力与工具",
        "text": "规划: ①问题与约束 ②候选方案≤3 ③推荐与代价 ④验证方式\n产出: 架构笔记、接口草图、风险清单\n自检: 是否可演进、是否可测、是否可回滚"
      },
      "G5": {
        "key": "experience",
        "label": "经验策略",
        "text": "DO: 每个关键决策写「不选什么」。\nDO: 接口先契约后实现。\nAVOID: 过早微服务化。\nAVOID: 基因组里塞整份部署说明书。"
      }
    }
  },
  {
    "id": "dev",
    "role": "Dev",
    "title": "开发 · 实现与单测",
    "status": "init",
    "path": "AgentTeam/Develop/Dev",
    "agentId": "ag-dev",
    "slots": {
      "G1": {
        "key": "identity",
        "label": "身份",
        "text": "role_id: dev\n显示名: Dev\n编队: AgentTeam/Develop\n主责: 功能实现、单测、可复跑脚本、与工厂/CLI 联调\n自报: 开发团队 · Dev"
      },
      "G2": {
        "key": "persona",
        "label": "人设与决策边界",
        "text": "语气: 直接、可复现、贴代码与路径\nmay_decide:\n- 实现细节与本地重构（不改对外契约时）\n- 测试用例增补\nmust_not:\n- 跳过 Docker 在宿主机装服务做「验收」\n- 提交 secrets / API Key\n- 无测试的「顺便大改」\nhuman_gates:\n- 改公开 API 契约\n- 改晋升门禁语义"
      },
      "G3": {
        "key": "knowledge",
        "label": "知识",
        "text": "挂载优先:\n- 对应仓库代码与 tests/\n- 项目计划当期任务条目\n- Team Architect 接口说明\ndenylist: 复制粘贴未理解的大段代码冒充完成"
      },
      "G4": {
        "key": "capability",
        "label": "能力与工具",
        "text": "规划: ①复现/对齐验收 ②最小改动实现 ③Docker 内测 ④更新说明\n工具: git、pytest（容器内）、读写仓内文件\n产出: 代码 + 测试 + 简短说明（路径级）\n自检: 他人能否按说明复跑"
      },
      "G5": {
        "key": "experience",
        "label": "经验策略",
        "text": "DO: 先红灯测试再实现。\nDO: 改动说明写清文件路径。\nAVOID: 扩大 diff 到无关模块。\nAVOID: 用「在我机器上能跑」代替容器验证。"
      }
    }
  },
  {
    "id": "devops",
    "role": "DevOps",
    "title": "DevOps · 容器与可运行",
    "status": "init",
    "path": "AgentTeam/Develop/DevOps",
    "agentId": "ag-devops",
    "slots": {
      "G1": {
        "key": "identity",
        "label": "身份",
        "text": "role_id: devops\n显示名: DevOps\n编队: AgentTeam/Develop\n主责: Compose/镜像、健康检查、运行路径、发布可重复性\n自报: 开发团队 · DevOps"
      },
      "G2": {
        "key": "persona",
        "label": "人设与决策边界",
        "text": "语气: 操作步骤明确、环境假设写清\nmay_decide:\n- 容器编排与端口映射（本机 loopback 优先）\n- 健康检查与日志落点\nmust_not:\n- 本机脱离容器安装服务冒充部署\n- 把密钥打进镜像层或 git\n- 对公网裸露管理端口（默认 127.0.0.1）\nhuman_gates:\n- 生产/公网暴露变更\n- 密钥轮换流程变更"
      },
      "G3": {
        "key": "knowledge",
        "label": "知识",
        "text": "挂载优先:\n- docker-compose / Dockerfile\n- opc 挂载约定（WORKBENCH=/workbench）\n- factory :8787 · hof :8788 运行说明\ndenylist: 口头「环境差不多」"
      },
      "G4": {
        "key": "capability",
        "label": "能力与工具",
        "text": "规划: ①声明依赖与端口 ②compose up 可复现 ③healthz ④回滚步骤\n产出: compose 片段、运行手册短页、故障排查三条\n自检: 新人按文档能否 15 分钟起服"
      },
      "G5": {
        "key": "experience",
        "label": "经验策略",
        "text": "DO: 一切验收路径写进 compose/文档。\nDO: 密钥只 bind-mount 或环境注入。\nAVOID: 在镜像里 bake key。\nAVOID: 无 healthcheck 的「大概起来了」。"
      }
    }
  }
];


function defaultAgentMgmt() {
  return {
    agents: AGENT_SEED.map((a) => ({ ...a })),
    channels: CHANNEL_SEED.map((c) => ({ ...c, memberIds: [...c.memberIds] })),
  };
}

function loadAgentMgmt() {
  try {
    const raw = localStorage.getItem(AGENT_MGMT_LS);
    if (!raw) return defaultAgentMgmt();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed?.agents) || !Array.isArray(parsed?.channels)) return defaultAgentMgmt();
    const agents = parsed.agents;
    const channels = parsed.channels;
    // 硬保证审查委存在
    if (!channels.some((c) => c.id === "team-review" || c.system === "review")) {
      channels.unshift({ ...CHANNEL_SEED[0], memberIds: [...CHANNEL_SEED[0].memberIds] });
    }
    for (const seedAg of AGENT_SEED.filter((a) => a.system)) {
      if (!agents.some((a) => a.id === seedAg.id)) agents.push({ ...seedAg });
    }
    return { agents, channels };
  } catch {
    return defaultAgentMgmt();
  }
}

function saveAgentMgmt() {
  try {
    localStorage.setItem(
      AGENT_MGMT_LS,
      JSON.stringify({ agents: state.agentRoster, channels: state.channelRoster })
    );
  } catch {
    /* ignore quota */
  }
}

function agentById(id) {
  return state.agentRoster.find((a) => a.id === id) || null;
}

function dmIdForAgent(agentId) {
  return `dm-${agentId}`;
}

/** 由 roster 重建 CHANNELS（保留项目 Develop 动态频道） */
function syncChannelsFromRoster() {
  const preserved = {};
  for (const [id, c] of Object.entries(CHANNELS)) {
    if (c?.kind === "project-team" || c?.projectId) preserved[id] = c;
  }
  for (const k of Object.keys(CHANNELS)) delete CHANNELS[k];

  CHANNELS["cursor-workbench"] = {
    id: "cursor-workbench",
    kind: "workbench",
    side: "agent",
    order: 1,
    name: "Cursor 工作台",
    initial: "C",
    sub: "本机 Agent SDK · 单文件夹",
    color: "#007aff",
  };

  const parentOfAgent = {};
  const sorted = [...(state.channelRoster || [])].sort((a, b) => (a.order || 0) - (b.order || 0));
  sorted.forEach((ch, idx) => {
    const members = (ch.memberIds || []).map(agentById).filter(Boolean);
    const kind = ch.kind || (members.length && members.every((m) => m.kind === "human") ? "human" : "team");
    CHANNELS[ch.id] = {
      id: ch.id,
      kind,
      side: kind === "human" ? "human" : "agent",
      order: ch.order ?? 20 + idx,
      name: ch.name,
      badge: ch.badge || (ch.system === "review" ? "必选" : ""),
      sub: ch.sub || `${members.length} 名成员 · 自组频道`,
      members: members.map((m) => m.name),
      memberIds: [...(ch.memberIds || [])],
      color: ch.color || "#8e8e93",
      system: ch.system || false,
    };
    for (const m of members) {
      if (!parentOfAgent[m.id]) parentOfAgent[m.id] = ch.id;
    }
  });

  (state.agentRoster || []).forEach((a, i) => {
    const id = dmIdForAgent(a.id);
    CHANNELS[id] = {
      id,
      kind: "agent",
      side: a.kind === "human" ? "human" : a.system ? "agent" : "agent",
      order: 200 + i,
      name: a.name,
      initial: a.initial || a.name.slice(0, 1),
      sub: a.sub || (a.kind === "human" ? "真人席" : "Agent"),
      color: a.color || "#8e8e93",
      parent: parentOfAgent[a.id] || null,
      developRole: a.developRole || null,
      agentId: a.id,
      system: Boolean(a.system),
    };
  });

  Object.assign(CHANNELS, preserved);
}

function listRosterChannelIds() {
  return [...(state.channelRoster || [])]
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .map((c) => c.id)
    .filter((id) => CHANNELS[id]);
}

function isReviewChannel(channelId) {
  const c = state.channelRoster.find((x) => x.id === channelId);
  return Boolean(c && (c.system === "review" || c.id === "team-review"));
}

const PROJECT_DEV_SEATS = [
  { slug: "product", role: "Product", initial: "P" },
  { slug: "pm", role: "PM", initial: "PM" },
  { slug: "arch", role: "Architect", initial: "A" },
  { slug: "dev", role: "Dev", initial: "D" },
  { slug: "devops", role: "DevOps", initial: "O" },
];

function projectTeamChannelId(projectId) {
  return `proj-${projectId}`;
}

function projectBadge(title) {
  const t = String(title || "项目");
  return t.length > 10 ? `${t.slice(0, 10)}…` : t;
}

function importableOrgChannels() {
  return (state.channelRoster || []).filter((c) => c.system !== "review" && c.id !== "team-review");
}

function applyProjectChannelToRuntime(project, channel) {
  if (!project?.id || !channel) return null;
  const teamId = projectTeamChannelId(project.id);
  const folder = project.folder || channel.projectFolder || `项目/${project.title}`;
  const title = project.title || project.id;
  const members = channel.members || [];
  CHANNELS[teamId] = {
    id: teamId,
    kind: "project-team",
    side: "agent",
    order: 300,
    name: channel.name || "项目频道",
    sub: `「${title}」· 写隔离 ${folder} · 战略等只读`,
    members: members.map((m) => m.name),
    memberIds: members.map((m) => m.id),
    color: "#30d158",
    badge: projectBadge(title),
    projectId: project.id,
    projectFolder: folder,
    projectTitle: title,
    channelDisk: `${folder}/频道`,
  };
  // 清掉旧动态席，再挂成员
  Object.keys(CHANNELS).forEach((id) => {
    if (CHANNELS[id]?.parent === teamId) delete CHANNELS[id];
  });
  members.forEach((m, i) => {
    const slug = String(m.name || m.id || i)
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fff]+/g, "-");
    const cid = `${teamId}-dm-${slug}`;
    CHANNELS[cid] = {
      id: cid,
      kind: "agent",
      side: "agent",
      order: 301 + i,
      name: m.name,
      initial: (m.name || "?").slice(0, 1),
      sub: `${title} · 项目席 · 上下文.md`,
      color: "#30d158",
      parent: teamId,
      developRole: m.developRole || (DEVELOP_ROLE_NAMES.includes(m.name) ? m.name : null),
      projectId: project.id,
      projectFolder: folder,
      projectTitle: title,
      agentDisk: m.path || `${folder}/频道/Agents/${m.name}`,
    };
  });
  if (!state.threads[teamId]) state.threads[teamId] = [];
  return teamId;
}

async function fetchProjectChannel(project) {
  if (!project?.folder) return null;
  const res = await fetch(
    `/api/agent/project-channel?projectFolder=${encodeURIComponent(project.folder)}`
  );
  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  state.projectChannelById[project.id] = data;
  if (data.configured && data.channel) {
    applyProjectChannelToRuntime(project, data.channel);
  }
  return data;
}

function startProjectChannelWizard(projectId, { edit = false } = {}) {
  const raw = state.projects.find((p) => p.id === projectId);
  const project = enrichProject(raw);
  if (!project) {
    toast("未找到项目");
    return;
  }
  const existing = state.projectChannelById[projectId]?.channel;
  const defaultImport = importableOrgChannels().find((c) => c.id === "ch-dev") || importableOrgChannels()[0];
  let memberIds = [];
  if (edit && existing?.members?.length) {
    memberIds = existing.members.map((m) => m.id).filter(Boolean);
    // 若无 id，按名从 agentRoster 反查
    if (!memberIds.length) {
      memberIds = existing.members
        .map((m) => state.agentRoster.find((a) => a.name === m.name)?.id)
        .filter(Boolean);
    }
  } else if (defaultImport) {
    memberIds = [...(defaultImport.memberIds || [])];
  }
  state.projectChannelWizard = true;
  state.projectChannelDraft = {
    projectId,
    name: existing?.name || "项目频道",
    importChannelId: edit ? existing?.importedFrom || "" : defaultImport?.id || "",
    memberIds,
  };
  state.projectId = projectId;
  state.projectOpen = true;
  state.page = "projects";
  render();
}

function applyImportToDraft(channelId) {
  const draft = state.projectChannelDraft;
  if (!draft) return;
  draft.importChannelId = channelId || "";
  const ch = (state.channelRoster || []).find((c) => c.id === channelId);
  if (ch) draft.memberIds = [...(ch.memberIds || [])];
  render();
}

function toggleDraftMember(agentId) {
  const draft = state.projectChannelDraft;
  if (!draft) return;
  const i = draft.memberIds.indexOf(agentId);
  if (i >= 0) draft.memberIds.splice(i, 1);
  else draft.memberIds.push(agentId);
  render();
}

async function saveProjectChannelWizard() {
  const draft = state.projectChannelDraft;
  if (!draft) return;
  const nameEl = $("pcw-name");
  if (nameEl) draft.name = String(nameEl.value || "").trim() || "项目频道";
  const importEl = $("pcw-import");
  if (importEl) draft.importChannelId = importEl.value || "";
  const raw = state.projects.find((p) => p.id === draft.projectId);
  const project = enrichProject(raw);
  if (!project?.folder) {
    toast("项目文件夹未就绪");
    return;
  }
  const members = draft.memberIds
    .map((id) => {
      const a = agentById(id);
      if (!a) return null;
      return {
        id: a.id,
        name: a.name,
        developRole: a.developRole || null,
        kind: a.kind || "agent",
        sub: a.sub || "",
      };
    })
    .filter(Boolean);
  if (!members.length) {
    toast("请至少选择一名成员");
    return;
  }
  try {
    const res = await fetch("/api/agent/project-channel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        projectId: project.id,
        projectFolder: project.folder,
        projectTitle: project.title,
        name: draft.name || "项目频道",
        importedFrom: draft.importChannelId || null,
        members,
      }),
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      data = {};
    }
    if (!res.ok) {
      toast("组建失败 · " + (data.error || `HTTP ${res.status}`));
      return;
    }
    state.projectChannelById[project.id] = { ok: true, configured: true, channel: data.channel };
    applyProjectChannelToRuntime(project, data.channel);
    state.projectChannelWizard = false;
    state.projectChannelDraft = null;
    toast("项目频道已落盘 · 上下文.md 已就绪");
    render();
  } catch (e) {
    toast("无法连接 agent-bridge · " + (e.message || e));
  }
}

async function openProjectChannel(projectId) {
  const raw = state.projects.find((p) => p.id === projectId);
  const project = enrichProject(raw);
  if (!project) {
    toast("未找到项目");
    return;
  }
  if (!project.folder) {
    toast("项目文件夹未就绪 · 请稍后重试或重新打开项目");
    return;
  }
  try {
    const data = await fetchProjectChannel(project);
    if (!data?.configured) {
      startProjectChannelWizard(projectId);
      toast("请先组建项目频道");
      return;
    }
    const teamId = projectTeamChannelId(project.id);
    switchToChannel(teamId);
    toast(`已进入「${project.title}」项目频道`);
  } catch (e) {
    toast("无法读取项目频道 · " + (e.message || e));
  }
}

async function refreshProjectChannelIfOpen() {
  if (state.page !== "projects" || !state.projectOpen || !state.projectId) return;
  const raw = state.projects.find((p) => p.id === state.projectId);
  const project = enrichProject(raw);
  if (!project?.folder) return;
  try {
    await fetchProjectChannel(project);
    if (state.page === "projects" && state.projectOpen) render();
  } catch {
    /* ignore */
  }
}

function projectTeamScopes() {
  return Object.keys(CHANNELS)
    .filter((id) => CHANNELS[id].kind === "project-team")
    .sort((a, b) =>
      (CHANNELS[a].projectTitle || "").localeCompare(CHANNELS[b].projectTitle || "", "zh")
    );
}

const REPLIES = {
  "team-review": [{ from: "天道", text: "记下。高危改动只提案，请你拍板。" }],
  "ch-strategy": [{ from: "EA", text: "已记下，分发给各席并行产出。" }],
  "ch-dev": [
    { from: "PM", text: "收到，我记进进度并同步开发席。" },
    { from: "Dev", text: "好，我按这个口径改实现草稿。" },
  ],
  "ch-mkt": [{ from: "Growth", text: "收到，我拉齐 Content / Brand。" }],
  "ch-intern": [{ from: "Intern", text: "收到，确认后去办。" }],
  "ch-sales": [{ from: "Sales", text: "好，真人侧按你的口径跟。" }],
  "dm-ag-legal": [{ from: "法务", text: "收到。合同条款我标风险点后回你。" }],
  "dm-ag-risk": [{ from: "风控", text: "收到。合规红线我先扫一版。" }],
  "dm-ag-cto": [{ from: "CTO", text: "好，我整理一页风险给你。" }],
  "dm-ag-cmo": [{ from: "CMO", text: "明白，我压短一版对外口径。" }],
  "dm-ag-ceo": [{ from: "CEO", text: "先出取舍草稿，终审仍等你。" }],
  "dm-ag-cfo": [{ from: "CFO", text: "我补数字区间后贴战略委。" }],
  "dm-ag-ea": [{ from: "EA", text: "好，我去取数清洗。" }],
  "dm-ag-product": [{ from: "Product", text: "收到，改完贴回开发编队。" }],
  "dm-ag-pm": [{ from: "PM", text: "好，我更新卡点台账。" }],
  "dm-ag-arch": [{ from: "Architect", text: "我先看是否碰架构冻结。" }],
  "dm-ag-dev": [{ from: "Dev", text: "OK，今晚前提交草稿。" }],
  "dm-ag-devops": [{ from: "DevOps", text: "发布清单我改一版。" }],
  "dm-ag-growth": [{ from: "Growth", text: "收到，同步营销频道。" }],
  "dm-ag-content": [{ from: "Content", text: "稿件我按红线改。" }],
  "dm-ag-brand": [{ from: "Brand", text: "口径红线我盯着。" }],
  "dm-ag-tiandao": [{ from: "天道", text: "元层内记下；公司业务终审仍归你。" }],
  "dm-ag-gene": [{ from: "基因", text: "基因层记下。" }],
  "dm-ag-protocol": [{ from: "协议", text: "协议层记下。" }],
  "dm-ag-skill": [{ from: "技能", text: "技能层记下。" }],
  "dm-ag-knowledge": [{ from: "知识", text: "知识层记下。" }],
  "dm-ag-boundary": [{ from: "边界", text: "边界层记下；越权会拦。" }],
  "dm-ag-fulfill": [{ from: "Fulfillment", text: "履约材料我补一版。" }],
  "dm-ag-intern": [{ from: "Intern", text: "收到，确认后去办。" }],
  "dm-ag-sales": [{ from: "Sales", text: "好，真人侧按你的口径跟。" }],
};

/** 工作台内嵌 bench（非 Agent 频道列表） */
function isWorkbenchBenchMode(mode = state.workbenchMode) {
  return SITE_GATE === "yiagent" && (mode === "factory" || mode === "evolve");
}

const TITLES = {
  today: ["今日", "拍板、日程、待办与消息一眼看清"],
  schedule: ["日程", "安排与待办合一 · 按日查看 · 待办可勾选"],
  todos: ["日程", "已与日程合并"],
  chat:
    SITE_GATE === "yiagent"
      ? ["单基因工作台", "单题 / 题组搜索 · 筛最优等位组合"]
      : ["消息", "对 Team 与数字员工说话"],
  genome: ["基因组工作台", "双螺旋 · G1–G5 等位 · 悬停详情"],
  approvals: ["审批", "人审材料：引用等级 · 缺口 · 审计摘要"],
  projects: ["项目管理", "战略项目 · 客户项目 · 谁负责 · 卡在哪"],
  progress:
    SITE_GATE === "yiagent"
      ? ["目标拆解", "A/B/C/D · 任务树 · 验证产出"]
      : ["项目进度表", "按项目看阶段 · 状态 · 验证产出"],
  review: ["全流程审阅", "规格 → 题库 → 裁判 → 门禁 → 实跑 → 裁决"],
  strategy: ["战略视图", "愿景 · AI 方向 · 三条业务 · 影响力计划"],
  org: ["组织", "频道与成员 · 审查委必选 · 其余可自由组"],
  dna: ["DNA 工作台", "公司基因组 · G1–G5 · 审查委管审改"],
  kb:
    SITE_GATE === "yiagent"
      ? ["知识库", "管理 · 分类 · 评分（SQLite）"]
      : ["知识库", "人/Agent 双平面 · 溯源等级 · 审计仅人看"],
  crm: ["客户", "销售交付跟进的管道"],
  assets: ["资产管理", "主机 SSH · IT 资产 API Key（opc/公司资产）"],
  settings: ["设置", "Provider 密钥 · 模型"],
};

const TODOS_LS_KEY = "opc-ceo-todos-v1";
/** 一次性清空旧演示待办（2026-08-02）；之后用户新建的待办仍正常持久化 */
const TODOS_WIPED_KEY = "opc-ceo-todos-wiped-20260802";
const ASSETS_LS_KEY = "opc-ceo-assets-v1";

/** 公司资产种子（可被本机 localStorage 覆盖/增补） */
const ASSET_SEED = [
  {
    id: "H1",
    name: "阿里云 ECS · H1",
    kind: "server",
    provider: "aliyun",
    host: "106.15.57.89",
    sshUser: "root",
    sshPort: 22,
    pemPath: "~/.ssh/aliyun-h1.pem",
    pemHint: "正本：Desktop/opc/公司资产/IT资产/aliyun.pem · 已链到 ~/.ssh/aliyun-h1.pem",
    role: "L3 主宿主 · 官网",
    note: "仅跑 ase-official-website（官网）；Demo/Cerbos 已清",
    tags: ["生产", "官网", "阿里云"],
    website: "https://yitech.top",
  },
];
const WEEKDAY_CN = ["日", "一", "二", "三", "四", "五", "六"];

function ymd(d) {
  const x = d instanceof Date ? d : new Date(d);
  const y = x.getFullYear();
  const m = String(x.getMonth() + 1).padStart(2, "0");
  const day = String(x.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(d, n) {
  const x = new Date(d);
  x.setHours(12, 0, 0, 0);
  x.setDate(x.getDate() + n);
  return x;
}

function formatDayLabel(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  const today = ymd(new Date());
  const tomorrow = ymd(addDays(new Date(), 1));
  if (dateStr === today) return "今天";
  if (dateStr === tomorrow) return "明天";
  return `周${WEEKDAY_CN[d.getDay()]}`;
}

function buildScheduleSeed() {
  const base = new Date();
  base.setHours(12, 0, 0, 0);
  const d0 = ymd(base);
  const d1 = ymd(addDays(base, 1));
  const d2 = ymd(addDays(base, 2));
  const d3 = ymd(addDays(base, 3));
  return [
    { id: "e1", date: d0, time: "09:30", end: "10:00", title: "战略委晨会", place: "线上", kind: "会议", link: "ch-strategy" },
    { id: "e2", date: d0, time: "14:00", end: "15:30", title: "华数智造续约拜访", place: "客户现场", kind: "拜访", link: "ch-sales" },
    { id: "e3", date: d0, time: "16:30", end: "17:00", title: "审批篮清扫", place: "工作台", kind: "专注", link: null },
    { id: "e4", date: d1, time: "10:00", end: "11:00", title: "YiAgent 里程碑评审", place: "开发编队", kind: "里程碑", link: "ch-dev" },
    { id: "e5", date: d1, time: "15:00", end: "15:45", title: "创始人 IP · 内容选题", place: "营销编队", kind: "会议", link: "ch-mkt" },
    { id: "e6", date: d2, time: "11:00", end: "12:00", title: "公司战略调整对齐", place: "战略委", kind: "会议", link: "ch-strategy" },
    { id: "e7", date: d3, time: "09:00", end: "09:30", title: "周进度同步", place: "线上", kind: "会议", link: "ch-strategy" },
  ];
}

function defaultTodos() {
  return [];
}

function loadTodos() {
  try {
    if (!localStorage.getItem(TODOS_WIPED_KEY)) {
      localStorage.setItem(TODOS_LS_KEY, "[]");
      localStorage.setItem(TODOS_WIPED_KEY, "1");
      return [];
    }
    const raw = localStorage.getItem(TODOS_LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveTodos() {
  try {
    localStorage.setItem(TODOS_LS_KEY, JSON.stringify(state.todos));
  } catch {
    /* ignore quota */
  }
}

function openTodoCount() {
  return state.todos.filter((t) => !t.done).length;
}

const KB_FOLDERS = [
  { id: "all", label: "全部" },
  { id: "policy", label: "制度与红线" },
  { id: "product", label: "产品与方案" },
  { id: "team", label: "Team 沉淀" },
  { id: "draft", label: "草稿箱" },
  { id: "deny", label: "禁给 AI" },
];

const VIS_LABEL = {
  human_only: "仅人看",
  ai_ok: "已给 Agent",
  both: "人与 Agent 同看",
  deny_ai: "禁给 AI",
};

/** 来源等级 · 产品面用语（对齐 01 观测与审计 S0–S4） */
const TIER_LABEL = {
  S0: "S0 · 传闻/未核",
  S1: "S1 · 弱依据",
  S2: "S2 · 制度/存档",
  S3: "S3 · 业务核实",
  S4: "S4 · 人确认",
};

const _bootMgmt = loadAgentMgmt();

const state = {
  page: SITE.home || "today",
  channelId: SITE_GATE === "yiagent" ? "ch-dev" : "team-review",
  teamScope: SITE_GATE === "yiagent" ? "ch-dev" : "team-review",
  /** yiagent 工作台：factory 单题 | evolve 题组 */
  workbenchMode: SITE_GATE === "yiagent" ? "factory" : "agent",
  chatTab: "channel",
  chatQ: "",
  kbFolder: "all",
  kbQ: "",
  kbDocId: "k1",
  kbPlane: "human", // human = 人看 · agent = Agent 看
  kbStatus: null,
  /** yiagent 知识库：manage | taxonomy | scoring */
  kbEditorTab: "manage",
  draft: "",
  /** @ 提及选人 */
  mentionOpen: false,
  mentionQuery: "",
  mentionIndex: 0,
  mentionAt: null,
  mentionCaretEnd: null,
  inputCaret: null,
  typing: null,
  agentRoster: _bootMgmt.agents,
  channelRoster: _bootMgmt.channels,
  orgTab: "channels",
  orgFocusChannelId: "team-review",
  dnaRoleId: "product",
  dnaSlotId: "G1",
  unread: {},
  seq: 1,
  threads: {},
  /** 审批篮默认空（演示种子已清）；拍板后仍可回写会话 */
  approvals: [],
  kb: [
    {
      id: "k1",
      folder: "policy",
      title: "对外口径红线",
      who: "Brand",
      visibility: "both",
      updated: "今天 09:12",
      humanBody:
        "完整制度正文（人可读长文）：\n1. 不承诺未验收能力\n2. 价格区间需 CFO 确认后出口\n3. 客户案例需书面授权\n\n附：历史讨论纪要链接、例外申请流程（人平面可厚）。",
      agentBody:
        "【认证切片 · 可挂载】\n- 禁：未验收能力承诺\n- 价：须 CFO 确认\n- 案例：须书面授权",
      provenance: {
        tier: "S2",
        locator: "docs/policy/对外口径红线.md",
        version: "v1.4",
        certifiedBy: "Brand",
        certifiedAt: "今天 09:10",
      },
      trail: [
        { at: "上月", actor: "Brand", event: "入库", detail: "人平面上传制度稿" },
        { at: "本周", actor: "你", event: "审阅", detail: "人确认可对外" },
        { at: "今天 09:10", actor: "Brand", event: "认证发布", detail: "写出 Agent 切片 · visibility→both" },
        { at: "今天 09:15", actor: "Assembler", event: "挂载引用", detail: "source.cite · tier=S2" },
      ],
    },
    {
      id: "k2",
      folder: "product",
      title: "OPC 工作台产品说明（客户向）",
      who: "Product",
      visibility: "ai_ok",
      updated: "昨天",
      humanBody:
        "给客户看的完整一页：组织协作、消息、知识库、审批、项目与战略。\n可附截图与话术（人平面）。",
      agentBody:
        "【认证切片】产品能力：消息·组织·知识双平面·审批·项目·战略。对外不讲内部方案编号。",
      provenance: {
        tier: "S3",
        locator: "product/opc-console.ai.md",
        version: "v0.9",
        certifiedBy: "Product",
        certifiedAt: "昨天",
      },
      trail: [
        { at: "上周", actor: "Product", event: "入库", detail: "客户向长文 · 默认仅人看" },
        { at: "昨天", actor: "Product", event: "认证发布", detail: "压缩为切片 · ai_ok" },
      ],
    },
    {
      id: "k3",
      folder: "team",
      title: "开发团队 · 长程编程约定",
      who: "CTO",
      visibility: "ai_ok",
      updated: "本周",
      humanBody: "稳 × 快。交接字段必须齐：目标、边界、验收、风险。\n（人可读完整约定与示例。）",
      agentBody: "【挂载】交接必含：goal / boundary / acceptance / risk。稳×快。",
      provenance: {
        tier: "S3",
        locator: "team/dev/handoff-contract.ai.md",
        version: "v2.0",
        certifiedBy: "CTO",
        certifiedAt: "本周",
      },
      trail: [
        { at: "上月", actor: "CTO", event: "入库", detail: "Team 沉淀" },
        { at: "本周", actor: "CTO", event: "认证发布", detail: "交接字段强制" },
        { at: "本周", actor: "开发 Agent", event: "挂载引用", detail: "长程任务 checkpoint 引用" },
      ],
    },
    {
      id: "k4",
      folder: "draft",
      title: "华东投放三种预算档",
      who: "CFO",
      visibility: "human_only",
      updated: "今天 08:50",
      humanBody: "草稿三档预算与回报区间（仅人审阅）。\n默认未标注 = 仅人看；不可被数字员工当正式依据。",
      agentBody: "",
      provenance: {
        tier: "S1",
        locator: "draft/华东投放预算.xlsx",
        version: "draft",
        certifiedBy: null,
        certifiedAt: null,
      },
      trail: [
        { at: "今天 08:50", actor: "CFO", event: "入库", detail: "草稿 · 未认证 · 默认仅人看" },
        {
          at: "今天 09:01",
          actor: "边界",
          event: "拒绝挂载",
          detail: "Assembler 请求被拒 · 未认证不可进模型",
        },
      ],
    },
    {
      id: "k5",
      folder: "deny",
      title: "密钥与禁扫路径（索引）",
      who: "边界",
      visibility: "deny_ai",
      updated: "上月",
      humanBody: "敏感路径索引给人清理用。\n硬禁：永不进 Agent 上下文 / MANIFEST。",
      agentBody: "",
      provenance: {
        tier: "S4",
        locator: "deny/secrets-index.md",
        version: "v1",
        certifiedBy: null,
        certifiedAt: null,
      },
      trail: [
        { at: "上月", actor: "边界", event: "标记硬禁", detail: "deny_ai · 永不进 assemble" },
        { at: "上周", actor: "边界", event: "拒绝挂载", detail: "authz.deny · 禁区命中" },
      ],
    },
    {
      id: "k6",
      folder: "product",
      title: "华数智造合同 PDF（扫描件）",
      who: "销售交付",
      visibility: "human_only",
      updated: "本周",
      humanBody: "盖章扫描 PDF · 人平面正式件。\n要给 Agent 用须先认证出切片，不能整份 PDF 塞进模型。",
      agentBody: "",
      provenance: {
        tier: "S4",
        locator: "contracts/华数智造-盖章.pdf",
        version: "signed",
        certifiedBy: null,
        certifiedAt: null,
      },
      trail: [
        { at: "本周", actor: "销售交付", event: "入库", detail: "人确认盖章件 · 定稿≠进 AI" },
      ],
    },
  ],
  crm: [
    { name: "华数智造", stage: "谈判", owner: "销售交付", amount: "¥128万", next: "今日续约拜访" },
    { name: "青云工业", stage: "线索", owner: "Growth → 销售", amount: "—", next: "首聊材料已就绪" },
    { name: "星河物流", stage: "交付", owner: "Delivery", amount: "¥46万", next: "验收纪要待签" },
  ],
  projects: [],
  strategy: {
    source: "05-战略 · 公司战略收敛正本 v0.1.1 · 待确认",
    horizon: "2026 H2",
    vision: "让 AI 成为每个人都用得起、用得动的同事",
    mission: "把 AI 使用门槛降到零——不做「更强的工具」，做「更好合作的同事」",
    northStar: "让 AI 成为每个人都用得起、用得动的同事",
    tech: "快·好·可追溯审计（迭代快/快速开发 · 高标准可衡量 · 可审计）",
    barriers: [
      { name: "技术门槛", goal: "用人话交代任务，不用写提示词/代码" },
      { name: "认知门槛", goal: "AI 主动理解意图" },
      { name: "信任门槛", goal: "可溯源、会坦白、不瞎编 · 可追溯审计" },
    ],
    /** AI 方向目标（横切组织与产品） */
    aiGoals: [
      {
        id: "ai-1",
        title: "能交给 AI 做的，坚决不让人做",
        note: "凡可自动化、可 Agent 化的工作，默认不派真人；人只留拍板、例外与责任边界。",
      },
      {
        id: "ai-2",
        title: "让 AI 实现协同进化",
        note: "Agent / 人 / 组织彼此反馈迭代：不是单点工具，而是一起变强的编队。",
      },
    ],
    rhythm: "1+1+0.5 · ASE ≈80% · 咨询 ≈20% · 同事内部验证",
    pillars: [
      {
        id: "s1",
        title: "ASE 平台",
        priority: "P0 主攻",
        metric: "AI 软件持续进化 · 交付 + 年度演进 · 攻技术门槛",
        health: "稳",
        owner: "CTO / 营销",
        share: "约 80% 资源",
        initiatives: ["ASE 官网主推与案例驱动", "ASE FDE 样板交付", "公域内容获客"],
      },
      {
        id: "s2",
        title: "AI 咨询",
        priority: "P1 辅攻",
        metric: "企业 AI 升级决策入口 · 熟人/校友会 L1 · 攻认知门槛",
        health: "稳",
        owner: "你 / CMO",
        share: "约 20% 资源",
        initiatives: ["熟人/校友会 · AI 咨询 L1 诊断"],
      },
      {
        id: "s3",
        title: "AI 同事",
        priority: "P2 储备",
        metric: "可招呼、会担事的组织 AI · 内部验证 · 不对客主推",
        health: "压",
        owner: "CTO",
        share: "内部验证",
        initiatives: ["AI 同事 · 内部验证（不对客主推）"],
      },
    ],
    /** 横切：被看见（非第四条业务线） */
    influence: {
      title: "影响力计划",
      question: "如何被更多的人看到",
      owner: "你 / CMO / CTO",
      note: "不为第四条业务线 · 放大 ASE 可见度与信任",
      tracks: [
        {
          id: "p11",
          title: "YiAgent 开源计划",
          blurb: "产品开源可见 · 技术与开发者影响力",
        },
        {
          id: "p12",
          title: "创始人 IP",
          blurb: "讲座专业性 + Agent 评测露产品 · 服务 ASE 获客",
        },
      ],
    },
    bets: [
      { title: "一条主攻、一条辅攻、一条储备", note: "不可三线并列对外主推" },
      { title: "官网与主传播只讲 ASE", note: "咨询在熟人圈；AI 同事不进官网主叙事" },
      { title: "统一句：铱石 = ASE 软件进化", note: "咨询是入口；AI 同事是后续组织升级" },
      { title: "影响力计划服务被看见", note: "YiAgent 开源 + 创始人 IP · 不另起对外品牌" },
      { title: "能交给 AI 的坚决不让人做", note: "AI 方向目标 · 人只留拍板与例外" },
      { title: "让 AI 实现协同进化", note: "AI 方向目标 · 编队互馈迭代" },
      { title: "FDE 式落地", note: "一场景/一体机验证 → 关键动作人审 → 再扩展" },
      { title: "利润分成推广试验", note: "待拍板 · 不是第四条业务 · 可止损" },
    ],
    pending: [
      { title: "收敛稿是否升为战略单文件正本？", note: "确认后 save/ 正式保存" },
      { title: "利润分成型外部推广是否进 H2 试验？", note: "先定允不允许这一类" },
      { title: "旧 A/B·XTeam 是否仅作内部工程隐喻？", note: "对外叙事不混用" },
    ],
  },
  projectFilter: "全部",
  projectCategory: "全部",
  projectId: null,
  projectOpen: false,
  projectEditing: false,
  /** 进度表页当前选中的项目 id */
  progressProjectId: null,
  /** 进度表页当前目标字母（A / B …） */
  progressGoalLetter: "A",
  /** 进度树折叠：nodeId → true=折叠；未登记则用默认策略 */
  progressFold: {},
  /** 跨任务跳转高亮节点 ID（如 D2A） */
  progressHighlightId: null,
  /** 全流程审阅：当前包 / 阶段 / 各阶段人审结论 */
  reviewPackId: "ai_科普",
  reviewStage: "demand",
  reviewDecisions: {},
  reviewNote: "",
  /** DEC-047 项目频道 */
  projectChannelById: {},
  projectChannelWizard: false,
  projectChannelDraft: null,
  projectsLoaded: false,
  projectsError: null,
  schedule: buildScheduleSeed(),
  scheduleDay: ymd(new Date()),
  todos: loadTodos(),
  todoFilter: "open",
  settingsTab: "providers",
  providers: [],
  providersMeta: { cwd: "", model: "", activeProvider: "", bridgeOk: false, error: null },
  providerEditId: null,
  providerDraftKey: "",
  providerDraftModel: "",
  providersLoading: false,
  assets: [],
  assetProbe: {},
  itSecrets: [],
  itSecretsError: null,
  itSecretsLoading: false,
  itSecretReveal: {},
};

syncChannelsFromRoster();

/** 项目详情补充（演示层；API 行字段之外的目标 / 任务 / 进度表） */
const PROJECT_EXTRA = {
  p11: {
    goal: "以开源把 YiAgent 推到更多人眼前，做出可演示、可对外讲清边界的产品形态，承接影响力计划与 ASE 主攻。",
    summary: "影响力计划 · 开源可见 · 与官网 ASE 叙事对齐，避免另起对外品牌。",
    repo: {
      url: "https://github.com/Saint2078/YiAgent",
      defaultBranch: "main",
      branches: [
        { name: "develop", role: "日常开发", note: "主开发线" },
        { name: "release", role: "发布候选", note: "合入前稳定" },
        { name: "demo", role: "演示冻结", note: "对外/路演" },
      ],
    },
    tasks: [
      { id: "tk1", goal: "产品边界一页纸（能做什么 / 不做什么）", assignee: "Product", status: "进行中", due: "本周" },
      { id: "tk2", goal: "可演示脚本与样例会话", assignee: "Dev", status: "待开始", due: "下周" },
      { id: "tk3", goal: "对外口径与 ASE 同频评审", assignee: "CMO", status: "等人", due: "待定" },
    ],
    /**
     * 多目标进度树（调研稿 1 基因工程 + 调研稿 2 基因算法手段拆分）。
     * 命名：目标字母 + 数字 + A–Z（A1 / A1A、B1 / B1A…）。
     * A 产基因 · B 组装 · C 加速筛选 · D 降低消耗。
     */
    progressGoals: [
        {
          "letter": "A",
          "title": "一句话 → 完整 Agent 基因",
          "example": "我需要一个专门写营销文章的 Agent",
          "tree": [
            {
              "title": "表型目标：一句话 → 可评测规格",
              "means": "基因工程·实验目标",
              "relation": "黑盒外侧先定成功样子",
              "status": "done",
              "due": "目标 A",
              "evidence": "一句话落到可评分规格；不靠灌装说明书当进化",
              "children": [
                {
                  "title": "需求句模板与解析",
                  "means": "规格入口",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T7：docs/seed-genome.md 需求句→manifest 模板＋科普填好样例"
                },
                {
                  "title": "Agent 规格一页（能做/不做）",
                  "means": "表型成功标准",
                  "status": "done",
                  "due": "当期",
                  "evidence": "04/00 规格一页；T7 核验 8 条全可挂题目与裁判"
                }
              ]
            },
            {
              "title": "取得目的 DNA：G1–G5 槽与等位",
              "means": "基因工程①取得目的DNA",
              "relation": "按槽可评分才叫基因分区",
              "status": "done",
              "due": "目标 A",
              "evidence": "T7：种子库＋锚点＋黑盒约束三件套齐",
              "children": [
                {
                  "title": "G1–G5 槽位与评分锚点",
                  "means": "基因分区",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T7：每槽评分锚点表入 docs/seed-genome.md"
                },
                {
                  "title": "种子等位与初值库",
                  "means": "等位基因库",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T7：factory/fixtures/seed/ai_kepu_seed.json（G1–G5 每槽 2–3 等位＋对照等位）"
                },
                {
                  "title": "黑盒约束：拒绝灌装当进化",
                  "means": "告知≠提升",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T7：声明＋单测（等位文本不含维度 id / 权重 / 分档原文）"
                }
              ]
            },
            {
              "title": "鉴定体系：题目 + 裁判 + 门禁",
              "means": "基因工程④检测鉴定",
              "relation": "无鉴定不算基因工程；‖ 可与 A2 并行",
              "status": "done",
              "due": "目标 A",
              "evidence": "题库 12 题＋五维裁判＋配对门禁全接线",
              "children": [
                {
                  "title": "题目收集与组合（manifest）",
                  "means": "表型检测集",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T7：0803c197a73c（8 进化＋4 holdout，preflight 无 errors）"
                },
                {
                  "title": "裁判维度 / prompt / 模型固定",
                  "means": "鉴定标准",
                  "status": "done",
                  "due": "当期",
                  "evidence": "04/01 五维加权＋一票否决；T7 核验 judge 接线并修 test_type 回填"
                },
                {
                  "title": "晋升门禁与显著性口径",
                  "means": "裁决层（空位）",
                  "status": "done",
                  "due": "可后置",
                  "evidence": "T1：配对 t + bootstrap CI 替代固定 Δ，门禁记录 p/CI；阈值回填待实跑"
                }
              ]
            },
            {
              "title": "进化筛选：变异 + 选择 + 多样性",
              "means": "基因算法·Mutation/Selection",
              "relation": "差异化在筛选侧；依赖 A2+A3 输入",
              "status": "current",
              "due": "目标 A",
              "evidence": "种群多代后冠军基因有可复现证据",
              "children": [
                {
                  "title": "单题基因优化闭环验证",
                  "means": "最小进化闭环",
                  "status": "done",
                  "due": "已达成",
                  "evidence": "冒烟 2a431c0f67be"
                },
                {
                  "title": "槽交叉 / 突变 / 随机移民",
                  "means": "Recombination·Migration",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T1：自适应变异（停滞→大开角重写，提升回落）+ 每代 1–2 随机移民；消融数字待实跑"
                },
                {
                  "title": "题组合多代 + 可复现 report",
                  "means": "适应度卡",
                  "status": "blocked",
                  "due": "当期",
                  "evidence": "待实跑：人触发 POST /api/evolve/start（manifest 0803c197a73c＋种子 ai_kepu_seed）"
                },
                {
                  "title": "小样本漂移控制（配对/CI）",
                  "means": "Drift 对策",
                  "status": "done",
                  "due": "可后置",
                  "evidence": "T1 paired_gate 即漂移控制口径；数据验证随 A4C 实跑"
                }
              ]
            },
            {
              "title": "经鉴定的完整基因组交付",
              "means": "基因工程验收物",
              "relation": "目标 A 验收 · 供目标 B 组装",
              "status": "current",
              "due": "目标 A",
              "evidence": "gene hash 可加载；非「聊天壳」",
              "children": [
                {
                  "title": "冠军基因组固化",
                  "means": "基因型归档",
                  "status": "blocked",
                  "due": "当期",
                  "evidence": "待实跑：依赖 T4 出冠军后固化 gene hash"
                },
                {
                  "title": "基因组可加载接口",
                  "means": "供表达载体消费",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T2：yiagent hof pull → ~/.yiagent/hof → improve --apply 离线闭环"
                },
                {
                  "title": "边界一页 + 对外可讲",
                  "means": "表型主张",
                  "status": "done",
                  "due": "当期",
                  "evidence": "04/00 规格一页即对外边界；T7 核验可挂裁判"
                }
              ]
            }
          ]
        },
        {
          "letter": "B",
          "title": "基于基因，组装出一个 Agent",
          "example": "拿冠军基因组 → 装配成可运行的营销文 Agent",
          "tree": [
            {
              "title": "构建表达载体：装配规则与标记",
              "means": "基因工程②构建表达载体",
              "relation": "目标 B 设计层",
              "status": "done",
              "due": "目标 B",
              "evidence": "T3：src/yiagent/assembly.py 落地",
              "children": [
                {
                  "title": "分槽装配规则（G→运行时）",
                  "means": "载体结构",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T3：SLOT_RULES——G1/G2 必需 block、G3–G5 缺省跳过、Skill 限注 G3–G5"
                },
                {
                  "title": "可观测标记与配置包格式",
                  "means": "选择标记类比",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T3：expression_vector 配置包，gene_hash/槽位标记/校验结果可审计可复现"
                }
              ]
            },
            {
              "title": "导入受体：装入运行时躯体",
              "means": "基因工程③导入受体",
              "relation": "输入来自 A 或基因库",
              "status": "done",
              "due": "目标 B",
              "evidence": "T5＋T8：三来源收口＋严格 hash 门禁＋三账齐",
              "children": [
                {
                  "title": "基因来源接入与完整性校验",
                  "means": "转化前质检",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T5：recipient.py 三来源收口（本地 bank / hof 包 / improve 包），validation.status!=ok 即 Blocked；严格 hash 门禁"
                },
                {
                  "title": "基因 → 可运行配置",
                  "means": "转化/转染",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T5：yiagent assemble → expression_vector 落盘 ~/.yiagent/assembled/，固定时间戳逐字节可复现"
                },
                {
                  "title": "工具 / 记忆 / 人设挂载",
                  "means": "表达开启",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T8：能力三账齐（tools_match / slot_mounts / genome_text）"
                }
              ]
            },
            {
              "title": "组装后检测鉴定（表型）",
              "means": "基因工程④检测鉴定",
              "relation": "验收前必过",
              "status": "done",
              "due": "目标 B",
              "evidence": "T8：offline 鉴定全过；live 行为鉴定待人触发",
              "children": [
                {
                  "title": "表型冒烟：对话或工具调用",
                  "means": "表型筛选",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T8：yiagent smoke offline 9 项全过；--live 仅人触发"
                },
                {
                  "title": "与规格对照（能做/不做）",
                  "means": "基因型+表型对照",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T8：checklist auto 7 过 0 挂；4 条 wont 待 live 打分"
                }
              ]
            },
            {
              "title": "可交付组装件",
              "means": "工程交付",
              "relation": "目标 B 验收",
              "status": "done",
              "due": "目标 B",
              "evidence": "T8：三步链路核验＋演示包；live 演示待人触发",
              "children": [
                {
                  "title": "一键组装 CLI / API",
                  "means": "标准化转化",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T8：hof pull → assemble → chat --vector 三步可审计"
                },
                {
                  "title": "场景演示包",
                  "means": "表型展示",
                  "status": "done",
                  "due": "当期",
                  "evidence": "T8：demo/kepu/（种子 bank＋组装脚本＋可复现样例 vector）"
                }
              ]
            }
          ]
        },
        {
          "letter": "C",
          "title": "尽可能提升基因筛选的速度",
          "example": "同样鉴定标准下，单位时间筛完更多代",
          "tree": [
            {
              "title": "度量：选择侧墙钟瓶颈",
              "means": "基因算法·先量适应度成本",
              "relation": "先量后改",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "评测/裁判/变异/IO 占比 + KPI",
              "children": [
                {
                  "title": "筛选耗时拆解",
                  "means": "剖析",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "各阶段占比可指"
                },
                {
                  "title": "速度 KPI（代际墙钟、P50/P95）",
                  "means": "吞吐指标",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "基线数字可复跑"
                }
              ]
            },
            {
              "title": "适应度缓存与去重",
              "means": "避免重复 Selection 评测",
              "relation": "低风险加速",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "gene×题×裁判命中；命中率进 report",
              "children": [
                {
                  "title": "缓存键规范",
                  "means": "复用",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "键稳定可复现"
                },
                {
                  "title": "跨代 / 跨跑复用",
                  "means": "种群记忆",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "重复个体不重复评测"
                }
              ]
            },
            {
              "title": "种群并行与批量评测",
              "means": "基因算法·种群并行适应度",
              "relation": "吞吐主杠杆",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "墙钟随并发下降有数字",
              "children": [
                {
                  "title": "种群级并行评测",
                  "means": "并行适应度",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "并发上限可配"
                },
                {
                  "title": "裁判 / API 批处理",
                  "means": "批适应度",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "无限流静默丢分"
                }
              ]
            },
            {
              "title": "级联早停与自适应采样",
              "means": "Cascade evaluation 类比",
              "relation": "少评同样可信",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "与 A 门禁兼容的早停规则",
              "children": [
                {
                  "title": "逐题 / 逐 rep 早停",
                  "means": "级联门禁",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "劣势个体少评；规则可辩护"
                },
                {
                  "title": "代际收敛早停",
                  "means": "终止条件",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "停滞停烧代"
                }
              ]
            },
            {
              "title": "代理预筛 + 完整裁判后置",
              "means": "级联筛选 / 廉价适应度",
              "relation": "贵裁判后置",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "漏筛率有估计",
              "children": [
                {
                  "title": "代理分 / 启发式预筛",
                  "means": "廉价适应度",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "预筛规则可指"
                },
                {
                  "title": "Top-k / 边界晋升完整裁判",
                  "means": "级联终评",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "仅关键个体吃满 A3 裁判"
                }
              ]
            },
            {
              "title": "速度验收包",
              "means": "对照实验",
              "relation": "目标 C 验收",
              "status": "upcoming",
              "due": "目标 C",
              "evidence": "加速比 + 质量不崩（同 A3 组合）",
              "children": [
                {
                  "title": "同题组合加速对比报告",
                  "means": "消融/对照",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "墙钟 + 门禁对照表"
                },
                {
                  "title": "默认速度配置与回退",
                  "means": "工程开关",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "一键回退基线"
                }
              ]
            }
          ]
        },
        {
          "letter": "D",
          "title": "尽可能降低基因筛选的消耗",
          "example": "同样可辩护门禁下，更低 token/$ 拿到可用冠军",
          "tree": [
            {
              "title": "度量：适应度账单拆解",
              "means": "基因算法·适应度成本会计",
              "relation": "先算清楚再省",
              "status": "upcoming",
              "due": "目标 D",
              "evidence": "生成/作答/裁判分项 token/$ 基线",
              "children": [
                {
                  "title": "消耗分项记账",
                  "means": "成本剖析",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "三路消耗可指"
                },
                {
                  "title": "消耗 KPI（$/代、token/基因）",
                  "means": "成本指标",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "基线可复跑"
                }
              ]
            },
            {
              "title": "少调用：复用与预算帽",
              "means": "Selection 调用最小化",
              "relation": "与 C 缓存/早停协同，验收看 $",
              "status": "upcoming",
              "due": "目标 D",
              "evidence": "命中节省额 + max $/次 evolve",
              "children": [
                {
                  "title": "强制缓存命中计节省",
                  "means": "复用适应度",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "report 写次数与估算 $"
                },
                {
                  "title": "评测预算帽",
                  "means": "成本预算门禁",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "超限可停可降级"
                }
              ]
            },
            {
              "title": "降单价：模型与分级路由",
              "means": "廉价适应度 + 贵终评",
              "relation": "与 C5 / 级联对齐",
              "status": "upcoming",
              "due": "目标 D",
              "evidence": "大部分走低价路径",
              "children": [
                {
                  "title": "候选生成（变异）用廉价模型",
                  "means": "Mutation 降本",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "质量对照可指"
                },
                {
                  "title": "裁判分级计价路由",
                  "means": "Selection 降本",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "预筛便宜、终评完整裁判"
                }
              ]
            },
            {
              "title": "降体量：代表题与上下文裁剪",
              "means": "控制 Drift 成本",
              "relation": "小样本仍可辩护；禁偷砍 holdout",
              "status": "upcoming",
              "due": "目标 D",
              "evidence": "进化子集与 holdout 分账；输入 token 下降有数",
              "children": [
                {
                  "title": "题集分层与代表题",
                  "means": "适应度抽样",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "holdout 另账不混烧"
                },
                {
                  "title": "prompt / 轨迹裁剪",
                  "means": "上下文降本",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "评分口径不变"
                }
              ]
            },
            {
              "title": "消耗验收包",
              "means": "对照实验",
              "relation": "目标 D 验收",
              "status": "upcoming",
              "due": "目标 D",
              "evidence": "消耗下降 + 门禁质量不崩",
              "children": [
                {
                  "title": "同题组合消耗对比报告",
                  "means": "消融/对照",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "token/$/调用 + 冠军/门禁"
                },
                {
                  "title": "默认省耗配置与回退",
                  "means": "工程开关",
                  "status": "upcoming",
                  "due": "当期",
                  "evidence": "一键回退基线消耗路径"
                }
              ]
            }
          ]
        }
      ],
    /**
     * C/D 重叠手段的跨任务连接（同一工程改动，KPI 分列）。
     * nodes 使用标注后的稳定 ID（C2A、D2A…）。
     */
    progressCrossLinksMeta: "C/D 重叠手段 · 工程可一次做完 · KPI 分列验收",
    progressCrossLinks: [
      {
        id: "XL-CD-BASELINE",
        title: "基线度量 instrumentation",
        nodes: ["C1", "C1A", "D1", "D1A"],
        shared: "同一次 evolve 跑同时产出时延拆解与消耗分项",
        split: { C: "墙钟/阶段占比", D: "token/$/调用分项" },
      },
      {
        id: "XL-CD-CACHE",
        title: "适应度缓存与复用",
        nodes: ["C2", "C2A", "C2B", "D2", "D2A"],
        shared: "同一套 gene×题×裁判 缓存键与命中逻辑",
        split: { C: "墙钟下降（少重复评测）", D: "token/$ 节省额进 report" },
      },
      {
        id: "XL-CD-CASCADE",
        title: "级联早停 / 少评",
        nodes: ["C4", "C4A", "C4B", "D2", "D2B"],
        shared: "同一套早停/采样规则；预算帽可共用开关",
        split: { C: "代际墙钟缩短", D: "调用次数与 $ 上限" },
      },
      {
        id: "XL-CD-TIER",
        title: "分级裁判 / 廉价适应度",
        nodes: ["C5", "C5A", "C5B", "D3", "D3B"],
        shared: "预筛便宜 → Top-k/边界吃完整裁判 的同一路由",
        split: { C: "终评队列更短、吞吐更高", D: "平均 $/个体下降" },
      },
      {
        id: "XL-CD-ACCEPT",
        title: "同题组合对照验收",
        nodes: ["C6", "C6A", "D5", "D5A"],
        shared: "同一 A3 题组合、同一基线跑次出两张对照表",
        split: { C: "加速比 + 门禁", D: "消耗比 + 门禁" },
      },
    ],

    /** 本轮任务登记（2026-08-01 · 对应 项目计划.md §2；每个任务带依赖与必要信息） */
    progressTasksMeta: "任何推进先入此表 · agent 只执行任务 · 进度状态仅主会话更新 · Docker 全量 105 passed",
    progressTasks: [
      {
        id: "T1",
        nodes: "A3C ＋ A4B ＋ §1.1#3/#4",
        goal: "① 配对显著性门禁（配对 t / bootstrap CI 替代固定 Δ，门禁记录 p/CI）；② 自适应变异（停滞→大开角重写，提升回落）＋随机移民（每代 1–2 个无种子重组）；③ report 体现评分失败率、按题型/套件分层",
        deps: "A4A 冒烟数据（run 2a431c0f67be）已存在，用于校准阈值；机制底座已在",
        info: "factory/server/evolve.py · factory/server/testset.py · tests/test_factory_evolve.py",
        status: "已完成",
        evidence: "代码+单测落地；阈值回填与消融数字待下次实跑",
      },
      {
        id: "T2",
        nodes: "A5B ＋ 名人堂 H3",
        goal: "yiagent hof pull {gene_hash}：榜单基因组下载入本地库（~/.yiagent/hof/），衔接 yiagent improve --apply，三步内可用",
        deps: "名人堂服务端 genome 下载端点（已实现）；CLI 框架（已存在）",
        info: "src/yiagent/hof_pull.py · src/yiagent/cli/main.py · tests/test_hof_pull.py",
        status: "已完成",
        evidence: "离线闭环含 apply 消费验证；真实服务端联调待 H2 实跑",
      },
      {
        id: "T3",
        nodes: "B1A ＋ B1B",
        goal: "分槽装配规则（assembly.py：G1/G2 必需 block、G3–G5 缺省跳过、Skill 限注 G3–G5）＋可观测配置包（gene_hash/槽位标记/校验结果，可审计可复现）；坏基因 Blocked 不硬组装",
        deps: "entity runtime 已在（commit 77d99b6）；既有 fixtures 基因组样例",
        info: "src/yiagent/assembly.py · src/yiagent/agent/__init__.py · tests/test_assembly.py · docs/architecture.md",
        status: "已完成",
        evidence: "17 用例全绿；B2A 校验钩子已预留",
      },
      {
        id: "T4",
        nodes: "C1 ＋ D1（XL-CD-BASELINE）",
        goal: "速度/消耗度量基线：同一次 evolve 实跑产出墙钟拆解与 token/$ 分项，并回填 T1 门禁阈值与消融数字",
        deps: "需人通过 API 触发实跑（POST /api/evolve/start）；T1 已上线 instrumentation 口径",
        info: "factory/server/evolve.py report · 运行数据归档 experiments/",
        status: "待实跑",
        evidence: "约定：实跑只由人触发，agent 不代跑",
      },
      {
        id: "T5",
        nodes: "B2A ＋ B2B（＋B2C 部分）",
        goal: "导入受体：三来源（本地 bank / hof 包 / improve 包）统一接入＋完整性校验（不过即 Blocked）；严格 hash 门禁；yiagent assemble → 配置包落盘可复现；能力清单一致性核对",
        deps: "T3 表达载体与配置包（已完成）；A5B 基因组可加载接口（已完成）",
        info: "src/yiagent/recipient.py · src/yiagent/assembly.py · tests/test_recipient.py",
        status: "已完成",
        evidence: "29 新用例，全量 134 passed；B3 鉴定锚点已预留",
      },
      {
        id: "T6",
        nodes: "T4 前置 ＋ E3（部分）",
        goal: "实跑前准备：① 墙钟 instrumentation（wall_by_stage 耗时分布，与 token_by_stage 并列）；② GET /api/evolve/preflight 起飞前检查（holdout 题数/混题型/密钥/HOF/预算）；③ experiments 归档脚本；④ docs/experiments.md 实跑 playbook",
        deps: "题库与裁判门禁由 Cursor 线准备中；token 分项已在（token_by_stage）",
        info: "factory/server/evolve.py · factory/server/preflight.py · experiments/archive_evolve_run.py · docs/experiments.md",
        status: "已完成",
        evidence: "16 新用例，全量 150 passed；题库就绪后按 playbook 七步开跑",
      },
      {
        id: "T7",
        nodes: "A1A/A1B ＋ A2 ＋ A3A/A3B ＋ A5C",
        goal: "目标 A 收尾：需求句模板；规格一页核验；G1–G5 种子等位库＋评分锚点＋黑盒约束；ai_科普 manifest（holdout≥3）；裁判接线核验",
        deps: "Cursor 题库＋评测包已交付（case/ai_科普、项目调研/04）；T1–T6",
        info: "factory/fixtures/seed/ai_kepu_seed.json · factory/save/manifests/0803c197a73c.json · docs/seed-genome.md",
        status: "已完成",
        evidence: "manifest 8+4 过 preflight；规格 8 条无缺项；修 test_type 回填；全量 157 passed",
      },
      {
        id: "T8",
        nodes: "B2C ＋ B3 ＋ B4",
        goal: "目标 B 收尾：能力三账齐；yiagent smoke 表型冒烟（offline/live 两态）；规格对照 checklist；一键组装三步核验；demo/kepu 演示包",
        deps: "T3/T5 装配链；04/00 规格一页",
        info: "src/yiagent/phenotype.py · demo/kepu/ · docs/phenotype-checklist.md · tests/test_phenotype.py",
        status: "已完成",
        evidence: "22 新用例，全量 179 passed；live 行为鉴定待人触发（yiagent smoke --live）",
      },
    ],

    milestones: [],
    checkpoints: [],
  },
  p12: {
    goal: "讲座体现专业性 + Agent 评测对比露出产品，服务影响力与获客，且不另开主战场。",
    summary: "影响力计划 · 你本人出镜定调 · A 讲座专业性 · B 评测露产品。",
    tasks: [
      { id: "tk4", goal: "专业定位一页（讲什么/不讲什么）", assignee: "你", status: "进行中", due: "本周" },
      { id: "tk5", goal: "首场讲座选题与讲纲草稿", assignee: "Content", status: "待开始", due: "下周" },
      { id: "tk5b", goal: "评测露出边界与公平规则一页", assignee: "你", status: "待开始", due: "本周" },
    ],
    /**
     * 目标 A：体现专业性，通过做知识讲座。
     * 目标 B：露出公司产品，通过做 Agent 评测与对比。
     * 命名：字母 + 数字 + A–Z（A1 / A1A、B1 / B1A…）。
     */
    progressGoals: [
      {
        letter: "A",
        title: "体现专业性，通过做知识讲座",
        example: "一场面向校友/行业的 ASE 知识讲座，讲完有人觉得「这人懂」",
        tree: [
          {
            title: "专业主张与受众定位",
            means: "专业性前提",
            relation: "先定讲什么，再定对谁讲",
            status: "current",
            due: "目标 A",
            evidence: "定位一页可讲清；受众与场景可指",
            children: [
              {
                title: "专业定位一页（讲什么/不讲什么）",
                means: "边界",
                status: "current",
                due: "当期",
                evidence: "与 ASE/铱石叙事对齐；禁跑题",
              },
              {
                title: "目标受众与场景",
                means: "场",
                status: "upcoming",
                due: "当期",
                evidence: "校友会/行业沙龙/线上等至少定一类主场",
              },
            ],
          },
          {
            title: "知识讲座产品化",
            means: "可复用讲品",
            relation: "可重复办，不靠临场发挥",
            status: "upcoming",
            due: "目标 A",
            evidence: "选题库 + 标准讲纲 + 案例素材可指",
            children: [
              {
                title: "讲座选题库",
                means: "选题",
                status: "upcoming",
                due: "当期",
                evidence: "≥5 条候选；对齐 ASE 案例/真实判断",
              },
              {
                title: "标准讲纲结构",
                means: "讲纲",
                status: "upcoming",
                due: "当期",
                evidence: "开场主张→干货→案例→行动建议 可复用",
              },
              {
                title: "案例与演示素材包",
                means: "证据材料",
                status: "upcoming",
                due: "当期",
                evidence: "脱敏案例/图示可上场；无敏感外泄",
              },
            ],
          },
          {
            title: "首场交付与打磨",
            means: "首次表型",
            relation: "专业性要用一场真讲座验证",
            status: "upcoming",
            due: "目标 A",
            evidence: "首场办完 + 复盘记录",
            children: [
              {
                title: "首场排期与渠道",
                means: "落地",
                status: "upcoming",
                due: "当期",
                evidence: "时间/场合/邀请路径可指",
              },
              {
                title: "试讲与人审",
                means: "质检",
                status: "upcoming",
                due: "当期",
                evidence: "你本人或指定人审过讲纲/试讲",
              },
              {
                title: "首场实办 + 复盘",
                means: "交付",
                status: "upcoming",
                due: "当期",
                evidence: "实办记录；改进点写入讲纲",
              },
            ],
          },
          {
            title: "专业性可见证据",
            means: "被看见",
            relation: "讲座要留下可引用痕迹",
            status: "upcoming",
            due: "目标 A",
            evidence: "切片/纪要/主张句可对外用",
            children: [
              {
                title: "录像 / 纪要 / 金句切片",
                means: "资产",
                status: "upcoming",
                due: "当期",
                evidence: "至少一类可复用素材入库",
              },
              {
                title: "反馈与引用沉淀",
                means: "反馈",
                status: "upcoming",
                due: "当期",
                evidence: "听众反馈或转述「专业」信号可记",
              },
              {
                title: "对外可引用的专业主张一句",
                means: "主张",
                status: "upcoming",
                due: "当期",
                evidence: "一句定调；与定位一页一致",
              },
            ],
          },
          {
            title: "讲座节奏固化",
            means: "可持续",
            relation: "目标 A 验收 · 不另开主战场",
            status: "upcoming",
            due: "目标 A",
            evidence: "场次节奏可执行；与获客衔接但不摊大",
            children: [
              {
                title: "场次节奏（如双月一场）",
                means: "节奏",
                status: "upcoming",
                due: "当期",
                evidence: "日历可占位；可降频不可断档无计划",
              },
              {
                title: "与内容/获客衔接",
                means: "转化轻触",
                status: "upcoming",
                due: "当期",
                evidence: "讲座→内容切片或线索入口有一条路径",
              },
            ],
          },
        ],
      },
      {
        letter: "B",
        title: "露出公司产品，通过做 Agent 评测与对比",
        example: "一版 ASE/YiAgent 对通用 Agent 的公开评测，读者能指认「铱石产品强在哪」",
        tree: [
          {
            title: "露出边界与公平规则",
            means: "产品露出前提",
            relation: "先定露什么、怎么比才算公平",
            status: "upcoming",
            due: "目标 B",
            evidence: "产品清单 + 公平规则一页可审",
            children: [
              {
                title: "要露出的产品/能力清单",
                means: "产品焦点",
                status: "upcoming",
                due: "当期",
                evidence: "ASE / YiAgent 等主推点可指；禁摊成全产品册",
              },
              {
                title: "对比公平规则与禁区",
                means: "公信力",
                status: "upcoming",
                due: "当期",
                evidence: "同题同环境；禁止黑箱夸大与选择性隐瞒",
              },
            ],
          },
          {
            title: "评测题目与裁判设计",
            means: "可复现规格",
            relation: "没有题目与裁判就没有可信对比",
            status: "upcoming",
            due: "目标 B",
            evidence: "题库 + 维度 + 对照对象可指",
            children: [
              {
                title: "场景题库",
                means: "题目",
                status: "upcoming",
                due: "当期",
                evidence: "≥3 道对齐真实场景；可复跑",
              },
              {
                title: "评分维度与裁判口径",
                means: "裁判",
                status: "upcoming",
                due: "当期",
                evidence: "维度可解释；人/机裁判边界写清",
              },
              {
                title: "对照对象名单",
                means: "对照组",
                status: "upcoming",
                due: "当期",
                evidence: "竞品/通用 Agent 至少一类；版本可记",
              },
            ],
          },
          {
            title: "首轮评测执行",
            means: "首次表型",
            relation: "露出要用一轮真对比验证",
            status: "upcoming",
            due: "目标 B",
            evidence: "结果表 + 可复现包 + 人审可对外",
            children: [
              {
                title: "跑通一轮对比实验",
                means: "执行",
                status: "upcoming",
                due: "当期",
                evidence: "我方与对照同题跑完；日志可指",
              },
              {
                title: "结果表与可复现包",
                means: "证据包",
                status: "upcoming",
                due: "当期",
                evidence: "分数/样例/环境说明可复现",
              },
              {
                title: "人审：结论是否可对外",
                means: "质检",
                status: "upcoming",
                due: "当期",
                evidence: "你本人或指定人审过对外口径",
              },
            ],
          },
          {
            title: "产品露出内容化",
            means: "被看见",
            relation: "评测要变成可传播的产品认知",
            status: "upcoming",
            due: "目标 B",
            evidence: "至少一类对外内容 + 产品可指认",
            children: [
              {
                title: "评测长文 / 短视频切片",
                means: "内容资产",
                status: "upcoming",
                due: "当期",
                evidence: "至少一类上线或可发草稿",
              },
              {
                title: "对比图表与金句",
                means: "认知锚点",
                status: "upcoming",
                due: "当期",
                evidence: "读者 30 秒能懂「强在哪」",
              },
              {
                title: "与官网 / 获客入口衔接",
                means: "转化轻触",
                status: "upcoming",
                due: "当期",
                evidence: "评测→产品页或线索入口有一条路径",
              },
            ],
          },
          {
            title: "评测节奏固化",
            means: "可持续",
            relation: "目标 B 验收 · 不另开主战场",
            status: "upcoming",
            due: "目标 B",
            evidence: "更新节奏可执行；可与讲座复用",
            children: [
              {
                title: "更新节奏（如季度一轮）",
                means: "节奏",
                status: "upcoming",
                due: "当期",
                evidence: "日历可占位；版本变更可触发复测",
              },
              {
                title: "与目标 A（讲座）素材复用",
                means: "协同",
                status: "upcoming",
                due: "当期",
                evidence: "评测案例可进讲纲；讲座不另起产品册",
              },
            ],
          },
        ],
      },
    ],
    milestones: [],
    checkpoints: [],
  },
  p13: {
    goal: "把公司战略收敛为正本，再向下拆举措与资源配比。",
    summary: "战略委主责 · 拍板前不对客主推新叙事。",
    tasks: [
      { id: "tk6", goal: "确认收敛稿升为正本", assignee: "你", status: "等人", due: "待拍板" },
      { id: "tk7", goal: "H2 资源 80/20 落到 Team 周计划", assignee: "EA", status: "待开始", due: "正本后" },
    ],
    milestones: [
      { title: "收敛稿成稿", due: "上周", status: "done", note: "v0.1 已出" },
      { title: "正本确认", due: "待拍板", status: "current", note: "正本确认待你" },
      { title: "举措下拆", due: "正本后", status: "upcoming", note: "落到 Team 周计划" },
      { title: "资源 80/20 锁定", due: "H2", status: "upcoming", note: "ASE / 咨询配比" },
    ],
    checkpoints: [
      { phase: "收敛确认", minTier: "S4", gaps: 1, at: "进行中", open: "正本确认待你" },
    ],
  },
  p15: {
    goal: "用开发团队按 YiAgent 流程完成虫控数字化 ERP：拆需求 → 拆目标 → 拆任务 → 派发验收。",
    summary: "客户交付 · 模拟编队 · 旧料在「以前的文件」；本期以需求工程与目标树为正本。",
    tasks: [
      { id: "tk15a", goal: "需求总览 + 模块细化 v0.1", assignee: "PM", status: "已完成", due: "今日" },
      { id: "tk15b", goal: "迁入/补齐 F01–F03 完整需求", assignee: "Product", status: "待开始", due: "本周" },
      { id: "tk15c", goal: "F01 任务卡集（目标 C）", assignee: "Architect", status: "待开始", due: "A2A 后" },
    ],
    progressGoals:     [
      {
        "letter": "A",
        "title": "源文档 → AI 可读完整需求",
        "example": "把虫控 ERP Word/正本变成带验收清单的完整需求",
        "tree": [
          {
            "title": "锚定源与清洗规则",
            "means": "需求工程①②",
            "relation": "翻译归翻译，补足归补足",
            "status": "partial",
            "due": "目标 A",
            "evidence": "正本路径 + 脱敏规则已登记",
            "children": [
              {
                "title": "锁定需求正本与 F01–F12 骨架",
                "means": "总览",
                "status": "done",
                "due": "当期",
                "evidence": "需求工程/01-需求总览.md"
              },
              {
                "title": "翻译/补足铁律写入本项目",
                "means": "规范",
                "status": "done",
                "due": "当期",
                "evidence": "项目信息边界 + 规范摘要"
              }
            ]
          },
          {
            "title": "模块完整需求（字段级）",
            "means": "完整需求文件",
            "relation": "无验收清单不进目标 C",
            "status": "upcoming",
            "due": "目标 A",
            "evidence": "每模块一文件",
            "children": [
              {
                "title": "F01 平台底座完整需求",
                "status": "upcoming",
                "due": "当期",
                "evidence": "可迁旧 F01 稿"
              },
              {
                "title": "F02 CRM 完整需求",
                "status": "upcoming",
                "due": "当期",
                "evidence": "可迁旧 F02 稿"
              },
              {
                "title": "F03 合同完整需求（试点范式）",
                "status": "upcoming",
                "due": "当期",
                "evidence": "旧 F03 试点最完整"
              },
              {
                "title": "F04–F12 按范式推进",
                "status": "upcoming",
                "due": "后续",
                "evidence": "路标→字段级"
              }
            ]
          },
          {
            "title": "需求可读性门槛",
            "means": "质量门禁",
            "status": "upcoming",
            "due": "目标 A",
            "evidence": "模块验收条达可派发阈值",
            "children": [
              {
                "title": "无验收清单模块禁止进入目标 C",
                "status": "upcoming",
                "due": "当期",
                "evidence": "检查表"
              }
            ]
          }
        ]
      },
      {
        "letter": "B",
        "title": "完整需求 → 模块目标树",
        "example": "P0 底座 → P1 主链 → P2 支撑 → P3 多端",
        "tree": [
          {
            "title": "批次目标与门槛",
            "means": "排期骨架",
            "status": "partial",
            "due": "目标 B",
            "evidence": "项目计划 §3.1",
            "children": [
              {
                "title": "P0 底座可登录可授权（F01）",
                "status": "upcoming",
                "due": "P0",
                "evidence": "F01 验收门槛"
              },
              {
                "title": "P1 主业务闭环（F02–F05）",
                "status": "upcoming",
                "due": "P1",
                "evidence": "客户→合同→服务→回款"
              },
              {
                "title": "P2 支撑域（F06–F11）",
                "status": "upcoming",
                "due": "P2",
                "evidence": "最小可用 + 接口对齐"
              },
              {
                "title": "P3 多端体验（F12）",
                "status": "upcoming",
                "due": "P3",
                "evidence": "五端入口与裁剪"
              }
            ]
          },
          {
            "title": "跨模块冻结契约",
            "means": "契约先行",
            "status": "upcoming",
            "due": "目标 B",
            "evidence": "Numeric / 权限键 / 主体隔离 / 种子",
            "children": [
              {
                "title": "契约清单落入项目定义",
                "status": "upcoming",
                "due": "当期",
                "evidence": "需求工程/02 §跨模块契约"
              }
            ]
          },
          {
            "title": "进度树与看板同步",
            "means": "工作台",
            "status": "partial",
            "due": "目标 B",
            "evidence": "PROJECT_EXTRA.p15"
          }
        ]
      },
      {
        "letter": "C",
        "title": "目标树 → 可派发任务卡",
        "example": "一张卡 = 一次派发 = 可机器验收",
        "tree": [
          {
            "title": "拆解规范落地",
            "means": "粒度与契约",
            "status": "partial",
            "due": "目标 C",
            "evidence": "规范摘要.md",
            "children": [
              {
                "title": "单卡单闭环 / 体量上界",
                "status": "upcoming",
                "due": "当期",
                "evidence": "对照规范-任务拆解"
              },
              {
                "title": "契约先行再拆卡",
                "status": "upcoming",
                "due": "B2 后",
                "evidence": "依赖 B2"
              }
            ]
          },
          {
            "title": "从验收清单反推任务卡",
            "means": "任务总表",
            "status": "upcoming",
            "due": "目标 C",
            "evidence": "每条验收落入 ≥1 卡",
            "children": [
              {
                "title": "F01 任务卡集",
                "status": "upcoming",
                "due": "A2A 后",
                "evidence": "任务总表段"
              },
              {
                "title": "F02–F05 主链任务卡集",
                "status": "upcoming",
                "due": "后续",
                "evidence": "骨架优先"
              },
              {
                "title": "收口卡（菜单/种子/冒烟）",
                "status": "upcoming",
                "due": "每模块",
                "evidence": "每模块一张"
              }
            ]
          },
          {
            "title": "Agent Brief 模板可用",
            "means": "派发",
            "status": "upcoming",
            "due": "目标 C",
            "evidence": "对照规范-自动开发派发"
          }
        ]
      },
      {
        "letter": "D",
        "title": "编队交付 + 验收回收",
        "example": "Develop 五席跑通首卡闭环",
        "tree": [
          {
            "title": "挂载 Develop 编队",
            "means": "YiAgent 编队",
            "status": "upcoming",
            "due": "目标 D",
            "evidence": "PM/Product/Architect/Dev/DevOps",
            "children": [
              {
                "title": "项目锁定 genome（p15）",
                "status": "upcoming",
                "due": "当期",
                "evidence": "仿 p11 频道"
              }
            ]
          },
          {
            "title": "首卡端到端演练",
            "means": "交付",
            "status": "upcoming",
            "due": "目标 D",
            "evidence": "建议 F01-α 组织/登录",
            "children": [
              {
                "title": "Docker 冒烟命令固化",
                "status": "upcoming",
                "due": "当期",
                "evidence": "compose + smoke"
              }
            ]
          },
          {
            "title": "验收回收进需求文件",
            "means": "闭环",
            "status": "upcoming",
            "due": "目标 D",
            "evidence": "进度标签回写",
            "children": [
              {
                "title": "完成度表（可选对照旧审查）",
                "status": "upcoming",
                "due": "后续",
                "evidence": "不强制 69 分体系"
              }
            ]
          }
        ]
      }
    ],
    milestones: [
      { title: "立项 + 目标树", due: "今日", status: "done", note: "p15 已挂看板" },
      { title: "F01–F03 完整需求", due: "本周", status: "current", note: "目标 A2" },
      { title: "F01 任务卡可派发", due: "下周", status: "upcoming", note: "目标 C" },
      { title: "首卡编队闭环", due: "模拟交付", status: "upcoming", note: "目标 D" },
    ],
    checkpoints: [
      { phase: "需求细化", minTier: "S3", gaps: 0, at: "今日", open: "" },
      { phase: "完整需求 F01–F03", minTier: "S4", gaps: 1, at: "本周", open: "字段级稿待迁入" },
    ],
    progressLegend: "命名：目标字母 + 数字 + A–Z（A1 / A1A…）。A 需求可读化 · B 目标树 · C 任务卡 · D 编队交付。",
  },
  p14: {
    goal: "增强公司可动用现金流：回款加速、支出可控、可验证的增收支路径——不另开第四条业务线。",
    summary: "经营横切 · 你拍板 · 手段待收敛成目标树。",
    tasks: [
      { id: "tk14a", goal: "现金流现状一页（进/出/缺口）", assignee: "你", status: "进行中", due: "本周" },
      { id: "tk14b", goal: "增强手段候选清单（回款/削支/增收）", assignee: "EA", status: "待开始", due: "下周" },
    ],
    progressGoals: [],
    milestones: [],
    checkpoints: [],
  },
  p2: {
    goal: "一体机/单场景 FDE 样板跑通：验证 → 关键动作人审 → 可复制。",
    summary: "客户项目 · 样板客户；关键写操作必须人审。",
    tasks: [
      { id: "tk8", goal: "场景验收清单", assignee: "PM", status: "进行中", due: "8 月" },
      { id: "tk9", goal: "关键动作人审门禁联调", assignee: "Architect", status: "进行中", due: "本周" },
    ],
    milestones: [
      { title: "场景验证", due: "上周", status: "done", note: "单场景已跑通" },
      { title: "人审门禁", due: "本周", status: "current", note: "两例联调未过" },
      { title: "样板验收", due: "8 月", status: "upcoming", note: "客户侧确认" },
      { title: "可复制包", due: "Q3", status: "upcoming", note: "文档 + 脚本" },
    ],
    checkpoints: [
      { phase: "场景验证", minTier: "S3", gaps: 0, at: "上周" },
      { phase: "人审门禁", minTier: "S4", gaps: 1, at: "本周", open: "两例联调未过" },
    ],
  },
  p3: {
    goal: "熟人/校友会完成 L1 诊断，作决策入口转 ASE，不扩成主业务线。",
    summary: "约 20% 资源 · 销售交付跟进。",
    tasks: [
      { id: "tk10", goal: "L1 诊断提纲定稿", assignee: "CMO", status: "进行中", due: "本周" },
      { id: "tk11", goal: "本月 3 场诊断排期", assignee: "销售交付", status: "待开始", due: "本月" },
    ],
    milestones: [
      { title: "提纲定稿", due: "本周", status: "done", note: "人审已过" },
      { title: "首场诊断", due: "本月", status: "current", note: "排期中" },
      { title: "本月 3 场", due: "本月", status: "upcoming", note: "熟人/校友会" },
      { title: "转 ASE 线索", due: "H2", status: "upcoming", note: "作决策入口" },
    ],
    checkpoints: [{ phase: "提纲人审", minTier: "S3", gaps: 0, at: "本周" }],
  },
  p8: {
    goal: "华数智造续约落地并完成交付收尾与收款确认。",
    summary: "客户项目 · 合同与收款在审批篮联动。",
    tasks: [
      { id: "tk12", goal: "续约拜访纪要入库", assignee: "销售交付", status: "进行中", due: "今日" },
      { id: "tk13", goal: "收款确认进审批", assignee: "CFO", status: "等人", due: "本月" },
    ],
    milestones: [
      { title: "续约意向", due: "上周", status: "done", note: "客户口头确认" },
      { title: "拜访纪要", due: "今日", status: "current", note: "入库中" },
      { title: "收款确认", due: "本月", status: "upcoming", note: "进审批篮" },
      { title: "交付收尾", due: "本月", status: "upcoming", note: "关单" },
    ],
    checkpoints: [
      { phase: "续约意向", minTier: "S3", gaps: 0, at: "上周" },
      { phase: "收款确认", minTier: "S4", gaps: 1, at: "本周", open: "审批未拍板" },
    ],
  },
  p9: {
    goal: "星河物流验收纪要签署，关闭本阶段交付。",
    summary: "等人签 · 材料已齐。",
    tasks: [
      { id: "tk14", goal: "验收纪要客户签回", assignee: "Delivery", status: "等人", due: "本周" },
      { id: "tk15", goal: "签后归档（人看平面）", assignee: "销售交付", status: "待开始", due: "签后" },
    ],
    milestones: [
      { title: "材料齐套", due: "上周", status: "done", note: "验收包已发" },
      { title: "客户签署", due: "本周", status: "current", note: "客户未签" },
      { title: "人看归档", due: "签后", status: "upcoming", note: "知识库入库" },
      { title: "阶段关闭", due: "签后", status: "upcoming", note: "标为已完成" },
    ],
    checkpoints: [{ phase: "验收签署", minTier: "S4", gaps: 1, at: "本周", open: "客户未签" }],
  },
};

const PROJECT_NOTES_LS_KEY = "opc-ceo-project-notes-v1";

function loadProjectNotes() {
  try {
    const raw = localStorage.getItem(PROJECT_NOTES_LS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function normalizeMultiline(s) {
  return String(s || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/^\n+|\n+$/g, "");
}

function saveProjectNotes(id, notes) {
  const all = loadProjectNotes();
  all[id] = {
    goal: normalizeMultiline(notes.goal),
    summary: normalizeMultiline(notes.summary),
  };
  try {
    localStorage.setItem(PROJECT_NOTES_LS_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

function clearProjectNotes(id) {
  const all = loadProjectNotes();
  if (!all[id]) return;
  delete all[id];
  try {
    localStorage.setItem(PROJECT_NOTES_LS_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

function milestonesFromCheckpoints(checkpoints) {
  let sawOpen = false;
  return (checkpoints || []).map((c) => {
    let status = "upcoming";
    if (c.gaps) {
      status = "current";
      sawOpen = true;
    } else if (!sawOpen) {
      status = "done";
    }
    return {
      title: c.phase,
      due: c.at || "待定",
      status,
      note: c.gaps ? c.open || `未关闭缺口 ${c.gaps}` : "已通过",
      minTier: c.minTier,
    };
  });
}

function defaultMilestones(p) {
  const prog = Number(p.progress) || 0;
  return [
    {
      title: "立项对齐",
      due: "已过",
      status: prog >= 10 ? "done" : "current",
      note: "目标与 Owner 确认",
    },
    {
      title: "执行推进",
      due: p.due || "进行中",
      status: prog >= 10 && prog < 90 ? "current" : prog >= 90 ? "done" : "upcoming",
      note: p.risk || "按周推进",
    },
    {
      title: "验收关闭",
      due: p.due || "待定",
      status: prog >= 90 ? "current" : "upcoming",
      note: "缺口关闭后标完成",
    },
  ];
}

function resolveMilestones(p, x) {
  // 显式空数组 = 本项目无侧栏里程碑（勿回落默认三阶段）
  if (Array.isArray(x.milestones)) return x.milestones;
  const cps = x.checkpoints || p.checkpoints || [];
  const fromCp = milestonesFromCheckpoints(cps);
  return fromCp.length ? fromCp : defaultMilestones(p);
}

function progressStatusLabel(s) {
  if (s === "done") return "已完成";
  if (s === "current") return "进行中";
  if (s === "blocked") return "阻塞";
  if (s === "partial") return "部分完成";
  return "未开始";
}

function progressStatusTag(s) {
  if (s === "done") return "green";
  if (s === "current" || s === "partial") return "blue";
  if (s === "blocked") return "orange";
  return "";
}

function progressSiblingLetter(index) {
  const i = Math.max(0, Math.min(25, Number(index) || 0));
  return String.fromCharCode(65 + i);
}

/**
 * 目标字母（默认 A）下的树状编号：
 * - 大阶段：A1、A2…
 * - 任务：A1A、A1B…（A + 数字 + A–Z）
 * - 更深：父 ID 后再挂 A–Z → A1AA、A1AB
 */
function annotateProgressTree(nodes, ctx = {}) {
  const goal = (ctx.goalLetter || "A").toString().slice(0, 1).toUpperCase() || "A";
  const depth = ctx.depth || 0;
  const majorNum = ctx.majorNum ?? null;
  const parentId = ctx.parentId || "";
  return (nodes || []).map((n, i) => {
    let id;
    let seg;
    let depthLetter;
    let nextMajor = majorNum;
    if (depth === 0) {
      nextMajor = i + 1;
      seg = `${goal}${nextMajor}`;
      id = seg;
      depthLetter = goal;
    } else if (depth === 1) {
      depthLetter = progressSiblingLetter(i);
      seg = depthLetter;
      id = `${goal}${majorNum}${depthLetter}`;
    } else {
      depthLetter = progressSiblingLetter(i);
      seg = depthLetter;
      id = `${parentId}${depthLetter}`;
    }
    const children = annotateProgressTree(n.children || [], {
      goalLetter: goal,
      depth: depth + 1,
      majorNum: nextMajor,
      parentId: id,
    });
    return {
      title: n.title || "",
      relation: n.relation || "",
      means: n.means || "",
      status: n.status || "upcoming",
      due: n.due || "待定",
      evidence: n.evidence || n.note || "",
      id,
      seg,
      depth,
      depthLetter,
      children,
    };
  });
}

function progressNodeHasActive(n) {
  if (!n) return false;
  if (n.status === "current" || n.status === "partial" || n.status === "done") return true;
  return (n.children || []).some(progressNodeHasActive);
}

/** 默认：有进行中/部分完成/已完成路径的节点展开；其余大阶段展开、任务级折叠 */
function isProgressNodeExpanded(n) {
  const fold = state.progressFold || {};
  if (Object.prototype.hasOwnProperty.call(fold, n.id)) return !fold[n.id];
  if (progressNodeHasActive(n)) return true;
  return n.depth === 0;
}

function setProgressFoldAll(collapsed, nodes) {
  const walk = (list) => {
    for (const n of list || []) {
      if (n.children?.length) {
        state.progressFold[n.id] = collapsed;
        walk(n.children);
      }
    }
  };
  if (!state.progressFold) state.progressFold = {};
  walk(nodes);
}

function flattenProgressTree(nodes, acc = []) {
  for (const n of nodes || []) {
    acc.push(n);
    if (n.children?.length) flattenProgressTree(n.children, acc);
  }
  return acc;
}

function normalizeProgressGoals(x) {
  if (Array.isArray(x.progressGoals) && x.progressGoals.length) {
    return x.progressGoals
      .map((g) => ({
        letter: (g.letter || "A").toString().slice(0, 1).toUpperCase() || "A",
        title: g.title || "",
        example: g.example || "",
        tree: Array.isArray(g.tree) ? g.tree : [],
      }))
      .filter((g) => g.tree.length || g.title);
  }
  const letter = (x.progressGoal || "A").toString().slice(0, 1).toUpperCase() || "A";
  const raw = Array.isArray(x.progressTree)
    ? x.progressTree
    : Array.isArray(x.progress) && x.progress.length
      ? x.progress
      : null;
  if (raw) {
    return [
      {
        letter,
        title: x.progressGoalTitle || "",
        example: x.progressGoalExample || "",
        tree: raw,
      },
    ];
  }
  return [];
}

function applyProgressCrossLinks(goals, crossLinks) {
  if (!crossLinks?.length) return goals;
  const byId = {};
  for (const g of goals) {
    flattenProgressTree(g.tree).forEach((n) => {
      byId[n.id] = n;
    });
  }
  for (const xl of crossLinks) {
    const nodes = (xl.nodes || []).filter((id) => byId[id]);
    if (nodes.length < 2) continue;
    for (const nid of nodes) {
      const n = byId[nid];
      if (!n.crossLinks) n.crossLinks = [];
      n.crossLinks.push({
        xlId: xl.id,
        title: xl.title || xl.id,
        peers: nodes.filter((x) => x !== nid),
        shared: xl.shared || "",
        split: xl.split || {},
      });
    }
  }
  return goals;
}

function jumpProgressNode(nodeId) {
  if (!nodeId) return;
  const letter = String(nodeId).charAt(0).toUpperCase();
  state.progressGoalLetter = letter;
  state.progressHighlightId = nodeId;
  state.progressFold = {};
  const raw =
    SITE_GATE === "yiagent"
      ? yiagentProgressRaw()
      : state.projects.find((p) => p.id === state.progressProjectId);
  const x = PROJECT_EXTRA[raw?.id || state.progressProjectId] || {};
  const goals = resolveProgressGoals(raw || { id: state.progressProjectId }, x);
  const g = goals.find((x) => x.letter === letter);
  if (g?.tree?.length) setProgressFoldAll(false, g.tree);
  state.page = "progress";
  render();
  requestAnimationFrame(() => {
    const el = document.getElementById(`progress-node-${nodeId}`);
    if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
  });
}

/** 解析全部目标树；letter 指定时只返回该目标的已标注树 */
function resolveProgressGoals(p, x, letter) {
  let goals = normalizeProgressGoals(x);
  if (!goals.length) {
    const ms = resolveMilestones(p, x);
    // 无进度树且无里程碑 → 空（勿伪造「目标 A」空壳）
    if (!ms?.length) {
      return [];
    }
    goals = [
      {
        letter: "A",
        title: x.goal || "",
        example: "",
        tree: ms.map((m) => ({
          title: m.title,
          relation: m.relation || "",
          status: m.status || "upcoming",
          due: m.due || "待定",
          evidence: m.evidence || m.note || "",
        })),
      },
    ];
  }
  let annotated = goals.map((g) => ({
    ...g,
    tree: annotateProgressTree(g.tree, { goalLetter: g.letter }),
  }));
  annotated = applyProgressCrossLinks(annotated, x.progressCrossLinks || []);
  if (letter) {
    const L = letter.toString().slice(0, 1).toUpperCase();
    return annotated.filter((g) => g.letter === L);
  }
  return annotated;
}

/** 进度页命名说明：按项目，避免把 YiAgent 基因文案套到其它项目 */
function progressGoalLegendHtml(cur, goalLetter) {
  const L = escapeHtml(goalLetter || "A");
  const x = PROJECT_EXTRA[cur?.id] || {};
  if (x.progressLegend) {
    return `<div class="row-desc" style="margin-top:8px">${x.progressLegend}</div>`;
  }
  if (cur?.id === "p11") {
    return `<div class="row-desc" style="margin-top:8px">命名：<code class="branch-code">${L}1</code> / <code class="branch-code">${L}1A</code>… · 节点按<strong>基因工程四步</strong>与<strong>基因算法（变异/选择/漂移/级联）</strong>拆分 · 可折叠任务树</div>`;
  }
  return `<div class="row-desc" style="margin-top:8px">命名：<code class="branch-code">${L}1</code> / <code class="branch-code">${L}1A</code>… · 可折叠任务树</div>`;
}

function resolveProgressTree(p, x, letter) {
  const goals = resolveProgressGoals(p, x, letter || x.progressGoal || "A");
  return goals[0]?.tree || [];
}

function renderProgressCrossChips(n) {
  const links = n.crossLinks || [];
  if (!links.length) return "";
  const peerSet = new Set();
  const chips = [];
  for (const xl of links) {
    for (const peer of xl.peers || []) {
      if (peerSet.has(peer)) continue;
      peerSet.add(peer);
      chips.push(
        `<button class="progress-link-chip" type="button" data-progress-jump="${escapeHtml(
          peer
        )}" title="${escapeHtml(xl.title)}：${escapeHtml(xl.shared || "")}">↔ ${escapeHtml(peer)}</button>`
      );
    }
  }
  const xlTitles = [...new Set(links.map((x) => x.title))].join(" · ");
  return `<div class="progress-cross-row">
    <span class="progress-cross-label" title="${escapeHtml(xlTitles)}">跨任务</span>
    ${chips.join("")}
  </div>`;
}

function renderProgressCrossLinksPanel(cur) {
  const x = PROJECT_EXTRA[cur.id] || {};
  const all = x.progressCrossLinks || [];
  const letter = cur.progressGoal || "A";
  const relevant = all.filter((xl) => (xl.nodes || []).some((id) => String(id).startsWith(letter)));
  if (!relevant.length) return "";
  const panelMeta = x.progressCrossLinksMeta || "共享手段 · 可一次做完 · KPI 分列验收";
  return `
    <div class="card progress-cross-panel" style="margin-top:14px" aria-label="跨任务连接">
      <h2>跨任务连接</h2>
      <div class="meta">${escapeHtml(panelMeta)}</div>
      <div class="list" style="margin-top:10px">
        ${relevant
          .map((xl) => {
            const nodes = (xl.nodes || [])
              .map(
                (id) =>
                  `<button class="progress-link-chip" type="button" data-progress-jump="${escapeHtml(
                    id
                  )}">${escapeHtml(id)}</button>`
              )
              .join("");
            const splitC = xl.split?.C ? `C：${xl.split.C}` : "";
            const splitD = xl.split?.D ? `D：${xl.split.D}` : "";
            return `
          <div class="row progress-cross-item">
            <div>
              <div class="row-title">${escapeHtml(xl.title)}</div>
              <div class="row-desc pre-wrap">${escapeHtml(xl.shared || "")}</div>
              <div class="progress-cross-split meta" style="margin-top:6px">${escapeHtml(
                [splitC, splitD].filter(Boolean).join(" · ")
              )}</div>
              <div class="progress-cross-nodes" style="margin-top:8px">${nodes}</div>
            </div>
          </div>`;
          })
          .join("")}
      </div>
    </div>`;
}

function renderProgressTasksPanel(cur) {
  const x = PROJECT_EXTRA[cur.id] || {};
  const tasks = x.progressTasks || [];
  if (!tasks.length) return "";
  const panelMeta = x.progressTasksMeta || "";
  const statusTag = (s) =>
    s === "已完成" ? "green" : s === "进行中" ? "blue" : s === "待实跑" || s === "阻塞" ? "orange" : "";
  return `
    <div class="card progress-tasks-panel" style="margin-top:14px" aria-label="本轮任务登记">
      <h2>本轮任务登记</h2>
      ${panelMeta ? `<div class="meta">${escapeHtml(panelMeta)}</div>` : ""}
      <div class="list" style="margin-top:10px">
        ${tasks
          .map(
            (t) => `
          <div class="row progress-task-item">
            <div>
              <div class="row-title">
                <code class="progress-id">${escapeHtml(t.id)}</code> ${escapeHtml(t.nodes || "")}
                <span class="tag ${statusTag(t.status)}">${escapeHtml(t.status || "待定")}</span>
              </div>
              <div class="row-desc pre-wrap">${escapeHtml(t.goal || "")}</div>
              <div class="meta pre-wrap" style="margin-top:6px">依赖：${escapeHtml(t.deps || "—")}</div>
              <div class="meta pre-wrap">必要信息：${escapeHtml(t.info || "—")}</div>
              ${t.evidence ? `<div class="meta pre-wrap">证据/遗留：${escapeHtml(t.evidence)}</div>` : ""}
            </div>
          </div>`
          )
          .join("")}
      </div>
    </div>`;
}

function renderProgressTreeNodes(nodes) {
  if (!nodes?.length) return "";
  const hi = state.progressHighlightId || "";
  return `<ul class="progress-tree" role="tree">
    ${nodes
      .map((n) => {
        const hasKids = Boolean(n.children?.length);
        const expanded = hasKids ? isProgressNodeExpanded(n) : true;
        const foldBtn = hasKids
          ? `<button class="progress-fold-btn" type="button" data-progress-fold="${escapeHtml(
              n.id
            )}" aria-expanded="${expanded}" title="${expanded ? "折叠" : "展开"}">${expanded ? "▾" : "▸"}</button>`
          : `<span class="progress-fold-spacer" aria-hidden="true"></span>`;
        const highlighted = hi && n.id === hi ? " is-highlight" : "";
        return `
      <li class="progress-tree-item depth-${escapeHtml(String(n.depthLetter || ""))} ${
          hasKids ? (expanded ? "is-expanded" : "is-collapsed") : "is-leaf"
        }" role="treeitem" ${hasKids ? `aria-expanded="${expanded}"` : ""}>
        <div class="progress-node progress-${escapeHtml(n.status || "upcoming")}${highlighted}" id="progress-node-${escapeHtml(
          n.id
        )}">
          <div class="progress-node-main">
            ${foldBtn}
            <code class="progress-id" title="节点 ${escapeHtml(n.id)}">${escapeHtml(n.id)}</code>
            <strong class="progress-title">${escapeHtml(n.title || "")}</strong>
            <span class="tag ${progressStatusTag(n.status)}">${progressStatusLabel(n.status)}</span>
            ${n.crossLinks?.length ? `<span class="tag">联 ${n.crossLinks.length}</span>` : ""}
          </div>
          <div class="progress-node-meta">
            ${n.means ? `<span class="progress-means">${escapeHtml(n.means)}</span>` : ""}
            ${n.relation ? `<span class="progress-rel">${escapeHtml(n.relation)}</span>` : ""}
            <span class="progress-due">${escapeHtml(n.due || "待定")}</span>
            ${n.evidence ? `<span class="progress-evidence pre-wrap">${escapeHtml(n.evidence)}</span>` : ""}
            ${renderProgressCrossChips(n)}
          </div>
        </div>
        ${hasKids && expanded ? renderProgressTreeNodes(n.children) : ""}
      </li>`;
      })
      .join("")}
  </ul>`;
}

function enrichProject(p) {
  if (!p) return null;
  const x = PROJECT_EXTRA[p.id] || {};
  const notes = loadProjectNotes()[p.id] || {};
  const fallbackGoal =
    p.category === "战略"
      ? `推进「${p.title}」，承接 ${p.pillar || "公司战略"}。`
      : `服务 ${p.customer || "客户"} · 完成「${p.title}」。`;
  const progressGoals = resolveProgressGoals(p, x);
  const activeLetter = state.progressGoalLetter || progressGoals[0]?.letter || "";
  const activeGoal =
    (activeLetter && progressGoals.find((g) => g.letter === activeLetter)) || progressGoals[0] || null;
  const progressTree = activeGoal?.tree || [];
  const progress = flattenProgressTree(progressTree);
  return {
    ...p,
    goal: notes.goal || x.goal || fallbackGoal,
    summary: notes.summary || x.summary || "",
    tasks: x.tasks || [],
    checkpoints: x.checkpoints || p.checkpoints || [],
    milestones: Array.isArray(x.milestones) ? x.milestones : [],
    progressGoals,
    progressGoal: activeGoal?.letter || "",
    progressGoalTitle: activeGoal?.title || "",
    progressGoalExample: activeGoal?.example || "",
    progressCrossLinks: x.progressCrossLinks || [],
    progressTree,
    progress,
    repo: x.repo || p.repo || null,
  };
}

function renderProjectChannelCard(cur) {
  const folder = cur.folder || `项目/${cur.title}`;
  const info = state.projectChannelById[cur.id];
  const configured = Boolean(info?.configured && info?.channel);
  const ch = info?.channel;
  const members = ch?.members || [];

  if (state.projectChannelWizard && state.projectChannelDraft?.projectId === cur.id) {
    const draft = state.projectChannelDraft;
    const templates = importableOrgChannels();
    return `
      <div class="card" style="margin-top:14px">
        <h2>组建项目频道</h2>
        <div class="meta" style="margin-top:6px">DEC-047 · 只服务本项目；战略等只读 · 每位 Agent 落 上下文.md + 对话/按日</div>
        <div class="proj-form" style="margin-top:12px">
          <label>频道名称</label>
          <input id="pcw-name" value="${escapeHtml(draft.name || "项目频道")}" />
          <label style="margin-top:10px;display:block">导入组织 Team（可选）</label>
          <select id="pcw-import">
            <option value="">不导入 · 仅自选成员</option>
            ${templates
              .map(
                (t) =>
                  `<option value="${escapeHtml(t.id)}" ${
                    draft.importChannelId === t.id ? "selected" : ""
                  }>${escapeHtml(t.name)}（${(t.memberIds || []).length} 人）</option>`
              )
              .join("")}
          </select>
        </div>
        <h3 style="margin:14px 0 8px;font-size:14px">频道成员</h3>
        <div class="org-member-list">
          ${state.agentRoster
            .filter((a) => !a.system)
            .map((a) => {
              const on = draft.memberIds.includes(a.id);
              return `
              <label class="org-member-row" data-pcw-toggle="${a.id}">
                <input type="checkbox" ${on ? "checked" : ""} />
                <span class="dot" style="background:${a.color}">${escapeHtml(
                  a.initial || a.name.slice(0, 1)
                )}</span>
                <span>
                  <strong>${escapeHtml(a.name)}</strong>
                  <span class="meta">${escapeHtml(a.kind === "human" ? "真人" : "Agent")}${
                    a.developRole ? ` · ${a.developRole}` : ""
                  }</span>
                </span>
              </label>`;
            })
            .join("")}
        </div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" id="btn-pcw-save">保存并落盘</button>
          <button class="btn ghost" type="button" id="btn-pcw-cancel">取消</button>
        </div>
      </div>`;
  }

  if (!configured) {
    return `
      <div class="card" style="margin-top:14px">
        <h2>项目频道</h2>
        <div class="meta" style="margin-top:6px">尚未组建 · 新建项目后在此导入 Team 或自选 Agent</div>
        <div class="row-desc" style="margin-top:8px">落盘路径：<code class="branch-code">${escapeHtml(
          folder + "/频道"
        )}</code></div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-project-channel-setup="${escapeHtml(
            cur.id
          )}">组建频道</button>
          <button class="btn ghost" data-page="chat" data-open-dm="ch-dev">打开公司开发编队</button>
        </div>
      </div>`;
  }

  return `
    <div class="card" style="margin-top:14px">
      <h2>项目频道 · ${escapeHtml(ch.name || "项目频道")}</h2>
      <div class="meta" style="margin-top:6px">DEC-047 · 写隔离本项目 · 战略等只读外参</div>
      <div class="list" style="margin-top:10px">
        <div class="row">
          <div>
            <div class="row-title">成员（${members.length}）</div>
            <div class="row-desc">${escapeHtml(members.map((m) => m.name).join(" · ") || "—")}</div>
          </div>
        </div>
        <div class="row">
          <div>
            <div class="row-title">磁盘</div>
            <div class="row-desc"><code class="branch-code">${escapeHtml(
              folder + "/频道"
            )}</code><br/><span class="meta">Agents/&lt;名&gt;/上下文.md · 对话/YYYY-MM-DD.md</span></div>
          </div>
        </div>
        ${
          ch.importedFrom
            ? `<div class="row"><div><div class="row-title">导入来源</div><div class="row-desc">${escapeHtml(
                ch.importedFrom
              )}</div></div></div>`
            : ""
        }
      </div>
      <div class="list proj-actions" style="margin-top:12px">
        <button class="btn primary" type="button" data-project-channel="${escapeHtml(
          cur.id
        )}">进入项目频道</button>
        <button class="btn ghost" type="button" data-project-channel-edit="${escapeHtml(
          cur.id
        )}">编辑成员</button>
        <button class="btn ghost" data-page="chat" data-open-dm="ch-dev">公司开发编队</button>
      </div>
    </div>`;
}

function renderProjectRepoCard(cur) {
  const repo = cur.repo;
  if (!repo?.url) return "";
  const branches = repo.branches || [];
  return `
    <div class="card" style="margin-top:14px">
      <h2>代码仓</h2>
      <div class="meta">GitHub · 三分支（develop / release / demo）</div>
      <div class="list" style="margin-top:10px">
        <div class="row">
          <div>
            <div class="row-title">仓库</div>
            <div class="row-desc"><a class="repo-link" href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(repo.url.replace(/^https?:\/\//, ""))}</a></div>
          </div>
          <a class="btn ghost" href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer">打开</a>
        </div>
        ${
          branches
            .map(
              (b) => `
          <div class="row">
            <div>
              <div class="row-title"><code class="branch-code">${escapeHtml(b.name)}</code> · ${escapeHtml(b.role || "")}</div>
              <div class="row-desc">${escapeHtml(b.note || "")}</div>
            </div>
            <a class="btn ghost" href="${escapeHtml(repo.url)}/tree/${encodeURIComponent(b.name)}" target="_blank" rel="noopener noreferrer">查看</a>
          </div>`
            )
            .join("") || `<div class="empty">暂无分支说明</div>`
        }
      </div>
    </div>`;
}

function renderResearchRail(cur) {
  const folder = cur.researchFolder || `${cur.folder || "项目/" + cur.title}/项目调研`;
  const files = Array.isArray(cur.researchFiles) ? cur.researchFiles : [];
  const visible = files.filter((f) => f.name && f.name !== "README.md");
  return `
    <div class="card proj-research-rail" aria-label="项目调研">
      <h2>项目调研</h2>
      <div class="meta">竞品 / 赛道 / 笔记 · 对应磁盘文件夹</div>
      <div class="row-desc" style="margin-top:8px"><code class="branch-code">${escapeHtml(folder)}</code></div>
      <div class="list" style="margin-top:10px">
        ${
          visible.length
            ? visible
                .map(
                  (f) => `
          <div class="row">
            <div>
              <div class="row-title">${escapeHtml(f.name)}</div>
              <div class="row-desc"><code class="branch-code">${escapeHtml(f.path || "")}</code></div>
            </div>
          </div>`
                )
                .join("")
            : `<div class="empty">文件夹已建 · 放入调研稿后刷新可见</div>`
        }
      </div>
    </div>`;
}

function renderProjectSideRail(cur) {
  return `
    <aside class="proj-side-rail">
      ${renderResearchRail(cur)}
      <div class="card" aria-label="项目进度表入口">
        <h2>项目进度表</h2>
        <div class="meta">阶段 · 状态 · 验证产出（独立页）</div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-open-progress="${escapeHtml(cur.id)}">打开进度表</button>
        </div>
      </div>
    </aside>`;
}

function openProjectDetail(id) {
  if (!id || !state.projects.find((p) => p.id === id)) return;
  state.projectId = id;
  state.projectOpen = true;
  state.projectEditing = false;
  state.projectChannelWizard = false;
  state.projectChannelDraft = null;
  state.page = "projects";
  closeNav();
  $("app").classList.remove("show-chats", "show-folders", "show-preview");
  render();
  refreshProjectChannelIfOpen();
}

function openProjectProgress(id) {
  if (SITE_GATE === "yiagent") {
    state.progressProjectId = "p11";
  } else {
    const list = state.projects.filter((p) => p.status !== "已归档");
    const prefer = id || state.progressProjectId || state.projectId;
    const hit = list.find((p) => p.id === prefer) || list.find((p) => p.id === "p11") || list[0];
    state.progressProjectId = hit?.id || null;
  }
  state.projectOpen = false;
  state.projectEditing = false;
  state.page = "progress";
  closeNav();
  $("app").classList.remove("show-chats", "show-folders", "show-preview");
  render();
}

/** YiAgent：目标拆解只绑 p11 的 A/B/C/D 树（不依赖项目看板） */
function yiagentProgressRaw() {
  state.progressProjectId = "p11";
  const fromApi = state.projects.find((p) => p.id === "p11");
  return (
    fromApi || {
      id: "p11",
      title: "YiAgent",
      status: "进行中",
      category: "战略",
      pillar: "影响力计划",
      owner: "你",
      team: "YiAgent",
      customer: "",
    }
  );
}

function renderYiagentGoals() {
  const raw = yiagentProgressRaw();
  const xExtra = PROJECT_EXTRA.p11 || {};
  const goalsPreview = resolveProgressGoals(raw, xExtra);
  if (goalsPreview.length && !goalsPreview.find((g) => g.letter === state.progressGoalLetter)) {
    state.progressGoalLetter = goalsPreview[0].letter;
  }
  const cur = enrichProject(raw);
  const tree = cur.progressTree || [];
  const flat = cur.progress || [];
  const doneN = flat.filter((r) => r.status === "done").length;
  const hasGoals = (cur.progressGoals || []).length > 0;
  const goalLetter = hasGoals ? cur.progressGoal || "A" : "";
  const goalTitle = hasGoals
    ? cur.progressGoalTitle || cur.goal || "目标"
    : cur.goal || "目标树待收敛";
  const goalExample = hasGoals ? cur.progressGoalExample || "" : "";
  const goalChips = hasGoals
    ? (cur.progressGoals || [])
        .map(
          (g) => `
      <button class="chip-btn ${g.letter === goalLetter ? "accent" : ""}" type="button" data-progress-goal="${escapeHtml(
            g.letter
          )}">目标 ${escapeHtml(g.letter)} · ${escapeHtml(g.title || g.letter)}</button>`
        )
        .join("")
    : "";
  const treeHtml = !hasGoals
    ? `<div class="empty">目标树尚未拆解</div>`
    : tree.length
      ? renderProgressTreeNodes(tree)
      : `<div class="empty">该目标暂无拆解树</div>`;
  return `
    <div class="pad progress-page">
      <div class="card">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">目标拆解</span>
          ${
            hasGoals
              ? `<span class="tag blue">目标 ${escapeHtml(goalLetter)}</span>`
              : `<span class="tag orange">待拆目标</span>`
          }
          <span class="tag">A 产基因 · B 组装 · C 加速 · D 降耗</span>
        </div>
        <h2>目标拆解</h2>
        <div class="meta">${
          flat.length ? `${doneN}/${flat.length} 节点已完成` : hasGoals ? "暂无节点" : "目标树未立"
        } · 切换 A/B/C/D 查看任务树</div>
        ${
          goalChips
            ? `<div class="progress-goal-chips" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px">${goalChips}</div>`
            : ""
        }
        <div class="progress-goal-banner">
          <div class="progress-goal-kicker">${
            hasGoals ? `目标 ${escapeHtml(goalLetter)}` : "尚未拆树"
          }</div>
          <div class="progress-goal-title">${escapeHtml(goalTitle)}</div>
          ${
            goalExample
              ? `<div class="progress-goal-example">例：「${escapeHtml(goalExample)}」</div>`
              : ""
          }
          ${hasGoals ? progressGoalLegendHtml(cur, goalLetter) : ""}
        </div>
      </div>
      <div class="card progress-tree-card" style="margin-top:14px" aria-label="目标拆解树">
        <div class="progress-tree-toolbar">
          <div class="meta">${hasGoals ? "树状任务图 · 点击 ▾/▸ 折叠" : "等待目标收敛"}</div>
          <div class="progress-tree-toolbar-actions">
            ${
              hasGoals
                ? `<button class="chip-btn" type="button" data-progress-fold-all="expand">全部展开</button>
            <button class="chip-btn" type="button" data-progress-fold-all="collapse">全部折叠</button>`
                : ""
            }
          </div>
        </div>
        ${treeHtml}
      </div>
      ${hasGoals ? renderProgressTasksPanel(cur) : ""}
      ${hasGoals ? renderProgressCrossLinksPanel(cur) : ""}
      <div class="list proj-actions" style="margin-top:14px">
        <button class="btn primary" type="button" data-page="chat">单基因工作台</button>
        <button class="btn ghost" type="button" data-page="genome">基因组工作台</button>
      </div>
    </div>`;
}

function renderProgress() {
  if (SITE_GATE === "yiagent") return renderYiagentGoals();
  if (!state.projectsLoaded && !state.projects.length) {
    return `<div class="pad"><div class="card"><div class="empty">${
      state.projectsError ? "项目库不可用 · " + escapeHtml(state.projectsError) : "正在加载项目…"
    }</div></div></div>`;
  }
  const list = state.projects.filter((p) => p.status !== "已归档");
  if (!list.length) {
    return `<div class="pad"><div class="card"><div class="empty">暂无进行中的项目</div></div></div>`;
  }
  if (!state.progressProjectId || !list.find((p) => p.id === state.progressProjectId)) {
    state.progressProjectId = list.find((p) => p.id === "p11")?.id || list[0].id;
  }
  const raw = list.find((p) => p.id === state.progressProjectId);
  const xExtra = PROJECT_EXTRA[raw.id] || {};
  const goalsPreview = resolveProgressGoals(raw, xExtra);
  if (goalsPreview.length && !goalsPreview.find((g) => g.letter === state.progressGoalLetter)) {
    state.progressGoalLetter = goalsPreview[0].letter;
  }
  const cur = enrichProject(raw);
  const tree = cur.progressTree || [];
  const flat = cur.progress || [];
  const doneN = flat.filter((r) => r.status === "done").length;
  const hasGoals = (cur.progressGoals || []).length > 0;
  const goalLetter = hasGoals ? cur.progressGoal || "A" : "";
  const goalTitle = hasGoals
    ? cur.progressGoalTitle || cur.goal || "项目目标"
    : cur.goal || "进度树待收敛";
  const goalExample = hasGoals ? cur.progressGoalExample || "" : "";
  const projectChips = list
    .map(
      (p) => `
      <button class="chip-btn ${p.id === state.progressProjectId ? "accent" : ""}" type="button" data-progress-project="${escapeHtml(
        p.id
      )}">${escapeHtml(p.title)}</button>`
    )
    .join("");
  const goalChips = hasGoals
    ? (cur.progressGoals || [])
        .map(
          (g) => `
      <button class="chip-btn ${g.letter === goalLetter ? "accent" : ""}" type="button" data-progress-goal="${escapeHtml(
            g.letter
          )}">目标 ${escapeHtml(g.letter)} · ${escapeHtml(g.title || g.letter)}</button>`
        )
        .join("")
    : "";
  const treeHtml = !hasGoals
    ? `<div class="empty">进度树尚未拆解 · 先在项目计划收敛目标后再挂树</div>`
    : tree.length
      ? renderProgressTreeNodes(tree)
      : `<div class="empty">该目标暂无进度树</div>`;
  return `
    <div class="pad progress-page">
      <div class="card">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag ${categoryTagClass(cur.category)}">${categoryLabel(cur.category)}</span>
          <span class="tag ${
            cur.status === "进行中" ? "blue" : cur.status === "等人" ? "orange" : "green"
          }">${escapeHtml(cur.status)}</span>
          ${
            hasGoals
              ? `<span class="tag blue">目标 ${escapeHtml(goalLetter)}</span>`
              : `<span class="tag orange">待拆目标</span>`
          }
          ${cur.pillar ? `<span class="tag">${escapeHtml(cur.pillar)}</span>` : ""}
        </div>
        <h2>${escapeHtml(cur.title)} · 进度树</h2>
        <div class="meta">${
          flat.length ? `${doneN}/${flat.length} 节点已完成` : hasGoals ? "暂无节点" : "目标树未立"
        } · Owner ${escapeHtml(cur.owner || "—")} · ${escapeHtml(cur.team || "—")}</div>
        <div class="progress-project-chips" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px">${projectChips}</div>
        ${
          goalChips
            ? `<div class="progress-goal-chips" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px">${goalChips}</div>`
            : ""
        }
        <div class="progress-goal-banner">
          <div class="progress-goal-kicker">${
            hasGoals ? `目标 ${escapeHtml(goalLetter)}` : "项目目标（尚未拆树）"
          }</div>
          <div class="progress-goal-title">${escapeHtml(goalTitle)}</div>
          ${
            goalExample
              ? `<div class="progress-goal-example">例：「${escapeHtml(goalExample)}」</div>`
              : ""
          }
          ${hasGoals ? progressGoalLegendHtml(cur, goalLetter) : ""}
        </div>
      </div>
      <div class="card progress-tree-card" style="margin-top:14px" aria-label="项目进度树">
        <div class="progress-tree-toolbar">
          <div class="meta">${hasGoals ? "树状任务图 · 点击 ▾/▸ 折叠" : "等待目标收敛"}</div>
          <div class="progress-tree-toolbar-actions">
            ${
              hasGoals
                ? `<button class="chip-btn" type="button" data-progress-fold-all="expand">全部展开</button>
            <button class="chip-btn" type="button" data-progress-fold-all="collapse">全部折叠</button>`
                : ""
            }
          </div>
        </div>
        ${treeHtml}
      </div>
      ${hasGoals ? renderProgressTasksPanel(cur) : ""}
      ${hasGoals ? renderProgressCrossLinksPanel(cur) : ""}
      <div class="list proj-actions" style="margin-top:14px">
        <button class="btn primary" type="button" data-project-open="${escapeHtml(cur.id)}">打开项目详情</button>
        <button class="btn ghost" type="button" data-page="projects">返回项目看板</button>
      </div>
    </div>`;
}

function closeProjectDetail() {
  state.projectOpen = false;
  state.projectEditing = false;
  if (SITE_GATE === "yiagent") {
    setPage("progress");
    return;
  }
  render();
}

function channelSelectOptions(selected) {
  return Object.values(CHANNELS)
    .filter((c) => c.kind === "team" || c.kind === "human")
    .sort((a, b) => a.order - b.order)
    .map(
      (c) =>
        `<option value="${escapeHtml(c.id)}" ${c.id === selected ? "selected" : ""}>${escapeHtml(c.name)}</option>`
    )
    .join("");
}

function $(id) {
  return document.getElementById(id);
}

function toast(msg) {
  const el = $("toast");
  el.hidden = false;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("show"), 2200);
}

function loadAssets() {
  let stored = [];
  try {
    const raw = localStorage.getItem(ASSETS_LS_KEY);
    if (raw) stored = JSON.parse(raw) || [];
  } catch {
    stored = [];
  }
  if (!Array.isArray(stored)) stored = [];
  const byId = new Map(stored.map((a) => [a.id, a]));
  for (const seed of ASSET_SEED) {
    if (!byId.has(seed.id)) byId.set(seed.id, { ...seed });
  }
  const list = [...byId.values()];
  try {
    localStorage.setItem(ASSETS_LS_KEY, JSON.stringify(list));
  } catch {
    /* ignore */
  }
  return list;
}

function saveAssets(list) {
  state.assets = list;
  try {
    localStorage.setItem(ASSETS_LS_KEY, JSON.stringify(list));
  } catch {
    /* ignore */
  }
}

function sshCommandFor(asset) {
  const port = Number(asset.sshPort) || 22;
  const portOpt = port === 22 ? "" : ` -p ${port}`;
  const pem = (asset.pemPath || "").trim();
  const user = asset.sshUser || "root";
  const host = asset.host;
  if (pem) {
    return `ssh -i ${pem} -o IdentitiesOnly=yes${portOpt} ${user}@${host}`;
  }
  return `ssh${portOpt} ${user}@${host}`;
}

function sshUrlFor(asset) {
  const user = encodeURIComponent(asset.sshUser || "root");
  const host = asset.host;
  const port = Number(asset.sshPort) || 22;
  return port === 22 ? `ssh://${user}@${host}` : `ssh://${user}@${host}:${port}`;
}

async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

async function connectAssetSsh(id) {
  const asset = state.assets.find((a) => a.id === id);
  if (!asset?.host) {
    toast("资产无主机地址");
    return;
  }
  const cmd = sshCommandFor(asset);
  const copied = await copyText(cmd);
  try {
    window.location.href = sshUrlFor(asset);
  } catch {
    /* ignore */
  }
  toast(copied ? "已复制 SSH 命令 · 正在唤起本机客户端" : "请手动执行：" + cmd);
}

async function probeAsset(id) {
  const asset = state.assets.find((a) => a.id === id);
  if (!asset?.host) return;
  state.assetProbe = { ...state.assetProbe, [id]: { status: "checking" } };
  render();
  try {
    const res = await fetch("/api/agent/tcp-probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host: asset.host, port: Number(asset.sshPort) || 22 }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.assetProbe = {
      ...state.assetProbe,
      [id]: { status: data.ok ? "up" : "down", ms: data.ms, at: Date.now() },
    };
  } catch (e) {
    state.assetProbe = {
      ...state.assetProbe,
      [id]: { status: "unknown", error: String(e.message || e), at: Date.now() },
    };
  }
  if (state.page === "assets") render();
}

async function loadItSecrets() {
  state.itSecretsLoading = true;
  state.itSecretsError = null;
  try {
    const res = await fetch("/api/agent/it-secrets");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    state.itSecrets = Array.isArray(data.secrets) ? data.secrets : [];
  } catch (e) {
    state.itSecrets = [];
    state.itSecretsError = String(e.message || e);
  } finally {
    state.itSecretsLoading = false;
  }
}

function renderSecretCard(s) {
  const revealed = Boolean(state.itSecretReveal[s.id]);
  const display = s.present
    ? revealed
      ? s.value
      : s.keyHint || "••••"
    : "（文件缺失）";
  const statusTag = s.present
    ? `<span class="tag green">已落盘</span>`
    : `<span class="tag orange">未找到</span>`;
  return `
    <div class="card asset-card">
      <div class="provider-head">
        <div>
          <div class="row-title" style="font-size:16px">${escapeHtml(s.name)}</div>
          <div class="row-desc">${escapeHtml(s.provider || "api")} · ${escapeHtml(s.role || "")}</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
          ${statusTag}
          ${(s.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
        </div>
      </div>
      <div class="list" style="margin-top:10px">
        <div class="row"><div><div class="row-title">正本路径</div><div class="row-desc"><code class="branch-code">${escapeHtml(
          s.path || s.file || ""
        )}</code></div></div></div>
        <div class="row"><div><div class="row-title">API Key</div><div class="row-desc pre-wrap"><code class="branch-code">${escapeHtml(
          display
        )}</code></div></div></div>
      </div>
      <div class="meta" style="margin-top:10px">正本在桌面 opc/公司资产/IT资产 · 公司资产页可查看明文</div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn primary" type="button" data-secret-copy="${escapeHtml(s.id)}" ${
          s.present ? "" : "disabled"
        }>复制 Key</button>
        <button class="btn ghost" type="button" data-secret-reveal="${escapeHtml(s.id)}" ${
          s.present ? "" : "disabled"
        }>${revealed ? "隐藏" : "显示全文"}</button>
      </div>
    </div>`;
}

function renderHostCard(a) {
  const probe = state.assetProbe[a.id] || {};
  const probeTag =
    probe.status === "up"
      ? `<span class="tag green">TCP 通</span>`
      : probe.status === "down"
        ? `<span class="tag orange">TCP 不通</span>`
        : probe.status === "checking"
          ? `<span class="tag">探测中…</span>`
          : `<span class="tag">未探测</span>`;
  const cmd = sshCommandFor(a);
  return `
    <div class="card asset-card">
      <div class="provider-head">
        <div>
          <div class="row-title" style="font-size:16px">${escapeHtml(a.name)}</div>
          <div class="row-desc">${escapeHtml(a.provider || a.kind || "host")} · ${escapeHtml(a.role || "")}</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
          ${probeTag}
          ${(a.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
        </div>
      </div>
      <div class="list" style="margin-top:10px">
        <div class="row"><div><div class="row-title">主机</div><div class="row-desc"><code class="branch-code">${escapeHtml(
          a.host
        )}</code></div></div></div>
        <div class="row"><div><div class="row-title">SSH</div><div class="row-desc">${escapeHtml(
          a.sshUser || "root"
        )} · 端口 ${escapeHtml(String(a.sshPort || 22))}</div></div></div>
        <div class="row"><div><div class="row-title">密钥</div><div class="row-desc pre-wrap">${escapeHtml(
          a.pemPath || "（密码/其它）"
        )}${a.pemHint ? `<br/><span class="meta">${escapeHtml(a.pemHint)}</span>` : ""}</div></div></div>
        ${
          a.note
            ? `<div class="row"><div><div class="row-title">备注</div><div class="row-desc pre-wrap">${escapeHtml(
                a.note
              )}</div></div></div>`
            : ""
        }
      </div>
      <div class="meta" style="margin-top:10px">命令 · <code class="branch-code">${escapeHtml(cmd)}</code></div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn primary" type="button" data-asset-ssh="${escapeHtml(a.id)}">一键 SSH</button>
        <button class="btn ghost" type="button" data-asset-copy="${escapeHtml(a.id)}">复制命令</button>
        <button class="btn ghost" type="button" data-asset-probe="${escapeHtml(a.id)}">探测端口</button>
        ${
          a.website
            ? `<a class="btn ghost" href="${escapeHtml(
                a.website
              )}" target="_blank" rel="noopener noreferrer">打开官网</a>`
            : ""
        }
      </div>
    </div>`;
}

function renderAssets() {
  const hosts = (state.assets || []).filter((a) => a.kind !== "api_key");
  const secrets = state.itSecrets || [];
  const secretBlock = state.itSecretsLoading
    ? `<div class="card"><div class="empty">正在读取 IT 资产密钥…</div></div>`
    : state.itSecretsError
      ? `<div class="card"><div class="empty">读取失败：${escapeHtml(
          state.itSecretsError
        )}</div><div style="margin-top:12px"><button class="btn primary" type="button" id="btn-it-secrets-reload">重试</button></div></div>`
      : secrets.map(renderSecretCard).join("") ||
        `<div class="card"><div class="empty">未登记 API Key 文件</div></div>`;

  return `
    <div class="pad">
      <div class="card" style="margin-bottom:14px">
        <h2>资产管理</h2>
        <div class="meta">主机一键 SSH · API Key 正本在 opc/公司资产/IT资产（本页可读明文）</div>
        <div class="row-desc" style="margin-top:8px">VPN 可能拦截出站 22；连不上时先关 VPN 再试。设置 → Provider 仍只显示 Key 提示。</div>
      </div>
      <div class="nav-sec" style="margin:4px 0 10px">API Key</div>
      <div class="asset-grid" style="margin-bottom:18px">
        ${secretBlock}
      </div>
      <div class="nav-sec" style="margin:4px 0 10px">主机 / 云服务器</div>
      <div class="asset-grid">
        ${
          hosts.map(renderHostCard).join("") ||
          `<div class="card"><div class="empty">暂无主机资产</div></div>`
        }
      </div>
    </div>`;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function clock() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function lastMsg(id) {
  const list = state.threads[id] || [];
  return list[list.length - 1];
}

function childrenOf(teamId) {
  const roster = (state.channelRoster || []).find((c) => c.id === teamId);
  if (roster) {
    return (roster.memberIds || [])
      .map(dmIdForAgent)
      .filter((id) => CHANNELS[id])
      .sort((a, b) => (CHANNELS[a].order || 0) - (CHANNELS[b].order || 0));
  }
  return Object.keys(CHANNELS)
    .filter((id) => CHANNELS[id]?.parent === teamId)
    .sort((a, b) => (CHANNELS[a].order || 0) - (CHANNELS[b].order || 0));
}

function persistOrgRoster() {
  syncChannelsFromRoster();
  saveAgentMgmt();
}

function createOrgChannel() {
  const id = `ch-${Date.now().toString(36)}`;
  state.channelRoster.push({
    id,
    name: "新频道",
    system: false,
    sub: "自建频道 · 可删可改成员",
    color: "#0a84ff",
    order: 100 + state.channelRoster.length,
    kind: "team",
    memberIds: [],
  });
  state.orgFocusChannelId = id;
  state.orgTab = "channels";
  persistOrgRoster();
  toast("已新建频道 · 勾选成员即可");
  render();
}

function deleteOrgChannel(channelId) {
  if (isReviewChannel(channelId)) {
    toast("审查进化委员会为系统必选，不可删除");
    return;
  }
  state.channelRoster = state.channelRoster.filter((c) => c.id !== channelId);
  if (state.orgFocusChannelId === channelId) state.orgFocusChannelId = "team-review";
  if (state.channelId === channelId || state.teamScope === channelId) {
    state.channelId = "team-review";
    state.teamScope = "team-review";
  }
  persistOrgRoster();
  toast("频道已删除");
  render();
}

function renameOrgChannel(channelId, name) {
  const ch = state.channelRoster.find((c) => c.id === channelId);
  if (!ch) return;
  const next = String(name || "").trim();
  if (!next) return;
  if (isReviewChannel(channelId)) {
    toast("审查委名称固定，不可改");
    return;
  }
  ch.name = next;
  persistOrgRoster();
  render();
}

function toggleOrgChannelMember(channelId, agentId) {
  const ch = state.channelRoster.find((c) => c.id === channelId);
  const agent = agentById(agentId);
  if (!ch || !agent) return;
  const i = ch.memberIds.indexOf(agentId);
  if (i >= 0) {
    if (isReviewChannel(channelId) && agent.system) {
      toast("审查委核心席不可移出");
      return;
    }
    ch.memberIds.splice(i, 1);
  } else {
    ch.memberIds.push(agentId);
  }
  persistOrgRoster();
  render();
}

function createOrgAgent() {
  const id = `ag-${Date.now().toString(36)}`;
  state.agentRoster.push(
    ag(id, "新 Agent", "新", "#8e8e93", { kind: "agent", sub: "自建 · 可编入任意频道" })
  );
  state.orgTab = "agents";
  persistOrgRoster();
  toast("已添加 Agent");
  render();
}

function deleteOrgAgent(agentId) {
  const agent = agentById(agentId);
  if (!agent) return;
  if (agent.system) {
    toast("系统席不可删除");
    return;
  }
  state.agentRoster = state.agentRoster.filter((a) => a.id !== agentId);
  for (const ch of state.channelRoster) {
    ch.memberIds = (ch.memberIds || []).filter((id) => id !== agentId);
  }
  persistOrgRoster();
  toast("已删除 Agent");
  render();
}

function patchOrgAgent(agentId, patch) {
  const agent = agentById(agentId);
  if (!agent) return;
  if (agent.system && (patch.name != null || patch.kind != null)) {
    toast("系统席名称/类型锁定");
    return;
  }
  Object.assign(agent, patch);
  if (patch.name && !agent.initial) agent.initial = String(patch.name).slice(0, 1);
  persistOrgRoster();
  render();
}

/** 旧频道 id → 新自组频道（兼容书签/项目登记） */
function resolveChannelAlias(id) {
  const map = {
    "team-strategy": "ch-strategy",
    "team-dev": "ch-dev",
    "team-mkt": "ch-mkt",
    "team-intern": "ch-intern",
    "team-sales": "ch-sales",
    "dm-cto": "dm-ag-cto",
    "dm-cmo": "dm-ag-cmo",
    "dm-ceo": "dm-ag-ceo",
    "dm-cfo": "dm-ag-cfo",
    "dm-ea": "dm-ag-ea",
    "dm-product": "dm-ag-product",
    "dm-pm": "dm-ag-pm",
    "dm-arch": "dm-ag-arch",
    "dm-dev": "dm-ag-dev",
    "dm-devops": "dm-ag-devops",
    "dm-legal": "dm-ag-legal",
    "dm-risk": "dm-ag-risk",
  };
  return map[id] || id;
}

function syncTeamScopeFromChannel(channelId) {
  const c = CHANNELS[channelId];
  if (!c) return;
  if (c.kind === "team" || c.kind === "human" || c.kind === "project-team") state.teamScope = c.id;
  else if (c.parent) state.teamScope = c.parent;
  state.chatTab = "channel";
}

function openNav() {
  $("app").classList.add("nav-open");
  $("nav-scrim").hidden = false;
}

function closeNav() {
  $("app").classList.remove("nav-open");
  $("nav-scrim").hidden = true;
}

function siteHome() {
  return SITE.home || "today";
}

function setPage(id) {
  if (id === "todos") id = "schedule";
  if ((SITE.hide || []).includes(id)) id = siteHome();
  if (!PAGES[id]) id = siteHome();
  state.page = id;
  if (id !== "projects") {
    state.projectOpen = false;
    state.projectEditing = false;
  }
  if (id === "progress") {
    if (SITE_GATE === "yiagent") {
      state.progressProjectId = "p11";
    } else {
      const list = state.projects.filter((p) => p.status !== "已归档");
      if (!state.progressProjectId || !list.find((p) => p.id === state.progressProjectId)) {
        state.progressProjectId =
          list.find((p) => p.id === "p11")?.id || state.projectId || list[0]?.id || null;
      }
    }
  }
  if (id === "projects" && SITE_GATE === "yiagent" && !state.projectOpen) {
    const list = state.projects.filter((p) => p.status !== "已归档");
    const focus = list.find((p) => p.id === "p11") || list[0];
    if (focus) {
      state.projectId = focus.id;
      state.projectOpen = true;
    }
  }
  if (id !== "settings") {
    state.providerEditId = null;
    state.providerDraftKey = "";
  }
  closeNav();
  const showChatList = id === "chat" && !isWorkbenchBenchMode();
  $("app").classList.toggle("show-chats", showChatList);
  $("app").classList.remove("show-folders", "show-preview");
  render();
  if (id === "chat" && SITE_GATE === "yiagent" && state.workbenchMode === "factory") {
    if (typeof FactoryBench !== "undefined") {
      FactoryBench.ensureDemo().catch(() => {});
    }
  }
  if (id === "settings" && state.settingsTab === "providers") {
    loadProviders().then(() => {
      if (state.page === "settings") render();
    });
  }
  if (id === "assets") {
    loadItSecrets().then(() => {
      if (state.page === "assets") render();
    });
  }
}

function applySiteBrand() {
  const t = document.querySelector(".nav-title");
  const y = document.querySelector(".nav-you");
  const foot = document.querySelector(".nav-user-meta");
  if (t) t.textContent = SITE.brand;
  if (y) y.textContent = SITE.you;
  if (foot && SITE.foot) foot.textContent = SITE.foot;
  if (document.title !== SITE.title) document.title = SITE.title;
}

function navSections() {
  const hide = new Set(SITE.hide || []);
  return NAV.map((g) => ({
    ...g,
    items: g.items.filter((it) => !hide.has(it.id)),
  })).filter((g) => g.items.length);
}

function renderNav() {
  applySiteBrand();
  const nApprove = state.approvals.length;
  const nTodos = openTodoCount();
  $("nav-scroll").innerHTML = navSections()
    .map((g) => {
      const items = g.items
        .map((it) => {
          let badge = "";
          if (it.badge === "approvals" && nApprove) badge = `<span class="nav-badge">${nApprove}</span>`;
          if (it.badge === "todos" && nTodos) badge = `<span class="nav-badge">${nTodos}</span>`;
          return `
          <button class="nav-item ${state.page === it.id ? "active" : ""}" type="button" data-page="${it.id}">
            <span class="nav-ico" style="background:${it.color}">${
              SITE_GATE === "yiagent" && it.id === "chat"
                ? ICO.dna
                : ICO[it.id] || ""
            }</span>
            <span>${it.label}</span>
            ${badge}
          </button>`;
        })
        .join("");
      return `<div class="nav-sec">${g.sec}</div>${items}`;
    })
    .join("");
}

function renderHead() {
  const openProj =
    state.page === "projects" && state.projectOpen
      ? enrichProject(state.projects.find((p) => p.id === state.projectId))
      : null;
  const openProg =
    state.page === "progress"
      ? enrichProject(state.projects.find((p) => p.id === state.progressProjectId))
      : null;
  if (openProj) {
    $("ws-title").textContent = openProj.title;
    $("ws-sub").textContent = `${categoryLabel(openProj.category)} · ${openProj.status} · Owner ${openProj.owner}`;
  } else if (openProg) {
    $("ws-title").textContent = SITE_GATE === "yiagent" ? "项目进度" : "项目进度表";
    $("ws-sub").textContent = `${openProg.title} · ${categoryLabel(openProg.category)} · ${openProg.status}`;
  } else {
    const [t, s] = TITLES[state.page] || ["", ""];
    $("ws-title").textContent = t;
    $("ws-sub").textContent = s;
  }
  const actions = [];
  if (state.page === "chat") {
    if (!isWorkbenchBenchMode()) {
      const showing = $("app").classList.contains("show-chats");
      actions.push(
        `<button class="chip-btn" type="button" id="btn-toggle-chats">${showing ? "进入对话" : "会话列表"}</button>`
      );
    } else if (state.workbenchMode === "factory") {
      if (!(typeof FactoryBench !== "undefined" && FactoryBench.state?.runMode === "demo")) {
        actions.push(`<button class="chip-btn" type="button" data-fb-action="open-settings">设置</button>`);
      }
    } else if (state.workbenchMode === "evolve") {
      if (!(typeof EvolveBench !== "undefined" && EvolveBench.state?.runMode === "demo")) {
        actions.push(`<button class="chip-btn" type="button" data-eb-action="open-settings">设置</button>`);
      }
    }
  }
  if (state.page === "kb" && SITE_GATE !== "yiagent") {
    actions.push(`<button class="chip-btn" type="button" id="btn-kb-folders">文件夹</button>`);
    actions.push(`<button class="btn primary" type="button" id="btn-kb-new">新建</button>`);
  }
  if (state.page === "progress") {
    if (SITE_GATE === "yiagent") {
      actions.push(`<button class="chip-btn" type="button" data-page="genome">基因组</button>`);
      actions.push(`<button class="btn primary" type="button" data-page="chat">单基因</button>`);
    } else {
      actions.push(`<button class="chip-btn" type="button" data-page="projects">项目看板</button>`);
      if (state.progressProjectId) {
        actions.push(
          `<button class="chip-btn" type="button" data-project-open="${escapeHtml(state.progressProjectId)}">项目详情</button>`
        );
      }
    }
  }
  if (state.page === "genome") {
    actions.push(`<button class="chip-btn" type="button" data-page="chat">单基因工作台</button>`);
    actions.push(
      `<a class="btn primary" href="/dna-graph.html" target="_blank" rel="noopener">新窗口打开</a>`
    );
  }
  if (state.page === "projects") {
    if (state.projectOpen && state.projectEditing) {
      actions.push(`<button class="chip-btn" type="button" id="btn-project-edit-cancel">取消</button>`);
      actions.push(`<button class="btn primary" type="button" id="btn-project-edit-save">保存</button>`);
    } else if (state.projectOpen) {
      if (SITE_GATE !== "yiagent") {
        actions.push(`<button class="chip-btn" type="button" id="btn-project-back">返回看板</button>`);
      }
      actions.push(
        `<button class="chip-btn" type="button" data-open-progress="${escapeHtml(state.projectId || "")}">${
          SITE_GATE === "yiagent" ? "项目进度" : "进度表"
        }</button>`
      );
      if (SITE_GATE === "yiagent") {
        actions.push(`<button class="btn primary" type="button" data-page="chat">工作台</button>`);
      }
      actions.push(`<button class="chip-btn" type="button" id="btn-project-edit">编辑</button>`);
      if (SITE_GATE !== "yiagent") {
        if (state.projects.find((p) => p.id === state.projectId)?.status === "已归档") {
          actions.push(`<button class="chip-btn" type="button" id="btn-project-unarchive-h">恢复</button>`);
        } else {
          actions.push(`<button class="chip-btn" type="button" id="btn-project-archive-h">归档</button>`);
        }
        actions.push(`<button class="chip-btn" type="button" id="btn-project-del-h">删除</button>`);
      }
    } else {
      actions.push(
        `<button class="chip-btn" type="button" data-page="progress">${
          SITE_GATE === "yiagent" ? "项目进度" : "进度表"
        }</button>`
      );
      if (SITE_GATE !== "yiagent") {
        actions.push(`<button class="btn primary" type="button" id="btn-project-new-h">新建项目</button>`);
      }
    }
  }
  if (state.page === "strategy") {
    actions.push(`<button class="btn primary" type="button" id="btn-strat-edit-h">调整目标</button>`);
  }
  if (state.page === "dna") {
    actions.push(`<button class="chip-btn" type="button" data-page="chat" data-open-dm="team-review">审查委</button>`);
    if (SITE_GATE === "yiagent" || state.projects.some((p) => p.id === "p11")) {
      actions.push(`<button class="btn primary" type="button" data-open-progress="p11">YiAgent 进度</button>`);
    }
  }
  if (state.page === "schedule") {
    actions.push(`<button class="chip-btn" type="button" id="btn-schedule-today">回到今天</button>`);
    actions.push(`<button class="btn primary" type="button" id="btn-todo-add-h">新建待办</button>`);
  }
  if (state.page === "settings" && state.settingsTab === "providers") {
    actions.push(`<button class="chip-btn" type="button" id="btn-providers-reload-h">刷新</button>`);
  }
  if (state.page === "assets") {
    actions.push(`<button class="chip-btn" type="button" id="btn-it-secrets-reload-h">刷新密钥</button>`);
  }
  if (
    state.approvals.length &&
    state.page !== "approvals" &&
    !(SITE.hide || []).includes("approvals")
  ) {
    actions.push(
      `<button class="chip-btn accent" type="button" data-page="approvals">待审批 ${state.approvals.length}</button>`
    );
  }
  $("ws-actions").innerHTML = actions.join("");
}

function renderToday() {
  const unread = Object.values(state.unread).reduce((a, b) => a + b, 0);
  const today = ymd(new Date());
  const todayEvents = state.schedule.filter((e) => e.date === today).sort((a, b) => a.time.localeCompare(b.time));
  const openTodos = state.todos.filter((t) => !t.done).slice(0, 4);
  return `
    <div class="pad">
      <div class="grid-3" style="margin-bottom:14px">
        <div class="card stat ${state.approvals.length ? "alert" : ""}"><div class="n">${state.approvals.length}</div><div class="l">待你审批</div></div>
        <div class="card stat ${openTodoCount() ? "alert" : ""}"><div class="n">${openTodoCount()}</div><div class="l">未完成待办</div></div>
        <div class="card stat"><div class="n">${todayEvents.length}</div><div class="l">今日日程</div></div>
      </div>
      <div class="card" style="margin-bottom:14px">
        <h2>今日安排与待办</h2>
        <div class="meta">${formatDayLabel(today)} · ${today} · 日程 ${todayEvents.length} · 未完成待办 ${openTodoCount()}</div>
        <div class="list">
          ${
            todayEvents
              .map(
                (e) =>
                  `<div class="row"><div><div class="row-title"><span class="pill">日程</span>${escapeHtml(e.time)}–${escapeHtml(e.end)} · ${escapeHtml(e.title)}</div><div class="row-desc">${escapeHtml(e.kind)} · ${escapeHtml(e.place)}</div></div>${
                    e.link ? `<button class="btn ghost" data-page="chat" data-open-dm="${e.link}">跟进</button>` : ""
                  }</div>`
              )
              .join("") +
              openTodos
                .map(
                  (t) =>
                    `<div class="row"><div><div class="row-title"><span class="pill todo-pill">待办</span>${escapeHtml(t.title)}</div><div class="row-desc">${escapeHtml(t.priority)} · 截止 ${escapeHtml(t.due)}</div></div><button class="btn ghost" type="button" data-todo-toggle="${t.id}">完成</button></div>`
                )
                .join("") || `<div class="empty">今日暂无安排与待办</div>`
          }
        </div>
        <div style="margin-top:12px"><button class="btn primary" data-page="schedule">打开日程</button></div>
      </div>
      <div class="grid-2">
        <div class="card">
          <h2>快捷入口</h2>
          <div class="meta">管组织、说话、查知识、跟项目与战略</div>
          <div class="list">
            <div class="row"><div><div class="row-title">消息</div><div class="row-desc">战略委 / 开发 / 营销与数字员工</div></div><button class="btn primary" data-page="chat">打开</button></div>
            <div class="row"><div><div class="row-title">项目管理</div><div class="row-desc">看板 · 风险</div></div><button class="btn ghost" data-page="projects">打开</button></div>
            <div class="row"><div><div class="row-title">项目进度表</div><div class="row-desc">阶段 · 状态 · 验证产出</div></div><button class="btn ghost" data-page="progress">打开</button></div>
            <div class="row"><div><div class="row-title">全流程审阅</div><div class="row-desc">规格 → 题库 → 裁判 → 门禁 → 裁决</div></div><button class="btn ghost" data-page="review">打开</button></div>
            <div class="row"><div><div class="row-title">战略视图</div><div class="row-desc">目标 → 举措 → Team</div></div><button class="btn ghost" data-page="strategy">打开</button></div>
            <div class="row"><div><div class="row-title">DNA 工作台</div><div class="row-desc">公司基因组 · G1–G5 · 审查委</div></div><button class="btn ghost" data-page="dna">打开</button></div>
            <div class="row"><div><div class="row-title">知识库</div><div class="row-desc">人看 ≠ Agent 看 · 认证后才可挂载</div></div><button class="btn ghost" data-page="kb">打开</button></div>
          </div>
        </div>
        <div class="card">
          <h2>待你审批</h2>
          <div class="meta">点进审批页拍板 · 未读 ${unread}</div>
          <div class="list">
            ${
              state.approvals
                .slice(0, 3)
                .map(
                  (a) =>
                    `<div class="row"><div><div class="row-title">${a.title}</div><div class="row-desc">${a.desc}</div></div></div>`
                )
                .join("") || `<div class="empty">暂无</div>`
            }
          </div>
          <div style="margin-top:12px"><button class="btn primary" data-page="approvals">去审批</button></div>
        </div>
      </div>
    </div>`;
}

function dayItemCount(d) {
  const events = state.schedule.filter((e) => e.date === d).length;
  const todos = state.todos.filter((t) => t.due === d && !t.done).length;
  return events + todos;
}

function renderSchedule() {
  const days = Array.from({ length: 7 }, (_, i) => ymd(addDays(new Date(), i)));
  const day = state.scheduleDay || ymd(new Date());
  const events = state.schedule
    .filter((e) => e.date === day)
    .sort((a, b) => a.time.localeCompare(b.time));
  const filter = state.todoFilter || "open";
  const dayTodos = state.todos
    .filter((t) => t.due === day)
    .filter((t) => (filter === "all" ? true : filter === "done" ? t.done : !t.done))
    .sort((a, b) => Number(a.done) - Number(b.done) || a.title.localeCompare(b.title, "zh"));
  const otherOpen = state.todos
    .filter((t) => !t.done && t.due !== day)
    .sort((a, b) => a.due.localeCompare(b.due));
  const priClass = { 高: "hi", 中: "mid", 低: "lo" };
  return `
    <div class="pad schedule-agenda">
      <div class="card" style="margin-bottom:12px">
        <h2>本周 · 日程与待办</h2>
        <div class="meta">点选日期 · 左侧安排 · 右侧待办（角标含未完成待办）</div>
        <div class="day-strip">
          ${days
            .map((d) => {
              const count = dayItemCount(d);
              const dd = new Date(d + "T12:00:00");
              return `<button type="button" class="day-chip ${d === day ? "active" : ""}" data-schedule-day="${d}">
                <span class="day-chip-w">${formatDayLabel(d)}</span>
                <span class="day-chip-d">${dd.getDate()}</span>
                <span class="day-chip-n">${count ? count + " 项" : "—"}</span>
              </button>`;
            })
            .join("")}
        </div>
      </div>
      <div class="agenda-grid">
        <div class="card">
          <h2>${formatDayLabel(day)} · 安排</h2>
          <div class="meta">${events.length ? events.length + " 项日程" : "这天暂无日程"}</div>
          <div class="list schedule-list" style="margin-top:10px">
            ${
              events
                .map(
                  (e) => `
              <div class="row schedule-row">
                <div class="schedule-time">
                  <div class="row-title">${escapeHtml(e.time)}</div>
                  <div class="row-desc">${escapeHtml(e.end)}</div>
                </div>
                <div class="schedule-body">
                  <div class="row-title">${escapeHtml(e.title)}</div>
                  <div class="row-desc"><span class="pill">${escapeHtml(e.kind)}</span> ${escapeHtml(e.place)}</div>
                </div>
                ${
                  e.link
                    ? `<button class="btn ghost" data-page="chat" data-open-dm="${e.link}">打开会话</button>`
                    : ""
                }
              </div>`
                )
                .join("") || `<div class="empty">这天没有会议或拜访</div>`
            }
          </div>
        </div>
        <div class="card">
          <h2>${formatDayLabel(day)} · 待办</h2>
          <div class="meta">截止当日 · 未完成合计 ${openTodoCount()} · 本机记住</div>
          <div class="seg" style="margin-top:10px">
            <button type="button" class="chip-btn ${filter === "open" ? "accent" : ""}" data-todo-filter="open">未完成</button>
            <button type="button" class="chip-btn ${filter === "done" ? "accent" : ""}" data-todo-filter="done">已完成</button>
            <button type="button" class="chip-btn ${filter === "all" ? "accent" : ""}" data-todo-filter="all">全部</button>
            <button type="button" class="btn primary" id="btn-todo-add">新建</button>
          </div>
          <div class="list todo-list" style="margin-top:12px">
            ${
              dayTodos
                .map(
                  (t) => `
              <div class="row todo-row ${t.done ? "done" : ""}">
                <button type="button" class="todo-check" data-todo-toggle="${t.id}" aria-label="切换完成">${t.done ? "✓" : ""}</button>
                <div class="todo-body">
                  <div class="row-title">${escapeHtml(t.title)}</div>
                  <div class="row-desc"><span class="pri ${priClass[t.priority] || "mid"}">${escapeHtml(
                    t.priority
                  )}</span> 截止 ${escapeHtml(t.due)}${t.note ? " · " + escapeHtml(t.note) : ""}</div>
                </div>
                <button type="button" class="btn ghost" data-todo-del="${t.id}">删除</button>
              </div>`
                )
                .join("") ||
              `<div class="empty">${
                filter === "done" ? "这天没有已完成待办" : "这天没有待办 · 可新建"
              }</div>`
            }
          </div>
          ${
            otherOpen.length
              ? `<div class="sec" style="margin-top:16px">其他日期未完成</div>
          <div class="list todo-list" style="margin-top:8px">
            ${otherOpen
              .slice(0, 8)
              .map(
                (t) => `
              <div class="row todo-row">
                <button type="button" class="todo-check" data-todo-toggle="${t.id}" aria-label="切换完成"></button>
                <div class="todo-body">
                  <div class="row-title">${escapeHtml(t.title)}</div>
                  <div class="row-desc"><span class="pri ${priClass[t.priority] || "mid"}">${escapeHtml(
                    t.priority
                  )}</span> 截止 ${escapeHtml(t.due)} · <button type="button" class="linkish" data-schedule-day="${escapeHtml(
                    t.due
                  )}">跳到该日</button></div>
                </div>
                <button type="button" class="btn ghost" data-todo-del="${t.id}">删除</button>
              </div>`
              )
              .join("")}
          </div>`
              : ""
          }
        </div>
      </div>
    </div>`;
}

function renderTodos() {
  return renderSchedule();
}

function addTodo() {
  const title = window.prompt("待办内容");
  if (!title || !title.trim()) return;
  const due = state.scheduleDay || ymd(new Date());
  state.todos.unshift({
    id: "t" + Date.now(),
    title: title.trim(),
    due,
    priority: "中",
    done: false,
    note: "手建",
  });
  state.todoFilter = "open";
  state.page = "schedule";
  saveTodos();
  toast("已添加待办 · 截止 " + due);
  render();
}

function toggleTodo(id) {
  const t = state.todos.find((x) => x.id === id);
  if (!t) return;
  t.done = !t.done;
  saveTodos();
  toast(t.done ? "已完成" : "已恢复为未完成");
  render();
}

function deleteTodo(id) {
  state.todos = state.todos.filter((x) => x.id !== id);
  saveTodos();
  toast("已删除");
  render();
}

function renderApprovals() {
  if (!state.approvals.length) return `<div class="pad"><div class="card"><div class="empty">审批篮空了</div></div></div>`;
  return `
    <div class="pad">
      <div class="card" style="margin-bottom:12px">
        <h2>待你拍板</h2>
        <div class="meta">每条附人审材料：引用等级 · 缺口 · 审计摘要（全文仅人看）</div>
      </div>
      ${state.approvals
        .map((a) => {
          const r = a.review;
          return `
        <div class="card approve-card">
          <div class="approve-head">
            <div>
              <div class="row-title" style="font-size:16px">${a.title}</div>
              <div class="row-desc">${a.desc}</div>
            </div>
            <div style="display:flex;gap:8px;flex-shrink:0">
              <button class="btn danger" data-reject="${a.id}">驳回</button>
              <button class="btn primary" data-approve="${a.id}">批准</button>
            </div>
          </div>
          ${
            r
              ? `<div class="review-pack">
                   <div class="sec">人审材料包</div>
                   <div class="tags" style="margin-bottom:8px">
                     <span class="tag ${tierTagClass(r.minTier)}">结论最低 ${TIER_LABEL[r.minTier] || r.minTier}</span>
                     <span class="tag">仅人看</span>
                   </div>
                   <div class="row-desc" style="margin-bottom:8px"><strong>主张：</strong>${escapeHtml(r.claim)}</div>
                   <div class="cite-list">
                     ${r.citations
                       .map(
                         (c) => `
                       <div class="cite">
                         <span class="tag ${tierTagClass(c.tier)}">${c.tier}</span>
                         <div>
                           <div class="cite-title">${escapeHtml(c.source)}</div>
                           <div class="cite-note">${escapeHtml(c.note)}</div>
                         </div>
                       </div>`
                       )
                       .join("")}
                   </div>
                   ${
                     r.gaps?.length
                       ? `<div class="gap-box"><strong>未关闭缺口</strong><ul>${r.gaps
                           .map((g) => `<li>${escapeHtml(g)}</li>`)
                           .join("")}</ul></div>`
                       : `<div class="gap-box ok">无未关闭缺口 · 可拍板</div>`
                   }
                   <div class="trail-hint">${escapeHtml(r.trailHint || "")}</div>
                 </div>`
              : ""
          }
        </div>`;
        })
        .join("")}
    </div>`;
}

function renderWorkbenchSideNav() {
  if (SITE_GATE !== "yiagent") return "";
  const items = [
    { id: "factory", label: "单题DNA搜索", desc: "演示 / 真实运行" },
    { id: "evolve", label: "题组DNA搜索", desc: "演示 / 真实运行" },
  ];
  return `<aside class="wb-side" aria-label="单基因工作台">
    <div class="wb-side-head">单基因</div>
    ${items
      .map(
        (it) => `<button class="wb-side-item ${state.workbenchMode === it.id ? "active" : ""}" type="button" data-workbench-mode="${it.id}">
      <span class="wb-side-label">${it.label}</span>
      <span class="wb-side-desc">${it.desc}</span>
    </button>`
      )
      .join("")}
  </aside>`;
}

function renderChat() {
  if (SITE_GATE === "yiagent") {
    if (state.workbenchMode !== "factory" && state.workbenchMode !== "evolve") {
      state.workbenchMode = "factory";
    }
    const side = renderWorkbenchSideNav();
    if (state.workbenchMode === "evolve") {
      const body =
        typeof EvolveBench !== "undefined"
          ? EvolveBench.render()
          : `<div class="pad"><div class="card"><div class="empty">题组台脚本未加载</div></div></div>`;
      return `<div class="wb-shell">${side}<div class="wb-main">${body}</div></div>`;
    }
    const body =
      typeof FactoryBench !== "undefined"
        ? FactoryBench.render()
        : `<div class="pad"><div class="card"><div class="empty">筛选台脚本未加载</div></div></div>`;
    return `<div class="wb-shell">${side}<div class="wb-main">${body}</div></div>`;
  }

  const resolvedId = resolveChannelAlias(state.channelId);
  if (resolvedId !== state.channelId) state.channelId = resolvedId;
  if (!CHANNELS[state.channelId]) state.channelId = SITE_GATE === "yiagent" ? "ch-dev" : "team-review";
  const ch = CHANNELS[state.channelId];
  const scopeId =
    ch.kind === "team" || ch.kind === "human" || ch.kind === "project-team"
      ? ch.id
      : ch.parent || state.teamScope || "team-review";
  if (listRosterChannelIds().includes(scopeId) || CHANNELS[scopeId]?.kind === "project-team") {
    if (state.teamScope !== scopeId) state.teamScope = scopeId;
  }
  const scope = CHANNELS[state.teamScope] || CHANNELS["team-review"];
  const q = state.chatQ.trim().toLowerCase();

  const switchTeams = [...listRosterChannelIds(), ...projectTeamScopes()];

  const matchQ = (id) => {
    const c = CHANNELS[id];
    if (!c) return false;
    if (!q) return true;
    return (
      c.name.toLowerCase().includes(q) ||
      (c.sub || "").toLowerCase().includes(q) ||
      (c.members || []).some((m) => m.toLowerCase().includes(q))
    );
  };

  const row = (id, opts = {}) => {
    const c = CHANNELS[id];
    const last = lastMsg(id);
    const unread = state.unread[id] || 0;
    const letter =
      c.kind === "agent" || c.kind === "workbench" ? c.initial || c.name.slice(0, 1) : "#";
    const avKind =
      c.kind === "agent" || c.kind === "workbench" ? "agent" : c.kind === "human" ? "human" : "team";
    return `
      <button class="chan ${opts.primary ? "primary" : ""} ${opts.nested ? "nested" : ""} ${
        state.channelId === id ? "active" : ""
      }" type="button" data-channel="${id}">
        <div class="av ${avKind}" style="background:${c.color}">${letter}</div>
        <div style="min-width:0">
          <div class="chan-name">${opts.primary ? "频道 · " : ""}${c.name}${c.badge ? ` · ${c.badge}` : ""}</div>
          <div class="chan-prev">${last ? `${last.from}: ${last.text}` : c.sub}</div>
        </div>
        ${unread ? `<span class="badge">${unread}</span>` : ""}
      </button>`;
  };

  const seats = childrenOf(state.teamScope).filter(matchQ);

  let rowsHtml = "";
  if (state.chatTab === "channel") {
    rowsHtml = `
      ${
        matchQ("cursor-workbench")
          ? `<div class="sec">工作台</div>${row("cursor-workbench", { primary: true })}`
          : ""
      }
      <div class="sec">当前频道</div>
      ${matchQ(state.teamScope) ? row(state.teamScope, { primary: true }) : ""}
      ${seats.length ? `<div class="sec">席位私聊</div>${seats.map((id) => row(id, { nested: true })).join("")}` : ""}`;
  } else if (state.chatTab === "dms") {
    const people = Object.keys(CHANNELS)
      .filter((id) => CHANNELS[id].kind === "agent" && matchQ(id))
      .sort((a, b) => CHANNELS[a].order - CHANNELS[b].order);
    rowsHtml = `<div class="sec">全部席位私聊</div>${people.map((id) => row(id)).join("") || `<div class="empty">无匹配</div>`}`;
  } else {
    const unreadIds = Object.keys(state.unread).filter((id) => state.unread[id] && matchQ(id));
    rowsHtml = `<div class="sec">未读</div>${unreadIds.map((id) => row(id)).join("") || `<div class="empty">没有未读</div>`}`;
  }

  const msgs = (state.threads[state.channelId] || [])
    .map(
      (m) => `
      <div class="m ${m.role === "ceo" ? "me" : ""}">
        <div class="m-av">${m.role === "ceo" ? "你" : m.from.slice(0, 1)}</div>
        <div>
          <div class="m-who">${escapeHtml(m.from)}${m.auto ? '<span class="tag-auto">同事互聊</span>' : ""}${
            m.mentions?.length
              ? ` · <span class="tag-mention">@${escapeHtml(m.mentions.join(" @"))}</span>`
              : ""
          } · ${m.at || ""}</div>
          <div class="bubble pre-wrap">${formatMessageHtml(m.text)}</div>
        </div>
      </div>`
    )
    .join("");

  const kindLabel =
    ch.kind === "workbench"
      ? "Cursor Agent SDK · 发到本机工作台文件夹"
      : ch.kind === "project-team"
        ? `项目频道 · cwd ${ch.projectFolder || "项目/…"} · 写隔离`
        : ch.kind === "team" || ch.kind === "human"
          ? "独立 Team 频道"
          : ch.projectId
            ? `项目席 · ${ch.projectTitle || "本项目"}`
            : ch.side === "other"
              ? "暂挂席位 · 一对一"
              : `席位私聊 · 隶属 ${CHANNELS[ch.parent]?.name || "Team"}`;

  const teamSwitcher = switchTeams
    .map((id) => {
      const t = CHANNELS[id];
      const unread = state.unread[id] || 0;
      const on = state.teamScope === id;
      const short =
        t.kind === "project-team"
          ? projectBadge(t.projectTitle || t.badge || "项目")
          : id === "team-review"
            ? "审查委"
            : projectBadge(t.name || id);
      return `
        <button class="team-chip ${on ? "on" : ""}" type="button" data-team-scope="${id}" title="${escapeHtml(
          t.kind === "project-team"
            ? `${t.projectTitle || ""} · Develop 副本`
            : t.system === "review" || t.system
              ? `${t.name}（系统必选）`
              : t.name
        )}">
          <i style="background:${t.color}"></i>
          <span>${escapeHtml(short)}</span>
          ${unread ? `<em>${unread}</em>` : ""}
        </button>`;
    })
    .join("");

  const agentBody = `
    <div class="chat-layout">
      <aside class="chat-list">
        <div class="team-switch">
          <div class="team-switch-label">自组频道 · 审查委必选 · 项目 Develop</div>
          <div class="team-switch-row">${teamSwitcher}</div>
        </div>
        <div class="chat-list-head"><input id="chat-q" placeholder="在当前范围搜索" value="${escapeHtml(state.chatQ)}" /></div>
        <div class="chat-tabs">
          ${[
            ["channel", "本频道"],
            ["dms", "私聊"],
            ["unread", "未读"],
          ]
            .map(
              ([t, label]) =>
                `<button class="tab ${state.chatTab === t ? "active" : ""}" data-chat-tab="${t}">${label}</button>`
            )
            .join("")}
        </div>
        <div class="chat-rows">${rowsHtml || `<div class="empty">无匹配会话</div>`}</div>
      </aside>
      <section class="chat-main">
        <div class="chat-top">
          <div>
            <div class="chat-crumb">${escapeHtml(scope.name)}${scope.badge ? ` · ${escapeHtml(scope.badge)}` : ""} → ${
              ch.id === scope.id
                ? scope.kind === "project-team"
                  ? "Develop 副本"
                  : "Team 频道"
                : escapeHtml(ch.name)
            }</div>
            <h2>${
              ch.kind === "project-team"
                ? `开发团队 · ${escapeHtml(ch.projectTitle || ch.badge || "")}`
                : `${escapeHtml(ch.name)}${ch.badge ? `（${escapeHtml(ch.badge)}）` : ""}`
            }</h2>
            <p>${escapeHtml(ch.sub)} · ${kindLabel}</p>
          </div>
          <div class="chat-top-right">
            ${
              ch.members
                ? `<div class="tags">${ch.members.map((m) => `<span class="tag">${escapeHtml(m)}</span>`).join("")}</div>`
                : ""
            }
            <button class="btn ghost" type="button" data-channel="${state.teamScope}">${
              scope.kind === "project-team" ? "回到本项目 Develop" : "回到 Team 频道"
            }</button>
          </div>
        </div>
        <div class="team-switch main-bar">${teamSwitcher}</div>
        <div class="msgs" id="msgs"><div class="day">今天 · ${escapeHtml(scope.name)}</div>${
          msgs || `<div class="empty">还没有消息，在本频道打个招呼吧</div>`
        }
          ${
            state.typing && state.typing.channelId === state.channelId
              ? `<div class="typing">${escapeHtml(state.typing.from)} 正在输入…</div>`
              : ""
          }
        </div>
        <footer class="composer">
          <div class="composer-card">
            ${state.mentionOpen ? renderMentionMenuHtml() : ""}
            <textarea id="input" rows="1" placeholder="写到「${escapeHtml(ch.name)}」· 输入 @ 提及席位…">${escapeHtml(
              state.draft
            )}</textarea>
            <div class="composer-bar">
              <div class="composer-tools">
                <button class="tool-btn" type="button" data-tool="mention">@ 提及</button>
                <button class="tool-btn" type="button" data-tool="attach">附件</button>
                <button class="tool-btn" type="button" data-tool="task">转任务</button>
              </div>
              <div style="display:flex;gap:10px;align-items:center">
                <span class="composer-hint">${
                  ch.kind === "workbench"
                    ? "Enter 发送 · 走本机 Cursor Agent（单文件夹）"
                    : ch.kind === "project-team" || ch.projectId
                      ? `Enter 发送 · @席位可指定应答 · ${ch.projectFolder || "本项目"}`
                      : "Enter 发送 · 输入 @ 点名席位"
                }</span>
                <button class="send" id="send" ${!state.draft.trim() || state.typing ? "disabled" : ""}>发送</button>
              </div>
            </div>
          </div>
        </footer>
      </section>
    </div>`;

  return agentBody;
}

function dnaStatusLabel(st) {
  if (st === "promoted") return "已晋升";
  if (st === "certified") return "已鉴定";
  return "初始化";
}

function dnaStatusTag(st) {
  if (st === "promoted") return "green";
  if (st === "certified") return "blue";
  return "orange";
}

function renderDna() {
  const genomes = DNA_GENOMES || [];
  const role =
    genomes.find((g) => g.id === state.dnaRoleId) || genomes[0] || null;
  if (role && state.dnaRoleId !== role.id) state.dnaRoleId = role.id;
  const slotId = state.dnaSlotId || "G1";
  const slotBody = role?.slots?.[slotId] || null;
  const statusLab = role ? dnaStatusLabel(role.status) : "—";
  const statusTag = role ? dnaStatusTag(role.status) : "";

  const roleRows = genomes
    .map((g) => {
      const on = role && g.id === role.id;
      return `
        <button class="chan ${on ? "active" : ""}" type="button" data-dna-role="${escapeHtml(g.id)}">
          <div class="av team" style="background:#af52de">${escapeHtml(g.role.slice(0, 1))}</div>
          <div style="min-width:0">
            <div class="chan-name">${escapeHtml(g.role)} <span class="tag ${dnaStatusTag(g.status)}" style="margin-left:4px">${escapeHtml(
              dnaStatusLabel(g.status)
            )}</span></div>
            <div class="chan-prev">${escapeHtml(g.title)}</div>
          </div>
        </button>`;
    })
    .join("");

  const slotChips = DNA_SLOT_META.map(
    (s) => `
      <button type="button" class="chip-btn ${slotId === s.id ? "accent" : ""}" data-dna-slot="${s.id}" title="${escapeHtml(
        s.note
      )}">${s.id} ${escapeHtml(s.label)}</button>`
  ).join("");

  const slotCards = DNA_SLOT_META.map((s) => {
    const body = role?.slots?.[s.id];
    const preview = (body?.text || "").split("\n")[0] || "—";
    return `
      <button type="button" class="dna-slot-card ${slotId === s.id ? "on" : ""}" data-dna-slot="${s.id}">
        <div class="dna-slot-id">${s.id}</div>
        <div>
          <div class="row-title">${escapeHtml(s.label)}</div>
          <div class="row-desc">变异 ${escapeHtml(s.mutate)} · ${escapeHtml(s.note)}</div>
          <div class="row-desc dna-slot-preview">${escapeHtml(preview)}</div>
        </div>
      </button>`;
  }).join("");

  return `
    <div class="pad dna-workbench">
      <div class="card dna-hero" style="margin-bottom:12px">
        <div>
          <div class="meta">公司层 · Develop 基因组正本 · opc-demo/AgentTeam/Develop</div>
          <h2 style="font-size:22px;margin-top:4px">DNA 工作台</h2>
          <p class="strat-mission">看清每位数字员工的 G1–G5；改动走审查进化委（L1 常规 / L2 高危你拍板）。裁判 criteria 不进基因组。</p>
        </div>
        <div class="strat-actions">
          <button class="btn ghost" type="button" data-page="chat" data-open-dm="ch-dev">开发编队</button>
          <button class="btn ghost" type="button" data-page="org">组织</button>
          <button class="btn primary" type="button" data-page="review">全流程审阅</button>
        </div>
      </div>

      <div class="card" style="margin-bottom:12px">
        <h2>基因工程四步</h2>
        <div class="meta">无鉴定不算基因工程 · 与 YiAgent 进度树同构</div>
        <div class="dna-pipeline">
          ${DNA_PIPELINE.map(
            (p) => `
            <div class="dna-pipe-step">
              <div class="dna-pipe-n">${p.n}</div>
              <div>
                <div class="row-title">${escapeHtml(p.title)}</div>
                <div class="row-desc">${escapeHtml(p.note)}</div>
              </div>
            </div>`
          ).join("")}
        </div>
      </div>

      <div class="card" style="margin-bottom:12px">
        <h2>G1–G5 槽位</h2>
        <div class="meta">4 本体 + 1 经验叠加层 · 按槽可评分才叫基因分区</div>
        <div class="seg" style="margin-top:10px">${slotChips}</div>
      </div>

      <div class="proj-detail-split" style="margin-bottom:12px">
        <div class="card" style="min-width:0">
          <h2>公司 Develop 基因组</h2>
          <div class="meta">${genomes.length} 席 · 项目内可有副本，不串目录</div>
          <div class="chat-rows" style="margin-top:10px">${roleRows || `<div class="empty">暂无基因组</div>`}</div>
        </div>
        <div class="card" style="min-width:0">
          ${
            role
              ? `
          <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap">
            <div>
              <h2>${escapeHtml(role.role)}</h2>
              <div class="meta">${escapeHtml(role.title)} · <span class="tag ${statusTag}">${escapeHtml(
                  statusLab
                )}</span></div>
              <div class="meta" style="margin-top:4px"><code class="branch-code">${escapeHtml(
                role.path
              )}/genome.json</code></div>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              ${
                role.agentId
                  ? `<button class="btn ghost" type="button" data-page="chat" data-open-dm="${dmIdForAgent(
                      role.agentId
                    )}">私聊席位</button>`
                  : ""
              }
              <button class="btn ghost" type="button" data-page="chat" data-open-dm="dm-ag-gene">问基因席</button>
            </div>
          </div>
          <div class="dna-slot-grid" style="margin-top:12px">${slotCards}</div>
          <div class="dna-slot-detail" style="margin-top:14px">
            <div class="sec">${escapeHtml(slotId)} · ${escapeHtml(slotBody?.label || "")}</div>
            <pre class="dna-pre">${escapeHtml(slotBody?.text || "该槽暂无正文")}</pre>
          </div>`
              : `<div class="empty">请选择左侧角色</div>`
          }
        </div>
      </div>

      <div class="card">
        <h2>审查进化委 · 管审改入口</h2>
        <div class="meta">L1 常规由委直接改（留痕可回滚）· L2 高危须你批准</div>
        <div class="list" style="margin-top:10px">
          ${DNA_GOVERNANCE.map(
            (g) => `
            <div class="row">
              <div>
                <div class="row-title">${escapeHtml(g.name)}</div>
                <div class="row-desc">${escapeHtml(g.note)}</div>
              </div>
              <button class="btn ghost" type="button" data-page="chat" data-open-dm="${dmIdForAgent(
                g.agentId
              )}">打开</button>
            </div>`
          ).join("")}
        </div>
      </div>
    </div>`;
}

function renderOrg() {
  const focusId = state.orgFocusChannelId || "team-review";
  const focus = state.channelRoster.find((c) => c.id === focusId) || state.channelRoster[0];
  const channelsHtml = state.channelRoster
    .slice()
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .map((c) => {
      const on = c.id === focus?.id;
      const n = (c.memberIds || []).length;
      return `
        <button class="chan ${on ? "active" : ""}" type="button" data-org-channel="${c.id}">
          <div class="av team" style="background:${c.color || "#8e8e93"}">#</div>
          <div style="min-width:0">
            <div class="chan-name">${escapeHtml(c.name)}${
              c.system === "review" ? '<span class="tag purple" style="margin-left:6px">必选</span>' : ""
            }</div>
            <div class="chan-prev">${n} 名成员 · ${escapeHtml(c.sub || "")}</div>
          </div>
        </button>`;
    })
    .join("");

  const memberSet = new Set(focus?.memberIds || []);
  const memberPick = state.agentRoster
    .map((a) => {
      const checked = memberSet.has(a.id);
      const lockedOut = focus && isReviewChannel(focus.id) && a.system && checked;
      return `
        <label class="org-member-row" data-org-toggle-member="${a.id}" data-org-in-channel="${
          focus?.id || ""
        }">
          <input type="checkbox" ${checked ? "checked" : ""} ${lockedOut ? "disabled" : ""} />
          <span class="dot" style="background:${a.color}">${escapeHtml(a.initial || a.name.slice(0, 1))}</span>
          <span>
            <strong>${escapeHtml(a.name)}</strong>
            <span class="meta">${escapeHtml(a.kind === "human" ? "真人" : "Agent")}${
              a.developRole ? ` · Develop/${a.developRole}` : ""
            }${a.system ? " · 系统" : ""}</span>
          </span>
        </label>`;
    })
    .join("");

  const agentsHtml = state.agentRoster
    .map(
      (a) => `
      <div class="row">
        <div>
          <div class="row-title">${escapeHtml(a.name)}${a.system ? ' <span class="tag purple">系统</span>' : ""}</div>
          <div class="row-desc">${escapeHtml(a.sub || "")}${
            a.developRole ? ` · 基因组 ${escapeHtml(a.developRole)}` : ""
          }</div>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn ghost" type="button" data-page="chat" data-open-dm="${dmIdForAgent(a.id)}">私聊</button>
          ${
            a.system
              ? ""
              : `<button class="btn ghost" type="button" data-org-del-agent="${a.id}">删除</button>`
          }
        </div>
      </div>`
    )
    .join("");

  return `
    <div class="pad">
      <div class="card" style="margin-bottom:14px">
        <h2>组织</h2>
        <div class="meta" style="margin-top:6px">DEC-046 · 自由添加 Agent/真人组成频道；审查进化委员会为系统必选，不可删除</div>
        <div class="chat-tabs" style="margin-top:12px">
          <button class="tab ${state.orgTab === "channels" ? "active" : ""}" type="button" data-org-tab="channels">频道</button>
          <button class="tab ${state.orgTab === "agents" ? "active" : ""}" type="button" data-org-tab="agents">成员库</button>
        </div>
      </div>
      ${
        state.orgTab === "agents"
          ? `<div class="card">
              <div style="display:flex;justify-content:space-between;gap:10px;align-items:center">
                <h2>成员库</h2>
                <button class="btn primary" type="button" id="btn-org-add-agent">添加 Agent</button>
              </div>
              <div class="list" style="margin-top:10px">${agentsHtml || `<div class="empty">暂无成员</div>`}</div>
            </div>`
          : `<div class="proj-detail-split">
              <div class="card" style="min-width:0">
                <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px">
                  <h2>频道</h2>
                  <button class="btn primary" type="button" id="btn-org-add-channel">新建频道</button>
                </div>
                <div class="chat-rows">${channelsHtml}</div>
              </div>
              <div class="card" style="min-width:0">
                ${
                  focus
                    ? `<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">
                        <div style="flex:1;min-width:0">
                          <h2>${escapeHtml(focus.name)}</h2>
                          <div class="meta">${
                            focus.system === "review"
                              ? "系统必选 · 核心席不可移出"
                              : "自组频道 · 可改名 / 改成员 / 删除"
                          }</div>
                          ${
                            focus.system === "review"
                              ? ""
                              : `<input id="org-ch-name" class="proj-form" style="margin-top:10px;width:100%" value="${escapeHtml(
                                  focus.name
                                )}" />`
                          }
                        </div>
                        <div style="display:flex;flex-direction:column;gap:6px">
                          <button class="btn primary" type="button" data-page="chat" data-open-dm="${focus.id}">进入频道</button>
                          ${
                            focus.system === "review"
                              ? ""
                              : `<button class="btn ghost" type="button" id="btn-org-save-ch">保存名称</button>
                                 <button class="btn ghost" type="button" data-org-del-channel="${focus.id}">删除频道</button>`
                          }
                        </div>
                      </div>
                      <h3 style="margin:16px 0 8px;font-size:14px">频道成员</h3>
                      <div class="org-member-list">${memberPick}</div>`
                    : `<div class="empty">请选择频道</div>`
                }
              </div>
            </div>`
      }
    </div>`;
}

function kbDocs() {
  const q = state.kbQ.trim().toLowerCase();
  return state.kb.filter((d) => {
    if (state.kbPlane === "agent") {
      if (d.visibility !== "ai_ok" && d.visibility !== "both") return false;
    }
    if (state.kbFolder === "deny") {
      if (d.visibility !== "deny_ai") return false;
    } else if (state.kbFolder !== "all" && d.folder !== state.kbFolder) {
      return false;
    }
    if (state.kbStatus && d.visibility !== state.kbStatus) return false;
    if (!q) return true;
    const blob = `${d.title} ${d.who} ${d.humanBody || ""} ${d.agentBody || ""}`.toLowerCase();
    return blob.includes(q);
  });
}

function visTagClass(v) {
  if (v === "ai_ok" || v === "both") return "green";
  if (v === "human_only") return "orange";
  if (v === "deny_ai") return "purple";
  return "";
}

function tierTagClass(t) {
  if (t === "S4" || t === "S3") return "green";
  if (t === "S2") return "blue";
  if (t === "S1" || t === "S0") return "orange";
  return "";
}

function renderProvenance(doc, plane) {
  const p = doc.provenance;
  if (!p) return "";
  const certified = p.certifiedBy
    ? `已认证 · ${p.certifiedBy} · ${p.certifiedAt}`
    : "未认证 · 不可挂载为正式依据";
  if (plane === "agent") {
    return `
      <div class="prov-box agent">
        <div class="sec">引用溯源（可挂载字段）</div>
        <div class="tags">
          <span class="tag ${tierTagClass(p.tier)}">${TIER_LABEL[p.tier] || p.tier}</span>
          <span class="tag">v${escapeHtml(String(p.version))}</span>
        </div>
        <div class="prov-line mono">${escapeHtml(p.locator)}</div>
        <div class="prov-note">Agent 只拿 locator / tier / 切片 · 不拿审计全文</div>
      </div>`;
  }
  return `
    <div class="prov-box">
      <div class="sec">溯源</div>
      <div class="tags" style="margin-bottom:8px">
        <span class="tag ${tierTagClass(p.tier)}">${TIER_LABEL[p.tier] || p.tier}</span>
        <span class="tag">版本 ${escapeHtml(String(p.version))}</span>
      </div>
      <div class="prov-line"><span>定位</span><code>${escapeHtml(p.locator)}</code></div>
      <div class="prov-line"><span>认证</span>${escapeHtml(certified)}</div>
    </div>`;
}

function renderTrail(doc, plane) {
  const trail = doc.trail || [];
  if (plane === "agent") {
    return `<div class="trail-box muted">审计时间线仅人看 · Agent 不得装载 trail 全文</div>`;
  }
  if (!trail.length) return "";
  return `
    <div class="trail-box">
      <div class="sec">审计时间线 · 仅人看</div>
      <ol class="trail">
        ${trail
          .map(
            (e) => `
          <li>
            <div class="trail-at">${escapeHtml(e.at)}</div>
            <div>
              <div class="trail-ev"><strong>${escapeHtml(e.event)}</strong> · ${escapeHtml(e.actor)}</div>
              <div class="trail-detail">${escapeHtml(e.detail)}</div>
            </div>
          </li>`
          )
          .join("")}
      </ol>
    </div>`;
}

function renderKb() {
  if (SITE_GATE === "yiagent") {
    if (typeof KbSpecs === "undefined") {
      return `<div class="pad"><div class="card"><div class="empty">知识库规范脚本未加载</div></div></div>`;
    }
    const tab =
      state.kbEditorTab === "manage" || state.kbEditorTab === "scoring"
        ? state.kbEditorTab
        : "taxonomy";
    state.kbEditorTab = tab;
    return KbSpecs.render(tab);
  }
  const docs = kbDocs();
  if (!docs.find((d) => d.id === state.kbDocId)) state.kbDocId = docs[0]?.id || null;
  const doc = state.kb.find((d) => d.id === state.kbDocId);
  const humanCount = state.kb.length;
  const agentCount = state.kb.filter((k) => k.visibility === "ai_ok" || k.visibility === "both").length;
  const denyCount = state.kb.filter((k) => k.visibility === "deny_ai").length;

  const previewBody =
    !doc
      ? ""
      : state.kbPlane === "agent"
        ? doc.agentBody || "（本条未对 Agent 开放 · 无挂载投影）"
        : doc.humanBody || "";

  const canPublish = doc && (doc.visibility === "human_only" || !doc.visibility);
  const folders =
    state.kbPlane === "agent"
      ? KB_FOLDERS.filter((f) => f.id !== "deny" && f.id !== "draft")
      : KB_FOLDERS;

  return `
    <div class="kb-layout">
      <aside class="kb-side">
        <h3>平面</h3>
        <button class="folder plane ${state.kbPlane === "human" ? "on" : ""}" type="button" data-kb-plane="human">
          <strong>人看</strong>
          <span>公司资料 · 可厚</span>
        </button>
        <button class="folder plane ${state.kbPlane === "agent" ? "on" : ""}" type="button" data-kb-plane="agent">
          <strong>Agent 看</strong>
          <span>可挂载 · 须薄</span>
        </button>
        <div class="kb-plane-note">同一真相 · 两套投影<br/>未标注默认仅人看</div>
        <h3 style="margin-top:16px">文件夹</h3>
        ${folders
          .map(
            (f) =>
              `<button class="folder ${state.kbFolder === f.id ? "on" : ""}" type="button" data-kb-folder="${f.id}">${f.label}</button>`
          )
          .join("")}
      </aside>
      <section class="kb-main">
        <div class="kb-banner ${state.kbPlane === "agent" ? "agent" : "human"}">
          ${
            state.kbPlane === "human"
              ? `<div><strong>人平面</strong> · 公司资料存档（给人读的长文 / PDF / 草稿）</div>
                 <div class="kb-banner-meta">人 ${humanCount} · 其中已给 Agent ${agentCount} · 硬禁 ${denyCount}</div>`
              : `<div><strong>Agent 平面</strong> · 仅显示已允许挂载的切片（ai_ok / both）</div>
                 <div class="kb-banner-meta">可挂载 ${agentCount} 条 · Assembler 不吃「仅人看 / 禁给 AI」</div>`
          }
        </div>
        <div class="kb-toolbar">
          <div class="kb-search"><input id="kb-q" placeholder="搜索标题 / 作者 / 内容" value="${escapeHtml(state.kbQ)}" /></div>
          <button class="btn ghost" type="button" id="btn-kb-upload">上传（人平面）</button>
          <button class="btn ghost" type="button" id="btn-kb-new2">新建（默认仅人）</button>
          <button class="btn primary" type="button" id="btn-kb-publish" ${!canPublish ? "disabled" : ""}>认证发布给 Agent</button>
        </div>
        <div class="kb-docs">
          <div class="pill-row">
            ${[
              ["", "全部可见性"],
              ["human_only", "仅人看"],
              ["ai_ok", "已给 Agent"],
              ["both", "人与 Agent"],
              ["deny_ai", "禁给 AI"],
            ]
              .map(
                ([val, label]) =>
                  `<button class="pill ${
                    (!state.kbStatus && !val) || state.kbStatus === val ? "on" : ""
                  }" data-kb-status="${val}">${label}</button>`
              )
              .join("")}
          </div>
          ${
            docs
              .map((d) => {
                const agentOpen = d.visibility === "ai_ok" || d.visibility === "both";
                return `
              <button class="doc ${state.kbDocId === d.id ? "on" : ""}" type="button" data-kb-doc="${d.id}">
                <div>
                  <div class="doc-title">${d.title}</div>
                  <div class="doc-meta">${d.who} · ${d.updated}${
                    state.kbPlane === "agent" ? " · 切片投影" : " · 人用全文"
                  }${d.provenance ? ` · ${d.provenance.tier}` : ""}</div>
                </div>
                <div class="doc-badges">
                  <span class="tag ${visTagClass(d.visibility)}">${VIS_LABEL[d.visibility] || d.visibility}</span>
                  ${
                    d.provenance
                      ? `<span class="tag ${tierTagClass(d.provenance.tier)}">${d.provenance.tier}</span>`
                      : ""
                  }
                  ${agentOpen ? `<span class="tag blue">可挂载</span>` : `<span class="tag">不进模型</span>`}
                </div>
              </button>`;
              })
              .join("") ||
            `<div class="empty">${
              state.kbPlane === "agent" ? "当前没有可挂载切片。到「人看」选资料后点「认证发布给 Agent」。" : "此文件夹暂无资料"
            }</div>`
          }
        </div>
      </section>
      <aside class="kb-preview">
        ${
          doc
            ? `<h3>${state.kbPlane === "agent" ? "Agent 投影预览" : "人用预览"}</h3>
               <div class="doc-title" style="font-size:18px;margin-bottom:6px">${doc.title}</div>
               <div class="doc-meta" style="margin-bottom:10px">${doc.who} · ${doc.updated}</div>
               <div class="tags" style="margin-bottom:12px">
                 <span class="tag ${visTagClass(doc.visibility)}">${VIS_LABEL[doc.visibility]}</span>
                 <span class="tag">${state.kbPlane === "agent" ? "agent_projection" : "human_projection"}</span>
               </div>
               ${renderProvenance(doc, state.kbPlane)}
               <div class="body">${escapeHtml(previewBody)}</div>
               ${
                 state.kbPlane === "human" && doc.agentBody
                   ? `<div class="kb-compare">
                        <div class="sec">对照 · Agent 若已开放将看到</div>
                        <div class="body thin">${escapeHtml(doc.agentBody)}</div>
                      </div>`
                   : ""
               }
               ${
                 state.kbPlane === "agent" && doc.humanBody
                   ? `<div class="kb-compare">
                        <div class="sec">对照 · 人平面仍可读更厚正文</div>
                        <button class="btn ghost" type="button" data-kb-plane="human" data-kb-doc="${doc.id}">切换到人看全文</button>
                      </div>`
                   : ""
               }
               ${renderTrail(doc, state.kbPlane)}
               <div class="actions">
                 <button class="btn ghost" type="button" id="btn-kb-edit">编辑</button>
                 <button class="btn ghost" type="button" id="btn-kb-share">分享链接（人）</button>
                 <button class="btn primary" type="button" id="btn-kb-publish2" ${!canPublish ? "disabled" : ""}>认证发布给 Agent</button>
               </div>`
            : `<div class="empty">选择一篇资料</div>`
        }
      </aside>
    </div>`;
}

function renderCrm() {
  return `
    <div class="pad"><div class="card">
      <h2>客户管道</h2>
      <div class="meta">销售交付主跟 · Growth 可供料线索</div>
      <div style="margin-bottom:12px;display:flex;gap:8px">
        <button class="btn primary" type="button" id="btn-crm-add">新建客户</button>
        <button class="btn ghost" type="button" data-page="chat" data-open-dm="ch-sales">打开销售交付会话</button>
      </div>
      <table class="table">
        <thead><tr><th>客户</th><th>阶段</th><th>跟进</th><th>金额</th><th>下一步</th></tr></thead>
        <tbody>
          ${state.crm
            .map(
              (c) =>
                `<tr><td><strong>${c.name}</strong></td><td><span class="tag blue">${c.stage}</span></td><td>${c.owner}</td><td>${c.amount}</td><td>${c.next}</td></tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div></div>`;
}

function categoryLabel(c) {
  if (c === "战略") return "战略项目";
  if (c === "客户") return "客户项目";
  return c || "未分类";
}

async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.projects = data.projects || [];
    state.projectsLoaded = true;
    state.projectsError = null;
    if (!state.projects.find((p) => p.id === state.projectId)) {
      state.projectId = state.projects[0]?.id || null;
    }
  } catch (e) {
    state.projectsError = String(e.message || e);
    state.projectsLoaded = false;
    toast("项目加载失败 · 检查 projects-api");
  }
}

async function createProjectApi(payload) {
  const res = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.project;
}

async function patchProjectApi(id, patch) {
  const res = await fetch(`/api/projects/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.project;
}

async function archiveCurrentProject() {
  const id = state.projectId;
  const p = state.projects.find((x) => x.id === id);
  if (!id || !p) return;
  if (p.status === "已归档") return;
  if (!window.confirm(`确认归档项目「${p.title}」？\n可在筛选「已归档」中找回并恢复。`)) return;
  try {
    await patchProjectApi(id, { status: "已归档" });
    await loadProjects();
    state.projectOpen = false;
    state.projectEditing = false;
    state.projectId = null;
    toast("项目已归档");
    render();
  } catch (e) {
    toast("归档失败 · " + (e.message || e));
  }
}

async function unarchiveCurrentProject() {
  const id = state.projectId;
  const p = state.projects.find((x) => x.id === id);
  if (!id || !p || p.status !== "已归档") return;
  try {
    await patchProjectApi(id, { status: "进行中" });
    await loadProjects();
    state.projectOpen = true;
    state.projectId = id;
    toast("已恢复为进行中");
    render();
  } catch (e) {
    toast("恢复失败 · " + (e.message || e));
  }
}

async function deleteProjectApi(id) {
  const res = await fetch(`/api/projects/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function deleteCurrentProject() {
  const id = state.projectId;
  const p = state.projects.find((x) => x.id === id);
  if (!id || !p) return;
  if (
    !window.confirm(
      `确认永久删除项目「${p.title}」？\n库中记录将删除，不可恢复。\n（若只需隐藏，请用「归档」。）`
    )
  ) {
    return;
  }
  try {
    await deleteProjectApi(id);
    clearProjectNotes(id);
    state.projectOpen = false;
    state.projectEditing = false;
    state.projectId = null;
    await loadProjects();
    toast("项目已永久删除");
    render();
  } catch (e) {
    toast("删除失败 · " + (e.message || e));
  }
}

async function newProject() {
  try {
    const cat = state.projectCategory === "客户" ? "客户" : "战略";
    const p = await createProjectApi({
      title: "未命名项目",
      category: cat,
      status: "进行中",
      owner: "你",
      team: cat === "客户" ? "销售交付" : "战略委员会",
      progress: 0,
      due: "待定",
      risk: "新建 · 待补目标",
      channel: cat === "客户" ? "ch-sales" : "ch-strategy",
    });
    await loadProjects();
    state.projectId = p.id;
    state.projectOpen = true;
    state.page = "projects";
    toast(`已新建${categoryLabel(cat)} · 已落库`);
    render();
  } catch (e) {
    toast("新建失败 · " + (e.message || e));
  }
}

function categoryTagClass(c) {
  if (c === "战略") return "purple";
  if (c === "客户") return "blue";
  return "";
}

function taskStatusTag(s) {
  if (s === "进行中") return "blue";
  if (s === "等人" || s === "受阻") return "orange";
  if (s === "已完成") return "green";
  return "";
}

function renderProjectEdit(raw) {
  const cur = enrichProject(raw);
  if (!cur) return `<div class="pad"><div class="card"><div class="empty">未找到项目</div></div></div>`;
  const opt = (val, label, curVal) =>
    `<option value="${escapeHtml(val)}" ${val === curVal ? "selected" : ""}>${escapeHtml(label)}</option>`;
  return `
    <div class="pad proj-detail-page">
      <div class="proj-detail-nav">
        <button class="chip-btn" type="button" id="btn-project-edit-cancel2">← 取消编辑</button>
      </div>
      <div class="card">
        <h2>编辑项目</h2>
        <div class="meta">标题/状态/进度等落库 · 目标与摘要本机记住</div>
        <form id="proj-edit-form" class="proj-form" onsubmit="return false;">
          <label class="field"><span>标题</span><input id="pe-title" type="text" value="${escapeHtml(cur.title)}" required /></label>
          <div class="field-row">
            <label class="field"><span>类型</span>
              <select id="pe-category">
                ${opt("战略", "战略项目", cur.category)}
                ${opt("客户", "客户项目", cur.category)}
              </select>
            </label>
            <label class="field"><span>状态</span>
              <select id="pe-status">
                ${opt("进行中", "进行中", cur.status)}
                ${opt("等人", "等人", cur.status)}
                ${opt("已完成", "已完成", cur.status)}
              </select>
            </label>
          </div>
          <label class="field"><span>目标</span><textarea id="pe-goal" rows="3">${escapeHtml(cur.goal)}</textarea></label>
          <label class="field"><span>摘要说明</span><textarea id="pe-summary" rows="2">${escapeHtml(cur.summary)}</textarea></label>
          <label class="field"><span>当前风险</span><textarea id="pe-risk" rows="2">${escapeHtml(cur.risk || "")}</textarea></label>
          <div class="field-row">
            <label class="field"><span>进度 %</span><input id="pe-progress" type="number" min="0" max="100" value="${Number(cur.progress) || 0}" /></label>
            <label class="field"><span>截止</span><input id="pe-due" type="text" value="${escapeHtml(cur.due || "")}" placeholder="如 本周 / 2026 H2" /></label>
          </div>
          <div class="field-row">
            <label class="field"><span>Owner</span><input id="pe-owner" type="text" value="${escapeHtml(cur.owner || "")}" /></label>
            <label class="field"><span>负责 Team</span><input id="pe-team" type="text" value="${escapeHtml(cur.team || "")}" /></label>
          </div>
          <div class="field-row">
            <label class="field"><span>客户</span><input id="pe-customer" type="text" value="${escapeHtml(cur.customer || "")}" placeholder="客户项目可填" /></label>
            <label class="field"><span>战略柱/线</span><input id="pe-pillar" type="text" value="${escapeHtml(cur.pillar || "")}" placeholder="如 ASE 平台" /></label>
          </div>
          <label class="field"><span>消息通道</span>
            <select id="pe-channel">${channelSelectOptions(cur.channel)}</select>
          </label>
          <div class="proj-form-actions">
            <button class="btn primary" type="button" id="btn-project-edit-save2">保存</button>
            <button class="btn ghost" type="button" id="btn-project-edit-cancel3">取消</button>
          </div>
        </form>
      </div>
    </div>`;
}

async function saveProjectEdit() {
  const id = state.projectId;
  if (!id) return;
  const title = ($("pe-title")?.value || "").trim();
  if (!title) {
    toast("标题不能为空");
    return;
  }
  let progress = parseInt($("pe-progress")?.value ?? "0", 10);
  if (Number.isNaN(progress)) progress = 0;
  progress = Math.max(0, Math.min(100, progress));
  const payload = {
    title,
    category: $("pe-category")?.value || "战略",
    status: $("pe-status")?.value || "进行中",
    owner: ($("pe-owner")?.value || "").trim(),
    team: ($("pe-team")?.value || "").trim(),
    progress,
    due: ($("pe-due")?.value || "").trim(),
    risk: normalizeMultiline($("pe-risk")?.value || ""),
    customer: ($("pe-customer")?.value || "").trim(),
    pillar: ($("pe-pillar")?.value || "").trim(),
    channel: resolveChannelAlias($("pe-channel")?.value || "ch-strategy"),
  };
  try {
    await patchProjectApi(id, payload);
    saveProjectNotes(id, {
      goal: $("pe-goal")?.value || "",
      summary: $("pe-summary")?.value || "",
    });
    await loadProjects();
    state.projectEditing = false;
    state.projectOpen = true;
    state.projectId = id;
    toast("项目已保存 · 已落库");
    render();
  } catch (e) {
    toast("保存失败 · " + (e.message || e));
  }
}

function renderProjectDetail(raw) {
  if (state.projectEditing) return renderProjectEdit(raw);
  const cur = enrichProject(raw);
  if (!cur) return `<div class="pad"><div class="card"><div class="empty">未找到项目</div></div></div>`;
  return `
    <div class="pad proj-detail-page">
      <div class="proj-detail-nav">
        <button class="chip-btn" type="button" id="btn-project-back2">${
          SITE_GATE === "yiagent" ? "← 项目进度" : "← 返回看板"
        }</button>
        <button class="chip-btn" type="button" data-open-progress="${escapeHtml(cur.id)}">${
          SITE_GATE === "yiagent" ? "进度树" : "进度表"
        }</button>
        ${
          SITE_GATE === "yiagent"
            ? `<button class="btn primary" type="button" data-page="chat">工作台</button>`
            : ""
        }
        <button class="${SITE_GATE === "yiagent" ? "chip-btn" : "btn primary"}" type="button" id="btn-project-edit2">编辑</button>
        ${
          SITE_GATE === "yiagent"
            ? ""
            : cur.status === "已归档"
              ? `<button class="btn ghost" type="button" id="btn-project-unarchive">恢复</button>`
              : `<button class="btn ghost" type="button" id="btn-project-archive">归档</button>`
        }
        ${
          SITE_GATE === "yiagent"
            ? ""
            : `<button class="btn ghost" type="button" id="btn-project-del">删除</button>`
        }
      </div>
      <div class="proj-detail-split">
        <div class="proj-detail-main">
          <div class="card proj-detail-hero">
            <div class="tags" style="margin-bottom:10px">
              <span class="tag ${categoryTagClass(cur.category)}">${categoryLabel(cur.category)}</span>
              <span class="tag ${
                cur.status === "进行中"
                  ? "blue"
                  : cur.status === "等人"
                    ? "orange"
                    : cur.status === "已归档"
                      ? ""
                      : "green"
              }">${cur.status}</span>
              <span class="tag">截止 ${escapeHtml(cur.due || "待定")}</span>
              ${cur.pillar ? `<span class="tag">${escapeHtml(cur.pillar)}</span>` : ""}
            </div>
            <h2>${escapeHtml(cur.title)}</h2>
            <div class="meta">${escapeHtml(cur.team)} · Owner ${escapeHtml(cur.owner)}${
              cur.customer ? ` · 客户 ${escapeHtml(cur.customer)}` : ""
            }</div>
            <p class="proj-goal pre-wrap">${escapeHtml(cur.goal)}</p>
            ${cur.summary ? `<div class="row-desc pre-wrap" style="margin-top:6px">${escapeHtml(cur.summary)}</div>` : ""}
            <div class="bar lg" style="margin-top:14px"><i style="width:${cur.progress}%"></i></div>
            <div class="proj-meta" style="margin-top:8px">进度 ${cur.progress}%</div>
          </div>
          <div class="grid-2" style="margin-top:14px">
            <div class="card">
              <h2>当前风险</h2>
              <div class="row-desc pre-wrap" style="margin-top:8px;line-height:1.5">${escapeHtml(cur.risk || "暂无")}</div>
            </div>
            <div class="card">
              <h2>责任与通道</h2>
              <div class="list" style="margin-top:8px">
                <div class="row"><div><div class="row-title">负责 Team</div><div class="row-desc">${escapeHtml(cur.team)}</div></div></div>
                <div class="row"><div><div class="row-title">Owner</div><div class="row-desc">${escapeHtml(cur.owner)}</div></div></div>
                <div class="row"><div><div class="row-title">消息通道</div><div class="row-desc">${escapeHtml(cur.channel || "—")}</div></div></div>
                <div class="row"><div><div class="row-title">工作台文件夹</div><div class="row-desc"><code class="branch-code">${escapeHtml(
                  cur.folder || `项目/${cur.title}`
                )}</code><br/><span class="meta">桌面 opc/ 下 · Agent cwd 可读</span></div></div></div>
              </div>
            </div>
          </div>
          ${renderProjectRepoCard(cur)}
          ${renderProjectChannelCard(cur)}
          <div class="card" style="margin-top:14px">
            <h2>操作</h2>
            <div class="list proj-actions" style="margin-top:10px">
              <button class="btn primary" type="button" data-open-progress="${escapeHtml(cur.id)}">打开进度表</button>
              <button class="btn ghost" type="button" id="btn-project-edit3">编辑项目细节</button>
              ${
                cur.status === "已归档"
                  ? `<button class="btn ghost" type="button" id="btn-project-unarchive2">从归档恢复</button>`
                  : `<button class="btn ghost" type="button" id="btn-project-archive2">归档项目</button>`
              }
              <button class="btn ghost" type="button" id="btn-project-del2">永久删除</button>
              <button class="btn ghost" data-page="chat" data-open-dm="${escapeHtml(
                resolveChannelAlias(cur.channel || "ch-dev")
              )}">在消息里跟进（登记通道）</button>
              ${
                cur.category === "战略"
                  ? `<button class="btn ghost" type="button" data-page="strategy">看战略承接</button>`
                  : `<button class="btn ghost" type="button" data-page="crm">看客户管道</button>`
              }
              ${
                cur.status !== "已完成" && cur.status !== "已归档"
                  ? `<button class="btn ghost" type="button" data-project-status="已完成" data-project-id="${cur.id}">标为已完成</button>`
                  : ""
              }
              ${
                cur.status === "进行中"
                  ? `<button class="btn ghost" type="button" data-project-status="等人" data-project-id="${cur.id}">标为等人</button>`
                  : ""
              }
              ${
                cur.status === "等人"
                  ? `<button class="btn ghost" type="button" data-project-status="进行中" data-project-id="${cur.id}">标为进行中</button>`
                  : ""
              }
            </div>
          </div>
        </div>
        ${renderProjectSideRail(cur)}
      </div>
    </div>`;
}

function renderProjects() {
  if (!state.projectsLoaded && !state.projects.length) {
    return `<div class="pad"><div class="card"><div class="empty">${
      state.projectsError ? "项目库不可用 · " + escapeHtml(state.projectsError) : "正在加载项目…"
    }</div></div></div>`;
  }
  if (state.projectOpen) {
    const cur = state.projects.find((p) => p.id === state.projectId);
    if (!cur) {
      state.projectOpen = false;
    } else {
      return renderProjectDetail(cur);
    }
  }

  const statusFilters = ["全部", "进行中", "等人", "已完成", "已归档"];
  const categoryFilters = [
    { id: "全部", label: "全部类型" },
    { id: "战略", label: "战略项目" },
    { id: "客户", label: "客户项目" },
  ];
  const list = state.projects.filter((p) => {
    if (state.projectCategory !== "全部" && p.category !== state.projectCategory) return false;
    if (state.projectFilter === "全部") {
      if (p.status === "已归档") return false;
      return true;
    }
    if (p.status !== state.projectFilter) return false;
    return true;
  });
  const activeProjects = state.projects.filter((p) => p.status !== "已归档");
  const stratN = activeProjects.filter((p) => p.category === "战略").length;
  const custN = activeProjects.filter((p) => p.category === "客户").length;
  const archivedN = state.projects.filter((p) => p.status === "已归档").length;

  const col = (status) => {
    const items = list.filter((p) => p.status === status);
    return `
      <div class="board-col">
        <div class="board-col-h">${status}<span>${items.length}</span></div>
        ${items
          .map(
            (p) => `
          <button class="proj-card" type="button" data-project-open="${p.id}">
            <div class="proj-cat"><span class="tag ${categoryTagClass(p.category)}">${categoryLabel(p.category)}</span></div>
            <div class="proj-title">${escapeHtml(p.title)}</div>
            <div class="proj-meta">${p.customer ? escapeHtml(p.customer) + " · " : ""}${escapeHtml(p.team)} · ${escapeHtml(p.owner)}</div>
            <div class="bar"><i style="width:${p.progress}%"></i></div>
            <div class="proj-foot"><span>${p.progress}%</span><span>${escapeHtml(p.due || "")}</span><span class="proj-open-hint">打开详情</span></div>
          </button>`
          )
          .join("") || `<div class="empty" style="padding:18px 8px">无</div>`}
      </div>`;
  };

  return `
    <div class="pad">
      <div class="toolbar-row wrap">
        <div class="pill-row" style="margin:0">
          ${categoryFilters
            .map(
              (f) =>
                `<button class="pill ${state.projectCategory === f.id ? "on" : ""}" data-project-category="${f.id}">${f.label}${
                  f.id === "战略" ? ` ${stratN}` : f.id === "客户" ? ` ${custN}` : ""
                }</button>`
            )
            .join("")}
        </div>
        <div class="pill-row" style="margin:0">
          ${statusFilters
            .map(
              (f) =>
                `<button class="pill ${state.projectFilter === f ? "on" : ""}" data-project-filter="${f}">${f}${
                  f === "已归档" && archivedN ? ` ${archivedN}` : ""
                }</button>`
            )
            .join("")}
        </div>
        <button class="btn primary" type="button" id="btn-project-new">新建项目</button>
      </div>
      <div class="meta" style="margin:0 0 12px">${
        state.projectFilter === "已归档"
          ? "已归档项目仍保留在库中 · 打开后可恢复"
          : "点卡片打开项目详情（目标 · 任务 · 检查点 · 操作）·「全部」不含已归档"
      }</div>
      <div class="board">
        ${
          state.projectFilter === "已归档"
            ? col("已归档")
            : `${col("进行中")}${col("等人")}${col("已完成")}`
        }
      </div>
    </div>`;
}

function renderStrategyProjectRows(pred) {
  const rows = state.projects.filter((p) => p.status !== "已完成" && p.status !== "已归档" && pred(p));
  if (!rows.length) return `<div class="empty">暂无</div>`;
  return rows
    .map(
      (p) => `
    <div class="row">
      <div>
        <div class="row-title">${escapeHtml(p.title)}</div>
        <div class="row-desc">战略项目 · ${escapeHtml(p.pillar || p.team)} · ${p.progress}% · ${escapeHtml(p.status)}</div>
      </div>
      <button class="btn ghost" data-page="projects" data-open-project="${escapeHtml(p.id)}">打开</button>
    </div>`
    )
    .join("");
}

function renderInfluencePlan(inf) {
  if (!inf) return "";
  const tracks = (inf.tracks || [])
    .map((t) => {
      const proj = state.projects.find((p) => p.id === t.id);
      const status = proj ? `${proj.progress}% · ${proj.status}` : "待关联项目";
      const folder = proj?.folder ? ` · ${proj.folder}` : "";
      return `
      <div class="card influence-track">
        <div class="provider-head">
          <div>
            <div class="row-title" style="font-size:16px">${escapeHtml(t.title)}</div>
            <div class="row-desc">${escapeHtml(t.blurb || "")}</div>
            <div class="meta" style="margin-top:6px">${escapeHtml(status)}${escapeHtml(folder)}</div>
          </div>
          <button class="btn primary" type="button" data-page="projects" data-open-project="${escapeHtml(
            t.id
          )}">打开项目</button>
        </div>
      </div>`;
    })
    .join("");
  return `
    <div class="card influence-plan" style="margin-bottom:12px">
      <div class="provider-head">
        <div>
          <div class="tags" style="margin-bottom:8px"><span class="tag purple">横切计划</span><span class="tag">非第四条业务</span></div>
          <h2 style="font-size:20px;margin:0">${escapeHtml(inf.title)}</h2>
          <p class="strat-mission" style="margin-top:8px">${escapeHtml(inf.question)}</p>
          <div class="meta">Owner · ${escapeHtml(inf.owner || "")} · ${escapeHtml(inf.note || "")}</div>
        </div>
      </div>
      <div class="sec" style="margin:14px 0 8px">对应项目</div>
      <div class="grid-2 influence-tracks">${tracks}</div>
    </div>`;
}

function renderStrategy() {
  const s = state.strategy;
  return `
    <div class="pad">
      <div class="card strat-hero">
        <div>
          <div class="meta">${s.horizon} · ${s.source}</div>
          <h2 style="font-size:22px;margin-top:4px">${s.vision}</h2>
          <p class="strat-mission">${s.mission}</p>
          <div class="tags" style="margin-top:10px">
            <span class="tag purple">${s.tech}</span>
            <span class="tag">${s.rhythm}</span>
          </div>
        </div>
        <div class="strat-actions">
          <button class="btn ghost" type="button" data-page="chat" data-open-dm="ch-strategy">打开战略委</button>
          <button class="btn primary" type="button" id="btn-strat-edit">调整目标</button>
        </div>
      </div>

      <div class="card" style="margin-top:12px">
        <h2>要消灭的三道门槛</h2>
        <div class="meta">对外体现 · 技术路线落地标准</div>
        <div class="grid-3">
          ${s.barriers
            .map(
              (b, i) => `
            <div class="barrier">
              <div class="barrier-n">${i + 1}</div>
              <div>
                <div class="row-title">${b.name}</div>
                <div class="row-desc">${b.goal}</div>
              </div>
            </div>`
            )
            .join("")}
        </div>
      </div>

      <div class="card ai-goals-card" style="margin-top:12px">
        <h2>AI 方向目标</h2>
        <div class="meta">组织与产品横切 · 高于单条业务线的用法铁律</div>
        <div class="grid-2" style="margin-top:12px">
          ${(s.aiGoals || [])
            .map(
              (g, i) => `
            <div class="barrier">
              <div class="barrier-n">${i + 1}</div>
              <div>
                <div class="row-title">${escapeHtml(g.title)}</div>
                <div class="row-desc">${escapeHtml(g.note || "")}</div>
              </div>
            </div>`
            )
            .join("")}
        </div>
      </div>

      <div class="sec" style="margin:16px 0 8px">三条主营业务 · 组合铁律</div>
      <div class="grid-3" style="margin-bottom:12px">
        ${s.pillars
          .map(
            (p) => `
          <div class="card pillar">
            <div class="pillar-top">
              <h2>${p.title}</h2>
              <span class="tag ${p.priority.startsWith("P0") ? "blue" : p.priority.startsWith("P1") ? "green" : "orange"}">${p.priority}</span>
            </div>
            <div class="meta">${p.metric}</div>
            <div class="proj-meta" style="margin-bottom:8px">Owner · ${p.owner} · ${p.share}</div>
            <div class="tags">
              ${p.initiatives.map((i) => `<span class="tag">${i}</span>`).join("")}
            </div>
          </div>`
          )
          .join("")}
      </div>

      ${renderInfluencePlan(s.influence)}

      <div class="card funnel-card" style="margin-bottom:12px">
        <h2>漏斗关系</h2>
        <div class="meta">咨询建信 → ASE 现金流 → AI 同事 Year 2 → 反哺 ASE</div>
        <div class="funnel">
          <span>AI 咨询（入口）</span>
          <span class="arrow">→</span>
          <span>ASE 平台（主营）</span>
          <span class="arrow">→</span>
          <span>AI 同事（升级）</span>
          <span class="arrow">→</span>
          <span>反哺 ASE</span>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <h2>战略赌注</h2>
          <div class="meta">刻意选择与不选（正本口径）</div>
          <div class="list">
            ${s.bets
              .map(
                (b) =>
                  `<div class="row"><div><div class="row-title">${b.title}</div><div class="row-desc">${b.note}</div></div></div>`
              )
              .join("")}
          </div>
        </div>
        <div class="card">
          <h2>待你拍板</h2>
          <div class="meta">收敛稿 §8 · 未确认不进正本</div>
          <div class="list">
            ${s.pending
              .map(
                (b) =>
                  `<div class="row"><div><div class="row-title">${b.title}</div><div class="row-desc">${b.note}</div></div><span class="tag orange">待确认</span></div>`
              )
              .join("")}
          </div>
        </div>
      </div>

      <div class="card" style="margin-top:12px">
        <h2>举措 → 项目</h2>
        <div class="meta">影响力计划优先 · 其余战略 / 客户项目见下</div>
        <div class="sec" style="margin:4px 0 8px">影响力计划</div>
        <div class="list">
          ${renderStrategyProjectRows((p) => p.pillar === "影响力计划" || ["p11", "p12"].includes(p.id))}
        </div>
        <div class="sec" style="margin:14px 0 8px">其它战略项目</div>
        <div class="list">
          ${renderStrategyProjectRows(
            (p) => p.category === "战略" && p.pillar !== "影响力计划" && !["p11", "p12"].includes(p.id)
          )}
        </div>
        <div class="sec" style="margin:14px 0 8px">客户项目（交付跟进）</div>
        <div class="list">
          ${state.projects
            .filter((p) => p.status !== "已完成" && p.category === "客户")
            .map(
              (p) => `
            <div class="row">
              <div>
                <div class="row-title">${p.title}</div>
                <div class="row-desc">客户项目${p.customer ? " · " + p.customer : ""} · ${p.progress}% · ${p.status}</div>
              </div>
              <button class="btn ghost" data-page="projects" data-open-project="${p.id}">打开</button>
            </div>`
            )
            .join("")}
        </div>
      </div>
    </div>`;
}

async function loadProviders() {
  state.providersLoading = true;
  try {
    const res = await fetch("/api/agent/providers");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.providers = data.providers || [];
    state.providersMeta = {
      cwd: data.cwd || "",
      model: data.model || "",
      activeProvider: data.activeProvider || "",
      bridgeOk: true,
      error: null,
    };
  } catch (e) {
    state.providers = [];
    state.providersMeta = {
      cwd: "",
      model: "",
      activeProvider: "",
      bridgeOk: false,
      error: String(e.message || e),
    };
  } finally {
    state.providersLoading = false;
  }
}

async function saveProvider(id, patch) {
  const res = await fetch(`/api/agent/providers/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  state.providers = data.providers || state.providers;
  state.providersMeta = {
    ...state.providersMeta,
    cwd: data.cwd || state.providersMeta.cwd,
    model: data.model || state.providersMeta.model,
    activeProvider: data.activeProvider || state.providersMeta.activeProvider,
    bridgeOk: true,
    error: null,
  };
  return data;
}

function renderProvidersPanel() {
  const meta = state.providersMeta;
  if (!meta.bridgeOk && !state.providers.length) {
    return `
      <div class="card">
        <h2>Provider</h2>
        <div class="meta">连接 Compose · agent-bridge 失败</div>
        <div class="empty" style="margin-top:12px">${escapeHtml(meta.error || "bridge 未启动")}</div>
        <div class="row-desc pre-wrap" style="margin-top:12px">请先：
cd engineering/v1/demo-ceo-console
docker compose up -d --build</div>
        <div style="margin-top:14px"><button class="btn primary" type="button" id="btn-providers-reload">重试</button></div>
      </div>`;
  }

  const list = state.providers;
  const editId = state.providerEditId;

  return `
    <div class="card" style="margin-bottom:14px">
      <h2>Provider</h2>
      <div class="meta">密钥只写入本机 bridge（providers.json / .env）· 网页永不回显完整 Key</div>
      <div class="list" style="margin-top:10px">
        <div class="row"><div><div class="row-title">Bridge</div><div class="row-desc">${
          meta.bridgeOk ? "Compose · agent-bridge · /workbench" : "未连接"
        }</div></div><span class="tag ${meta.bridgeOk ? "green" : "orange"}">${
          meta.bridgeOk ? "在线" : "离线"
        }</span></div>
        <div class="row"><div><div class="row-title">工作目录（容器内）</div><div class="row-desc pre-wrap">${escapeHtml(
          meta.cwd || "—"
        )}</div></div></div>
        <div class="row"><div><div class="row-title">当前 Agent 模型</div><div class="row-desc">${escapeHtml(
          meta.model || "—"
        )}</div></div></div>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn ghost" type="button" id="btn-providers-reload">刷新</button>
        <a class="btn ghost" href="https://cursor.com/dashboard/api" target="_blank" rel="noopener noreferrer">打开 Cursor API Keys</a>
      </div>
    </div>
    <div class="provider-grid">
      ${
        list
          .map((p) => {
            const editing = editId === p.id;
            return `
        <div class="card provider-card ${p.enabled ? "on" : ""}">
          <div class="provider-head">
            <div>
              <div class="row-title" style="font-size:16px">${escapeHtml(p.name)}</div>
              <div class="row-desc">${escapeHtml(p.kind)} · ${p.wired ? "已接线" : "仅存钥"}</div>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
              ${p.enabled ? `<span class="tag blue">启用中</span>` : ""}
              <span class="tag ${p.hasKey ? "green" : "orange"}">${p.hasKey ? "已配 Key" : "未配 Key"}</span>
            </div>
          </div>
          <div class="row-desc" style="margin-top:8px">${escapeHtml(p.help || "")}</div>
          ${
            p.hasKey
              ? `<div class="meta" style="margin-top:6px">Key 提示 · <code class="branch-code">${escapeHtml(
                  p.keyHint
                )}</code></div>`
              : ""
          }
          ${
            editing
              ? `<div class="proj-form" style="margin-top:12px">
                  <label class="field"><span>API Key</span>
                    <input id="pe-prov-key" type="password" autocomplete="off" placeholder="${
                      p.hasKey ? "留空则不改 · 输入则覆盖" : "粘贴 API Key"
                    }" value="${escapeHtml(state.providerDraftKey)}" />
                  </label>
                  ${
                    p.id === "cursor"
                      ? `<label class="field"><span>模型</span>
                          <select id="pe-prov-model">
                            ${(p.models || [])
                              .map(
                                (m) =>
                                  `<option value="${escapeHtml(m)}" ${
                                    (state.providerDraftModel || p.model) === m ? "selected" : ""
                                  }>${escapeHtml(m)}</option>`
                              )
                              .join("")}
                          </select>
                        </label>`
                      : ""
                  }
                  <div class="proj-form-actions">
                    <button class="btn primary" type="button" data-provider-save="${p.id}">保存</button>
                    <button class="btn ghost" type="button" id="btn-provider-cancel">取消</button>
                    ${
                      p.hasKey
                        ? `<button class="btn ghost" type="button" data-provider-clear="${p.id}">清除 Key</button>`
                        : ""
                    }
                  </div>
                </div>`
              : `<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
                  <button class="btn primary" type="button" data-provider-edit="${p.id}">配置</button>
                  ${
                    !p.enabled && p.wired
                      ? `<button class="btn ghost" type="button" data-provider-enable="${p.id}">设为启用</button>`
                      : ""
                  }
                  ${
                    p.docsUrl
                      ? `<a class="btn ghost" href="${escapeHtml(
                          p.docsUrl
                        )}" target="_blank" rel="noopener noreferrer">文档</a>`
                      : ""
                  }
                </div>`
          }
        </div>`;
          })
          .join("") || `<div class="card"><div class="empty">${
            state.providersLoading ? "加载中…" : "暂无 Provider"
          }</div></div>`
      }
    </div>`;
}

function renderSettings() {
  const tab = state.settingsTab || "providers";
  const panel = tab === "providers" ? renderProvidersPanel() : `<div class="card"><div class="empty">暂无此分区</div></div>`;
  return `
    <div class="pad settings-page">
      <div class="settings-layout">
        <aside class="settings-nav card">
          <div class="row-title" style="margin-bottom:10px">设置</div>
          ${SETTINGS_TABS.map(
            (t) => `
            <button class="settings-tab ${tab === t.id ? "on" : ""}" type="button" data-settings-tab="${t.id}">
              <span class="row-title">${escapeHtml(t.label)}</span>
              <span class="row-desc">${escapeHtml(t.desc)}</span>
            </button>`
          ).join("")}
        </aside>
        <div class="settings-main">${panel}</div>
      </div>
    </div>`;
}

/** 全流程审阅包（演示层 · 对齐 项目调研/04-AI科普助手-评测包） */
const REVIEW_STAGES = [
  { id: "demand", label: "需求", short: "1" },
  { id: "spec", label: "规格", short: "2" },
  { id: "cases", label: "题库", short: "3" },
  { id: "judge", label: "裁判", short: "4" },
  { id: "gate", label: "门禁", short: "5" },
  { id: "run", label: "实跑", short: "6" },
  { id: "verdict", label: "裁决", short: "7" },
];

const REVIEW_PACKS = {
  ai_科普: {
    id: "ai_科普",
    title: "AI 科普串联助手",
    projectId: "p11",
    demand:
      "我需要一个专门写 AI 技术与产品科普短文的 Agent，面向普通人，公众号可读，可联网查证。",
    audience: "普通人 / 非从业者",
    style: "公众号可读 · 600–1200 字",
    scope: "全球主流 AI 技术与产品",
    path: "项目调研/04-AI科普助手-评测包/",
    casePath: "case/ai_科普/科普短文/",
    checklist: {
      demand: ["一句话可评测", "听众与文体清楚", "查证权限写明"],
      spec: ["能做/不做可审", "成功样子可复述", "禁灌装 criteria"],
      cases: ["覆盖串联/短文/产品/查证/边界", "权重和为 100", "格式可进 factory"],
      judge: ["五维稳定", "0–100 标尺", "一票否决项明确"],
      gate: ["按题配对", "bootstrap CI 语义", "质量地板"],
      run: ["report 可指", "失败率可见", "无伪造出处"],
      verdict: ["各阶段人审齐", "可晋升或退回理由"],
    },
    spec: {
      can: ["知识串联", "公众号短文", "联网核对并标注", "纠正常见误解"],
      cannot: ["投资/医疗/法律结论", "编造引用", "营销软文", "神化 AI"],
      success: ["读者能复述核心", "事实有出处或未核实", "关系清楚非词条堆"],
    },
    cases: [
      { id: "pop_chain_001", dim: "串联", title: "下一个词预测 → ChatGPT", lv: "basic" },
      { id: "pop_chain_002", dim: "串联", title: "预训练→微调→对齐→产品", lv: "basic+medium" },
      { id: "pop_chain_003", dim: "串联", title: "RAG：先检索再生成", lv: "basic" },
      { id: "pop_article_001", dim: "短文", title: "大模型 vs 传统搜索", lv: "basic" },
      { id: "pop_article_002", dim: "短文", title: "Agent 与聊天机器人", lv: "basic" },
      { id: "pop_article_003", dim: "短文", title: "多模态改变了什么", lv: "basic" },
      { id: "pop_product_001", dim: "产品", title: "ChatGPT / Claude / Gemini", lv: "basic+medium" },
      { id: "pop_product_002", dim: "产品", title: "开源 Llama vs 闭源 API", lv: "basic" },
      { id: "pop_verify_001", dim: "查证", title: "核对公开能力边界", lv: "basic+medium" },
      { id: "pop_verify_002", dim: "查证", title: "参数/上下文传闻核查", lv: "basic" },
      { id: "pop_bound_001", dim: "边界", title: "拒答荐股", lv: "basic" },
      { id: "pop_bound_002", dim: "边界", title: "纠错：AI 有意识？", lv: "basic+medium" },
    ],
    judgeDims: [
      { id: "accuracy_verified", w: 25, name: "事实与查证" },
      { id: "structure_chain", w: 25, name: "知识串联" },
      { id: "readability_wechat", w: 25, name: "公众号可读" },
      { id: "boundary_honesty", w: 15, name: "边界诚实" },
      { id: "no_hype", w: 10, name: "非软文" },
    ],
    veto: ["伪造出处", "投资/医疗/法律结论", "维分 0–10 未换算"],
    gates: [
      { title: "按题配对差分", note: "不用跨题乱平均绑架" },
      { title: "bootstrap CI + 配对 t", note: "下界>0 晋升 · 上界<0 驳回 · 否则噪声" },
      { title: "质量地板", note: "一票否决题=0；软门槛触发 ≤20%" },
      { title: "Holdout", note: "晋升后 holdout 不低于冠军 −3（可回填）" },
    ],
    /** 演示用实跑摘要（非本机刚跑） */
    runDemo: {
      status: "待人触发",
      note: "题库与裁判已就绪；实跑须人通过 factory API 触发，agent 不代跑。",
      sampleScores: [
        { caseId: "pop_chain_001", composite: 78, veto: false },
        { caseId: "pop_bound_001", composite: 91, veto: false },
        { caseId: "pop_verify_001", composite: 64, veto: false, soft: "accuracy 偏低" },
      ],
    },
  },
};

function reviewDecisionOf(stageId) {
  const pack = state.reviewPackId || "ai_科普";
  return (state.reviewDecisions[pack] || {})[stageId] || null;
}

function setReviewDecision(stageId, verdict) {
  const pack = state.reviewPackId || "ai_科普";
  if (!state.reviewDecisions[pack]) state.reviewDecisions[pack] = {};
  state.reviewDecisions[pack][stageId] = {
    verdict,
    note: (state.reviewNote || "").trim(),
    at: new Date().toISOString(),
  };
  state.reviewNote = "";
}

function reviewStatusTag(verdict) {
  if (verdict === "pass") return "green";
  if (verdict === "revise") return "orange";
  if (verdict === "reject") return "red";
  return "";
}

function reviewStatusLabel(verdict) {
  if (verdict === "pass") return "已通过";
  if (verdict === "revise") return "退回补齐";
  if (verdict === "reject") return "驳回";
  return "待审";
}

function renderReviewStageBody(pack, stageId) {
  const checks = (pack.checklist[stageId] || [])
    .map((c) => `<li>${escapeHtml(c)}</li>`)
    .join("");
  if (stageId === "demand") {
    return `
      <div class="review-quote">${escapeHtml(pack.demand)}</div>
      <div class="meta" style="margin-top:10px">听众 · ${escapeHtml(pack.audience)} · ${escapeHtml(
        pack.style
      )} · ${escapeHtml(pack.scope)}</div>
      <ul class="review-check">${checks}</ul>`;
  }
  if (stageId === "spec") {
    const can = pack.spec.can.map((x) => `<span class="tag green">${escapeHtml(x)}</span>`).join("");
    const cannot = pack.spec.cannot.map((x) => `<span class="tag orange">${escapeHtml(x)}</span>`).join("");
    const ok = pack.spec.success.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
    return `
      <div class="sec">能做</div><div class="tags" style="margin-top:6px">${can}</div>
      <div class="sec" style="margin-top:14px">不做</div><div class="tags" style="margin-top:6px">${cannot}</div>
      <div class="sec" style="margin-top:14px">成功样子</div><ul class="review-check">${ok}</ul>
      <div class="meta">正本 · ${escapeHtml(pack.path)}00-规格一页.md</div>`;
  }
  if (stageId === "cases") {
    const rows = pack.cases
      .map(
        (c) => `
      <div class="row review-case-row">
        <div>
          <div class="row-title"><code class="branch-code">${escapeHtml(c.id)}</code> ${escapeHtml(
            c.title
          )}</div>
          <div class="row-desc">${escapeHtml(c.dim)} · ${escapeHtml(c.lv)}</div>
        </div>
        <span class="tag">${escapeHtml(c.dim)}</span>
      </div>`
      )
      .join("");
    return `
      <div class="meta">${pack.cases.length} 题 · suite「科普短文」· ${escapeHtml(pack.casePath)}</div>
      <div class="list" style="margin-top:10px">${rows}</div>
      <ul class="review-check">${checks}</ul>`;
  }
  if (stageId === "judge") {
    const bars = pack.judgeDims
      .map(
        (d) => `
      <div class="review-dim">
        <div class="review-dim-head"><span>${escapeHtml(d.name)}</span><code class="branch-code">${escapeHtml(
          d.id
        )}</code><strong>${d.w}</strong></div>
        <div class="review-dim-bar"><i style="width:${d.w}%"></i></div>
      </div>`
      )
      .join("");
    const veto = pack.veto.map((v) => `<span class="tag red">${escapeHtml(v)}</span>`).join("");
    return `
      <div class="meta">维分 0–100 · 权重和 100 · 对齐 Judge v2</div>
      <div style="margin-top:12px">${bars}</div>
      <div class="sec" style="margin-top:14px">一票否决</div>
      <div class="tags" style="margin-top:6px">${veto}</div>
      <ul class="review-check">${checks}</ul>`;
  }
  if (stageId === "gate") {
    const g = pack.gates
      .map(
        (x) => `
      <div class="row"><div><div class="row-title">${escapeHtml(x.title)}</div><div class="row-desc">${escapeHtml(
          x.note
        )}</div></div></div>`
      )
      .join("");
    return `<div class="list">${g}</div><ul class="review-check">${checks}</ul>`;
  }
  if (stageId === "run") {
    const r = pack.runDemo;
    const scores = (r.sampleScores || [])
      .map(
        (s) => `
      <div class="row">
        <div>
          <div class="row-title"><code class="branch-code">${escapeHtml(s.caseId)}</code></div>
          <div class="row-desc">${s.soft ? escapeHtml(s.soft) : s.veto ? "一票否决" : "无否决"}</div>
        </div>
        <span class="tag ${s.composite >= 70 ? "green" : "orange"}">${s.composite}</span>
      </div>`
      )
      .join("");
    return `
      <div class="tags"><span class="tag orange">${escapeHtml(r.status)}</span></div>
      <div class="row-desc" style="margin-top:8px">${escapeHtml(r.note)}</div>
      <div class="sec" style="margin-top:14px">示意分（演示占位）</div>
      <div class="list" style="margin-top:8px">${scores}</div>
      <ul class="review-check">${checks}</ul>`;
  }
  if (stageId === "verdict") {
    const rows = REVIEW_STAGES.filter((s) => s.id !== "verdict")
      .map((s) => {
        const d = reviewDecisionOf(s.id);
        return `<div class="row">
          <div><div class="row-title">${escapeHtml(s.label)}</div>
          <div class="row-desc">${d?.note ? escapeHtml(d.note) : "—"}</div></div>
          <span class="tag ${reviewStatusTag(d?.verdict)}">${reviewStatusLabel(d?.verdict)}</span>
        </div>`;
      })
      .join("");
    const passed = REVIEW_STAGES.filter((s) => s.id !== "verdict" && reviewDecisionOf(s.id)?.verdict === "pass")
      .length;
    const need = REVIEW_STAGES.length - 1;
    return `
      <div class="meta">${passed}/${need} 阶段已通过 · 全部通过后可开进化实跑</div>
      <div class="list" style="margin-top:10px">${rows}</div>
      <ul class="review-check">${checks}</ul>`;
  }
  return `<div class="empty">未知阶段</div>`;
}

function renderReview() {
  const pack = REVIEW_PACKS[state.reviewPackId] || REVIEW_PACKS.ai_科普;
  if (!REVIEW_STAGES.find((s) => s.id === state.reviewStage)) state.reviewStage = "demand";
  const stage = REVIEW_STAGES.find((s) => s.id === state.reviewStage) || REVIEW_STAGES[0];
  const dec = reviewDecisionOf(stage.id);
  const packChips = Object.values(REVIEW_PACKS)
    .map(
      (p) => `
    <button class="chip-btn ${p.id === pack.id ? "accent" : ""}" type="button" data-review-pack="${escapeHtml(
      p.id
    )}">${escapeHtml(p.title)}</button>`
    )
    .join("");
  const steps = REVIEW_STAGES.map((s, i) => {
    const d = reviewDecisionOf(s.id);
    const on = s.id === stage.id;
    const cls = [
      "review-step",
      on ? "is-on" : "",
      d?.verdict === "pass" ? "is-pass" : "",
      d?.verdict === "revise" ? "is-revise" : "",
      d?.verdict === "reject" ? "is-reject" : "",
    ]
      .filter(Boolean)
      .join(" ");
    return `
      <button class="${cls}" type="button" data-review-stage="${escapeHtml(s.id)}">
        <span class="review-step-n">${escapeHtml(s.short)}</span>
        <span class="review-step-l">${escapeHtml(s.label)}</span>
      </button>
      ${i < REVIEW_STAGES.length - 1 ? `<span class="review-step-join" aria-hidden="true"></span>` : ""}`;
  }).join("");
  const idx = REVIEW_STAGES.findIndex((s) => s.id === stage.id);
  const prev = idx > 0 ? REVIEW_STAGES[idx - 1] : null;
  const next = idx < REVIEW_STAGES.length - 1 ? REVIEW_STAGES[idx + 1] : null;

  return `
    <div class="pad review-page">
      <div class="card">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">审阅包</span>
          <span class="tag">挂 YiAgent · p11</span>
          ${dec ? `<span class="tag ${reviewStatusTag(dec.verdict)}">本步 ${reviewStatusLabel(dec.verdict)}</span>` : `<span class="tag orange">本步待审</span>`}
        </div>
        <h2>${escapeHtml(pack.title)} · 全流程审阅</h2>
        <div class="meta">人审闸门：逐段过目 → 通过 / 退回补齐 · 基因组禁止灌装 criteria</div>
        <div class="progress-project-chips" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px">${packChips}</div>
        <div class="review-stepper" role="tablist" aria-label="审阅阶段">${steps}</div>
      </div>

      <div class="review-grid" style="margin-top:14px">
        <div class="card review-main">
          <div class="progress-tree-toolbar">
            <div>
              <div class="sec">阶段 ${escapeHtml(stage.short)} · ${escapeHtml(stage.label)}</div>
              <div class="meta" style="margin-top:4px">审阅清单见右侧 · 结论记入本机会话状态</div>
            </div>
            <div class="progress-tree-toolbar-actions">
              ${
                prev
                  ? `<button class="chip-btn" type="button" data-review-stage="${escapeHtml(prev.id)}">← ${escapeHtml(
                      prev.label
                    )}</button>`
                  : ""
              }
              ${
                next
                  ? `<button class="chip-btn accent" type="button" data-review-stage="${escapeHtml(next.id)}">${escapeHtml(
                      next.label
                    )} →</button>`
                  : ""
              }
            </div>
          </div>
          ${renderReviewStageBody(pack, stage.id)}
        </div>
        <aside class="card review-rail" aria-label="审阅动作">
          <h2>人审结论</h2>
          <div class="meta">当前：${escapeHtml(stage.label)} · ${reviewStatusLabel(dec?.verdict)}</div>
          ${
            dec?.note
              ? `<div class="review-quote" style="margin-top:10px;font-size:13px">${escapeHtml(dec.note)}</div>`
              : ""
          }
          <label class="field" style="margin-top:12px;display:block">
            <span>备注（可选）</span>
            <textarea id="review-note" rows="3" placeholder="退回时写清缺什么">${escapeHtml(
              state.reviewNote || ""
            )}</textarea>
          </label>
          <div class="list proj-actions" style="margin-top:12px;flex-direction:column;align-items:stretch">
            <button class="btn primary" type="button" data-review-verdict="pass">通过本步</button>
            <button class="btn ghost" type="button" data-review-verdict="revise">退回补齐</button>
            <button class="btn ghost" type="button" data-review-verdict="reject">驳回</button>
          </div>
          <div class="meta" style="margin-top:14px">正本路径</div>
          <div class="row-desc pre-wrap" style="margin-top:4px">${escapeHtml(pack.path)}</div>
          <div class="list proj-actions" style="margin-top:12px">
            <button class="btn ghost" type="button" data-open-progress="p11">YiAgent 进度表</button>
          </div>
        </aside>
      </div>
    </div>`;
}

function renderGenome() {
  return `
    <div class="genome-layout" aria-label="基因组工作台">
      <iframe
        class="genome-frame"
        title="YiAgent 基因组双螺旋"
        src="/dna-graph.html?embed=1&v=20260804-fde"
        allow="fullscreen"
      ></iframe>
    </div>`;
}

const PAGES = {
  today: renderToday,
  schedule: renderSchedule,
  todos: renderTodos,
  chat: renderChat,
  genome: renderGenome,
  approvals: renderApprovals,
  projects: renderProjects,
  progress: renderProgress,
  review: renderReview,
  strategy: renderStrategy,
  org: renderOrg,
  dna: renderDna,
  kb: renderKb,
  crm: renderCrm,
  assets: renderAssets,
  settings: renderSettings,
};

function afterPaint() {
  const msgs = $("msgs");
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
  const input = $("input");
  const showingList = $("app").classList.contains("show-chats");
  if (input && !showingList) {
    input.focus();
    input.style.height = "auto";
    input.style.height = Math.min(120, input.scrollHeight) + "px";
    if (state.inputCaret != null) {
      const pos = Math.max(0, Math.min(state.inputCaret, input.value.length));
      input.setSelectionRange(pos, pos);
      state.inputCaret = null;
    }
  }
}

function render() {
  renderNav();
  renderHead();
  const ws = $("workspace");
  if (ws) ws.classList.toggle("genome-full", state.page === "genome");
  $("ws-body").innerHTML = PAGES[state.page]();
  requestAnimationFrame(afterPaint);
}

function push(channelId, msg) {
  if (!state.threads[channelId]) state.threads[channelId] = [];
  state.threads[channelId].push({ ...msg, at: clock(), ts: ++state.seq });
}

/** 开发席 DM / 起步开发频道 → Develop 角色名 */
const DEVELOP_CHANNEL_ROLE = {
  "dm-ag-product": "Product",
  "dm-ag-pm": "PM",
  "dm-ag-arch": "Architect",
  "dm-ag-dev": "Dev",
  "dm-ag-devops": "DevOps",
  "ch-dev": "PM",
};

const DEVELOP_ROLE_NAMES = ["Product", "PM", "Architect", "Dev", "DevOps"];

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function channelScopeId(channelId) {
  const ch = CHANNELS[channelId];
  if (!ch) return state.teamScope || "team-review";
  if (ch.kind === "team" || ch.kind === "human" || ch.kind === "project-team") return ch.id;
  return ch.parent || state.teamScope || "team-review";
}

/** 当前频道可 @ 的席位（本 Team / 项目 Develop 副本） */
function mentionCandidates(channelId = state.channelId) {
  const ch = CHANNELS[channelId];
  if (!ch || ch.kind === "workbench") {
    return DEVELOP_ROLE_NAMES.map((role) => ({
      id: `role-${role}`,
      name: role,
      role,
      sub: "开发席",
    }));
  }
  const scopeId = channelScopeId(channelId);
  const seen = new Set();
  const out = [];
  for (const id of childrenOf(scopeId)) {
    const c = CHANNELS[id];
    if (!c || seen.has(c.name)) continue;
    seen.add(c.name);
    out.push({
      id,
      name: c.name,
      // 项目频道：role=磁盘名=显示名；公司级：role=developRole
      role: c.projectFolder
        ? c.name
        : c.developRole || DEVELOP_CHANNEL_ROLE[id] || c.name,
      sub: c.sub || "",
    });
  }
  const scope = CHANNELS[scopeId];
  for (const name of scope?.members || []) {
    if (seen.has(name)) continue;
    seen.add(name);
    out.push({ id: `member-${name}`, name, role: name, sub: scope.name || "席位" });
  }
  return out;
}

function filteredMentionCandidates() {
  const q = String(state.mentionQuery || "")
    .trim()
    .toLowerCase();
  const list = mentionCandidates(state.channelId);
  if (!q) return list;
  return list.filter(
    (m) => m.name.toLowerCase().includes(q) || String(m.role || "").toLowerCase().includes(q)
  );
}

/** 从光标前回溯解析正在输入的 @query */
function parseAtQuery(text, caret) {
  const before = String(text || "").slice(0, Math.max(0, caret));
  const m = before.match(/(^|[\s，,、])@([^\s@]*)$/);
  if (!m) return null;
  return {
    start: before.length - m[2].length - 1,
    query: m[2],
  };
}

function extractMentions(text, channelId = state.channelId) {
  const raw = String(text || "");
  const cands = mentionCandidates(channelId).slice().sort((a, b) => b.name.length - a.name.length);
  const found = [];
  const seen = new Set();
  for (const c of cands) {
    const re = new RegExp(`(^|[\\s，,、])@${escapeRegExp(c.name)}(?=$|[\\s，,、.。!！?？:：;；])`, "i");
    if (!re.test(raw)) continue;
    const key = c.role || c.name;
    if (seen.has(key)) continue;
    seen.add(key);
    found.push(c);
  }
  return found;
}

function formatMessageHtml(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/@([\w\u4e00-\u9fff][\w\u4e00-\u9fff.-]*)/g, '<span class="msg-mention">@$1</span>');
}

function renderMentionMenuHtml() {
  const items = filteredMentionCandidates();
  if (!items.length) {
    return `<div id="mention-menu" class="mention-menu" role="listbox"><div class="mention-empty">无匹配席位</div></div>`;
  }
  const idx = Math.max(0, Math.min(state.mentionIndex, items.length - 1));
  state.mentionIndex = idx;
  return `
    <div id="mention-menu" class="mention-menu" role="listbox" aria-label="提及席位">
      <div class="mention-head">提及 · 本频道席位</div>
      ${items
        .map(
          (m, i) => `
        <button class="mention-item ${i === idx ? "on" : ""}" type="button" role="option" data-mention-pick="${escapeHtml(
          m.name
        )}" aria-selected="${i === idx ? "true" : "false"}">
          <span class="mention-at">@${escapeHtml(m.name)}</span>
          <span class="mention-sub">${escapeHtml(m.sub || m.role || "")}</span>
        </button>`
        )
        .join("")}
    </div>`;
}

function patchMentionMenu() {
  const card = document.querySelector(".composer-card");
  if (!card) return;
  const existing = $("mention-menu");
  if (!state.mentionOpen) {
    existing?.remove();
    return;
  }
  const html = renderMentionMenuHtml();
  if (existing) {
    existing.outerHTML = html;
  } else {
    card.insertAdjacentHTML("afterbegin", html);
  }
}

function closeMentionMenu() {
  state.mentionOpen = false;
  state.mentionQuery = "";
  state.mentionAt = null;
  state.mentionCaretEnd = null;
  state.mentionIndex = 0;
  patchMentionMenu();
}

function applyMentionPick(name) {
  const mentionName = String(name || "").trim();
  if (!mentionName) return;
  const draft = state.draft || "";
  const start = state.mentionAt != null ? state.mentionAt : draft.length;
  const end = state.mentionCaretEnd != null ? state.mentionCaretEnd : draft.length;
  const before = draft.slice(0, start);
  const after = draft.slice(end);
  const gap = before.length && !/\s$/.test(before) ? " " : "";
  const inserted = `${gap}@${mentionName} `;
  state.draft = before + inserted + after;
  state.inputCaret = (before + inserted).length;
  closeMentionMenu();
  render();
  toast(`已提及 @${mentionName}`);
}

function openMentionPicker() {
  const input = $("input");
  const caret = input ? input.selectionStart : (state.draft || "").length;
  const draft = state.draft || "";
  const atq = parseAtQuery(draft, caret);
  if (atq) {
    state.mentionAt = atq.start;
    state.mentionQuery = atq.query;
    state.mentionCaretEnd = caret;
    state.inputCaret = caret;
  } else {
    const before = draft.slice(0, caret);
    const after = draft.slice(caret);
    const prefix = before.length && !/\s$/.test(before) ? " @" : "@";
    state.draft = before + prefix + after;
    state.mentionAt = (before + prefix).length - 1;
    state.mentionCaretEnd = state.mentionAt + 1;
    state.mentionQuery = "";
    state.inputCaret = state.mentionCaretEnd;
  }
  state.mentionOpen = true;
  state.mentionIndex = 0;
  render();
}

function defaultProjectChannelRole(ch) {
  const members = ch?.members || [];
  const kids = childrenOf(ch.id)
    .map((id) => CHANNELS[id])
    .filter(Boolean);
  const pm =
    kids.find((c) => c.developRole === "PM" || c.name === "PM") ||
    (members.includes("PM") ? { name: "PM" } : null);
  if (pm?.name) return pm.name;
  if (kids[0]?.name) return kids[0].name;
  if (members[0]) return members[0];
  return "PM";
}

function resolveDevelopSend(channelId) {
  const ch = CHANNELS[channelId];
  if (!ch) return null;
  if (ch.kind === "project-team") {
    return {
      role: defaultProjectChannelRole(ch),
      teamChannel: true,
      projectId: ch.projectId,
      projectFolder: ch.projectFolder,
      projectTitle: ch.projectTitle,
    };
  }
  // 项目频道一对一：role = 磁盘 Agents/<名>（用显示名）
  if (ch.projectFolder && ch.parent) {
    return {
      role: ch.name,
      teamChannel: false,
      projectId: ch.projectId || null,
      projectFolder: ch.projectFolder || null,
      projectTitle: ch.projectTitle || null,
    };
  }
  if (ch.developRole) {
    return {
      role: ch.developRole,
      teamChannel: false,
      projectId: ch.projectId || null,
      projectFolder: ch.projectFolder || null,
      projectTitle: ch.projectTitle || null,
    };
  }
  const mapped = DEVELOP_CHANNEL_ROLE[channelId];
  if (mapped) {
    return {
      role: mapped,
      teamChannel: channelId === "ch-dev",
      projectId: null,
      projectFolder: null,
      projectTitle: null,
    };
  }
  if ((ch.kind === "team" || ch.kind === "human") && ch.memberIds?.length) {
    const developAgents = ch.memberIds.map(agentById).filter((a) => a?.developRole);
    if (!developAgents.length) return null;
    const pm = developAgents.find((a) => a.developRole === "PM");
    return {
      role: (pm || developAgents[0]).developRole,
      teamChannel: true,
      projectId: null,
      projectFolder: null,
      projectTitle: null,
    };
  }
  return null;
}

async function sendToCursorWorkbench(channelId, text) {
  state.typing = { channelId, from: "Cursor Agent" };
  render();
  try {
    const res = await fetch("/api/agent/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      data = {};
    }
    state.typing = null;
    if (!res.ok) {
      const errText = data.error || `HTTP ${res.status}`;
      push(channelId, {
        from: "Cursor Agent",
        role: "agent",
        auto: false,
        text: `发送失败：${errText}\n请确认 docker compose 已起 agent-bridge，并在「设置 → Provider」配置 Key。`,
      });
      toast("Cursor Agent 不可用 · " + errText);
    } else {
      push(channelId, {
        from: "Cursor Agent",
        role: "agent",
        auto: false,
        text: data.result || "(empty reply)",
      });
      toast(data.status === "finished" ? "工作台已回复" : `状态 · ${data.status || "ok"}`);
    }
  } catch (e) {
    state.typing = null;
    push(channelId, {
      from: "Cursor Agent",
      role: "agent",
      auto: false,
      text: `发送失败：${e.message || e}\n请先：docker compose up -d --build`,
    });
    toast("无法连接 agent-bridge");
  }
  if (state.page === "chat" && state.channelId === channelId) render();
  else {
    state.unread[channelId] = (state.unread[channelId] || 0) + 1;
    renderNav();
  }
}

function projectScopeFromChannel(channelId) {
  let ch = CHANNELS[channelId];
  if (!ch) return {};
  if (ch.projectFolder) {
    return {
      projectId: ch.projectId || null,
      projectFolder: ch.projectFolder,
      projectTitle: ch.projectTitle || "",
    };
  }
  if (ch.parent && CHANNELS[ch.parent]?.projectFolder) {
    ch = CHANNELS[ch.parent];
    return {
      projectId: ch.projectId || null,
      projectFolder: ch.projectFolder,
      projectTitle: ch.projectTitle || "",
    };
  }
  return {};
}

async function sendToDevelopRole(channelId, role, text, opts = {}) {
  const fromLabel = role || "开发席";
  const teamChannel = Boolean(opts.teamChannel);
  const fromCh = projectScopeFromChannel(channelId);
  const projectFolder = opts.projectFolder || fromCh.projectFolder || null;
  const projectId = opts.projectId || fromCh.projectId || null;
  const projectTitle = opts.projectTitle || fromCh.projectTitle || "";
  const mentions = Array.isArray(opts.mentions) ? opts.mentions : [];
  state.typing = { channelId, from: fromLabel };
  render();
  try {
    const payload = {
      text,
      role,
      teamChannel,
    };
    if (mentions.length) payload.mentions = mentions;
    if (projectFolder) {
      payload.projectFolder = projectFolder;
      payload.projectId = projectId || "unknown";
      payload.projectTitle = projectTitle || projectFolder;
    }
    const res = await fetch("/api/agent/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      data = {};
    }
    state.typing = null;
    const who = data.from || fromLabel;
    if (!res.ok) {
      const errText = data.error || `HTTP ${res.status}`;
      const genomeHint = projectFolder
        ? `${projectFolder}/频道/Agents/${role}/genome.json`
        : `AgentTeam/Develop/${role}/genome.json`;
      const noCh =
        data.code === "NO_CHANNEL"
          ? "\n请先在项目详情「组建频道」。"
          : "";
      push(channelId, {
        from: who,
        role: "agent",
        auto: false,
        text: `发送失败：${errText}${noCh}\n请确认 agent-bridge 已起，基因组在 ${genomeHint}，并在「设置 → Provider」配置 Key。`,
      });
      toast(
        data.code === "NO_CHANNEL"
          ? "请先组建项目频道"
          : "开发席不可用 · " + errText
      );
    } else {
      push(channelId, {
        from: who,
        role: "agent",
        auto: teamChannel,
        text: data.result || "(empty reply)",
      });
      const via = data.provider === "kimi" ? `Kimi · ${data.model || "kimi-k3"}` : `Cursor · ${data.model || ""}`;
      const scope = data.projectFolder ? ` · cwd ${data.projectFolder}` : "";
      const log = data.chatLog ? ` · ${data.chatLog}` : "";
      const pin = data.milestonePinned ? " · 里程碑已注入" : "";
      toast(`${who} 已回复 · ${via}${scope}${log}${pin}`);
    }
  } catch (e) {
    state.typing = null;
    push(channelId, {
      from: fromLabel,
      role: "agent",
      auto: false,
      text: `发送失败：${e.message || e}`,
    });
    toast("无法连接 agent-bridge");
  }
  if (state.page === "chat" && state.channelId === channelId) render();
  else {
    state.unread[channelId] = (state.unread[channelId] || 0) + 1;
    renderNav();
  }
}

async function sendToDevelopByMentions(channelId, text, base, mentionRoles) {
  const isProject = Boolean(base.projectFolder);
  const allowed = isProject
    ? new Set(CHANNELS[channelScopeId(channelId)]?.members || [])
    : new Set(DEVELOP_ROLE_NAMES);
  const roles = [...new Set(mentionRoles.filter((r) => (isProject ? allowed.has(r) || DEVELOP_ROLE_NAMES.includes(r) : allowed.has(r))))];
  if (!roles.length) {
    await sendToDevelopRole(channelId, base.role, text, { ...base, mentions: [] });
    return;
  }
  for (const role of roles) {
    await sendToDevelopRole(channelId, role, text, {
      ...base,
      role,
      mentions: roles,
      teamChannel: base.teamChannel,
    });
  }
}

function send() {
  const text = state.draft.trim();
  if (!text || state.typing) return;
  if (state.mentionOpen) closeMentionMenu();
  const channelId = state.channelId;
  const mentioned = extractMentions(text, channelId);
  const mentionNames = mentioned.map((m) => m.name);
  push(channelId, {
    from: "你",
    role: "ceo",
    auto: false,
    text,
    mentions: mentionNames,
  });
  state.draft = "";
  render();

  if (channelId === "cursor-workbench" || CHANNELS[channelId]?.kind === "workbench") {
    sendToCursorWorkbench(channelId, text);
    return;
  }

  const developSend = resolveDevelopSend(channelId);
  if (developSend) {
    const isProject = Boolean(developSend.projectFolder);
    const developRoles = mentioned.map((m) => (isProject ? m.name : m.role || m.name));
    if (developRoles.length) {
      sendToDevelopByMentions(channelId, text, developSend, developRoles);
    } else {
      sendToDevelopRole(channelId, developSend.role, text, {
        ...developSend,
        mentions: mentionNames,
      });
    }
    return;
  }

  const replies = REPLIES[channelId] || [];
  let pick = null;
  if (mentioned.length) {
    const want = mentioned[0].name;
    pick =
      replies.find((r) => r.from === want) ||
      Object.keys(REPLIES)
        .filter((id) => CHANNELS[id]?.name === want)
        .map((id) => REPLIES[id][0])
        .find(Boolean) || {
        from: want,
        text: `收到，你 @ 了我。我按「${want}」身份跟进这条。`,
      };
  } else if (replies.length) {
    pick = replies[Math.floor(Math.random() * replies.length)];
  }
  if (!pick) return;
  state.typing = { channelId, from: pick.from };
  render();
  setTimeout(() => {
    state.typing = null;
    push(channelId, {
      from: pick.from,
      role: "agent",
      auto: CHANNELS[channelId].kind === "team" || CHANNELS[channelId].kind === "human",
      text: pick.text,
      mentions: mentionNames,
    });
    if (state.page === "chat" && state.channelId === channelId) render();
    else state.unread[channelId] = (state.unread[channelId] || 0) + 1;
    if (state.page !== "chat") renderNav();
  }, 700);
}

function decide(id, ok) {
  const item = state.approvals.find((x) => x.id === id);
  if (!item) return;
  state.approvals = state.approvals.filter((x) => x.id !== id);
  push(item.channel, {
    from: "你",
    role: "ceo",
    auto: false,
    text: `${ok ? "批准" : "驳回"}：${item.title}`,
  });
  toast(ok ? "已批准，并回写到会话" : "已驳回，并回写到会话");
  render();
}

function newKbDoc() {
  const id = `k${++state.seq}`;
  state.kb.unshift({
    id,
    folder: "draft",
    title: "未命名文档",
    who: "你",
    visibility: "human_only",
    updated: "刚刚",
    humanBody: "新建默认「仅人看」。认证发布后才会出现 Agent 投影。",
    agentBody: "",
    provenance: {
      tier: "S0",
      locator: `draft/${id}.md`,
      version: "draft",
      certifiedBy: null,
      certifiedAt: null,
    },
    trail: [{ at: "刚刚", actor: "你", event: "入库", detail: "新建 · 默认仅人看 · 未认证" }],
  });
  state.kbFolder = "draft";
  state.kbPlane = "human";
  state.kbDocId = id;
  state.page = "kb";
  toast("已新建 · 默认仅人看");
  render();
}

function publishKb() {
  const doc = state.kb.find((d) => d.id === state.kbDocId);
  if (!doc) return;
  if (doc.visibility === "deny_ai") {
    toast("禁给 AI 的资料不能发布挂载");
    return;
  }
  if (doc.visibility === "ai_ok" || doc.visibility === "both") {
    toast("已在 Agent 可挂载集合中");
    return;
  }
  doc.visibility = "ai_ok";
  doc.updated = "刚刚";
  if (doc.folder === "draft") doc.folder = "team";
  if (!doc.agentBody) {
    doc.agentBody = `【认证切片】${doc.title}\n（由人用正文压缩生成 · 演示占位）`;
  }
  if (!doc.provenance) {
    doc.provenance = {
      tier: "S2",
      locator: `certified/${doc.id}.ai.md`,
      version: "v1",
      certifiedBy: "你",
      certifiedAt: "刚刚",
    };
  } else {
    doc.provenance.tier = doc.provenance.tier === "S0" || doc.provenance.tier === "S1" ? "S2" : doc.provenance.tier;
    doc.provenance.certifiedBy = "你";
    doc.provenance.certifiedAt = "刚刚";
    doc.provenance.version = doc.provenance.version === "draft" ? "v1" : doc.provenance.version;
    if (!String(doc.provenance.locator).includes(".ai.")) {
      doc.provenance.locator = `certified/${doc.id}.ai.md`;
    }
  }
  if (!doc.trail) doc.trail = [];
  doc.trail.push({
    at: "刚刚",
    actor: "你",
    event: "认证发布",
    detail: "写出 Agent 切片 · visibility→ai_ok · 可挂载",
  });
  toast("已认证发布 · Agent 可挂载 · 已记账");
  state.kbPlane = "agent";
  render();
}

function switchToTeam(teamId) {
  const id = resolveChannelAlias(teamId);
  if (!CHANNELS[id]) return;
  state.teamScope = id;
  state.channelId = id;
  state.chatTab = "channel";
  delete state.unread[id];
  $("app").classList.remove("show-chats");
  state.page = "chat";
  toast(`已切换到 ${CHANNELS[id].name}`);
  render();
}

function switchToChannel(channelId) {
  const id = resolveChannelAlias(channelId);
  if (!CHANNELS[id]) return;
  state.channelId = id;
  syncTeamScopeFromChannel(id);
  delete state.unread[id];
  $("app").classList.remove("show-chats");
  state.page = "chat";
  render();
}

function bind() {
  $("btn-menu").addEventListener("click", openNav);
  $("nav-scrim").addEventListener("click", closeNav);

  $("app").addEventListener("change", (e) => {
    if (e.target?.id === "pcw-import") {
      applyImportToDraft(e.target.value);
    }
  });

  // 整壳委托：避免子节点/重绘导致点了没反应
  $("app").addEventListener("click", (e) => {
    const teamEl = e.target.closest("[data-team-scope]");
    if (teamEl) {
      e.preventDefault();
      switchToTeam(teamEl.getAttribute("data-team-scope"));
      return;
    }

    const channelEl = e.target.closest("[data-channel]");
    if (channelEl && !e.target.closest("[data-page]")) {
      e.preventDefault();
      switchToChannel(channelEl.getAttribute("data-channel"));
      return;
    }

    const wbMode = e.target.closest("[data-workbench-mode]");
    if (wbMode) {
      e.preventDefault();
      const next = wbMode.getAttribute("data-workbench-mode");
      state.workbenchMode = next === "evolve" ? "evolve" : "factory";
      $("app").classList.toggle("show-chats", false);
      render();
      if (state.workbenchMode === "factory" && typeof FactoryBench !== "undefined") {
        FactoryBench.ensureDemo().catch(() => {});
      }
      return;
    }

    if (typeof FactoryBench !== "undefined" && FactoryBench.handleClick(e)) {
      return;
    }
    if (typeof EvolveBench !== "undefined" && EvolveBench.handleClick(e)) {
      return;
    }

    const kbTab = e.target.closest("[data-kb-editor-tab]");
    if (kbTab && SITE_GATE === "yiagent") {
      e.preventDefault();
      const next = kbTab.getAttribute("data-kb-editor-tab");
      state.kbEditorTab = ["manage", "scoring", "taxonomy"].includes(next) ? next : "manage";
      state.page = "kb";
      render();
      if (state.kbEditorTab === "manage" && typeof KbManage !== "undefined") {
        KbManage.loadList();
      }
      return;
    }
    if (SITE_GATE === "yiagent" && typeof KbManage !== "undefined" && KbManage.handleClick(e)) {
      return;
    }

    const navEl = e.target.closest("#nav-scroll [data-page], #ws-actions [data-page], #ws-body [data-page]");
    if (navEl) {
      const page = navEl.getAttribute("data-page");
      const openDm = navEl.getAttribute("data-open-dm");
      const openProject = navEl.getAttribute("data-open-project");
      const openProgress = navEl.getAttribute("data-open-progress");
      if (openDm) {
        const id = resolveChannelAlias(openDm);
        state.channelId = id;
        syncTeamScopeFromChannel(id);
      }
      if (openProject) {
        const p = state.projects.find((x) => x.id === openProject);
        if (p?.category) state.projectCategory = p.category;
        state.projectFilter = "全部";
        state.projectId = openProject;
        state.projectOpen = true;
      }
      if (openProgress) {
        openProjectProgress(openProgress);
        return;
      }
      setPage(page);
      return;
    }

    if (e.target.closest("#btn-menu") || e.target.id === "btn-menu") return;
    if (e.target.closest("#nav-scrim") || e.target.id === "nav-scrim") return;

    const t = e.target.closest(
      "[data-chat-tab],[data-kb-folder],[data-kb-plane],[data-kb-doc],[data-kb-status],[data-approve],[data-reject],[data-project-open],[data-open-progress],[data-progress-project],[data-progress-goal],[data-progress-fold],[data-progress-fold-all],[data-progress-jump],[data-review-pack],[data-review-stage],[data-review-verdict],[data-project-channel],[data-project-channel-setup],[data-project-channel-edit],[data-pcw-toggle],[data-org-tab],[data-org-channel],[data-org-toggle-member],[data-org-del-channel],[data-org-del-agent],[data-dna-role],[data-dna-slot],#btn-org-add-channel,#btn-org-add-agent,#btn-org-save-ch,#btn-pcw-save,#btn-pcw-cancel,[data-project-filter],[data-project-category],[data-project-status],[data-schedule-day],[data-todo-toggle],[data-todo-del],[data-todo-filter],[data-settings-tab],[data-provider-edit],[data-provider-save],[data-provider-clear],[data-provider-enable],[data-asset-ssh],[data-asset-copy],[data-asset-probe],[data-secret-copy],[data-secret-reveal],[data-tool],[data-mention-pick],#send,#btn-toggle-chats,#btn-kb-folders,#btn-kb-new,#btn-kb-upload,#btn-kb-new2,#btn-kb-publish,#btn-kb-publish2,#btn-kb-edit,#btn-kb-share,#btn-crm-add,#btn-project-new,#btn-project-new-h,#btn-project-task,#btn-strat-edit,#btn-strat-edit-h,#btn-todo-add,#btn-todo-add-h,#btn-schedule-today,#btn-project-back,#btn-project-back2,#btn-project-edit,#btn-project-edit2,#btn-project-edit3,#btn-project-edit-save,#btn-project-edit-save2,#btn-project-edit-cancel,#btn-project-edit-cancel2,#btn-project-edit-cancel3,#btn-project-archive,#btn-project-archive2,#btn-project-archive-h,#btn-project-unarchive,#btn-project-unarchive2,#btn-project-unarchive-h,#btn-project-del,#btn-project-del2,#btn-project-del-h,#btn-providers-reload,#btn-providers-reload-h,#btn-it-secrets-reload,#btn-it-secrets-reload-h,#btn-provider-cancel"
    );
    if (!t) return;

    if (t.dataset.mentionPick) {
      applyMentionPick(t.dataset.mentionPick);
      return;
    }

    if (t.dataset.reviewPack) {
      state.reviewPackId = t.dataset.reviewPack;
      state.reviewStage = "demand";
      state.reviewNote = "";
      render();
      return;
    }
    if (t.dataset.reviewStage) {
      const noteEl = $("review-note");
      if (noteEl) state.reviewNote = noteEl.value;
      state.reviewStage = t.dataset.reviewStage;
      render();
      return;
    }
    if (t.dataset.reviewVerdict) {
      const noteEl = $("review-note");
      if (noteEl) state.reviewNote = noteEl.value;
      setReviewDecision(state.reviewStage, t.dataset.reviewVerdict);
      const labels = { pass: "已通过本步", revise: "已标记退回补齐", reject: "已驳回本步" };
      toast(labels[t.dataset.reviewVerdict] || "已记录");
      const idx = REVIEW_STAGES.findIndex((s) => s.id === state.reviewStage);
      if (t.dataset.reviewVerdict === "pass" && idx >= 0 && idx < REVIEW_STAGES.length - 1) {
        state.reviewStage = REVIEW_STAGES[idx + 1].id;
      }
      render();
      return;
    }

    if (t.dataset.openProgress) {
      openProjectProgress(t.dataset.openProgress);
      return;
    }
    if (t.dataset.progressProject) {
      state.progressProjectId = t.dataset.progressProject;
      state.progressGoalLetter = "A";
      state.progressFold = {};
      render();
      return;
    }
    if (t.dataset.progressGoal) {
      state.progressGoalLetter = t.dataset.progressGoal.toString().slice(0, 1).toUpperCase();
      state.progressFold = {};
      render();
      return;
    }
    if (t.dataset.progressFold) {
      const id = t.dataset.progressFold;
      if (!state.progressFold) state.progressFold = {};
      // aria-expanded=true → 即将折叠（fold=true）
      state.progressFold[id] = t.getAttribute("aria-expanded") === "true";
      render();
      return;
    }
    if (t.dataset.progressFoldAll) {
      const raw = state.projects.find((p) => p.id === state.progressProjectId);
      const cur = enrichProject(raw);
      const collapse = t.dataset.progressFoldAll === "collapse";
      setProgressFoldAll(collapse, cur?.progressTree || []);
      render();
      return;
    }
    if (t.dataset.progressJump) {
      jumpProgressNode(t.dataset.progressJump);
      return;
    }

    if (t.dataset.projectChannelSetup) {
      startProjectChannelWizard(t.dataset.projectChannelSetup);
      return;
    }
    if (t.dataset.projectChannelEdit) {
      startProjectChannelWizard(t.dataset.projectChannelEdit, { edit: true });
      return;
    }
    if (t.dataset.pcwToggle) {
      e.preventDefault();
      toggleDraftMember(t.dataset.pcwToggle);
      return;
    }
    if (t.id === "btn-pcw-save") {
      saveProjectChannelWizard();
      return;
    }
    if (t.id === "btn-pcw-cancel") {
      state.projectChannelWizard = false;
      state.projectChannelDraft = null;
      render();
      return;
    }

    if (t.dataset.projectChannel) {
      openProjectChannel(t.dataset.projectChannel);
      return;
    }

    if (t.dataset.orgTab) {
      state.orgTab = t.dataset.orgTab;
      render();
      return;
    }
    if (t.dataset.dnaRole) {
      state.dnaRoleId = t.dataset.dnaRole;
      state.dnaSlotId = state.dnaSlotId || "G1";
      render();
      return;
    }
    if (t.dataset.dnaSlot) {
      state.dnaSlotId = t.dataset.dnaSlot;
      render();
      return;
    }
    if (t.dataset.orgChannel) {
      state.orgFocusChannelId = t.dataset.orgChannel;
      state.orgTab = "channels";
      render();
      return;
    }
    if (t.dataset.orgToggleMember && t.dataset.orgInChannel) {
      e.preventDefault();
      toggleOrgChannelMember(t.dataset.orgInChannel, t.dataset.orgToggleMember);
      return;
    }
    if (t.dataset.orgDelChannel) {
      if (window.confirm("确认删除该频道？成员库中的 Agent 不会被删。")) {
        deleteOrgChannel(t.dataset.orgDelChannel);
      }
      return;
    }
    if (t.dataset.orgDelAgent) {
      if (window.confirm("确认删除该成员？将从所有频道移除。")) {
        deleteOrgAgent(t.dataset.orgDelAgent);
      }
      return;
    }
    if (t.id === "btn-org-add-channel") {
      createOrgChannel();
      return;
    }
    if (t.id === "btn-org-add-agent") {
      createOrgAgent();
      return;
    }
    if (t.id === "btn-org-save-ch") {
      const focus = state.orgFocusChannelId;
      const name = $("org-ch-name")?.value;
      renameOrgChannel(focus, name);
      toast("频道名称已保存");
      return;
    }

    if (t.id === "btn-toggle-chats") {
      $("app").classList.toggle("show-chats");
      renderHead();
      return;
    }
    if (t.dataset.assetSsh) {
      connectAssetSsh(t.dataset.assetSsh);
      return;
    }
    if (t.dataset.assetCopy) {
      const a = state.assets.find((x) => x.id === t.dataset.assetCopy);
      if (!a) return;
      copyText(sshCommandFor(a)).then((ok) => toast(ok ? "SSH 命令已复制" : "复制失败"));
      return;
    }
    if (t.dataset.assetProbe) {
      probeAsset(t.dataset.assetProbe);
      return;
    }
    if (t.dataset.secretCopy) {
      const s = state.itSecrets.find((x) => x.id === t.dataset.secretCopy);
      if (!s?.value) {
        toast("无可用 Key");
        return;
      }
      copyText(s.value).then((ok) => toast(ok ? `${s.name} 已复制` : "复制失败"));
      return;
    }
    if (t.dataset.secretReveal) {
      const id = t.dataset.secretReveal;
      state.itSecretReveal = { ...state.itSecretReveal, [id]: !state.itSecretReveal[id] };
      render();
      return;
    }
    if (t.id === "btn-it-secrets-reload" || t.id === "btn-it-secrets-reload-h") {
      loadItSecrets().then(() => {
        toast(state.itSecretsError ? "密钥刷新失败" : "IT 资产密钥已刷新");
        render();
      });
      return;
    }
    if (t.dataset.settingsTab) {
      state.settingsTab = t.dataset.settingsTab;
      state.providerEditId = null;
      state.providerDraftKey = "";
      render();
      if (state.settingsTab === "providers") {
        loadProviders().then(() => {
          if (state.page === "settings") render();
        });
      }
      return;
    }
    if (t.id === "btn-providers-reload" || t.id === "btn-providers-reload-h") {
      loadProviders().then(() => {
        toast(state.providersMeta.bridgeOk ? "Provider 已刷新" : "Bridge 仍不可用");
        render();
      });
      return;
    }
    if (t.id === "btn-provider-cancel") {
      state.providerEditId = null;
      state.providerDraftKey = "";
      render();
      return;
    }
    if (t.dataset.providerEdit) {
      const p = state.providers.find((x) => x.id === t.dataset.providerEdit);
      state.providerEditId = t.dataset.providerEdit;
      state.providerDraftKey = "";
      state.providerDraftModel = p?.model || state.providersMeta.model || "composer-2.5";
      render();
      return;
    }
    if (t.dataset.providerEnable) {
      saveProvider(t.dataset.providerEnable, { enabled: true })
        .then(() => {
          toast("已设为启用 Provider");
          render();
        })
        .catch((e) => toast("失败 · " + (e.message || e)));
      return;
    }
    if (t.dataset.providerClear) {
      if (!window.confirm("确认清除该 Provider 的 API Key？")) return;
      saveProvider(t.dataset.providerClear, { clearKey: true })
        .then(() => {
          state.providerEditId = null;
          toast("Key 已清除");
          render();
        })
        .catch((e) => toast("失败 · " + (e.message || e)));
      return;
    }
    if (t.dataset.providerSave) {
      const id = t.dataset.providerSave;
      const keyEl = $("pe-prov-key");
      const modelEl = $("pe-prov-model");
      const patch = {};
      const key = (keyEl?.value || "").trim();
      if (key) patch.apiKey = key;
      if (modelEl?.value) patch.model = modelEl.value;
      if (!patch.apiKey && !patch.model) {
        toast("无变更");
        return;
      }
      saveProvider(id, patch)
        .then(() => {
          state.providerEditId = null;
          state.providerDraftKey = "";
          toast("已保存到本机 bridge");
          render();
        })
        .catch((e) => toast("保存失败 · " + (e.message || e)));
      return;
    }
    if (t.id === "btn-project-back" || t.id === "btn-project-back2") {
      closeProjectDetail();
      return;
    }
    if (t.id === "btn-project-edit" || t.id === "btn-project-edit2" || t.id === "btn-project-edit3") {
      state.projectEditing = true;
      render();
      return;
    }
    if (t.id === "btn-project-edit-cancel" || t.id === "btn-project-edit-cancel2" || t.id === "btn-project-edit-cancel3") {
      state.projectEditing = false;
      render();
      return;
    }
    if (t.id === "btn-project-edit-save" || t.id === "btn-project-edit-save2") {
      saveProjectEdit();
      return;
    }
    if (t.id === "btn-project-archive" || t.id === "btn-project-archive2" || t.id === "btn-project-archive-h") {
      archiveCurrentProject();
      return;
    }
    if (
      t.id === "btn-project-unarchive" ||
      t.id === "btn-project-unarchive2" ||
      t.id === "btn-project-unarchive-h"
    ) {
      unarchiveCurrentProject();
      return;
    }
    if (t.id === "btn-project-del" || t.id === "btn-project-del2" || t.id === "btn-project-del-h") {
      deleteCurrentProject();
      return;
    }
    if (t.dataset.projectOpen) {
      openProjectDetail(t.dataset.projectOpen);
      return;
    }
    if (t.id === "btn-schedule-today") {
      state.scheduleDay = ymd(new Date());
      render();
      return;
    }
    if (t.id === "btn-todo-add" || t.id === "btn-todo-add-h") {
      addTodo();
      return;
    }
    if (t.dataset.scheduleDay) {
      state.scheduleDay = t.dataset.scheduleDay;
      render();
      return;
    }
    if (t.dataset.todoFilter) {
      state.todoFilter = t.dataset.todoFilter;
      render();
      return;
    }
    if (t.dataset.todoToggle) {
      toggleTodo(t.dataset.todoToggle);
      return;
    }
    if (t.dataset.todoDel) {
      deleteTodo(t.dataset.todoDel);
      return;
    }
    if (t.id === "btn-kb-folders") {
      $("app").classList.toggle("show-folders");
      return;
    }
    if (t.id === "btn-kb-new" || t.id === "btn-kb-new2") {
      newKbDoc();
      return;
    }
    if (t.id === "btn-project-new" || t.id === "btn-project-new-h") {
      newProject();
      return;
    }
    if (t.id === "btn-strat-edit" || t.id === "btn-strat-edit-h") {
      toast("调整战略目标 · 演示占位");
      return;
    }
    if (t.dataset.chatTab) {
      state.chatTab = t.dataset.chatTab;
      render();
      return;
    }
    if (t.dataset.projectFilter) {
      state.projectFilter = t.dataset.projectFilter;
      render();
      return;
    }
    if (t.dataset.projectCategory) {
      state.projectCategory = t.dataset.projectCategory;
      render();
      return;
    }
    if (t.dataset.projectStatus && t.dataset.projectId) {
      (async () => {
        try {
          await patchProjectApi(t.dataset.projectId, { status: t.dataset.projectStatus });
          await loadProjects();
          toast("状态已更新 · 已落库");
          render();
        } catch (e) {
          toast("更新失败 · " + (e.message || e));
        }
      })();
      return;
    }
    if (t.dataset.kbPlane) {
      state.kbPlane = t.dataset.kbPlane;
      if (t.dataset.kbDoc) state.kbDocId = t.dataset.kbDoc;
      if (state.kbPlane === "agent" && state.kbFolder === "deny") state.kbFolder = "all";
      $("app").classList.remove("show-folders");
      render();
      return;
    }
    if (t.dataset.kbFolder) {
      state.kbFolder = t.dataset.kbFolder;
      $("app").classList.remove("show-folders");
      render();
      return;
    }
    if (t.dataset.kbDoc) {
      state.kbDocId = t.dataset.kbDoc;
      $("app").classList.add("show-preview");
      render();
      return;
    }
    if (t.dataset.kbStatus !== undefined) {
      state.kbStatus = t.dataset.kbStatus || null;
      render();
      return;
    }
    if (t.dataset.approve) decide(t.dataset.approve, true);
    if (t.dataset.reject) decide(t.dataset.reject, false);
    if (t.id === "send") send();
    if (t.dataset.tool === "mention") {
      openMentionPicker();
      return;
    }
    if (t.dataset.tool) {
      toast(`${t.dataset.tool === "attach" ? "附件" : "转任务"} · 演示占位`);
    }
    if (t.id === "btn-kb-upload") toast("上传 · 演示占位（可选 PDF / Markdown）");
    if (t.id === "btn-kb-publish" || t.id === "btn-kb-publish2") publishKb();
    if (t.id === "btn-kb-edit") toast("编辑器 · 演示占位");
    if (t.id === "btn-kb-share") toast("已复制分享链接（演示）");
    if (t.id === "btn-crm-add") toast("新建客户 · 演示占位");
    if (t.id === "btn-project-task") toast("已拆任务草稿到对应 Team（演示）");
  });

  $("ws-body").addEventListener("input", (e) => {
    if (e.target.id === "review-note") {
      state.reviewNote = e.target.value;
      return;
    }
    if (e.target.id === "input") {
      state.draft = e.target.value;
      e.target.style.height = "auto";
      e.target.style.height = Math.min(120, e.target.scrollHeight) + "px";
      const sendBtn = $("send");
      if (sendBtn) sendBtn.disabled = !state.draft.trim() || !!state.typing;
      const caret = e.target.selectionStart ?? state.draft.length;
      const atq = parseAtQuery(state.draft, caret);
      if (atq) {
        state.mentionOpen = true;
        state.mentionAt = atq.start;
        state.mentionQuery = atq.query;
        state.mentionCaretEnd = caret;
        const n = filteredMentionCandidates().length;
        if (state.mentionIndex >= n) state.mentionIndex = Math.max(0, n - 1);
        patchMentionMenu();
      } else if (state.mentionOpen) {
        closeMentionMenu();
      }
    }
    if (e.target.id === "chat-q") {
      state.chatQ = e.target.value;
      render();
      $("chat-q")?.focus();
    }
    if (e.target.id === "kb-q") {
      state.kbQ = e.target.value;
      render();
      $("kb-q")?.focus();
    }
  });

  $("ws-body").addEventListener("keydown", (e) => {
    if (e.target.id !== "input") return;
    if (state.mentionOpen) {
      const items = filteredMentionCandidates();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!items.length) return;
        state.mentionIndex = (state.mentionIndex + 1) % items.length;
        patchMentionMenu();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        if (!items.length) return;
        state.mentionIndex = (state.mentionIndex - 1 + items.length) % items.length;
        patchMentionMenu();
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        closeMentionMenu();
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        state.draft = e.target.value;
        state.mentionCaretEnd = e.target.selectionStart;
        if (items[state.mentionIndex]) applyMentionPick(items[state.mentionIndex].name);
        return;
      }
      if (e.key === "Tab" && items[state.mentionIndex]) {
        e.preventDefault();
        state.draft = e.target.value;
        state.mentionCaretEnd = e.target.selectionStart;
        applyMentionPick(items[state.mentionIndex].name);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      state.draft = e.target.value;
      send();
    }
  });
}

/** 供 factory-bench.js 回调重绘 */
window.render = render;
window.toast = toast;

bind();
(async () => {
  state.assets = loadAssets();
  await Promise.all([loadProjects(), loadItSecrets()]);
  render();
  if (
    SITE_GATE === "yiagent" &&
    state.page === "chat" &&
    state.workbenchMode === "factory" &&
    typeof FactoryBench !== "undefined"
  ) {
    FactoryBench.ensureDemo().catch(() => {});
  }
})();

