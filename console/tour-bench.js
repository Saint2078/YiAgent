/**
 * DNA 全链路导览 · 完整可视化原型入口（PURPOSE-YIAGENT-001）
 * 开源叙事 + 四维 → 四菜单可跳转；Docker only。
 */
const TourBench = (() => {
  const STEPS = [
    {
      id: "purpose",
      title: "目的",
      body: "开源项目：用 DNA 做可解释、可迭代、可量化、可溯源的 Agent；提升公司与个人知名度。",
      page: null,
    },
    {
      id: "d3",
      title: "可量化",
      body: "产品经理英雄路径：同一基因组，外挂「企业内 / 外向」知识库对照边界与 Non-Goals（非改身份）。",
      page: "chat",
      label: "打开单基因 · 产品经理",
      genome: "product_manager",
      kb: "kb_enterprise_internal",
    },
    {
      id: "d1",
      title: "可解释",
      body: "基因组双螺旋：G1–G5 槽位与等位可指认；产品经理默认包可对照 G3 挂载。",
      page: "genome",
      label: "打开基因组 · 产品经理",
      genome: "product_manager",
    },
    {
      id: "d2",
      title: "可迭代",
      body: "失败样例 → 弱点 → 提案 → 前后对比；可复制优化契约。",
      page: "optimize",
      label: "打开优化闭环",
    },
    {
      id: "d4",
      title: "可溯源",
      body: "加载基因组后直接会话；显示 trace_ref，可导出实体契约。",
      page: "runagent",
      label: "打开可调用实体",
    },
    {
      id: "d5",
      title: "知名度 · 开源",
      body: "公开仓 Saint2078/YiAgent · 本页可一分钟讲清 DNA 做 Agent。",
      page: null,
      href: "https://github.com/Saint2078/YiAgent",
      label: "打开 GitHub",
    },
  ];

  const st = { step: 0 };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render() {
    const cur = STEPS[st.step] || STEPS[0];
    return `<div class="pad tour-bench">
      <div class="tags" style="margin-bottom:12px">
        <span class="tag blue">导览</span>
        <span class="tag">PURPOSE-YIAGENT-001</span>
        <span class="tag">开源 · 可视化原型</span>
      </div>
      <div class="card" style="margin-bottom:12px">
        <div class="meta" style="margin-bottom:8px">DNA 全链路 · ${st.step + 1}/${STEPS.length}</div>
        <div class="list" style="gap:8px;flex-wrap:wrap">
          ${STEPS.map(
            (s, i) =>
              `<button type="button" class="chip-btn ${i === st.step ? "active" : ""}" data-tour-step="${i}">${i + 1}. ${esc(
                s.title
              )}</button>`
          ).join("")}
        </div>
      </div>
      <div class="card">
        <h2 style="margin:0 0 8px;font-size:1.25rem">${esc(cur.title)}</h2>
        <p style="margin:0 0 14px;line-height:1.55;color:var(--muted,#8aa)">${esc(cur.body)}</p>
        <div class="list proj-actions" style="gap:8px;flex-wrap:wrap">
          ${
            cur.page
              ? `<button class="btn primary" type="button" data-page="${esc(cur.page)}"${
                  cur.genome ? ` data-genome="${esc(cur.genome)}"` : ""
                }${cur.kb ? ` data-kb="${esc(cur.kb)}"` : ""}>${esc(cur.label || "进入")}</button>`
              : ""
          }
          ${
            cur.href
              ? `<a class="btn primary" href="${esc(cur.href)}" target="_blank" rel="noopener">${esc(
                  cur.label || "外链"
                )}</a>`
              : ""
          }
          <button class="btn ghost" type="button" data-tour-prev ${st.step === 0 ? "disabled" : ""}>上一步</button>
          <button class="btn ghost" type="button" data-tour-next ${
            st.step >= STEPS.length - 1 ? "disabled" : ""
          }>下一步</button>
        </div>
      </div>
      <div class="card" style="margin-top:12px">
        <div class="meta">一分钟叙事（可照读）</div>
        <p style="margin:8px 0 0;line-height:1.55">
          YiAgent 把 Agent 当成基因组：槽位里装等位基因。用题库量化谁更好，看图谱解释为什么，失败了换基因再测，最后加载成可调用实体——全程可溯源。项目开源，欢迎复现。
        </p>
      </div>
    </div>`;
  }

  function handleClick(e) {
    const step = e.target.closest("[data-tour-step]");
    if (step) {
      st.step = Number(step.getAttribute("data-tour-step")) || 0;
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-tour-prev]")) {
      st.step = Math.max(0, st.step - 1);
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-tour-next]")) {
      st.step = Math.min(STEPS.length - 1, st.step + 1);
      if (typeof window.render === "function") window.render();
      return true;
    }
    return false;
  }

  return { render, handleClick };
})();
