/**
 * 单题 DNA 搜索 · 控制台风格（/api/factory）
 * 演示 = 冻结包导览（上/下一步）；真实运行 = 可执行动作
 */
const FactoryBench = (() => {
  const STEPS = [
    "选题",
    "题目 / 裁判",
    "A/B 基线",
    "基因组",
    "初筛",
    "冠军池",
    "终筛金牌",
  ];

  const DEMO_STORY = [
    "先锁定一道题：后面所有筛选都围绕它展开。",
    "原题给选手看；裁判标准只给评分用，不进基因组。",
    "A 是裸原题地板，B 是灌入标准的天花板——看差距有多大。",
    "枚举候选人格/策略基因组，供后续初筛。",
    "用较少次数打分，留下过线的候选进入冠军池。",
    "从初筛结果里圈定要做终筛的少数几个。",
    "更高次数复测，标出均衡 / 效果 / 稳定金牌。",
  ];

  const SETTINGS_KEY = "yiagent-factory-bench-settings-v1";

  const fb = {
    /** home | pick | run */
    view: "home",
    /** demo | live */
    runMode: null,
    sessionId: null,
    snap: null,
    focusStep: 1,
    busy: false,
    busyLabel: "",
    error: null,
    settingsOpen: false,
    pollTimer: null,
    oral: "",
    apiKey: "",
    model: "k3",
    workers: 4,
    baselineReps: 3,
    preReps: 3,
    champReps: 5,
    passMean: 70,
    qualifyTarget: 5,
    championMark: "balanced",
    /** demo: which variant id is expanded */
    demoVariantId: null,
  };

  function loadSettings() {
    try {
      const o = JSON.parse(sessionStorage.getItem(SETTINGS_KEY) || "{}");
      if (o.apiKey != null) fb.apiKey = String(o.apiKey);
      if (o.model) fb.model = o.model;
      if (o.workers) fb.workers = Number(o.workers) || 4;
      if (o.championMark) fb.championMark = o.championMark;
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
          apiKey: fb.apiKey,
          model: fb.model,
          workers: fb.workers,
          championMark: fb.championMark,
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

  function phaseRank(phase) {
    const order = [
      "idle",
      "case_ready",
      "baselining",
      "baseline_done",
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

  function unlockedMax(rank, snap) {
    if (fb.runMode === "demo" && snap?.frozen_demo) return 7;
    if (rank >= 7) return 7;
    if (rank >= 6) return 7;
    if (rank >= 4) return 5;
    if (rank >= 3) return 4;
    if (rank >= 1) return 3;
    if (snap) return 2;
    return 1;
  }

  function applySnap(snap) {
    fb.snap = snap;
    fb.sessionId = snap?.id || null;
  }

  function stopPoll() {
    if (fb.pollTimer) {
      clearInterval(fb.pollTimer);
      fb.pollTimer = null;
    }
  }

  function startPoll() {
    stopPoll();
    fb.pollTimer = setInterval(async () => {
      if (!fb.sessionId) return;
      try {
        const snap = await api(`/session/${fb.sessionId}`);
        applySnap(snap);
        if (snap.status !== "running" && !snap.auto) {
          stopPoll();
          fb.busy = false;
          fb.busyLabel = "";
        }
        requestRender();
      } catch {
        /* keep */
      }
    }, 1200);
  }

  function needKey() {
    if (!fb.apiKey || fb.apiKey.length < 8) {
      fb.error = "真实运行需先填写 API Key（设置）";
      fb.settingsOpen = true;
      requestRender();
      return false;
    }
    return true;
  }

  function resetSession() {
    stopPoll();
    fb.sessionId = null;
    fb.snap = null;
    fb.focusStep = 1;
    fb.error = null;
    fb.busy = false;
    fb.busyLabel = "";
    fb.demoVariantId = null;
  }

  function openPick() {
    resetSession();
    fb.view = "pick";
    fb.runMode = null;
    requestRender();
  }

  function backHome() {
    resetSession();
    fb.view = "home";
    fb.runMode = null;
    requestRender();
  }

  function demoGoto(step) {
    const n = Math.min(7, Math.max(1, Number(step) || 1));
    fb.focusStep = n;
    fb.error = null;
    requestRender();
  }

  function demoNext() {
    if (fb.focusStep >= 7) {
      toast("演示已走完 · 可点步骤条回看，或退出重选");
      return;
    }
    demoGoto(fb.focusStep + 1);
  }

  function demoPrev() {
    if (fb.focusStep <= 1) return;
    demoGoto(fb.focusStep - 1);
  }

  async function startDemo() {
    fb.runMode = "demo";
    fb.view = "run";
    fb.busy = true;
    fb.busyLabel = "载入冻结演示";
    fb.error = null;
    fb.focusStep = 1;
    fb.demoVariantId = null;
    requestRender();
    try {
      const snap = await api("/session/demo", {
        method: "POST",
        body: JSON.stringify({ fresh: false }),
      });
      applySnap(snap);
      fb.focusStep = 1;
      toast("演示已载入 · 用底部「下一步」浏览");
    } catch (e) {
      fb.error = String(e.message || e);
      fb.view = "pick";
    } finally {
      fb.busy = false;
      fb.busyLabel = "";
      requestRender();
    }
  }

  async function startLive() {
    fb.runMode = "live";
    fb.view = "run";
    fb.busy = true;
    fb.busyLabel = "准备真实运行";
    fb.error = null;
    requestRender();
    try {
      const snap = await api("/session/demo", {
        method: "POST",
        body: JSON.stringify({ fresh: true }),
      });
      applySnap(snap);
      fb.focusStep = 1;
      toast("已进入真实运行 · 可改口述/选题后开跑");
    } catch (e) {
      fb.snap = null;
      fb.sessionId = null;
      fb.focusStep = 1;
      fb.error = null;
      toast("真实运行台已就绪 · 请配置 Key 后生成题目");
    } finally {
      fb.busy = false;
      fb.busyLabel = "";
      requestRender();
    }
  }

  async function postAction(label, path, body) {
    if (!fb.sessionId) {
      fb.error = "请先选题或载入演示";
      requestRender();
      return;
    }
    fb.busy = true;
    fb.busyLabel = label;
    fb.error = null;
    requestRender();
    try {
      const snap = await api(path, { method: "POST", body: JSON.stringify(body || {}) });
      applySnap(snap);
      if (snap.status === "running" || snap.auto) startPoll();
      else {
        fb.busy = false;
        fb.busyLabel = "";
      }
    } catch (e) {
      fb.error = String(e.message || e);
      fb.busy = false;
      fb.busyLabel = "";
    }
    requestRender();
  }

  async function onGenCase() {
    if (!needKey()) return;
    const oral = (document.getElementById("fb-oral")?.value || fb.oral || "").trim();
    if (oral.length < 4) {
      fb.error = "请先填写场景口述";
      requestRender();
      return;
    }
    fb.oral = oral;
    fb.busy = true;
    fb.busyLabel = "生成题目";
    fb.error = null;
    requestRender();
    try {
      const snap = await api("/session/case", {
        method: "POST",
        body: JSON.stringify({ api_key: fb.apiKey, model: fb.model, oral }),
      });
      applySnap(snap);
      fb.focusStep = 2;
      toast("题目已生成");
    } catch (e) {
      fb.error = String(e.message || e);
    } finally {
      fb.busy = false;
      fb.busyLabel = "";
      requestRender();
    }
  }

  async function onBaseline() {
    if (!needKey()) return;
    await postAction("A/B 基线", `/session/${fb.sessionId}/baseline/start`, {
      api_key: fb.apiKey,
      baseline_reps: fb.baselineReps,
      workers: fb.workers,
    });
    fb.focusStep = 3;
  }

  async function onGenomes() {
    if (!needKey()) return;
    await postAction("生成基因组", `/session/${fb.sessionId}/genomes`, {
      api_key: fb.apiKey,
      model: fb.model,
    });
    fb.focusStep = 4;
  }

  async function onPrefilter() {
    if (!needKey()) return;
    await postAction("初筛", `/session/${fb.sessionId}/prefilter/start`, {
      api_key: fb.apiKey,
      pre_reps: fb.preReps,
      qualify_target: fb.qualifyTarget,
      pass_mean: fb.passMean,
      workers: fb.workers,
    });
    fb.focusStep = 5;
  }

  async function onChampion() {
    if (!needKey()) return;
    const pool = fb.snap?.pool || [];
    if (pool.length) {
      try {
        await api(`/session/${fb.sessionId}/champion/pool`, {
          method: "POST",
          body: JSON.stringify({ variant_ids: pool }),
        });
      } catch {
        /* ignore */
      }
    }
    await postAction("终筛", `/session/${fb.sessionId}/champion/start`, {
      api_key: fb.apiKey,
      champ_reps: fb.champReps,
      workers: fb.workers,
    });
    fb.focusStep = 7;
  }

  async function onAbort() {
    if (!fb.sessionId) return;
    try {
      applySnap(await api(`/session/${fb.sessionId}/abort`, { method: "POST", body: "{}" }));
    } catch (e) {
      fb.error = String(e.message || e);
    }
    stopPoll();
    fb.busy = false;
    fb.busyLabel = "";
    requestRender();
  }

  function scoreRow(label, mean, n, extra = "") {
    const m = mean == null ? "—" : Number(mean).toFixed(1);
    return `<div class="fb-score-row">
      <span class="fb-score-label">${esc(label)}</span>
      <div class="fb-score-track"><i style="width:${mean != null ? Math.min(100, mean) : 0}%"></i></div>
      <span class="fb-score-num mono">${esc(m)}${n != null ? ` · n=${n}` : ""}${extra ? ` · ${esc(extra)}` : ""}</span>
    </div>`;
  }

  function titleOf(snap, variantId) {
    const v = (snap?.variants || []).find((x) => x.id === variantId);
    return v?.title || variantId;
  }

  function stepperHtml(focus, unlock) {
    return `<nav class="fb-stepper" aria-label="筛选七步">
      ${STEPS.map((label, i) => {
        const n = i + 1;
        const done = n < focus;
        const active = n === focus;
        const locked = n > unlock;
        return `<button type="button" class="fb-step ${active ? "active" : ""} ${done ? "done" : ""} ${
          locked ? "locked" : ""
        }" data-fb-goto="${n}" ${locked ? "disabled" : ""} title="${esc(label)}">
          <span class="fb-step-n">${done ? "✓" : n}</span>
          <span class="fb-step-label">${esc(label)}</span>
        </button>`;
      }).join("")}
    </nav>`;
  }

  function demoNavBar(focus) {
    const atStart = focus <= 1;
    const atEnd = focus >= 7;
    return `<div class="fb-demo-nav" role="navigation" aria-label="演示导览">
      <button class="btn ghost" type="button" data-fb-action="demo-prev" ${atStart ? "disabled" : ""}>← 上一步</button>
      <div class="fb-demo-progress">
        <span class="fb-demo-progress-label">${focus} / 7 · ${esc(STEPS[focus - 1])}</span>
        <div class="fb-demo-progress-track"><i style="width:${(focus / 7) * 100}%"></i></div>
      </div>
      ${
        atEnd
          ? `<button class="btn primary" type="button" data-fb-action="demo-restart">从头再看</button>`
          : `<button class="btn primary" type="button" data-fb-action="demo-next">下一步 →</button>`
      }
    </div>`;
  }

  function settingsModal() {
    if (!fb.settingsOpen) return "";
    return `<div class="fb-modal-scrim" data-fb-scrim="1">
      <div class="card fb-modal" role="dialog" aria-modal="true">
        <div class="fb-modal-head">
          <h2>运行设置</h2>
          <button class="chip-btn" type="button" data-fb-action="close-settings">关闭</button>
        </div>
        <div class="meta" style="margin-bottom:12px">真实运行需要 Key · 仅存本浏览器 sessionStorage</div>
        <label class="fb-field"><span>API Key</span>
          <input id="fb-api-key" type="password" autocomplete="off" value="${esc(fb.apiKey)}" placeholder="sk-…" />
        </label>
        <label class="fb-field"><span>模型 id</span>
          <input id="fb-model" type="text" value="${esc(fb.model)}" />
        </label>
        <label class="fb-field"><span>并发 workers</span>
          <input id="fb-workers" type="number" min="1" max="16" value="${esc(fb.workers)}" />
        </label>
        <div class="list proj-actions" style="margin-top:14px">
          <button class="btn primary" type="button" data-fb-action="save-settings">保存</button>
          <button class="btn ghost" type="button" data-fb-action="close-settings">取消</button>
        </div>
      </div>
    </div>`;
  }

  function renderHome() {
    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <div class="tags" style="margin-bottom:10px"><span class="tag blue">单题 DNA 搜索</span></div>
        <h2>从一道题筛出最优基因组</h2>
        <div class="meta">七步：选题 → 裁判 → A/B → 基因组 → 初筛 → 冠军池 → 终筛</div>
        <div class="list proj-actions" style="margin-top:14px">
          <button class="btn primary" type="button" data-fb-action="open-pick">进入</button>
        </div>
      </div>
    </div>`;
  }

  function renderPick() {
    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <button class="chip-btn" type="button" data-fb-action="back-home" style="margin-bottom:12px">← 返回</button>
        <h2>选择运行方式</h2>
        <div class="meta">演示：浏览冻结结果，不调模型 · 真实运行：消耗 API</div>
        <div class="fb-mode-grid">
          <button class="fb-mode-card" type="button" data-fb-action="start-demo" ${fb.busy ? "disabled" : ""}>
            <div class="fb-mode-kicker">推荐先看</div>
            <div class="row-title">演示形式</div>
            <div class="row-desc">批判思维冻结包 · 七步导览（上一步 / 下一步）</div>
          </button>
          <button class="fb-mode-card" type="button" data-fb-action="start-live" ${fb.busy ? "disabled" : ""}>
            <div class="fb-mode-kicker">真实 API</div>
            <div class="row-title">真实运行</div>
            <div class="row-desc">配置 Key 后生成题目 / 跑基线与筛选</div>
          </button>
        </div>
        ${fb.error ? `<div class="fb-error">${esc(fb.error)}</div>` : ""}
        ${fb.busy ? `<div class="meta" style="margin-top:12px">${esc(fb.busyLabel || "加载中…")}</div>` : ""}
      </div>
      ${settingsModal()}
    </div>`;
  }

  /* —— 演示：每一步只展示内容 + 导览，无假动作按钮 —— */
  function demoPanel(focus, snap) {
    const story = DEMO_STORY[focus - 1] || "";
    const head = `<div class="fb-story">
      <div class="fb-story-kicker">第 ${focus} 步 · ${esc(STEPS[focus - 1])}</div>
      <p>${esc(story)}</p>
    </div>`;

    if (focus === 1) {
      return `${head}<div class="card fb-panel">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">${esc(snap?.case?.id || "—")}</span>
          <span class="tag green">冻结演示</span>
        </div>
        <h2>${esc(snap?.case?.title || "批判思维题")}</h2>
        <div class="meta" style="margin-top:6px">${esc(snap?.case?.description || "")}</div>
        <div class="fb-panel-kicker" style="margin-top:14px">场景口述</div>
        <div class="fb-oral">${esc(snap?.oral || "演示：批判思维虚假二选一")}</div>
      </div>`;
    }

    if (focus === 2) {
      return `${head}<div class="card fb-panel">
        <div class="fb-split">
          <div>
            <div class="fb-panel-kicker">原题（选手可见）</div>
            <pre class="fb-pre">${esc(snap?.target_text || "（无）")}</pre>
          </div>
          <div>
            <div class="fb-panel-kicker">裁判标准（不进基因组）</div>
            <pre class="fb-pre">${esc(snap?.criteria_text || "（无）")}</pre>
          </div>
        </div>
      </div>`;
    }

    if (focus === 3) {
      const rows = snap?.baseline_summaries || [];
      const a = rows.find((r) => r.arm === "A" || r.variant_id === "A");
      const b = rows.find((r) => r.arm === "B" || r.variant_id === "B");
      const gap =
        a?.mean != null && b?.mean != null ? (Number(b.mean) - Number(a.mean)).toFixed(1) : null;
      return `${head}<div class="card fb-panel">
        ${
          gap != null
            ? `<div class="fb-insight">B − A ≈ <strong>${esc(gap)}</strong> 分 · 天花板与地板的差距，就是基因组可争取的空间</div>`
            : ""
        }
        ${
          rows.length
            ? rows
                .map((r) =>
                  scoreRow(r.title || r.arm || r.variant_id, r.mean, r.n, r.sdv != null ? `sd=${Number(r.sdv).toFixed(2)}` : "")
                )
                .join("")
            : `<div class="empty" style="padding:16px 0">冻结包缺少基线数据</div>`
        }
      </div>`;
    }

    if (focus === 4) {
      const list = snap?.variants || [];
      const pool = new Set(snap?.pool || []);
      const openId = fb.demoVariantId || list[0]?.id || null;
      const open = list.find((v) => v.id === openId) || list[0];
      const slots = open?.slots && typeof open.slots === "object" ? open.slots : {};
      return `${head}<div class="card fb-panel">
        <div class="meta" style="margin-bottom:10px">共 ${list.length} 个候选 · 点名称展开槽位</div>
        <div class="fb-variant-list">
          ${
            list
              .map((v) => {
                const on = v.id === open?.id;
                const inPool = pool.has(v.id);
                return `<button type="button" class="fb-variant fb-variant-btn ${on ? "active" : ""}" data-fb-action="demo-pick-variant" data-fb-variant="${esc(v.id)}">
                  <div class="fb-variant-row">
                    <div>
                      <div class="row-title">${esc(v.title || v.id)}</div>
                      <div class="row-desc mono">${esc(v.id)}</div>
                    </div>
                    <div class="tags">${inPool ? `<span class="tag orange">入池</span>` : ""}</div>
                  </div>
                </button>`;
              })
              .join("") || `<div class="empty">暂无 variant</div>`
          }
        </div>
        ${
          open
            ? `<div class="fb-slot-box">
                <div class="fb-panel-kicker">${esc(open.title || open.id)} · 基因组槽位</div>
                <div class="fb-slots">${Object.entries(slots)
                  .map(([k, val]) => `<div class="fb-slot"><span>${esc(k)}</span><code>${esc(val)}</code></div>`)
                  .join("")}</div>
              </div>`
            : ""
        }
      </div>`;
    }

    if (focus === 5) {
      const rows = [...(snap?.pre_summaries || [])].sort((a, b) => (b.mean || 0) - (a.mean || 0));
      return `${head}<div class="card fb-panel">
        <div class="meta" style="margin-bottom:10px">按均分排序 · passed 表示过线</div>
        ${
          rows.length
            ? rows
                .map((r) =>
                  scoreRow(
                    r.title || r.variant_id,
                    r.mean,
                    r.n,
                    r.passed ? "过线" : "未过"
                  )
                )
                .join("")
            : `<div class="empty" style="padding:16px 0">冻结包缺少初筛数据</div>`
        }
      </div>`;
    }

    if (focus === 6) {
      const pool = snap?.pool || [];
      return `${head}<div class="card fb-panel">
        <div class="meta" style="margin-bottom:10px">终筛只测这 ${pool.length} 个，控制成本</div>
        <div class="fb-variant-list">
          ${
            pool
              .map(
                (id, i) => `<div class="fb-variant">
              <div class="fb-variant-row">
                <div>
                  <div class="row-title">${i + 1}. ${esc(titleOf(snap, id))}</div>
                  <div class="row-desc mono">${esc(id)}</div>
                </div>
                <span class="tag orange">冠军池</span>
              </div>
            </div>`
              )
              .join("") || `<div class="empty">池为空</div>`
          }
        </div>
      </div>`;
    }

    const marks = snap?.marks || {};
    const rows = [...(snap?.champ_summaries || [])].sort((a, b) => (b.mean || 0) - (a.mean || 0));
    const bal = marks.balanced;
    return `${head}<div class="card fb-panel">
      ${
        bal
          ? `<div class="fb-insight fb-insight-win">金牌（均衡）· <strong>${esc(titleOf(snap, bal))}</strong>
              <span class="mono"> · ${esc(bal)}</span></div>`
          : ""
      }
      <div class="tags" style="margin:10px 0">
        ${marks.balanced ? `<span class="tag">均衡 · ${esc(titleOf(snap, marks.balanced))}</span>` : ""}
        ${marks.perf ? `<span class="tag green">效果 · ${esc(titleOf(snap, marks.perf))}</span>` : ""}
        ${marks.stable ? `<span class="tag blue">稳定 · ${esc(titleOf(snap, marks.stable))}</span>` : ""}
      </div>
      ${
        rows.length
          ? rows.map((r) => scoreRow(r.title || r.variant_id, r.mean, r.n, r.sdv != null ? `sd=${Number(r.sdv).toFixed(2)}` : "")).join("")
          : `<div class="empty" style="padding:16px 0">冻结包缺少终筛数据</div>`
      }
    </div>`;
  }

  function livePanel(focus, snap) {
    if (focus === 1) {
      const oral = snap?.oral || fb.oral || "";
      return `<div class="card">
        <h2>1 · 选题</h2>
        <div class="meta">真实运行 · 口述生成题目（需 Key）</div>
        <label class="fb-field"><span>场景口述</span>
          <textarea id="fb-oral" rows="4" class="fb-textarea">${esc(oral)}</textarea>
        </label>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="gen-case" ${fb.busy ? "disabled" : ""}>生成题目与标准</button>
          <button class="chip-btn" type="button" data-fb-action="open-settings">设置 API Key</button>
        </div>
      </div>`;
    }
    if (focus === 2) {
      return `<div class="card">
        <h2>2 · 题目 / 裁判</h2>
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">${esc(snap?.case?.id || "—")}</span>
          <span class="tag">${esc(snap?.case?.title || "—")}</span>
        </div>
        <div class="fb-split">
          <div>
            <div class="fb-panel-kicker">原题</div>
            <pre class="fb-pre">${esc(snap?.target_text || "")}</pre>
          </div>
          <div>
            <div class="fb-panel-kicker">裁判标准</div>
            <pre class="fb-pre">${esc(snap?.criteria_text || "")}</pre>
          </div>
        </div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="goto-next-live" ${!snap?.case ? "disabled" : ""}>下一步 · 跑 A/B</button>
        </div>
      </div>`;
    }
    if (focus === 3) {
      const rows = snap?.baseline_summaries || [];
      return `<div class="card">
        <h2>3 · A/B 基线</h2>
        <div class="meta">A 地板 · B 天花板（教考泄露）</div>
        ${
          rows.length
            ? rows.map((r) => scoreRow(r.arm || r.variant_id, r.mean, r.n)).join("")
            : `<div class="empty" style="padding:16px 0">尚未跑基线</div>`
        }
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="baseline" ${
            fb.busy || !fb.sessionId ? "disabled" : ""
          }>开始 A/B 基线</button>
        </div>
      </div>`;
    }
    if (focus === 4) {
      const list = snap?.variants || [];
      return `<div class="card">
        <h2>4 · 基因组</h2>
        <div class="fb-variant-list">
          ${
            list
              .map(
                (v) => `<div class="fb-variant">
              <div class="row-title">${esc(v.title || v.id)}</div>
              <div class="row-desc mono">${esc(v.id || "")}</div>
            </div>`
              )
              .join("") || `<div class="empty">暂无 variant · 点下方生成</div>`
          }
        </div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="genomes" ${fb.busy ? "disabled" : ""}>生成基因组</button>
        </div>
      </div>`;
    }
    if (focus === 5) {
      const rows = snap?.pre_summaries || [];
      return `<div class="card">
        <h2>5 · 初筛</h2>
        ${
          rows.length
            ? rows.map((r) => scoreRow(r.title || r.variant_id, r.mean, r.n)).join("")
            : `<div class="empty" style="padding:16px 0">尚未初筛</div>`
        }
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="prefilter" ${fb.busy ? "disabled" : ""}>开始初筛</button>
        </div>
      </div>`;
    }
    if (focus === 6) {
      const pool = snap?.pool || [];
      return `<div class="card">
        <h2>6 · 冠军池</h2>
        <div class="fb-variant-list">
          ${
            pool.map((id) => `<div class="fb-variant"><div class="row-title mono">${esc(id)}</div></div>`).join("") ||
            `<div class="empty">池为空 · 初筛完成后自动填充</div>`
          }
        </div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-fb-action="goto-champ" ${!pool.length || fb.busy ? "disabled" : ""}>下一步 · 终筛</button>
        </div>
      </div>`;
    }
    const marks = snap?.marks || {};
    const rows = snap?.champ_summaries || [];
    return `<div class="card">
      <h2>7 · 终筛金牌</h2>
      <div class="tags" style="margin-bottom:10px">
        ${marks.balanced ? `<span class="tag">均衡 · ${esc(marks.balanced)}</span>` : ""}
        ${marks.perf ? `<span class="tag green">效果 · ${esc(marks.perf)}</span>` : ""}
        ${marks.stable ? `<span class="tag blue">稳定 · ${esc(marks.stable)}</span>` : ""}
      </div>
      ${
        rows.length
          ? rows.map((r) => scoreRow(r.title || r.variant_id, r.mean, r.n)).join("")
          : `<div class="empty" style="padding:16px 0">尚未终筛</div>`
      }
      <div class="list proj-actions" style="margin-top:12px">
        <button class="btn primary" type="button" data-fb-action="champion" ${fb.busy ? "disabled" : ""}>开始终筛</button>
      </div>
    </div>`;
  }

  function renderRunDemo() {
    const snap = fb.snap;
    if (fb.busy && !snap) {
      return `<div class="pad fb-page">
        <div class="card fb-hero">
          <h2>载入冻结演示…</h2>
          <div class="meta">${esc(fb.busyLabel || "请稍候")}</div>
        </div>
      </div>`;
    }
    if (!snap) {
      return `<div class="pad fb-page">
        <div class="card fb-hero">
          <h2>演示未载入</h2>
          ${fb.error ? `<div class="fb-error">${esc(fb.error)}</div>` : ""}
          <div class="list proj-actions" style="margin-top:12px">
            <button class="btn primary" type="button" data-fb-action="start-demo">重试载入</button>
            <button class="chip-btn" type="button" data-fb-action="open-pick">返回选择</button>
          </div>
        </div>
      </div>`;
    }

    const focus = Math.min(7, Math.max(1, fb.focusStep || 1));
    fb.focusStep = focus;

    return `<div class="pad fb-page fb-demo">
      <div class="card fb-hero">
        <div class="fb-run-top">
          <button class="chip-btn" type="button" data-fb-action="open-pick">← 退出演示</button>
          <div class="tags">
            <span class="tag green">演示导览</span>
            <span class="tag orange">冻结包</span>
          </div>
        </div>
        <h2>${esc(snap.case?.title || "冻结演示")}</h2>
        <div class="meta">用底部「下一步」按故事浏览 · 也可点上方步骤条跳转 · 不消耗 Token</div>
        ${fb.error ? `<div class="fb-error">${esc(fb.error)}</div>` : ""}
      </div>
      <div class="card fb-stepper-card">${stepperHtml(focus, 7)}</div>
      <div class="fb-demo-body">${demoPanel(focus, snap)}</div>
      ${demoNavBar(focus)}
    </div>`;
  }

  function renderRunLive() {
    const snap = fb.snap;
    const phase = snap?.phase || "idle";
    const rank = phaseRank(phase);
    const unlock = unlockedMax(rank, snap);
    const focus = Math.min(Math.max(1, fb.focusStep), Math.max(unlock, 1));
    fb.focusStep = focus;
    const running = snap?.status === "running" || fb.busy;

    return `<div class="pad fb-page">
      <div class="card fb-hero">
        <div class="fb-run-top">
          <button class="chip-btn" type="button" data-fb-action="open-pick">← 重选方式</button>
          <div class="tags">
            <span class="tag blue">真实运行</span>
            <span class="tag">${esc(phase)}</span>
            ${running ? `<span class="tag orange">${esc(fb.busyLabel || "运行中")}</span>` : ""}
          </div>
        </div>
        <h2>${esc(snap?.case?.title || "真实运行台")}</h2>
        <div class="meta mono">${esc(snap?.case?.id || "—")}${
          fb.sessionId ? ` · ${esc(String(fb.sessionId).slice(0, 8))}` : ""
        }</div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="chip-btn" type="button" data-fb-action="open-settings">设置</button>
          ${running ? `<button class="btn ghost" type="button" data-fb-action="abort">中止</button>` : ""}
        </div>
        ${fb.error ? `<div class="fb-error">${esc(fb.error)}</div>` : ""}
      </div>
      <div class="card" style="margin-top:14px">${stepperHtml(focus, unlock)}</div>
      <div style="margin-top:14px">${livePanel(focus, snap)}</div>
      ${settingsModal()}
    </div>`;
  }

  function renderRun() {
    if (fb.runMode === "demo") return renderRunDemo();
    return renderRunLive();
  }

  function render() {
    if (fb.view === "pick") return renderPick();
    if (fb.view === "run") return renderRun();
    return renderHome();
  }

  function readSettingsForm() {
    const key = document.getElementById("fb-api-key");
    const model = document.getElementById("fb-model");
    const workers = document.getElementById("fb-workers");
    if (key) fb.apiKey = key.value.trim();
    if (model) fb.model = model.value.trim() || "k3";
    if (workers) fb.workers = Math.max(1, Math.min(16, Number(workers.value) || 4));
  }

  function handleClick(e) {
    if (fb.settingsOpen && e.target?.getAttribute?.("data-fb-scrim") === "1") {
      e.preventDefault();
      fb.settingsOpen = false;
      requestRender();
      return true;
    }
    const t = e.target.closest("[data-fb-action],[data-fb-goto]");
    if (!t) return false;
    e.preventDefault();
    const goto = t.getAttribute("data-fb-goto");
    if (goto) {
      const unlock =
        fb.runMode === "demo" ? 7 : unlockedMax(phaseRank(fb.snap?.phase), fb.snap);
      const n = Number(goto) || 1;
      if (n > unlock) return true;
      fb.focusStep = n;
      requestRender();
      return true;
    }
    switch (t.getAttribute("data-fb-action")) {
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
        demoNext();
        break;
      case "demo-prev":
        demoPrev();
        break;
      case "demo-restart":
        demoGoto(1);
        toast("回到第 1 步");
        break;
      case "demo-pick-variant": {
        const id = t.getAttribute("data-fb-variant");
        if (id) {
          fb.demoVariantId = id;
          requestRender();
        }
        break;
      }
      case "goto-next-live":
        fb.focusStep = 3;
        requestRender();
        break;
      case "goto-champ":
        fb.focusStep = 7;
        requestRender();
        break;
      case "open-settings":
        fb.settingsOpen = true;
        requestRender();
        break;
      case "close-settings":
        fb.settingsOpen = false;
        requestRender();
        break;
      case "save-settings":
        readSettingsForm();
        saveSettings();
        fb.settingsOpen = false;
        toast("设置已保存");
        requestRender();
        break;
      case "gen-case":
        onGenCase();
        break;
      case "baseline":
        onBaseline();
        break;
      case "genomes":
        onGenomes();
        break;
      case "prefilter":
        onPrefilter();
        break;
      case "champion":
        onChampion();
        break;
      case "abort":
        onAbort();
        break;
      default:
        return false;
    }
    return true;
  }

  function ensureDemo() {
    return Promise.resolve();
  }

  return {
    render,
    handleClick,
    ensureDemo,
    openPick,
    get state() {
      return fb;
    },
  };
})();
