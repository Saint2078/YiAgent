/**
 * 角色工厂：填一个角色名 → 锚点题源 → 能力维度 → 题组+裁判 → 种子基因库 → 进化+Holdout → 冠军基因组
 *
 * 演示 = 冻结「结构」（role-factory-demo.json，分数一律标未实跑）
 * 实跑 = POST /api/factory/role/build 出题组与裁判，再把 manifest 交给 /api/factory/evolve/start 搜基因
 */
const RoleFactory = (() => {
  const STEPS = [
    "角色与目标",
    "锚点题源",
    "能力维度",
    "题组 + 裁判",
    "种子基因库",
    "进化 + Holdout",
    "冠军基因组",
  ];
  const STORIES = [
    "只填一个角色名。角色名决定后面所有题目与裁判的走向，所以它是唯一的人类输入。",
    "先看这个角色能借哪些 benchmark 的题型与判分口径当锚点——借口径，不抄题面。",
    "把角色拆成能拉开差距的能力维度：每一维都要能出题、能打分、能指出失败样态。",
    "每个维度出题并同时产出裁判 rubric：题面进表达集，评分标准只进评分库，两边不混。",
    "按锚点题生成 G1–G5 等位库与候选基因组，其中故意保留对照弱等位以拉开分差。",
    "多代进化在进化集上选种，Holdout 不参与选种，用来验证不是过拟合题组。",
    "冠军基因组 = 可导出的角色成品：槽位可指认、分数可复算、题组与裁判可追溯。",
  ];

  const DEMO_URL = "/role-factory-demo.json";
  const SETTINGS_KEY = "yiagent-factory-bench-settings-v1";

  const rf = {
    view: "home", // home | run
    mode: null, // demo | live
    focusStep: 1,
    role: "数据分析专家",
    busy: false,
    busyLabel: "",
    error: null,
    settingsOpen: false,
    demo: null,
    build: null,
    evolve: null,
    report: null,
    anchors: null,
    factoryOk: null,
    pollTimer: null,
    apiKey: "",
    model: "k3",
    perDim: 2,
    maxGenerations: 2,
    variantsPerGen: 6,
    workers: 8,
  };

  function loadSettings() {
    try {
      const o = JSON.parse(sessionStorage.getItem(SETTINGS_KEY) || "{}");
      if (o.apiKey != null) rf.apiKey = String(o.apiKey);
      if (o.model) rf.model = o.model;
    } catch {
      /* ignore */
    }
  }
  loadSettings();

  function saveSettings() {
    try {
      const prev = JSON.parse(sessionStorage.getItem(SETTINGS_KEY) || "{}");
      sessionStorage.setItem(
        SETTINGS_KEY,
        JSON.stringify({ ...prev, apiKey: rf.apiKey, model: rf.model })
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

  /** nginx: /api/factory/X → factory:80/api/X */
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

  async function probeFactory() {
    try {
      const res = await fetch("/api/factory/health", { method: "GET" });
      const text = await res.text();
      rf.factoryOk = res.ok && !/<!DOCTYPE|<html/i.test(text);
    } catch {
      rf.factoryOk = false;
    }
    return rf.factoryOk;
  }

  function stopPoll() {
    if (rf.pollTimer) {
      clearInterval(rf.pollTimer);
      rf.pollTimer = null;
    }
  }

  function reset() {
    stopPoll();
    rf.build = null;
    rf.evolve = null;
    rf.report = null;
    rf.anchors = null;
    rf.error = null;
    rf.busy = false;
    rf.busyLabel = "";
    rf.focusStep = 1;
  }

  function roleInputValue() {
    const el = document.getElementById("rf-role");
    const v = el ? String(el.value || "").trim() : "";
    if (v) rf.role = v;
    return rf.role;
  }

  function needKey() {
    if (!rf.apiKey || rf.apiKey.length < 8) {
      rf.error = "真实构建需先填写 API Key（设置）";
      rf.settingsOpen = true;
      requestRender();
      return false;
    }
    return true;
  }

  // ---------------------------------------------------------------- data view

  function view() {
    if (rf.mode === "demo") {
      const d = rf.demo || {};
      return {
        frozen: true,
        role: d.role,
        roleId: d.role_id,
        blueprint: d.blueprint || null,
        anchors: d.anchors || null,
        cases: d.cases || [],
        bank: d.seed_bank || null,
        manifest: d.manifest_preview || null,
        scoresStatus: d.scores_status || "未实跑",
        scoresNote: d.scores_note || "",
        demoScope: d.demo_scope || "",
        nextStep: d.next_step || null,
      };
    }
    const b = rf.build || {};
    return {
      frozen: false,
      role: b.role || rf.role,
      roleId: b.role_id,
      blueprint: b.blueprint || null,
      anchors: b.anchors || rf.anchors || null,
      cases: b.cases || [],
      bank: null,
      manifest: b.manifest || null,
      scoresStatus: rf.report ? "已实跑" : rf.evolve ? "进行中" : "未实跑",
      scoresNote: "",
      demoScope: "",
      nextStep: b.next_step || null,
    };
  }

  // ---------------------------------------------------------------- actions

  async function startDemo() {
    reset();
    rf.mode = "demo";
    rf.view = "run";
    rf.busy = true;
    rf.busyLabel = "载入结构演示";
    requestRender();
    try {
      const res = await fetch(DEMO_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`结构演示 HTTP ${res.status}`);
      rf.demo = await res.json();
      rf.role = rf.demo.role || rf.role;
      toast("结构演示已载入 · 分数需真实运行才有");
    } catch (e) {
      rf.error = String(e.message || e);
      rf.view = "home";
    } finally {
      rf.busy = false;
      rf.busyLabel = "";
      requestRender();
    }
  }

  async function startLive() {
    const role = roleInputValue();
    if (!role || role.length < 2) {
      rf.error = "请先填角色名，如「数据分析专家」";
      requestRender();
      return;
    }
    if (!needKey()) return;
    if (rf.factoryOk === null) await probeFactory();
    if (!rf.factoryOk) {
      rf.error =
        "factory 服务不可达。角色工厂的出题与进化跑在 factory 容器里：在 console/ 目录 docker compose up -d 后重试。";
      requestRender();
      return;
    }
    reset();
    rf.mode = "live";
    rf.view = "run";
    rf.busy = true;
    rf.busyLabel = "构建题组与裁判";
    requestRender();
    try {
      const snap = await api("/role/build", {
        method: "POST",
        body: JSON.stringify({
          api_key: rf.apiKey,
          model: rf.model,
          role,
          per_dim: rf.perDim,
        }),
      });
      rf.build = snap;
      rf.focusStep = 2;
      pollBuild();
      toast(`角色工厂已开跑 · ${role}`);
    } catch (e) {
      rf.error = String(e.message || e);
      rf.busy = false;
      rf.busyLabel = "";
      rf.view = "home";
    }
    requestRender();
  }

  function pollBuild() {
    stopPoll();
    rf.pollTimer = setInterval(async () => {
      const id = rf.build?.id;
      if (!id) return;
      try {
        const snap = await api(`/role/build/${id}`);
        rf.build = snap;
        if (snap.phase === "blueprint" && rf.focusStep < 3) rf.focusStep = 3;
        if (snap.phase === "cases" && rf.focusStep < 4) rf.focusStep = 4;
        if (snap.status !== "running") {
          stopPoll();
          rf.busy = false;
          rf.busyLabel = "";
          if (snap.status === "done") {
            rf.focusStep = 5;
            toast(`题组就绪 · ${snap.suite?.cases || 0} 题 · manifest ${snap.manifest?.id || "—"}`);
          } else if (snap.error) {
            rf.error = snap.error;
          }
        }
        requestRender();
      } catch {
        /* keep polling */
      }
    }, 1500);
  }

  async function startEvolve() {
    if (!needKey()) return;
    const manifestId = rf.build?.manifest?.id;
    if (!manifestId) {
      rf.error = "还没有 manifest，先完成题组构建";
      requestRender();
      return;
    }
    rf.busy = true;
    rf.busyLabel = "启动基因搜索";
    rf.error = null;
    requestRender();
    try {
      const snap = await api("/evolve/start", {
        method: "POST",
        body: JSON.stringify({
          api_key: rf.apiKey,
          model: rf.model,
          manifest_id: manifestId,
          oral: rf.build?.blueprint?.display_name || rf.role,
          max_generations: rf.maxGenerations,
          variants_per_gen: rf.variantsPerGen,
          workers: rf.workers,
          with_baseline: true,
          use_cache: true,
        }),
      });
      rf.evolve = snap;
      rf.focusStep = 6;
      pollEvolve();
      toast("基因搜索已启动");
    } catch (e) {
      rf.error = String(e.message || e);
      rf.busy = false;
      rf.busyLabel = "";
    }
    requestRender();
  }

  function pollEvolve() {
    stopPoll();
    rf.pollTimer = setInterval(async () => {
      const id = rf.evolve?.id || rf.evolve?.run_id;
      if (!id) return;
      try {
        const snap = await api(`/evolve/${id}`);
        rf.evolve = snap;
        if (snap.status === "done" || snap.status === "error" || snap.status === "aborted") {
          stopPoll();
          rf.busy = false;
          rf.busyLabel = "";
          if (snap.status === "done") {
            try {
              rf.report = await api(`/evolve/${id}/report`);
              rf.focusStep = 7;
            } catch {
              /* report may lag */
            }
          }
        }
        requestRender();
      } catch {
        /* keep */
      }
    }, 1800);
  }

  async function abortAll() {
    try {
      if (rf.evolve?.id) {
        await api(`/evolve/${rf.evolve.id}/abort`, { method: "POST", body: "{}" });
      } else if (rf.build?.id) {
        await api(`/role/build/${rf.build.id}/abort`, { method: "POST", body: "{}" });
      }
    } catch (e) {
      rf.error = String(e.message || e);
    }
    stopPoll();
    rf.busy = false;
    rf.busyLabel = "";
    requestRender();
  }

  async function loadAnchorsOnly() {
    const role = roleInputValue();
    if (!role) return;
    rf.busy = true;
    rf.busyLabel = "检索锚点题源";
    rf.error = null;
    requestRender();
    try {
      rf.anchors = await api(`/role/anchors?role=${encodeURIComponent(role)}`);
      rf.mode = "live";
      rf.view = "run";
      rf.focusStep = 2;
      toast(`锚点：benchmark ${rf.anchors.benchmarks?.length || 0} 条（不发 LLM、不花 token）`);
    } catch (e) {
      rf.error = `${String(e.message || e)} · 锚点检索需要 factory 服务`;
    } finally {
      rf.busy = false;
      rf.busyLabel = "";
      requestRender();
    }
  }

  // ---------------------------------------------------------------- render

  function stepperHtml(focus) {
    return `<nav class="fb-stepper" aria-label="角色工厂七步">
      ${STEPS.map((label, i) => {
        const n = i + 1;
        return `<button type="button" class="fb-step ${n === focus ? "active" : ""} ${
          n < focus ? "done" : ""
        }" data-rf-goto="${n}">
          <span class="fb-step-n">${n < focus ? "✓" : n}</span>
          <span class="fb-step-label">${esc(label)}</span>
        </button>`;
      }).join("")}
    </nav>`;
  }

  function navBar(focus) {
    return `<div class="list proj-actions" style="margin-top:14px;gap:6px;flex-wrap:wrap">
      <button class="chip-btn" type="button" data-rf-goto="${Math.max(1, focus - 1)}" ${
      focus <= 1 ? "disabled" : ""
    }>← 上一步</button>
      <button class="chip-btn primary" type="button" data-rf-goto="${Math.min(7, focus + 1)}" ${
      focus >= 7 ? "disabled" : ""
    }>下一步 →</button>
      <button class="chip-btn" type="button" data-rf-action="back-home">退出</button>
    </div>`;
  }

  function scoresBadge(v) {
    const cls =
      v.scoresStatus === "已实跑" ? "green" : v.scoresStatus === "进行中" ? "blue" : "orange";
    return `<span class="tag ${cls}">分数：${esc(v.scoresStatus)}</span>`;
  }

  function anchorPanel(v) {
    const list = v.anchors?.benchmarks || [];
    if (!list.length) return `<div class="empty">暂无锚点（未检索或无匹配）</div>`;
    return `<div class="fb-variant-list">${list
      .map(
        (b) => `<div class="fb-slot-box" style="margin-bottom:10px">
          <div class="fb-panel-kicker">${esc(b.title || b.id)} ${
          b.runnable_here
            ? `<span class="tag green">可直接实跑</span>`
            : `<span class="tag">仅作口径锚点</span>`
        }</div>
          <div class="meta">题型：${esc(b.task_shape || "—")}</div>
          <div class="meta">判分：${esc(b.scoring || "—")}</div>
          <div class="meta">路径：<code>${esc(b.path || "—")}</code>${
          b.scale ? ` · ${esc(b.scale)}` : ""
        }</div>
          ${b.blocked_by ? `<div class="meta">原题跑不了的原因：${esc(b.blocked_by)}</div>` : ""}
        </div>`
      )
      .join("")}</div>`;
  }

  function dimPanel(v) {
    const bp = v.blueprint;
    if (!bp) return `<div class="empty">能力维度尚未生成</div>`;
    const dims = bp.dimensions || [];
    return `<div>
      <div class="fb-insight">${esc(bp.summary || "")}${
      bp.users ? ` · 服务对象：${esc(bp.users)}` : ""
    }</div>
      <div class="fb-variant-list" style="margin-top:12px">${dims
        .map(
          (d) => `<div class="fb-slot-box" style="margin-bottom:10px">
            <div class="fb-panel-kicker">${esc(d.label)} · 权重 ${esc(d.weight)}</div>
            <div class="meta">为何是分水岭：${esc(d.why || "—")}</div>
            <div class="meta">怎么考：${esc(d.probe || "—")}</div>
            ${
              (d.failure_modes || []).length
                ? `<div class="meta">失败样态：${esc((d.failure_modes || []).join(" / "))}</div>`
                : ""
            }
          </div>`
        )
        .join("")}</div>
      ${
        (bp.denylist || []).length
          ? `<div class="fb-panel-kicker" style="margin-top:12px">denylist（进扣分项）</div>
             <ul class="fb-req">${(bp.denylist || [])
               .map((x) => `<li>${esc(x)}</li>`)
               .join("")}</ul>`
          : ""
      }
    </div>`;
  }

  function casePanel(v) {
    const cases = v.cases || [];
    if (!cases.length) return `<div class="empty">题组尚未生成</div>`;
    return `<div>
      ${v.demoScope ? `<div class="meta" style="margin-bottom:10px">${esc(v.demoScope)}</div>` : ""}
      <div class="fb-variant-list">${cases
        .map((c) => {
          const crit = c.criteria || {};
          const critNames = Array.isArray(crit) ? crit : Object.keys(crit);
          const reqs = c.requirements || [];
          return `<div class="fb-slot-box" style="margin-bottom:10px">
            <div class="fb-panel-kicker">${esc(c.title || c.id)} <span class="tag blue">${esc(
            c.dimension || "—"
          )}</span><span class="tag">${esc(c.level || "basic")}</span></div>
            <div class="meta"><code>${esc(c.id)}</code>${
            c.description ? ` · ${esc(c.description)}` : ""
          }</div>
            ${
              reqs.length
                ? `<div class="meta" style="margin-top:6px">验收要点：</div><ul class="fb-req">${reqs
                    .slice(0, 6)
                    .map((r) => `<li>${esc(r)}</li>`)
                    .join("")}</ul>`
                : ""
            }
            <div class="meta">裁判维度（只进评分库）：${
              critNames.length ? esc(critNames.join(" / ")) : "—"
            }</div>
          </div>`;
        })
        .join("")}</div>
    </div>`;
  }

  function bankPanel(v) {
    if (v.frozen && v.bank) {
      const alleles = v.bank.alleles || {};
      return `<div>
        <div class="meta" style="margin-bottom:10px">${esc(v.bank.note || "")}</div>
        ${Object.keys(alleles)
          .map(
            (slot) => `<div class="fb-slot-box" style="margin-bottom:10px">
              <div class="fb-panel-kicker">${esc(slot)}</div>
              ${(alleles[slot] || [])
                .map(
                  (a) =>
                    `<div class="fb-slot"><span>${esc(a.label)}</span><code>${esc(a.id)}</code></div>`
                )
                .join("")}
            </div>`
          )
          .join("")}
        <div class="fb-panel-kicker" style="margin-top:12px">候选基因组</div>
        <div class="fb-variant-list">${(v.bank.variants || [])
          .map(
            (x) =>
              `<div class="fb-slot"><span>${esc(x.title || x.id)}</span><code>${esc(x.id)}</code></div>`
          )
          .join("")}</div>
      </div>`;
    }
    const manifest = rf.build?.manifest;
    return `<div>
      ${
        manifest
          ? `<div class="fb-insight">题组已就绪：manifest <code>${esc(
              manifest.id
            )}</code> · 进化集 ${manifest.cases?.length || 0} 题 · Holdout ${
              manifest.holdout?.length || 0
            } 题</div>`
          : `<div class="empty">题组尚未就绪</div>`
      }
      <div class="meta" style="margin-top:10px">种子等位库由 <code>generate_genomes</code> 依锚点题在进化启动时生成；点下面开始搜基因。</div>
      <div class="list proj-actions" style="margin-top:12px;gap:6px;flex-wrap:wrap">
        <button class="chip-btn primary" type="button" data-rf-action="start-evolve" ${
          manifest ? "" : "disabled"
        }>开始基因搜索（真实消耗 token）</button>
        <button class="chip-btn" type="button" data-rf-action="open-settings">设置</button>
      </div>
    </div>`;
  }

  function evolvePanel(v) {
    if (v.frozen) {
      return `<div>
        <div class="fb-insight">${esc(v.scoresNote || "")}</div>
        <div class="meta" style="margin-top:10px">题组切分：${esc(
          v.manifest?.evolve_cases || "—"
        )} · Holdout：${esc(v.manifest?.holdout_cases || "—")}</div>
        <div class="fb-panel-kicker" style="margin-top:12px">要拿到分数，需依次调用</div>
        <pre class="fb-pre">${esc(
          [v.nextStep?.build, v.nextStep?.evolve, v.nextStep?.ship].filter(Boolean).join("\n")
        )}</pre>
      </div>`;
    }
    const snap = rf.evolve;
    if (!snap) return `<div class="empty">尚未启动基因搜索</div>`;
    const gens = snap.generations || snap.gens || [];
    return `<div>
      <div class="tags" style="margin-bottom:10px">
        <span class="tag blue">run ${esc(snap.id || snap.run_id || "—")}</span>
        <span class="tag">${esc(snap.status || "—")}</span>
        ${snap.phase ? `<span class="tag">${esc(snap.phase)}</span>` : ""}
      </div>
      ${
        gens.length
          ? `<div class="fb-variant-list" style="margin-top:10px">${gens
              .map(
                (g) =>
                  `<div class="fb-slot"><span>第 ${esc(g.gen ?? "—")} 代 · ${esc(
                    g.verdict || g.status || ""
                  )}</span><code>${esc(g.champion?.mean ?? g.mean ?? "—")}</code></div>`
              )
              .join("")}</div>`
          : `<div class="meta" style="margin-top:10px">进化中…（Holdout 在末代才评，用于验证不是过拟合题组）</div>`
      }
      <div class="list proj-actions" style="margin-top:12px">
        <button class="chip-btn" type="button" data-rf-action="abort">中止</button>
      </div>
    </div>`;
  }

  function championPanel(v) {
    if (v.frozen) {
      return `<div>
        <div class="fb-insight">冠军基因组需真实运行产出，本演示不放示意分数。</div>
        <div class="meta" style="margin-top:10px">实跑完成后这一步会给出：冠军槽位（G1–G5 等位可指认）、相对裸基线的提升、Holdout 分数、门禁记录与 token 消耗。</div>
      </div>`;
    }
    const rep = rf.report;
    if (!rep) return `<div class="empty">冠军报告未就绪</div>`;
    const champ = rep.champion || {};
    const slots = champ.variant?.slots || {};
    return `<div>
      <div class="fb-insight fb-insight-win">冠军 · <strong>${esc(
        champ.variant?.title || champ.variant_id || "—"
      )}</strong> · composite ${esc(champ.composite ?? "—")}</div>
      <div class="meta" style="margin-top:8px">相对裸基线均分提升：${esc(
        rep.champion_minus_baseline_mean ?? "—"
      )} · Holdout 均分：${esc(rep.holdout?.mean ?? "—")}（n=${esc(rep.holdout?.n ?? "—")}）</div>
      <div class="fb-slot-box" style="margin-top:12px">
        <div class="fb-panel-kicker">冠军槽位</div>
        <div class="fb-slots">${Object.entries(slots)
          .map(
            ([k, val]) => `<div class="fb-slot"><span>${esc(k)}</span><code>${esc(val)}</code></div>`
          )
          .join("")}</div>
      </div>
      <div class="meta" style="margin-top:10px">停机原因：${esc(
        rep.stop_reason || "—"
      )} · token 合计 ${esc(rep.token_usage?.total_tokens ?? "—")}</div>
    </div>`;
  }

  function settingsPanel() {
    if (!rf.settingsOpen) return "";
    return `<div class="card fb-panel" style="margin-bottom:12px">
      <div class="fb-panel-kicker">设置 · Key 仅存 sessionStorage（与单基因工作台共用）</div>
      <label class="fb-field"><span>API Key</span>
        <input id="rf-api-key" type="password" autocomplete="off" value="${esc(
          rf.apiKey
        )}" placeholder="Coding Plan Key" />
      </label>
      <label class="fb-field"><span>模型 id</span>
        <input id="rf-model" type="text" value="${esc(rf.model)}" placeholder="k3" />
      </label>
      <label class="fb-field"><span>每维出题数</span>
        <input id="rf-per-dim" type="number" min="1" max="4" value="${esc(rf.perDim)}" />
      </label>
      <label class="fb-field"><span>最大代数</span>
        <input id="rf-max-gen" type="number" min="1" max="10" value="${esc(rf.maxGenerations)}" />
      </label>
      <div class="list proj-actions" style="margin-top:10px;gap:6px">
        <button class="chip-btn primary" type="button" data-rf-action="save-settings">保存</button>
        <button class="chip-btn" type="button" data-rf-action="close-settings">关闭</button>
      </div>
    </div>`;
  }

  function renderHome() {
    return `<div class="pad fb-page">
      ${settingsPanel()}
      <div class="card fb-hero">
        <div class="tags" style="margin-bottom:10px">
          <span class="tag blue">一个输入：角色名</span>
          <span class="tag green">自动出题 + 出裁判</span>
          <span class="tag orange">再搜基因</span>
        </div>
        <h2>角色工厂</h2>
        <div class="meta" style="margin-top:6px">填一个角色名，自动拆能力维度 → 出题组与裁判 → 搜 G1–G5 基因 → 用 Holdout 鉴定 → 导出角色成品基因组。</div>
        <label class="fb-field" style="margin-top:14px"><span>角色名</span>
          <input id="rf-role" type="text" value="${esc(
            rf.role
          )}" placeholder="例如：数据分析专家 / 合同审核专员 / 供应链计划员" />
        </label>
        <div class="list proj-actions" style="margin-top:12px;gap:6px;flex-wrap:wrap">
          <button class="chip-btn primary" type="button" data-rf-action="start-demo">看结构演示（不花 token）</button>
          <button class="chip-btn" type="button" data-rf-action="anchors">只查锚点题源</button>
          <button class="chip-btn" type="button" data-rf-action="start-live">真实构建题组与裁判</button>
          <button class="chip-btn" type="button" data-rf-action="open-settings">设置</button>
        </div>
        ${rf.error ? `<div class="fb-error" style="margin-top:12px">${esc(rf.error)}</div>` : ""}
        <div class="meta" style="margin-top:12px">结构演示冻结的是「角色→题组→裁判→基因库」的结构与内容；分数一律标未实跑，不放示意数字。真实构建与进化跑在 factory 容器里。</div>
      </div>
      <div class="card fb-panel" style="margin-top:12px">
        <div class="fb-panel-kicker">七步</div>
        ${STEPS.map(
          (s, i) =>
            `<div class="fb-slot"><span>${i + 1}. ${esc(s)}</span><code>${esc(
              STORIES[i].slice(0, 30)
            )}…</code></div>`
        ).join("")}
      </div>
    </div>`;
  }

  function renderRun() {
    const v = view();
    const focus = Math.min(7, Math.max(1, rf.focusStep));
    const build = rf.build;
    const head = `<div class="card fb-hero">
      <div class="fb-run-top">
        <button class="chip-btn" type="button" data-rf-action="back-home">← 退出</button>
        <div class="tags">
          <span class="tag blue">${esc(v.role || rf.role)}</span>
          ${v.roleId ? `<span class="tag">${esc(v.roleId)}</span>` : ""}
          ${
            rf.mode === "demo"
              ? `<span class="tag">结构演示</span>`
              : `<span class="tag green">真实构建</span>`
          }
          ${scoresBadge(v)}
        </div>
      </div>
      ${stepperHtml(focus)}
      <div class="fb-story" style="margin-top:10px">${esc(STORIES[focus - 1])}</div>
      ${
        build?.status === "running"
          ? `<div class="meta" style="margin-top:8px">进行中 · ${esc(
              build.phase || ""
            )} · 出题 ${esc(build.progress?.cases_done ?? 0)}/${esc(
              build.progress?.cases_planned ?? "?"
            )}</div>`
          : ""
      }
      ${rf.error ? `<div class="fb-error" style="margin-top:10px">${esc(rf.error)}</div>` : ""}
    </div>`;

    let body = "";
    if (focus === 1) {
      body = `<div class="card fb-panel">
        <div class="fb-panel-kicker">唯一人类输入</div>
        <div class="fb-oral">${esc(v.role || rf.role)}</div>
        <div class="meta" style="margin-top:10px">${esc(
          v.blueprint?.summary || "能力维度将在第 3 步生成"
        )}</div>
        ${
          (v.blueprint?.hard_constraints || []).length
            ? `<div class="fb-panel-kicker" style="margin-top:12px">硬约束</div>
               <ul class="fb-req">${(v.blueprint.hard_constraints || [])
                 .map((x) => `<li>${esc(x)}</li>`)
                 .join("")}</ul>`
            : ""
        }
      </div>`;
    } else if (focus === 2) {
      body = `<div class="card fb-panel">${anchorPanel(v)}</div>`;
    } else if (focus === 3) {
      body = `<div class="card fb-panel">${dimPanel(v)}</div>`;
    } else if (focus === 4) {
      body = `<div class="card fb-panel">${casePanel(v)}</div>`;
    } else if (focus === 5) {
      body = `<div class="card fb-panel">${bankPanel(v)}</div>`;
    } else if (focus === 6) {
      body = `<div class="card fb-panel">${evolvePanel(v)}</div>`;
    } else {
      body = `<div class="card fb-panel">${championPanel(v)}</div>`;
    }

    const logs = (build?.logs || []).slice(-8);
    const logBox = logs.length
      ? `<div class="card fb-panel" style="margin-top:12px">
          <div class="fb-panel-kicker">构建日志</div>
          <pre class="fb-pre">${esc(logs.join("\n"))}</pre>
        </div>`
      : "";

    return `<div class="pad fb-page">
      ${settingsPanel()}
      ${head}
      <div style="margin-top:12px">${body}</div>
      ${navBar(focus)}
      ${logBox}
    </div>`;
  }

  function render() {
    if (rf.view === "run") return renderRun();
    return renderHome();
  }

  // ---------------------------------------------------------------- events

  function handleClick(e) {
    const gotoEl = e.target.closest("[data-rf-goto]");
    if (gotoEl) {
      e.preventDefault();
      rf.focusStep = Math.min(7, Math.max(1, Number(gotoEl.getAttribute("data-rf-goto")) || 1));
      rf.error = null;
      requestRender();
      return true;
    }
    const el = e.target.closest("[data-rf-action]");
    if (!el) return false;
    e.preventDefault();
    const action = el.getAttribute("data-rf-action");
    switch (action) {
      case "start-demo":
        roleInputValue();
        startDemo();
        break;
      case "start-live":
        startLive();
        break;
      case "anchors":
        loadAnchorsOnly();
        break;
      case "start-evolve":
        startEvolve();
        break;
      case "abort":
        abortAll();
        break;
      case "back-home":
        reset();
        rf.view = "home";
        rf.mode = null;
        requestRender();
        break;
      case "open-settings":
        roleInputValue();
        rf.settingsOpen = true;
        requestRender();
        break;
      case "close-settings":
        rf.settingsOpen = false;
        requestRender();
        break;
      case "save-settings": {
        const key = document.getElementById("rf-api-key");
        const model = document.getElementById("rf-model");
        const perDim = document.getElementById("rf-per-dim");
        const maxGen = document.getElementById("rf-max-gen");
        if (key) rf.apiKey = String(key.value || "").trim();
        if (model) rf.model = String(model.value || "").trim() || "k3";
        if (perDim) rf.perDim = Math.max(1, Math.min(4, Number(perDim.value) || 2));
        if (maxGen) rf.maxGenerations = Math.max(1, Math.min(10, Number(maxGen.value) || 2));
        saveSettings();
        rf.settingsOpen = false;
        toast("已保存（Key 仅存 sessionStorage）");
        requestRender();
        break;
      }
      default:
        return false;
    }
    return true;
  }

  return { render, handleClick, state: rf };
})();

window.RoleFactory = RoleFactory;
