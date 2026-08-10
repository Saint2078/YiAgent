/**
 * 产品经理可外挂知识库包 · G3 挂载对照（非改 G1 身份）
 * 约定：角色基因组不变；换 KB = 换公司/场景知识，用于 A/B 对照。
 */
window.YIAGENT_KB_PACKS = {
  product_manager: {
    role_id: "product_manager",
    role_short: "产品经理",
    note: "G1–G2–G4–G5 共用 product_manager 基因组；仅 G3 外挂下方知识库做对照。",
    default_kb: "kb_enterprise_internal",
    packs: [
      {
        id: "kb_enterprise_internal",
        title: "企业内部软件知识库",
        short: "企业内",
        layer: "02-公司层 · 内部系统",
        taxonomy: "company",
        summary: "员工/业务侧系统：SSO、权限、审计、主数据、跨部门 UAT、变更窗口。",
        mount_text: [
          "【G3 挂载 · 企业内部软件知识库】",
          "适用：采购/审批/主数据/排班/MES·ERP 模块等员工与职能用户系统。",
          "用户：业务部门、一线操作、财务/审计/安全等内部干系人（非公网 C 端）。",
          "硬约束：公司 SSO；操作可审计；预算/主数据口径不可擅自改；全公司 rollout 需人闸。",
          "Non-Goals 常见刀：外网影子 SaaS、外包商直开账号、跳过预算校验的「拍一拍」、无审计日志上线。",
          "验收：角色×权限路径、审计日志、UAT 部门签字、灰度范围。",
          "对内发布：写给业务的变更说明（谁受益、怎么用、何时灰度），不是获客文案。",
          "denylist: 用增长黑客话术替代合规；把内部工程隐喻当对客主叙事。",
        ].join("\n"),
      },
      {
        id: "kb_external_gtm",
        title: "外向产品 / GTM 知识库",
        short: "外向",
        layer: "01-行业层 · 对外产品",
        taxonomy: "industry",
        summary: "对外产品与增长：细分用户、漏斗、竞品替代、定价信号、对外承诺人闸。",
        mount_text: [
          "【G3 挂载 · 外向产品/GTM 知识库】",
          "适用：面向外部客户或开发者的产品表面、官网能力、套餐与增长实验。",
          "用户：外部买家/终端用户/社区开发者；内部员工不是主用户。",
          "硬约束：对外承诺经人审；品牌/付费表述升级；隐私与公开数据边界。",
          "Non-Goals 常见刀：未验证的付费墙、与开源主叙事冲突的私有锁死、无冻结 Demo 的功能许诺。",
          "验收：可点路径或冻结证据；北向指标/漏斗可观测；对外话术与能力一致。",
          "发布说明：用户为何在意（press-release 门禁）；写不出则暂停需求。",
          "denylist: 把内部审批流当卖点堆砌；未人审的商务承诺。",
        ].join("\n"),
      },
    ],
  },
};

window.YIAGENT_KB_PACKS_listForRole = function (roleId) {
  const block = window.YIAGENT_KB_PACKS?.[roleId];
  return block?.packs || [];
};

window.YIAGENT_KB_PACKS_get = function (roleId, kbId) {
  const packs = window.YIAGENT_KB_PACKS_listForRole(roleId);
  if (!packs.length) return null;
  return packs.find((p) => p.id === kbId) || packs[0] || null;
};
