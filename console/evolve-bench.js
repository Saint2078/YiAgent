/**
 * 题组 DNA 搜索 · 控制台风格（/api/factory/evolve · testset）
 * 演示 = 冻结 evolve report 导览；真实运行 = AI科普 manifest + 种子开跑
 */
const EvolveBench = (() => {
  const STEPS = ["需求与题组", "Manifest", "基因组库", "A 基线", "多代进化", "Holdout", "冠军报告"];
  const STORIES = [
    "题组搜索不再盯单题，而是用一组题 + holdout 鉴定「能不能泛化」。",
    "Manifest 固定进化集与留出集，同 seed 可复现。",
    "种子基因组给出 G1–G5 等位与候选 variant，供交叉/变异。",
    "先在题组上测裸基线 A，后面冠军分数要相对它谈提升。",
    "每一代评测 → 配对门禁 → 晋升或停滞，直到停机条件。",
    "Holdout 不参与选种，用来检验是否过拟合进化集。",
    "落盘 report：冠军、曲线、门禁、token——可复现证据。",
  ];
  const SETTINGS_KEY = "yiagent-evolve-bench-settings-v1";
  const DEMO_PACK_URL = "/evolve-demo-pack.json";
  const SEED_URL = "/evolve-seed-ai-kepu.json";
  const DEFAULT_MANIFEST = "0803c197a73c";

  const eb = {
    view: "home", // home | pick | run
    runMode: null, // demo | live
    focusStep: 1,
    busy: false,
    busyLabel: "",
    error: null,
    settingsOpen: false,
    pack: null,
    manifest: null,
    seed: null,
    runId: null,
    snap: null,
    pollTimer: null,
    apiKey: "",
    model: "k3",
    maxGenerations: 2,
    variantsPerGen: 6,
    evalReps: 2,
    workers: 4,
  };

  function loadSettings() {
    try {
      const o = JSON.parse(sessionStorage.getItem(SETTINGS_KEY) || "{}");
      if (o.apiKey != null) eb.apiKey = String(o.apiKey);
      if (o.model) eb.model = o.model;
      if (o.maxGenerations) eb.maxGenerations = Number(o.maxGenerations) || 2;
      if (o.workers) eb.workers = Number(o.workers) || 4;
    } catch {
      /* ignore */
    }
  }
  loadSettings();

  function saveSettings() {
    try {
      sessionStorage.setItem(
        SETTINGS_KEY,
        JSON.stringify({
          apiKey: eb.apiKey,
          model: eb.model,
          maxGenerations: eb.maxGenerations,
          workers: eb.workers,
        })
      );
    } catch {
      /* ignore */
    }
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function toast(msg) {
    if (typeof window.toast === "function") window.toast(msg);
  }

  function requestRender() {
    if (typeof window.render === "function") window.render();
  }

  async function api(path, opts = {}) {
    const res = await fetch(`/api/factory${path}`, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      const detail = data?.detail || data?.message || text || `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function stopPoll() {
    if (eb.pollTimer) {
      clearInterval(eb.pollTimer);
      eb.pollTimer = null;
    }
  }

  function startPoll() {
    stopPoll();
    eb.pollTimer = setInterval(async () => {
      if (!eb.runId) return;
      try {
        const snap = await api(`/evolve/${eb.runId}`);
        eb.snap = snap;
        if (snap.status === "done" || snap.status === "error" || snap.status === "aborted") {
          stopPoll();
          eb.busy = false;
          eb.busyLabel = "";
          if (snap.status === "done") {
            try {
              eb.pack = await api(`/evolve/${eb.runId}/report`);
              eb.focusStep = 7;
            } catch {
              /* report may lag */
            }
          }
        }
        requestRender();
      } catch {
        /* keep */
      }
    }, 1500);
  }

  function resetRun() {
    stopPoll();
    eb.runId = null;
    eb.snap = null;
    eb.pack = null;
    eb.manifest = null;
    eb.focusStep = 1;
    eb.error = null;
    eb.busy = false;
    eb.busyLabel = "";
  }

  function openPick() {
    resetRun();
    eb.view = "pick";
    eb.runMode = null;
    requestRender();
  }

  function backHome() {
    resetRun();
    eb.view = "home";
    eb.runMode = null;
    requestRender();
  }

  function demoGoto(step) {
    eb.focusStep = Math.min(7, Math.max(1, Number(step) || 1));
    eb.error = null;
    requestRender();
  }

  function needKey() {
    if (!eb.apiKey || eb.apiKey.length < 8) {
      eb.error = "真实运行需先填写 API Key（设置）";
      eb.settingsOpen = true;
      requestRender();
      return false;
    }
    return true;
  }

  async function startDemo() {
    eb.runMode = "demo";
    eb.view = "run";
    eb.busy = true;
    eb.busyLabel = "载入题组冻结演示";
    eb.error = null;
    eb.focusStep = 1;
    requestRender();
    try {
      let pack = null;
      try {
        const res = await fetch(DEMO_PACK_URL);
        if (res.ok) pack = await res.json();
      } catch {
        /* fallback API */
      }
      if (!pack) {
        const report = await api("/evolve/2a431c0f67be/report");
        pack = {
          ...report,
          label: "题组冻结演示",
          source_run_id: report.run_id,
          variants: report.champion?.bank?.variants || [],
        };
      }
      try {
        eb.manifest = await api(`/testset/manifest/${DEFAULT_MANIFEST}`);
      } catch {
        eb.manifest = null;
      }
      eb.pack = pack;
      toast("题组演示已载入 · 用「下一步」浏览");
    } catch (e) {
      eb.error = String(e.message || e);
      eb.view = "pick";
    } finally {
      eb.busy = false;
      eb.busyLabel = "";
      requestRender();
    }
  }

  async function startLive() {
    eb.runMode = "live";
    eb.view = "run";
    eb.busy = true;
    eb.busyLabel = "准备 AI 科普题组";
    eb.error = null;
    eb.focusStep = 1;
    requestRender();
    try {
      eb.manifest = await api(`/testset/manifest/${DEFAULT_MANIFEST}`);
      try {
        const res = await fetch(SEED_URL);
        if (res.ok) eb.seed = await res.json();
      } catch {
        eb.seed = null;
      }
      toast("已绑定 AI 科普 manifest · 配置 Key 后可开跑");
    } catch (e) {
      eb.error = String(e.message || e);
      eb.view = "pick";
    } finally {
      eb.busy = false;
      eb.busyLabel = "";
      requestRender();
    }
  }

  async function onStartEvolve() {
    if (!needKey()) return;
    if (!eb.manifest?.id && !DEFAULT_MANIFEST) {
      eb.error = "缺少 manifest";
      requestRender();
      return;
    }
    eb.busy = true;
    eb.busyLabel = "启动题组进化";
    eb.error = null;
    requestRender();
    try {
      const body = {
        api_key: eb.apiKey,
        model: eb.model,
        manifest_id: eb.manifest?.id || DEFAULT_MANIFEST,
        max_generations: eb.maxGenerations,
        variants_per_gen: eb.variantsPerGen,
        eval_reps: eb.evalReps,
        final_reps: Math.max(2, eb.evalReps),
        workers: eb.workers,
        with_baseline: true,
        use_cache: true,
      };
      if (eb.seed) body.seed = eb.seed;
      else body.oral = eb.manifest?.demand || "AI 科普串联助手";
      const snap = await api("/evolve/start", { method: "POST", body: JSON.stringify(body) });
      eb.snap = snap;
      eb.runId = snap.id || snap.run_id;
      eb.focusStep = 5;
      startPoll();
      toast("进化已启动");
    } catch (e) {
      eb.error = String(e.message || e);
      eb.busy = false;
      eb.busyLabel = "";
    }
    requestRender();
  }

  async function onAbort() {
    if (!eb.runId) return;
    try {
      eb.snap = await api(`/evolve/${eb.runId}/abort`, { method: "POST", body: "{}" });
    } catch (e) {
      eb.error = String(e.message || e);
    }
    stopPoll();
    eb.busy = false;
    eb.busyLabel = "";
    requestRender();
  }

  function scoreRow(label, mean, extra = "") {
    const m = mean == null ? "—" : Number(mean).toFixed(1);
    return `<div class="fb-score-row">
      <span class="fb-score-label">${esc(label)}</span>
      <div class="fb-score-track"><i style="width:${mean != null ? Math.min(100, Number(mean)) : 0}%"></i></div>
      <span class="fb-score-num mono">${esc(m)}${extra ? ` · ${esc(extra)}` : ""}</span>
    </div>`;
  }

  function stepperHtml(focus) {
    return `<nav class="fb-stepper" aria-label="题组七步">
      ${STEPS.map((label, i) => {
        const n = i + 1;
        const done = n < focus;
        const active = n === focus;
        return `<button type="button" class="fb-step ${active ? "active" : ""} ${done ? "done" : ""}" data-eb-goto="${n}">
          <span class="fb-step-n">${done ? "✓" : n}</span>
          <span class="fb-step-label">${esc(label)}</span>
        </button>`;
      }).join("")}
    </nav>`;
  }

  function demoNavBar(focus) {
    const atStart = focus <= 1;
    const atEnd = focus >= 7;
    return `<div class="fb-demo-nav" role="navigation" aria-label="题组演示导览">
      <button class="btn ghost" type="button" data-eb-action="demo-prev" ${atStart ? "disabled" : ""}>← 上一步</button>
      <div class="fb-demo-progress">
        <span class="fb-demo-progress-label">${focus} / 7 · ${esc(STEPS[focus - 1])}</span>
        <div class="fb-demo-progress-track"><i style="width:${(focus / 7) * 100}%"></i></div>
      </div>
      ${
        atEnd
          ? `<button class="btn primary" type="button" data-eb-action="demo-restart">从头再看</button>`
          : `<button class="btn primary" type="button" data-eb-action="demo-next">下一步 →</button>`
      }
    </div>`;
  }

  function settingsModal() {
    if (!eb.settingsOpen) return "";
    return `<div class="fb-modal-scrim" data-eb-scrim="1">
      <div class="card fb-modal" role="dialog" aria-modal="true">
        <div class="fb-modal-head">
          <h2>题组运行设置</h2>
          <button class="chip-btn" type="button" data-eb-action="close-settings">关闭</button>
        </div>
        <div class="meta" style="margin-bottom:12px">Key 仅存本浏览器 sessionStorage</div>
        <label class="fb-field"><span>API Key</span>
          <input id="eb-api-key" type="password" autocomplete="off" value="${esc(eb.apiKey)}" placeholder="sk-…" />
        </label>
        <label class="fb-field"><span>模型 id</span>
          <input id="eb-model" type="text" value="${esc(eb.model)}" />
        </label>
        <label class="fb-field"><span>代数 max_generations</span>
          <input id="eb-gens" type="number" min="1" max="10" value="${esc(eb.maxGenerations)}" />
        </label>
        <label class="fb-field"><span>并发 workers</span>
          <input id="eb-workers" type="number" min="1" max="32" value="${esc(eb.workers)}" />
        </label>
        <div class="list proj-actions" style="margin-top:14px">
          <button class="btn primary" type="button" data-eb-action="save-settings">保存</button>
          <button class="btn ghost" type="button" data-eb-action="close-settings">取消</button>
        </div>
      </div>
    </div>`;
  }

  function renderHome() {
    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <div class="tags" style="margin-bottom:10px"><span class="tag blue">题组 DNA 搜索</span></div>
        <h2>用一组题进化出可泛化基因组</h2>
        <div class="meta">Manifest → 基线 → 多代鉴定 → Holdout → 冠军 report</div>
        <div class="list proj-actions" style="margin-top:14px">
          <button class="btn primary" type="button" data-eb-action="open-pick">进入</button>
        </div>
      </div>
    </div>`;
  }

  function renderPick() {
    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <button class="chip-btn" type="button" data-eb-action="back-home" style="margin-bottom:12px">← 返回</button>
        <h2>选择运行方式</h2>
        <div class="meta">演示浏览冻结 report；真实运行绑定 AI 科普 8+4 manifest</div>
        <div class="fb-mode-grid">
          <button class="fb-mode-card" type="button" data-eb-action="start-demo" ${eb.busy ? "disabled" : ""}>
            <div class="fb-mode-kicker">推荐先看</div>
            <div class="row-title">演示形式</div>
            <div class="row-desc">冒烟 evolve 冻结包 · 七步导览（不消耗 Token）</div>
          </button>
          <button class="fb-mode-card" type="button" data-eb-action="start-live" ${eb.busy ? "disabled" : ""}>
            <div class="fb-mode-kicker">真实 API</div>
            <div class="row-title">真实运行</div>
            <div class="row-desc">manifest ${esc(DEFAULT_MANIFEST)} · 种子 ai_kepu · 需 Key</div>
          </button>
        </div>
        ${eb.error ? `<div class="fb-error">${esc(eb.error)}</div>` : ""}
        ${eb.busy ? `<div class="meta" style="margin-top:12px">${esc(eb.busyLabel || "加载中…")}</div>` : ""}
      </div>
      ${settingsModal()}
    </div>`;
  }

  function demoPanel(focus, pack, manifest) {
    const story = STORIES[focus - 1] || "";
    const head = `<div class="fb-story">
      <div class="fb-story-kicker">第 ${focus} 步 · ${esc(STEPS[focus - 1])}</div>
      <p>${esc(story)}</p>
    </div>`;
    const storyMan = pack.manifest_story || {};
    const m = manifest || {};

    if (focus === 1) {
      return `${head}<div class="card fb-panel">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag green">演示导览</span>
          <span class="tag">run ${esc(pack.source_run_id || pack.run_id || "—")}</span>
        </div>
        <h2>题组进化在解决什么</h2>
        <div class="fb-panel-kicker" style="margin-top:12px">演示 run 需求</div>
        <div class="fb-oral">${esc(pack.demand || "")}</div>
        <div class="fb-panel-kicker" style="margin-top:14px">产品线目标题组（AI 科普）</div>
        <div class="fb-oral">${esc(storyMan.demand || m.demand || "AI 科普串联助手")}</div>
        <div class="meta" style="margin-top:10px">${esc(
          storyMan.note || "演示曲线来自批判思维冒烟包；真实运行默认绑 AI 科普 manifest"
        )}</div>
      </div>`;
    }

    if (focus === 2) {
      const evolveIds =
        storyMan.evolve_cases ||
        (m.cases || []).map((c) => c.id || c) ||
        [];
      const holdIds =
        storyMan.holdout_cases ||
        (m.holdout || []).map((c) => c.id || c) ||
        [];
      const demoMan = pack.manifest || {};
      return `${head}<div class="card fb-panel">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">目标 ${esc(storyMan.id || m.id || DEFAULT_MANIFEST)}</span>
          <span class="tag">演示 run manifest ${esc(demoMan.id || "—")} · ${esc(demoMan.cases)}+${esc(demoMan.holdout)}</span>
        </div>
        <div class="fb-split">
          <div>
            <div class="fb-panel-kicker">进化集（${evolveIds.length}）</div>
            <div class="fb-variant-list">${
              evolveIds.map((id) => `<div class="fb-variant"><div class="row-title mono">${esc(id)}</div></div>`).join("") ||
              `<div class="empty">—</div>`
            }</div>
          </div>
          <div>
            <div class="fb-panel-kicker">Holdout（${holdIds.length}）</div>
            <div class="fb-variant-list">${
              holdIds.map((id) => `<div class="fb-variant"><div class="row-title mono">${esc(id)}</div></div>`).join("") ||
              `<div class="empty">—</div>`
            }</div>
          </div>
        </div>
      </div>`;
    }

    if (focus === 3) {
      const variants = pack.variants || [];
      return `${head}<div class="card fb-panel">
        <div class="meta" style="margin-bottom:10px">候选 ${variants.length} · 点击查看槽位</div>
        <div class="fb-variant-list">
          ${
            variants
              .map((v) => {
                const slots = v.slots || {};
                return `<div class="fb-variant">
                  <div class="row-title">${esc(v.title || v.id)}</div>
                  <div class="row-desc mono">${esc(v.id)}</div>
                  <div class="fb-slots" style="margin-top:8px">${Object.entries(slots)
                    .map(([k, val]) => `<div class="fb-slot"><span>${esc(k)}</span><code>${esc(val)}</code></div>`)
                    .join("")}</div>
                </div>`;
              })
              .join("") || `<div class="empty">无 variant</div>`
          }
        </div>
      </div>`;
    }

    if (focus === 4) {
      const a = pack.baseline_arm_a || {};
      const delta = pack.champion_minus_baseline_mean;
      return `${head}<div class="card fb-panel">
        ${
          delta != null
            ? `<div class="fb-insight">冠军相对基线 A 均分提升 ≈ <strong>${esc(Number(delta).toFixed(2))}</strong></div>`
            : ""
        }
        ${scoreRow("A · 题组基线", a.mean, `n=${a.n ?? "—"} · composite=${a.composite ?? "—"}`)}
      </div>`;
    }

    if (focus === 5) {
      const curve = pack.champion_curve || [];
      const gates = pack.gates || [];
      return `${head}<div class="card fb-panel">
        <div class="fb-panel-kicker">冠军曲线</div>
        ${
          curve
            .map((c) =>
              scoreRow(
                `Gen ${c.gen}`,
                c.mean,
                `${c.variant_id || ""} · cmp=${c.composite != null ? Number(c.composite).toFixed(1) : "—"}`
              )
            )
            .join("") || `<div class="empty">无曲线</div>`
        }
        <div class="fb-panel-kicker" style="margin-top:16px">配对门禁</div>
        <div class="fb-variant-list">
          ${
            gates
              .map(
                (g) => `<div class="fb-variant">
              <div class="fb-variant-row">
                <div>
                  <div class="row-title">Gen ${esc(g.gen)} · ${esc(g.verdict)}</div>
                  <div class="row-desc">${esc(g.reason || "")}</div>
                </div>
                <span class="tag ${g.verdict === "promote" ? "green" : "orange"}">${esc(g.verdict)}</span>
              </div>
            </div>`
              )
              .join("") || `<div class="empty">无门禁记录</div>`
          }
        </div>
        <div class="meta" style="margin-top:10px">停机：${esc(pack.stop_reason || "—")}</div>
      </div>`;
    }

    if (focus === 6) {
      const h = pack.holdout || {};
      return `${head}<div class="card fb-panel">
        <div class="fb-insight">Holdout 均分 <strong>${esc(h.mean != null ? Number(h.mean).toFixed(1) : "—")}</strong>
          · n=${esc(h.n ?? "—")} · composite=${esc(h.composite ?? "—")}</div>
        <div class="meta">留出集不参与选种；分数偏高时也要结合题型难度解读。</div>
      </div>`;
    }

    const champ = pack.champion || {};
    const v = champ.variant || {};
    const tok = pack.token_usage || {};
    return `${head}<div class="card fb-panel">
      <div class="fb-insight fb-insight-win">冠军 · <strong>${esc(v.title || champ.variant_id || "—")}</strong>
        <span class="mono"> · ${esc(champ.variant_id || "")}</span>
        · composite ${esc(champ.composite != null ? Number(champ.composite).toFixed(2) : "—")}
        · gen ${esc(champ.gen ?? "—")}</div>
      ${
        v.slots
          ? `<div class="fb-slots" style="margin-top:12px">${Object.entries(v.slots)
              .map(([k, val]) => `<div class="fb-slot"><span>${esc(k)}</span><code>${esc(val)}</code></div>`)
              .join("")}</div>`
          : ""
      }
      <div class="tags" style="margin-top:14px">
        <span class="tag">tokens ${esc(tok.total_tokens ?? "—")}</span>
        <span class="tag">calls ${esc(tok.calls ?? "—")}</span>
        ${Object.entries(tok.by_purpose || {})
          .map(([k, val]) => `<span class="tag blue">${esc(k)} ${esc(val)}</span>`)
          .join("")}
      </div>
    </div>`;
  }

  function renderRunDemo() {
    if (eb.busy && !eb.pack) {
      return `<div class="pad fb-page"><div class="card fb-hero"><h2>载入题组演示…</h2><div class="meta">${esc(
        eb.busyLabel || ""
      )}</div></div></div>`;
    }
    if (!eb.pack) {
      return `<div class="pad fb-page"><div class="card fb-hero">
        <h2>演示未载入</h2>
        ${eb.error ? `<div class="fb-error">${esc(eb.error)}</div>` : ""}
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-eb-action="start-demo">重试</button>
          <button class="chip-btn" type="button" data-eb-action="open-pick">返回</button>
        </div>
      </div></div>`;
    }
    const focus = Math.min(7, Math.max(1, eb.focusStep || 1));
    eb.focusStep = focus;
    return `<div class="pad fb-page fb-demo">
      <div class="card fb-hero">
        <div class="fb-run-top">
          <button class="chip-btn" type="button" data-eb-action="open-pick">← 退出演示</button>
          <div class="tags">
            <span class="tag green">题组演示</span>
            <span class="tag orange">冻结包</span>
          </div>
        </div>
        <h2>${esc(eb.pack.label || "题组 DNA 搜索")}</h2>
        <div class="meta">底部「下一步」浏览 · 或点步骤条跳转 · 不消耗 Token</div>
      </div>
      <div class="card fb-stepper-card">${stepperHtml(focus)}</div>
      <div class="fb-demo-body">${demoPanel(focus, eb.pack, eb.manifest)}</div>
      ${demoNavBar(focus)}
    </div>`;
  }

  function renderRunLive() {
    const m = eb.manifest;
    const running = eb.busy || eb.snap?.status === "running";
    const cases = (m?.cases || []).map((c) => c.id || c);
    const hold = (m?.holdout || []).map((c) => c.id || c);
    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <div class="fb-run-top">
          <button class="chip-btn" type="button" data-eb-action="open-pick">← 重选方式</button>
          <div class="tags">
            <span class="tag blue">真实运行</span>
            ${eb.runId ? `<span class="tag mono">${esc(String(eb.runId).slice(0, 12))}</span>` : ""}
            ${running ? `<span class="tag orange">${esc(eb.busyLabel || eb.snap?.status || "运行中")}</span>` : ""}
          </div>
        </div>
        <h2>AI 科普题组进化</h2>
        <div class="meta">${esc(m?.demand || "绑定 manifest 后开跑")}</div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="chip-btn" type="button" data-eb-action="open-settings">设置</button>
          <button class="btn primary" type="button" data-eb-action="start-evolve" ${
            running || !m ? "disabled" : ""
          }>启动进化</button>
          ${running ? `<button class="btn ghost" type="button" data-eb-action="abort">中止</button>` : ""}
        </div>
        ${eb.error ? `<div class="fb-error">${esc(eb.error)}</div>` : ""}
      </div>
      <div class="card" style="margin-top:14px">
        <h2 style="margin:0 0 8px;font-size:18px">Manifest · ${esc(m?.id || DEFAULT_MANIFEST)}</h2>
        <div class="tags" style="margin-bottom:10px">
          <span class="tag">进化 ${cases.length}</span>
          <span class="tag orange">holdout ${hold.length}</span>
          <span class="tag">${eb.seed ? "已载入种子" : "无种子 · 将用口述生成"}</span>
        </div>
        <div class="fb-split">
          <div>
            <div class="fb-panel-kicker">进化集</div>
            <div class="fb-variant-list">${cases
              .map((id) => `<div class="fb-variant"><div class="row-title mono">${esc(id)}</div></div>`)
              .join("")}</div>
          </div>
          <div>
            <div class="fb-panel-kicker">Holdout</div>
            <div class="fb-variant-list">${hold
              .map((id) => `<div class="fb-variant"><div class="row-title mono">${esc(id)}</div></div>`)
              .join("")}</div>
          </div>
        </div>
      </div>
      ${
        eb.snap
          ? `<div class="card" style="margin-top:14px">
              <h2 style="margin:0 0 8px;font-size:18px">运行状态</h2>
              <div class="meta">status=${esc(eb.snap.status)} · phase=${esc(eb.snap.phase || "—")} · gen=${esc(
                eb.snap.generation ?? eb.snap.gen ?? "—"
              )}</div>
              ${eb.pack ? `<div class="fb-insight" style="margin-top:10px">report 已就绪 · 可切到演示对照，或刷新本页查看快照字段</div>` : ""}
            </div>`
          : ""
      }
      ${
        eb.pack && eb.runMode === "live"
          ? `<div class="fb-demo-body" style="margin-top:14px">${demoPanel(7, eb.pack, eb.manifest)}</div>`
          : ""
      }
      ${settingsModal()}
    </div>`;
  }

  function renderRun() {
    if (eb.runMode === "demo") return renderRunDemo();
    return renderRunLive();
  }

  function render() {
    if (eb.view === "pick") return renderPick();
    if (eb.view === "run") return renderRun();
    return renderHome();
  }

  function readSettingsForm() {
    const key = document.getElementById("eb-api-key");
    const model = document.getElementById("eb-model");
    const gens = document.getElementById("eb-gens");
    const workers = document.getElementById("eb-workers");
    if (key) eb.apiKey = key.value.trim();
    if (model) eb.model = model.value.trim() || "k3";
    if (gens) eb.maxGenerations = Math.max(1, Math.min(10, Number(gens.value) || 2));
    if (workers) eb.workers = Math.max(1, Math.min(32, Number(workers.value) || 4));
  }

  function handleClick(e) {
    if (eb.settingsOpen && e.target?.getAttribute?.("data-eb-scrim") === "1") {
      e.preventDefault();
      eb.settingsOpen = false;
      requestRender();
      return true;
    }
    const t = e.target.closest("[data-eb-action],[data-eb-goto]");
    if (!t) return false;
    e.preventDefault();
    const goto = t.getAttribute("data-eb-goto");
    if (goto) {
      demoGoto(goto);
      return true;
    }
    switch (t.getAttribute("data-eb-action")) {
      case "open-pick":
        openPick();
        break;
      case "back-home":
        backHome();
        break;
      case "start-demo":
        startDemo();
        break;
      case "start-live":
        startLive();
        break;
      case "demo-next":
        if (eb.focusStep >= 7) toast("演示已走完");
        else demoGoto(eb.focusStep + 1);
        break;
      case "demo-prev":
        if (eb.focusStep > 1) demoGoto(eb.focusStep - 1);
        break;
      case "demo-restart":
        demoGoto(1);
        toast("回到第 1 步");
        break;
      case "open-settings":
        eb.settingsOpen = true;
        requestRender();
        break;
      case "close-settings":
        eb.settingsOpen = false;
        requestRender();
        break;
      case "save-settings":
        readSettingsForm();
        saveSettings();
        eb.settingsOpen = false;
        toast("设置已保存");
        requestRender();
        break;
      case "start-evolve":
        onStartEvolve();
        break;
      case "abort":
        onAbort();
        break;
      default:
        return false;
    }
    return true;
  }

  return {
    render,
    handleClick,
    get state() {
      return eb;
    },
  };
})();
