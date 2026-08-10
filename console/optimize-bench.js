/**
 * US-002 · 优化闭环（产品可交互原型）
 * 纯前端可交互；经 console Docker 提供，不裸跑本地服务。
 */
const OptimizeBench = (() => {
  const LS = "yiagent-optimize-bench-v1";
  const CASES = [
    { id: "c_deep", title: "多跳检索依据", weak: "深搜不足", before: 52 },
    { id: "c_detail", title: "边界与反例说明", weak: "详解不够", before: 61 },
    { id: "c_sum", title: "长文压缩不失真", weak: "总结丢要点", before: 58 },
  ];
  const FIXES = {
    深搜不足: { from: "g3.shallow_summary", to: "g3.deep_cite", slot: "G3", delta: 19 },
    详解不够: { from: "g5.brief_only", to: "g5.edge_cases", slot: "G5", delta: 17 },
    总结丢要点: { from: "g2.casual", to: "g2.structured", slot: "G2", delta: 15 },
  };

  const st = {
    step: 1,
    caseId: null,
    proposalApplied: false,
    after: null,
  };

  function load() {
    try {
      Object.assign(st, JSON.parse(localStorage.getItem(LS) || "{}"));
    } catch {
      /* ignore */
    }
  }
  function save() {
    try {
      localStorage.setItem(LS, JSON.stringify(st));
    } catch {
      /* ignore */
    }
  }
  load();

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function currentCase() {
    return CASES.find((c) => c.id === st.caseId) || null;
  }

  /** 同 case+weak → 同 after，满足 E2「同输入稳定」 */
  function scoreAfter(c, fix) {
    if (!c || !fix) return null;
    return Math.min(98, c.before + (fix.delta || 18));
  }

  function render() {
    const c = currentCase();
    const fix = c ? FIXES[c.weak] : null;
    const steps = [
      ["1", "失败样例"],
      ["2", "弱点"],
      ["3", "优化提案"],
      ["4", "前后对比"],
    ];
    return `<div class="pad opt-bench">
      <div class="tags" style="margin-bottom:12px">
        <span class="tag blue">US-002</span>
        <span class="tag">产品 · 可交互原型</span>
        <span class="tag">Docker only</span>
      </div>
      <div class="card" style="margin-bottom:12px">
        <div class="meta" style="margin-bottom:8px">优化闭环</div>
        <div class="list" style="gap:8px;flex-wrap:wrap">
          ${steps
            .map(
              ([n, lab], i) =>
                `<button type="button" class="chip-btn ${st.step === i + 1 ? "active" : ""}" data-opt-step="${i + 1}">${n}. ${lab}</button>`
            )
            .join("")}
        </div>
      </div>
      ${st.step === 1 ? renderStep1() : ""}
      ${st.step === 2 ? renderStep2(c) : ""}
      ${st.step === 3 ? renderStep3(c, fix) : ""}
      ${st.step === 4 ? renderStep4(c, fix) : ""}
    </div>`;
  }

  function renderStep1() {
    return `<div class="card">
      <h3 style="margin:0 0 8px;font-size:15px">选择失败样例</h3>
      <p class="meta">点击一道薄弱题进入下一步（本地可交互，不调 API）。也可先从单基因台跑完再回来优化。</p>
      <div class="list" style="margin:8px 0 12px;gap:8px">
        <button class="btn ghost" type="button" data-page="chat">从单基因工作台带回失败题（示意联通）</button>
      </div>
      <div class="list" style="flex-direction:column;align-items:stretch;margin-top:12px;gap:8px">
        ${CASES.map(
          (c) => `<button type="button" class="btn ${st.caseId === c.id ? "primary" : "ghost"}" data-opt-pick="${c.id}" style="justify-content:space-between">
            <span>${esc(c.title)}</span>
            <span class="meta">均分 ${c.before}</span>
          </button>`
        ).join("")}
      </div>
    </div>`;
  }

  function renderStep2(c) {
    if (!c) {
      return `<div class="card"><div class="empty">请先选题</div>
        <button class="btn ghost" type="button" data-opt-step="1" style="margin-top:10px">返回选题</button></div>`;
    }
    return `<div class="card">
      <h3 style="margin:0 0 8px;font-size:15px">弱点标注</h3>
      <p>题目：<strong>${esc(c.title)}</strong></p>
      <p>判定弱点：<span class="tag" style="margin-left:6px">${esc(c.weak)}</span></p>
      <p class="meta">可改弱点标签（示意）：</p>
      <div class="list" style="gap:8px;margin-top:8px;flex-wrap:wrap">
        ${["深搜不足", "详解不够", "总结丢要点"]
          .map(
            (w) =>
              `<button type="button" class="chip-btn ${c.weak === w ? "active" : ""}" data-opt-weak="${esc(w)}">${esc(w)}</button>`
          )
          .join("")}
      </div>
      <div class="list proj-actions" style="margin-top:14px">
        <button class="btn primary" type="button" data-opt-step="3">生成优化提案</button>
        <button class="btn ghost" type="button" data-opt-step="1">换题</button>
      </div>
    </div>`;
  }

  function renderStep3(c, fix) {
    if (!c || !fix) {
      return `<div class="card"><div class="empty">缺提案上下文</div></div>`;
    }
    return `<div class="card">
      <h3 style="margin:0 0 8px;font-size:15px">优化提案</h3>
      <p class="meta">槽位 ${esc(fix.slot)}</p>
      <p>将等位 <code>${esc(fix.from)}</code> → <code>${esc(fix.to)}</code></p>
      <p class="meta">复测 reps=3（示意）</p>
      <div class="list proj-actions" style="margin-top:14px">
        <button class="btn primary" type="button" data-opt-apply>应用并复测</button>
        <button class="btn ghost" type="button" data-opt-step="2">返回弱点</button>
      </div>
      ${st.proposalApplied ? `<p class="meta" style="margin-top:10px;color:var(--ok,#3ecf8e)">已应用</p>` : ""}
    </div>`;
  }

  function buildContract(c, fix) {
    if (!c || !fix) return null;
    const after = st.after != null ? st.after : scoreAfter(c, fix);
    return {
      case_id: c.id,
      weakness: c.weak,
      scores_before: { mean: c.before, reps: 3 },
      scores_after: { mean: after, reps: 3 },
      proposal: {
        slot: fix.slot,
        from_allele: fix.from,
        to_allele: fix.to,
        rationale: `弱点「${c.weak}」→ 替换 ${fix.slot} 等位`,
      },
      delta: after - c.before,
    };
  }

  function renderStep4(c, fix) {
    if (!c) return `<div class="card"><div class="empty">请先完成前序步骤</div></div>`;
    const after = st.after != null ? st.after : c.before;
    const delta = after - c.before;
    const contract = buildContract(c, fix);
    return `<div class="card">
      <h3 style="margin:0 0 8px;font-size:15px">前后对比</h3>
      <table class="opt-table" style="width:100%;border-collapse:collapse;font-size:14px">
        <thead><tr><th align="left">题</th><th>前</th><th>后</th><th>Δ</th></tr></thead>
        <tbody>
          <tr>
            <td>${esc(c.title)}</td>
            <td>${c.before}</td>
            <td><strong>${after}</strong></td>
            <td style="color:${delta >= 0 ? "#3ecf8e" : "#d4785a"}">${delta >= 0 ? "+" : ""}${delta}</td>
          </tr>
        </tbody>
      </table>
      ${fix ? `<p class="meta" style="margin-top:12px">已换：${esc(fix.from)} → ${esc(fix.to)}</p>` : ""}
      ${
        contract
          ? `<details style="margin-top:12px"><summary class="meta">E1 契约预览（可复制）</summary>
        <pre style="white-space:pre-wrap;font-size:12px;background:rgba(0,0,0,.25);padding:10px;border-radius:8px;margin:8px 0 0">${esc(
          JSON.stringify(contract, null, 2)
        )}</pre>
        <button class="btn ghost" type="button" data-opt-copy style="margin-top:8px">复制契约 JSON</button>
      </details>`
          : ""
      }
      <div class="list proj-actions" style="margin-top:14px">
        <button class="btn ghost" type="button" data-opt-reset>重置演示</button>
        <button class="btn primary" type="button" data-opt-step="1">再优化一道</button>
      </div>
    </div>`;
  }

  function handleClick(e) {
    const step = e.target.closest("[data-opt-step]");
    if (step) {
      st.step = Number(step.getAttribute("data-opt-step"));
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    const pick = e.target.closest("[data-opt-pick]");
    if (pick) {
      st.caseId = pick.getAttribute("data-opt-pick");
      st.step = 2;
      st.proposalApplied = false;
      st.after = null;
      const c = currentCase();
      if (c) {
        /* keep weak from case */
      }
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    const weak = e.target.closest("[data-opt-weak]");
    if (weak && st.caseId) {
      const c = currentCase();
      if (c) c.weak = weak.getAttribute("data-opt-weak");
      // mutate CASES entry
      const row = CASES.find((x) => x.id === st.caseId);
      if (row) row.weak = weak.getAttribute("data-opt-weak");
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-opt-apply]")) {
      const c = currentCase();
      if (!c) return true;
      st.proposalApplied = true;
      st.after = scoreAfter(c, FIXES[c.weak]);
      st.step = 4;
      save();
      if (typeof window.toast === "function") window.toast("已应用提案并完成示意复测");
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-opt-reset]")) {
      st.step = 1;
      st.caseId = null;
      st.proposalApplied = false;
      st.after = null;
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-opt-copy]")) {
      const c = currentCase();
      const fix = c ? FIXES[c.weak] : null;
      const contract = buildContract(c, fix);
      if (contract && navigator.clipboard) {
        navigator.clipboard.writeText(JSON.stringify(contract, null, 2)).then(
          () => typeof window.toast === "function" && window.toast("已复制 US-002 契约"),
          () => typeof window.toast === "function" && window.toast("复制失败")
        );
      }
      return true;
    }
    return false;
  }

  return { render, handleClick };
})();
