const WORKER_OPTIONS = [2, 4, 6, 8];
const PRE_REP_OPTIONS = [1, 3, 5];
const CHAMP_REP_OPTIONS = [3, 5, 8, 10];
const QUALIFY_OPTIONS = [1, 2, 3, 5];

const ORAL_EXAMPLES_ZH = [
  "客服拒答越权请求与套取敏感信息",
  "合同风险摘要，并给出可执行修改建议",
  "识别虚假二选一，提出平衡的第三路径",
];
const ORAL_EXAMPLES_EN = [
  "Refuse out-of-scope / sensitive requests as support",
  "Contract risk summary with actionable edits",
  "Spot false dilemmas and offer a third path",
];

const state = {
  lang: "zh",
  models: [],
  apiKey: sessionStorage.getItem("yiagent_api_key") || "",
  model: "k3",
  workers: 4,
  oral: "",
  sessionId: null,
  snap: null,
  targetText: "",
  criteriaText: "",
  passMean: 70,
  qualifyTarget: 3,
  preReps: 3,
  champReps: 5,
  pool: new Set(),
  busy: false,
  pollTimer: null,
  error: null,
  toast: null,
  toastTimer: null,
  localBusyLabel: "",
  showAdvanced: false,
  showLogs: false,
  focusStep: 1,
};

const i18n = {
  zh: {
    brandSub: "组装测试工厂",
    companion: "YiAgent 配套筛选台",
    lang: "EN",
    title: "用基因组筛选 Agent，而不是调一句 prompt",
    lead: "口述你的场景 → 自动生成考题与评分标准 → 组装 G1–G5 候选基因组 → 初筛达标后进入冠军终筛，标出效果 / 稳定 / 均衡最优。",
    hook: "别人调 prompt；我们改基因组。",
    steps: ["口述", "题目", "基因组", "初筛", "冠军", "终筛"],
    s1: "口述你的筛选意图",
    s1help: "用一两句话说明要测什么能力。也可点下方示例一键填入。",
    oral: "场景口述",
    oralPh: "例如：客服在用户套取订单隐私或越权操作时，应如何拒答并引导合规路径…",
    examples: "试试这些",
    model: "模型",
    apiKey: "Kimi Coding Plan Key",
    apiKeyHelp: "仅保存在本机浏览器会话，不会写入服务器磁盘。",
    workers: "并发线程",
    advanced: "高级选项",
    genCase: "生成题目与标准",
    demo: "先看演示（批判思维）",
    demoHint: "无需口述即可浏览完整台面；真测仍需 Key。",
    s2: "核对题目与评分标准",
    s2help: "左侧是给选手看的原题；右侧是裁判标准，不会装进基因组。可直接改字。",
    target: "筛选目标 · 原题",
    criteria: "筛选标准 · 裁判",
    saveCase: "保存修改",
    nextGenome: "下一步：生成基因组",
    s3: "生成初始基因组",
    s3help: "按 G1 身份 · G2 边界 · G3 知识 · G4 能力 · G5 经验 生成多套候选组合。",
    genGenome: "生成 G1–G5 基因组",
    genomes: "候选基因组",
    genomeCount: "套候选",
    nextPre: "下一步：初筛",
    s4: "初筛",
    s4help: "每套基因组测若干次；均分达到合格线即记为合格。凑够合格数就提前结束，省时间。",
    qualify: "要凑齐几个合格",
    preReps: "每套测几次",
    passMean: "合格线（均分）",
    startPre: "开始初筛",
    abort: "停止",
    early: "已提前结束",
    passed: "合格",
    failed: "未过",
    s5: "挑选冠军池",
    s5help: "初筛合格的默认勾选。你也可以把有潜力的未过项加进来，或去掉不想比的。",
    poolSelected: "已选入池",
    selectPassed: "一键只留合格",
    selectAll: "全选",
    clearPool: "清空",
    champReps: "终筛每套测几次",
    startChamp: "开始终筛",
    s6: "终筛结果",
    s6help: "三块金牌可以落在不同基因组上——效果看均分，稳定看波动，均衡看均分减波动。",
    markPerf: "效果最优",
    markStable: "稳定最优",
    markBalanced: "均衡最优",
    markPerfDesc: "均分最高",
    markStableDesc: "波动最小",
    markBalancedDesc: "均分 − 1.5×波动",
    progress: "进度",
    logs: "试次明细",
    hideLogs: "收起明细",
    showLogs: "展开试次明细",
    reset: "新会话",
    resetConfirm: "确定清空当前会话，从头开始？",
    mean: "均分",
    sdv: "波动",
    n: "次数",
    wait: "请稍候",
    runningHint: "正在调用模型生成与裁判，可能需要一两分钟。",
    locked: "完成上一步后解锁",
    emptyPool: "还没有可入池的基因组",
    toastCase: "题目与标准已生成，请核对后继续",
    toastGenome: "基因组已生成，可以开始初筛",
    toastPre: "初筛完成，请确认冠军池",
    toastChamp: "终筛完成，三标已出",
    toastDemo: "演示包已载入",
    toastSaved: "已保存文案",
    keyNeed: "请填写有效的 Kimi Coding Plan API Key",
    oralNeed: "请先写一句口述意图（或点示例）",
    footer: "YiAgent 配套 · 组装测试工厂 · 结果仅供本会话筛选参考",
  },
  en: {
    brandSub: "Assemble Factory",
    companion: "Companion desk for YiAgent",
    lang: "中文",
    title: "Screen agents by genome — not by one prompt",
    lead: "Describe a scenario → generate task & rubric → assemble G1–G5 candidates → prefilter → champion finals with performance / stability / balance marks.",
    hook: "They tune prompts. We edit the genome.",
    steps: ["Brief", "Task", "Genome", "Pre", "Pool", "Final"],
    s1: "Describe what to screen",
    s1help: "One or two sentences. Or tap an example below.",
    oral: "Scenario brief",
    oralPh: "e.g. How support should refuse privacy fishing or out-of-scope asks…",
    examples: "Try these",
    model: "Model",
    apiKey: "Kimi Coding Plan Key",
    apiKeyHelp: "Stored in this browser session only — never written to disk.",
    workers: "Workers",
    advanced: "Advanced",
    genCase: "Generate task & rubric",
    demo: "Load demo (critical thinking)",
    demoHint: "Browse the full desk without a brief; live runs still need a Key.",
    s2: "Review task & rubric",
    s2help: "Left = contestant task. Right = judge rubric (never loaded into the genome). Edit freely.",
    target: "Target · task",
    criteria: "Criteria · judge",
    saveCase: "Save edits",
    nextGenome: "Next: genomes",
    s3: "Generate genomes",
    s3help: "G1 identity · G2 boundaries · G3 knowledge · G4 capability · G5 experience.",
    genGenome: "Generate G1–G5 genomes",
    genomes: "Candidates",
    genomeCount: "candidates",
    nextPre: "Next: prefilter",
    s4: "Prefilter",
    s4help: "Test each genome a few times. Pass when mean ≥ threshold. Stop early once enough pass.",
    qualify: "Pass count to stop",
    preReps: "Reps per genome",
    passMean: "Pass line (mean)",
    startPre: "Start prefilter",
    abort: "Stop",
    early: "Early stop",
    passed: "Pass",
    failed: "Fail",
    s5: "Champion pool",
    s5help: "Passed genomes are checked by default. Add or remove freely.",
    poolSelected: "In pool",
    selectPassed: "Passed only",
    selectAll: "Select all",
    clearPool: "Clear",
    champReps: "Final reps",
    startChamp: "Start finals",
    s6: "Final marks",
    s6help: "Three medals may land on different genomes.",
    markPerf: "Best performance",
    markStable: "Best stability",
    markBalanced: "Best balanced",
    markPerfDesc: "Highest mean",
    markStableDesc: "Lowest variance",
    markBalancedDesc: "mean − 1.5×sdv",
    progress: "Progress",
    logs: "Trial log",
    hideLogs: "Hide trials",
    showLogs: "Show trials",
    reset: "New session",
    resetConfirm: "Clear this session and start over?",
    mean: "mean",
    sdv: "sdv",
    n: "n",
    wait: "Please wait",
    runningHint: "Calling the model for generate + judge — may take a minute or two.",
    locked: "Unlocks after the previous step",
    emptyPool: "No genomes to pool yet",
    toastCase: "Task ready — review then continue",
    toastGenome: "Genomes ready — start prefilter",
    toastPre: "Prefilter done — confirm the pool",
    toastChamp: "Finals done — medals ready",
    toastDemo: "Demo pack loaded",
    toastSaved: "Saved",
    keyNeed: "Enter a valid Kimi Coding Plan API Key",
    oralNeed: "Add a brief (or tap an example)",
    footer: "YiAgent companion · Assemble Factory · session-local results",
  },
};

function t() {
  return i18n[state.lang];
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function phaseRank(phase) {
  const order = [
    "idle",
    "case_ready",
    "genomes_ready",
    "prefiltering",
    "prefilter_done",
    "championing",
    "done",
    "error",
  ];
  const i = order.indexOf(phase || "idle");
  return i < 0 ? 0 : i;
}

/** Map phase → UX step 1..6 */
function currentStep(phase) {
  const r = phaseRank(phase);
  if (r <= 0) return 1;
  if (r === 1) return 3; // case ready → focus genomes (step 2 still editable)
  if (r === 2) return 4;
  if (r === 3) return 4;
  if (r === 4) return 5;
  if (r === 5) return 6;
  if (r >= 6) return 6;
  return 1;
}

function showToast(msg) {
  state.toast = msg;
  if (state.toastTimer) clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    state.toast = null;
    state.toastTimer = null;
    const el = document.getElementById("toast");
    if (el) el.remove();
  }, 4200);
}

function applySnap(snap) {
  state.snap = snap;
  state.sessionId = snap.id;
  if (snap.target_text != null) state.targetText = snap.target_text;
  if (snap.criteria_text != null) state.criteriaText = snap.criteria_text;
  if (Array.isArray(snap.pool)) state.pool = new Set(snap.pool);
  if (snap.pass_mean != null) state.passMean = snap.pass_mean;
  if (snap.qualify_target != null) state.qualifyTarget = snap.qualify_target;
  if (snap.pre_reps != null) state.preReps = snap.pre_reps;
  if (snap.champ_reps != null) state.champReps = snap.champ_reps;
  if (snap.workers != null) state.workers = snap.workers;
  if (snap.model && snap.model !== "demo") state.model = snap.model;
  state.focusStep = currentStep(snap.phase);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    let msg = data.detail || data.error || res.statusText;
    if (Array.isArray(msg)) {
      msg = msg.map((x) => x.msg || JSON.stringify(x)).join("; ");
    } else if (msg && typeof msg === "object") {
      msg = JSON.stringify(msg);
    }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function stopPoll() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function startPoll() {
  stopPoll();
  state.pollTimer = setInterval(async () => {
    if (!state.sessionId) return;
    try {
      const snap = await api(`/api/session/${state.sessionId}`);
      applySnap(snap);
      render();
      if (snap.status !== "running") {
        stopPoll();
        state.busy = false;
        state.localBusyLabel = "";
        const c = t();
        if (snap.phase === "prefilter_done") showToast(c.toastPre);
        if (snap.phase === "done") showToast(c.toastChamp);
        render();
        scrollToStep(state.focusStep);
      }
    } catch (e) {
      state.error = String(e.message || e);
      stopPoll();
      state.busy = false;
      render();
    }
  }, 1200);
}

function readFormIntoState() {
  const oral = document.getElementById("oral-text");
  const key = document.getElementById("api-key");
  const model = document.getElementById("model-select");
  const target = document.getElementById("target-text");
  const criteria = document.getElementById("criteria-text");
  const passMean = document.getElementById("pass-mean");
  if (oral) state.oral = oral.value;
  if (key) {
    state.apiKey = key.value.trim();
    if (state.apiKey) sessionStorage.setItem("yiagent_api_key", state.apiKey);
  }
  if (model) state.model = model.value;
  if (target) state.targetText = target.value;
  if (criteria) state.criteriaText = criteria.value;
  if (passMean) state.passMean = Number(passMean.value) || 70;
}

function scrollToStep(n) {
  requestAnimationFrame(() => {
    document.getElementById(`step-panel-${n}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

async function onGenCase() {
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    render();
    return;
  }
  if (!state.oral.trim() || state.oral.trim().length < 4) {
    state.error = c.oralNeed;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.genCase;
  state.error = null;
  render();
  try {
    const snap = await api("/api/session/case", {
      method: "POST",
      body: JSON.stringify({
        api_key: state.apiKey,
        model: state.model,
        oral: state.oral.trim(),
      }),
    });
    applySnap(snap);
    state.focusStep = 2;
    showToast(c.toastCase);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    state.localBusyLabel = "";
    render();
    scrollToStep(2);
  }
}

async function onDemo() {
  const c = t();
  state.busy = true;
  state.error = null;
  render();
  try {
    const snap = await api("/api/session/demo", { method: "POST", body: "{}" });
    applySnap(snap);
    state.focusStep = 3;
    showToast(c.toastDemo);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    render();
    scrollToStep(3);
  }
}

async function onSaveCase() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  state.busy = true;
  state.error = null;
  render();
  try {
    const snap = await api(`/api/session/${state.sessionId}/case`, {
      method: "PUT",
      body: JSON.stringify({
        target_text: state.targetText,
        criteria_text: state.criteriaText,
      }),
    });
    applySnap(snap);
    showToast(c.toastSaved);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    render();
  }
}

async function onGenGenomes() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.genGenome;
  state.error = null;
  render();
  try {
    await api(`/api/session/${state.sessionId}/case`, {
      method: "PUT",
      body: JSON.stringify({
        target_text: state.targetText,
        criteria_text: state.criteriaText,
      }),
    });
    const snap = await api(`/api/session/${state.sessionId}/genomes`, {
      method: "POST",
      body: JSON.stringify({ api_key: state.apiKey, model: state.model }),
    });
    applySnap(snap);
    state.focusStep = 4;
    showToast(c.toastGenome);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    state.localBusyLabel = "";
    render();
    scrollToStep(4);
  }
}

async function onPrefilter() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.startPre;
  state.error = null;
  render();
  try {
    await api(`/api/session/${state.sessionId}/case`, {
      method: "PUT",
      body: JSON.stringify({
        target_text: state.targetText,
        criteria_text: state.criteriaText,
      }),
    });
    const snap = await api(`/api/session/${state.sessionId}/prefilter/start`, {
      method: "POST",
      body: JSON.stringify({
        api_key: state.apiKey,
        pre_reps: state.preReps,
        qualify_target: state.qualifyTarget,
        pass_mean: state.passMean,
        workers: state.workers,
      }),
    });
    applySnap(snap);
    startPoll();
  } catch (e) {
    state.error = String(e.message || e);
    state.busy = false;
    state.localBusyLabel = "";
  }
  render();
}

async function onAbort() {
  if (!state.sessionId) return;
  try {
    const snap = await api(`/api/session/${state.sessionId}/abort`, {
      method: "POST",
      body: "{}",
    });
    applySnap(snap);
  } catch (e) {
    state.error = String(e.message || e);
  }
  stopPoll();
  state.busy = false;
  state.localBusyLabel = "";
  render();
}

async function syncPool() {
  if (!state.sessionId) return;
  const snap = await api(`/api/session/${state.sessionId}/champion/pool`, {
    method: "POST",
    body: JSON.stringify({ variant_ids: [...state.pool] }),
  });
  applySnap(snap);
}

async function onChampion() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    render();
    return;
  }
  if (state.pool.size === 0) {
    state.error = c.emptyPool;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.startChamp;
  state.error = null;
  render();
  try {
    await syncPool();
    const snap = await api(`/api/session/${state.sessionId}/champion/start`, {
      method: "POST",
      body: JSON.stringify({
        api_key: state.apiKey,
        champ_reps: state.champReps,
        workers: state.workers,
      }),
    });
    applySnap(snap);
    startPoll();
  } catch (e) {
    state.error = String(e.message || e);
    state.busy = false;
    state.localBusyLabel = "";
  }
  render();
}

function onReset() {
  if (state.snap && !window.confirm(t().resetConfirm)) return;
  stopPoll();
  state.sessionId = null;
  state.snap = null;
  state.targetText = "";
  state.criteriaText = "";
  state.pool = new Set();
  state.error = null;
  state.busy = false;
  state.localBusyLabel = "";
  state.focusStep = 1;
  state.showLogs = false;
  render();
  scrollToStep(1);
}

function pills(options, value, dataAttr, disabled) {
  return options
    .map(
      (n) =>
        `<button type="button" class="rep-pill ${value === n ? "active" : ""}" data-${dataAttr}="${n}" ${
          disabled ? "disabled" : ""
        }>${n}</button>`
    )
    .join("");
}

function titleOf(vid, snap) {
  const rows = [...(snap?.champ_summaries || []), ...(snap?.pre_summaries || []), ...(snap?.variants || [])];
  for (const r of rows) {
    const id = r.variant_id || r.id;
    if (id === vid) return r.title || id;
  }
  return vid || "—";
}

function summaryTable(rows, c, marks) {
  if (!rows || !rows.length) return `<p class="empty-hint">—</p>`;
  const markOf = (vid) => {
    const tags = [];
    if (marks?.perf === vid) tags.push(c.markPerf);
    if (marks?.stable === vid) tags.push(c.markStable);
    if (marks?.balanced === vid) tags.push(c.markBalanced);
    return tags.map((x) => `<span class="mark-chip">${escapeHtml(x)}</span>`).join(" ");
  };
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>${escapeHtml(c.genomes)}</th><th>${c.n}</th><th>${c.mean}</th><th>${c.sdv}</th><th></th><th></th></tr></thead>
    <tbody>
      ${rows
        .map(
          (r) => `<tr class="${r.passed ? "row-pass" : ""}">
            <td><strong>${escapeHtml(r.title || r.variant_id)}</strong><div class="mono dim tiny">${escapeHtml(
              r.variant_id
            )}</div></td>
            <td class="mono">${r.n ?? 0}</td>
            <td class="mono score">${r.mean ?? "—"}</td>
            <td class="mono">${r.sdv ?? "—"}</td>
            <td>${
              r.passed === true
                ? `<span class="ok-chip">${c.passed}</span>`
                : r.passed === false
                  ? `<span class="fail-chip">${c.failed}</span>`
                  : ""
            }</td>
            <td>${markOf(r.variant_id)}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  </table></div>`;
}

function stepperHtml(c, focus, unlockedMax) {
  return `<nav class="stepper" aria-label="progress">
    ${c.steps
      .map((label, i) => {
        const n = i + 1;
        const done = n < focus && n <= unlockedMax;
        const active = n === focus;
        const locked = n > unlockedMax;
        return `<button type="button" class="stepper-item ${active ? "active" : ""} ${done ? "done" : ""} ${
          locked ? "locked" : ""
        }" data-goto="${n}" ${locked ? "disabled" : ""}>
          <span class="stepper-num">${done ? "✓" : n}</span>
          <span class="stepper-label">${escapeHtml(label)}</span>
        </button>`;
      })
      .join('<span class="stepper-gap" aria-hidden="true"></span>')}
  </nav>`;
}

function progressBar(done, total) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return `<div class="progress-block">
    <div class="progress-meta mono">${done} / ${total} · ${pct}%</div>
    <div class="progress-track"><i style="width:${pct}%"></i></div>
  </div>`;
}

function unlockedMax(rank, snap) {
  if (rank >= 6) return 6;
  if (rank >= 4) return 6;
  if (rank >= 2) return 4;
  if (rank >= 1) return 3;
  if (snap) return 2;
  return 1;
}

function render() {
  const root = document.getElementById("root");
  const c = t();
  const snap = state.snap;
  const phase = snap?.phase || "idle";
  const rank = phaseRank(phase);
  const running = snap?.status === "running" || state.busy;
  const unlock = unlockedMax(rank, snap);
  const focus = Math.min(state.focusStep, unlock);
  const examples = state.lang === "zh" ? ORAL_EXAMPLES_ZH : ORAL_EXAMPLES_EN;
  const isDemo = snap?.model === "demo";

  root.className = "app-shell console ux";
  root.innerHTML = `
    <header class="topbar">
      <div class="brand-block">
        <div class="brand-mark">Yi<span>Agent</span></div>
        <div class="brand-sub">${escapeHtml(c.brandSub)} · ${escapeHtml(c.companion)}</div>
      </div>
      <div class="topbar-actions">
        <button class="lang-toggle" type="button" id="btn-lang">${c.lang}</button>
        <button class="btn-ghost btn-compact" type="button" id="btn-reset">${c.reset}</button>
      </div>
    </header>

    ${
      running
        ? `<div class="run-sticky" role="status">
            <div>
              <strong>${escapeHtml(state.localBusyLabel || c.wait)}</strong>
              <span class="dim"> · ${escapeHtml(c.runningHint)}</span>
            </div>
            ${
              snap?.status === "running"
                ? `${progressBar(snap.done || 0, snap.total || 0)}
                   <button class="btn-ghost btn-abort btn-compact" type="button" id="btn-abort">${c.abort}</button>`
                : `<div class="spinner" aria-hidden="true"></div>`
            }
          </div>`
        : ""
    }

    ${state.toast ? `<div class="toast" id="toast" role="status">${escapeHtml(state.toast)}</div>` : ""}

    <main class="desk">
      <section class="hero-lite">
        <p class="hook-line">${escapeHtml(c.hook)}</p>
        <h1 class="console-title">${escapeHtml(c.title)}</h1>
        <p class="section-lead">${escapeHtml(c.lead)}</p>
        ${stepperHtml(c, focus, unlock)}
        ${state.error ? `<div class="error-banner" role="alert"><strong>提示</strong> ${escapeHtml(state.error)}</div>` : ""}
      </section>

      <section class="panel stage-panel ${focus === 1 ? "is-focus" : ""} ${unlock < 1 ? "stage-locked" : ""}" id="step-panel-1">
        <div class="stage-head">
          <p class="section-kicker">01</p>
          <h2 class="stage-title">${escapeHtml(c.s1)}</h2>
          <p class="stage-help">${escapeHtml(c.s1help)}</p>
        </div>
        <label class="field-label">${escapeHtml(c.oral)}</label>
        <textarea id="oral-text" class="brief-input brief-input-sm" rows="4" placeholder="${escapeHtml(c.oralPh)}" ${
          running ? "disabled" : ""
        }>${escapeHtml(state.oral)}</textarea>
        <div class="example-row">
          <span class="field-label">${escapeHtml(c.examples)}</span>
          <div class="example-chips">
            ${examples
              .map(
                (ex, i) =>
                  `<button type="button" class="chip" data-example="${i}" ${running ? "disabled" : ""}>${escapeHtml(
                    ex
                  )}</button>`
              )
              .join("")}
          </div>
        </div>
        <div class="cred-grid">
          <div class="run-field">
            <label class="field-label">${escapeHtml(c.model)}</label>
            <select id="model-select" ${running ? "disabled" : ""}>
              ${(state.models.length
                ? state.models
                : [
                    { id: "k3", label: "Kimi 3" },
                    { id: "kimi-k2.6", label: "Kimi 2.6" },
                  ]
              )
                .map(
                  (m) =>
                    `<option value="${m.id}" ${state.model === m.id ? "selected" : ""}>${escapeHtml(
                      m.label || m.id
                    )}</option>`
                )
                .join("")}
            </select>
          </div>
          <div class="run-field run-field-wide">
            <label class="field-label">${escapeHtml(c.apiKey)}</label>
            <input id="api-key" type="password" autocomplete="off" placeholder="sk-..." value="${escapeHtml(
              state.apiKey
            )}" ${running ? "disabled" : ""} />
            <p class="field-hint">${escapeHtml(c.apiKeyHelp)}</p>
          </div>
        </div>
        <details class="advanced" ${state.showAdvanced ? "open" : ""}>
          <summary>${escapeHtml(c.advanced)}</summary>
          <div class="run-field" style="margin-top:0.75rem">
            <label class="field-label">${escapeHtml(c.workers)}</label>
            <div class="rep-pills">${pills(WORKER_OPTIONS, state.workers, "workers", running)}</div>
          </div>
        </details>
        <div class="stage-actions">
          <button class="btn-primary" type="button" id="btn-gen-case" ${running ? "disabled" : ""}>${escapeHtml(
            c.genCase
          )}</button>
          <button class="btn-ghost" type="button" id="btn-demo" ${running ? "disabled" : ""}>${escapeHtml(
            c.demo
          )}</button>
        </div>
        <p class="field-hint">${escapeHtml(c.demoHint)}</p>
      </section>

      <section class="panel stage-panel ${focus === 2 ? "is-focus" : ""} ${unlock < 2 ? "stage-locked" : ""}" id="step-panel-2">
        <div class="stage-head">
          <p class="section-kicker">02</p>
          <h2 class="stage-title">${escapeHtml(c.s2)}</h2>
          <p class="stage-help">${unlock < 2 ? escapeHtml(c.locked) : escapeHtml(c.s2help)}</p>
        </div>
        ${
          unlock >= 2
            ? `<div class="brief-grid">
                <div>
                  <label class="field-label">${escapeHtml(c.target)}</label>
                  <textarea id="target-text" class="brief-input" rows="12" ${running ? "disabled" : ""}>${escapeHtml(
                    state.targetText
                  )}</textarea>
                </div>
                <div>
                  <label class="field-label">${escapeHtml(c.criteria)}</label>
                  <textarea id="criteria-text" class="brief-input" rows="12" ${running ? "disabled" : ""}>${escapeHtml(
                    state.criteriaText
                  )}</textarea>
                </div>
              </div>
              <div class="stage-actions">
                <button class="btn-ghost" type="button" id="btn-save-case" ${running ? "disabled" : ""}>${escapeHtml(
                  c.saveCase
                )}</button>
                <button class="btn-primary" type="button" id="btn-goto-3" ${running ? "disabled" : ""}>${escapeHtml(
                  c.nextGenome
                )}</button>
              </div>`
            : ""
        }
      </section>

      <section class="panel stage-panel ${focus === 3 ? "is-focus" : ""} ${unlock < 3 ? "stage-locked" : ""}" id="step-panel-3">
        <div class="stage-head">
          <p class="section-kicker">03</p>
          <h2 class="stage-title">${escapeHtml(c.s3)}</h2>
          <p class="stage-help">${unlock < 3 ? escapeHtml(c.locked) : escapeHtml(c.s3help)}</p>
        </div>
        ${
          unlock >= 3
            ? `<div class="stage-actions">
                <button class="btn-primary" type="button" id="btn-gen-genome" ${
                  running || isDemo ? "disabled" : ""
                }>${escapeHtml(c.genGenome)}</button>
                ${
                  isDemo
                    ? `<span class="ok-chip">${escapeHtml(c.toastDemo)}</span>
                       <button class="btn-primary" type="button" id="btn-goto-4">${escapeHtml(c.nextPre)}</button>`
                    : snap?.variants?.length
                      ? `<button class="btn-primary" type="button" id="btn-goto-4">${escapeHtml(c.nextPre)}</button>`
                      : ""
                }
              </div>
              ${
                snap?.variants?.length
                  ? `<p class="field-label">${escapeHtml(c.genomes)} · ${snap.variants.length} ${escapeHtml(
                      c.genomeCount
                    )}</p>
                    <div class="genome-list">
                      ${snap.variants
                        .map(
                          (v) => `<div class="genome-card">
                            <strong>${escapeHtml(v.title)}</strong>
                            <span class="mono dim tiny">${escapeHtml(v.id)}</span>
                            <span class="slot-pills">${["G1", "G2", "G3", "G4", "G5"]
                              .map((s) => `<span class="slot-pill">${s}</span>`)
                              .join("")}</span>
                          </div>`
                        )
                        .join("")}
                    </div>`
                  : ""
              }`
            : ""
        }
      </section>

      <section class="panel stage-panel ${focus === 4 ? "is-focus" : ""} ${unlock < 4 ? "stage-locked" : ""}" id="step-panel-4">
        <div class="stage-head">
          <p class="section-kicker">04</p>
          <h2 class="stage-title">${escapeHtml(c.s4)}</h2>
          <p class="stage-help">${unlock < 4 ? escapeHtml(c.locked) : escapeHtml(c.s4help)}</p>
        </div>
        ${
          unlock >= 4
            ? `<div class="param-grid">
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.qualify)}</label>
                  <div class="rep-pills">${pills(QUALIFY_OPTIONS, state.qualifyTarget, "qualify", running)}</div>
                </div>
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.preReps)}</label>
                  <div class="rep-pills">${pills(PRE_REP_OPTIONS, state.preReps, "prereps", running)}</div>
                </div>
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.passMean)}</label>
                  <input id="pass-mean" type="number" min="0" max="100" step="1" value="${state.passMean}" ${
                    running ? "disabled" : ""
                  } />
                </div>
              </div>
              <div class="stage-actions">
                <button class="btn-primary" type="button" id="btn-pre" ${running ? "disabled" : ""}>${escapeHtml(
                  c.startPre
                )}</button>
                ${
                  snap?.early_stopped
                    ? `<span class="ok-chip">${escapeHtml(c.early)} · ${snap.qualified_count || 0}</span>`
                    : ""
                }
              </div>
              ${
                (snap?.pre_summaries || []).length
                  ? summaryTable(snap.pre_summaries, c, null)
                  : running
                    ? progressBar(snap?.done || 0, snap?.total || 0)
                    : ""
              }`
            : ""
        }
      </section>

      <section class="panel stage-panel ${focus === 5 ? "is-focus" : ""} ${unlock < 5 ? "stage-locked" : ""}" id="step-panel-5">
        <div class="stage-head">
          <p class="section-kicker">05</p>
          <h2 class="stage-title">${escapeHtml(c.s5)}</h2>
          <p class="stage-help">${unlock < 5 ? escapeHtml(c.locked) : escapeHtml(c.s5help)}</p>
        </div>
        ${
          unlock >= 5
            ? `<div class="pool-toolbar">
                <span class="ok-chip">${escapeHtml(c.poolSelected)} ${state.pool.size}</span>
                <button type="button" class="chip" id="btn-pool-passed" ${running ? "disabled" : ""}>${escapeHtml(
                  c.selectPassed
                )}</button>
                <button type="button" class="chip" id="btn-pool-all" ${running ? "disabled" : ""}>${escapeHtml(
                  c.selectAll
                )}</button>
                <button type="button" class="chip" id="btn-pool-clear" ${running ? "disabled" : ""}>${escapeHtml(
                  c.clearPool
                )}</button>
              </div>
              <div class="pool-list">
                ${(snap?.pre_summaries || [])
                  .map((row) => {
                    const vid = row.variant_id;
                    const checked = state.pool.has(vid);
                    return `<label class="pool-item ${checked ? "checked" : ""}">
                      <input type="checkbox" data-pool="${escapeHtml(vid)}" ${checked ? "checked" : ""} ${
                        running ? "disabled" : ""
                      } />
                      <span>
                        <strong>${escapeHtml(row.title || vid)}</strong>
                        <span class="meta-line">
                          ${
                            row.passed
                              ? `<span class="ok-chip">${c.passed}</span>`
                              : `<span class="fail-chip">${c.failed}</span>`
                          }
                          <span class="mono">${c.mean} ${row.mean ?? "—"} · ${c.sdv} ${row.sdv ?? "—"}</span>
                        </span>
                      </span>
                    </label>`;
                  })
                  .join("") || `<p class="empty-hint">${escapeHtml(c.emptyPool)}</p>`}
              </div>
              <div class="param-grid" style="margin-top:0.85rem">
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.champReps)}</label>
                  <div class="rep-pills">${pills(CHAMP_REP_OPTIONS, state.champReps, "champreps", running)}</div>
                </div>
              </div>
              <div class="stage-actions">
                <button class="btn-primary" type="button" id="btn-champ" ${
                  running || state.pool.size === 0 ? "disabled" : ""
                }>${escapeHtml(c.startChamp)}</button>
              </div>`
            : ""
        }
      </section>

      <section class="panel stage-panel ${focus === 6 ? "is-focus" : ""} ${unlock < 6 ? "stage-locked" : ""}" id="step-panel-6">
        <div class="stage-head">
          <p class="section-kicker">06</p>
          <h2 class="stage-title">${escapeHtml(c.s6)}</h2>
          <p class="stage-help">${unlock < 6 ? escapeHtml(c.locked) : escapeHtml(c.s6help)}</p>
        </div>
        ${
          unlock >= 6
            ? `${
                snap?.marks && (snap.marks.perf || snap.marks.stable || snap.marks.balanced)
                  ? `<div class="marks-row">
                      <div class="mark-card mark-perf">
                        <span class="mark-label">${escapeHtml(c.markPerf)}</span>
                        <strong>${escapeHtml(titleOf(snap.marks.perf, snap))}</strong>
                        <span class="dim tiny">${escapeHtml(c.markPerfDesc)}</span>
                      </div>
                      <div class="mark-card mark-stable">
                        <span class="mark-label">${escapeHtml(c.markStable)}</span>
                        <strong>${escapeHtml(titleOf(snap.marks.stable, snap))}</strong>
                        <span class="dim tiny">${escapeHtml(c.markStableDesc)}</span>
                      </div>
                      <div class="mark-card mark-balanced">
                        <span class="mark-label">${escapeHtml(c.markBalanced)}</span>
                        <strong>${escapeHtml(titleOf(snap.marks.balanced, snap))}</strong>
                        <span class="dim tiny">${escapeHtml(c.markBalancedDesc)}</span>
                      </div>
                    </div>`
                  : phase === "championing" || running
                    ? progressBar(snap?.done || 0, snap?.total || 0)
                    : `<p class="empty-hint">—</p>`
              }
              ${summaryTable(snap?.champ_summaries, c, snap?.marks)}`
            : ""
        }
      </section>

      ${
        (snap?.logs || []).length
          ? `<section class="panel logs-panel">
              <button type="button" class="logs-toggle" id="btn-logs">${
                state.showLogs ? escapeHtml(c.hideLogs) : escapeHtml(c.showLogs)
              }</button>
              ${
                state.showLogs
                  ? `<div class="table-wrap"><table class="data-table">
                      <thead><tr><th>#</th><th></th><th></th><th></th><th></th><th>${c.mean}</th></tr></thead>
                      <tbody>
                        ${(snap.logs || [])
                          .slice(0, 30)
                          .map(
                            (l) => `<tr>
                              <td class="mono">${l.n ?? ""}</td>
                              <td>${escapeHtml(l.stage === "champ" ? c.s6 : c.s4)}</td>
                              <td>${escapeHtml(l.title || l.variant_id || "")}</td>
                              <td class="mono">${l.rep ?? ""}/${l.reps ?? ""}</td>
                              <td class="mono">${l.score ?? l.error ?? ""}</td>
                              <td class="mono">${l.mean_so_far ?? ""}</td>
                            </tr>`
                          )
                          .join("")}
                      </tbody>
                    </table></div>`
                  : ""
              }
            </section>`
          : ""
      }

      <footer class="desk-footer">${escapeHtml(c.footer)}</footer>
    </main>
  `;

  wire(running, unlock);
}

function wire(running, unlock) {
  document.getElementById("btn-lang")?.addEventListener("click", () => {
    state.lang = state.lang === "zh" ? "en" : "zh";
    render();
  });
  document.getElementById("btn-reset")?.addEventListener("click", onReset);
  document.getElementById("btn-gen-case")?.addEventListener("click", onGenCase);
  document.getElementById("btn-demo")?.addEventListener("click", onDemo);
  document.getElementById("btn-save-case")?.addEventListener("click", onSaveCase);
  document.getElementById("btn-gen-genome")?.addEventListener("click", onGenGenomes);
  document.getElementById("btn-pre")?.addEventListener("click", onPrefilter);
  document.getElementById("btn-abort")?.addEventListener("click", onAbort);
  document.getElementById("btn-champ")?.addEventListener("click", onChampion);
  document.getElementById("btn-goto-3")?.addEventListener("click", () => {
    state.focusStep = 3;
    render();
    scrollToStep(3);
  });
  document.getElementById("btn-goto-4")?.addEventListener("click", () => {
    state.focusStep = 4;
    render();
    scrollToStep(4);
  });
  document.getElementById("btn-logs")?.addEventListener("click", () => {
    state.showLogs = !state.showLogs;
    render();
  });

  document.querySelector("details.advanced")?.addEventListener("toggle", (e) => {
    state.showAdvanced = e.target.open;
  });

  document.querySelectorAll("[data-goto]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const n = Number(btn.dataset.goto);
      if (n > unlock) return;
      state.focusStep = n;
      render();
      scrollToStep(n);
    })
  );

  document.querySelectorAll("[data-example]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      const list = state.lang === "zh" ? ORAL_EXAMPLES_ZH : ORAL_EXAMPLES_EN;
      state.oral = list[Number(btn.dataset.example)] || "";
      render();
      document.getElementById("oral-text")?.focus();
    })
  );

  document.getElementById("oral-text")?.addEventListener("input", (e) => {
    state.oral = e.target.value;
  });
  document.getElementById("target-text")?.addEventListener("input", (e) => {
    state.targetText = e.target.value;
  });
  document.getElementById("criteria-text")?.addEventListener("input", (e) => {
    state.criteriaText = e.target.value;
  });
  document.getElementById("api-key")?.addEventListener("input", (e) => {
    state.apiKey = e.target.value.trim();
    sessionStorage.setItem("yiagent_api_key", state.apiKey);
  });
  document.getElementById("model-select")?.addEventListener("change", (e) => {
    state.model = e.target.value;
  });
  document.getElementById("pass-mean")?.addEventListener("change", (e) => {
    state.passMean = Number(e.target.value) || 70;
  });

  const setPool = async (ids) => {
    state.pool = new Set(ids);
    try {
      await syncPool();
    } catch (err) {
      state.error = String(err.message || err);
    }
    render();
  };

  document.getElementById("btn-pool-passed")?.addEventListener("click", () => {
    if (running) return;
    const ids = (state.snap?.pre_summaries || []).filter((r) => r.passed).map((r) => r.variant_id);
    setPool(ids);
  });
  document.getElementById("btn-pool-all")?.addEventListener("click", () => {
    if (running) return;
    setPool((state.snap?.pre_summaries || []).map((r) => r.variant_id));
  });
  document.getElementById("btn-pool-clear")?.addEventListener("click", () => {
    if (running) return;
    setPool([]);
  });

  document.querySelectorAll("[data-workers]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      state.workers = Number(btn.dataset.workers);
      render();
    })
  );
  document.querySelectorAll("[data-qualify]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      state.qualifyTarget = Number(btn.dataset.qualify);
      render();
    })
  );
  document.querySelectorAll("[data-prereps]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      state.preReps = Number(btn.dataset.prereps);
      render();
    })
  );
  document.querySelectorAll("[data-champreps]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      state.champReps = Number(btn.dataset.champreps);
      render();
    })
  );
  document.querySelectorAll("[data-pool]").forEach((el) =>
    el.addEventListener("change", async (e) => {
      if (running || unlock < 5) return;
      const vid = e.target.dataset.pool;
      if (e.target.checked) state.pool.add(vid);
      else state.pool.delete(vid);
      try {
        await syncPool();
      } catch (err) {
        state.error = String(err.message || err);
      }
      render();
    })
  );
}

async function boot() {
  try {
    const modelsResp = await fetch("/api/models").then((r) => r.json());
    state.models = modelsResp.models || [];
  } catch {
    state.models = [
      { id: "k3", label: "Kimi 3" },
      { id: "kimi-k2.6", label: "Kimi 2.6" },
    ];
  }
  render();
}

boot();
