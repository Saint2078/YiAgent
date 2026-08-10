/**
 * 高性能角色工厂（独立容器 rolefactory，默认 http://127.0.0.1:8790）
 *
 * 与「角色工厂」演示页的区别：这里全部是实跑——填角色名后由独立服务并行完成
 * 锚点 → 蓝图 → 题组+裁判 → 基因库 → 基线 → 多代进化 → holdout → 冠军，
 * 分数全部来自真实评测，没有冻结数据。
 */
const RFLive = (() => {
  const PHASES = [
    ["anchors", "锚点"],
    ["blueprint", "能力维度"],
    ["cases", "题组+裁判"],
    ["bank", "基因库"],
    ["baseline", "基线"],
    ["evolve", "多代进化"],
    ["holdout", "Holdout"],
    ["done", "冠军"],
  ];
  const KEY = "yiagent-rflive-v1";

  const st = {
    base: "http://127.0.0.1:8790",
    health: null,
    role: "数据分析专家",
    perDim: 2,
    generations: 3,
    variantsPerGen: 6,
    reps: 2,
    concurrency: 24,
    scoringMode: "objective",
    runId: null,
    run: null,
    report: null,
    runs: [],
    shadow: null,
    error: null,
    busy: false,
    timer: null,
    tab: "overview",
  };

  try {
    const o = JSON.parse(localStorage.getItem(KEY) || "{}");
    if (o.base) st.base = o.base;
    if (o.role) st.role = o.role;
    if (o.runId) st.runId = o.runId;
  } catch {
    /* ignore */
  }
  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify({ base: st.base, role: st.role, runId: st.runId }));
    } catch {
      /* ignore */
    }
  }

  const esc = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  const num = (v, d = "—") => (v === null || v === undefined || v === "" ? d : v);
  const rerender = () => {
    if (typeof window.render === "function") window.render();
  };
  const toast = (m) => {
    if (typeof window.toast === "function") window.toast(m);
  };

  async function api(path, opts) {
    const res = await fetch(st.base + path, {
      ...(opts || {}),
      headers: { "Content-Type": "application/json", ...((opts || {}).headers || {}) },
    });
    const txt = await res.text();
    let body = null;
    try {
      body = txt ? JSON.parse(txt) : null;
    } catch {
      body = { raw: txt };
    }
    if (!res.ok) throw new Error((body && (body.detail || body.error)) || `HTTP ${res.status}`);
    return body;
  }

  async function probe() {
    try {
      st.health = await api("/healthz");
      st.error = null;
    } catch (e) {
      st.health = null;
      st.error = `服务不可达：${e.message}（先 docker compose up -d 起 rolefactory）`;
    }
    rerender();
  }

  async function loadRuns() {
    try {
      const r = await api("/api/runs?limit=20");
      st.runs = r.items || [];
    } catch {
      st.runs = [];
    }
    rerender();
  }

  function readForm() {
    const g = (id, dflt) => {
      const el = document.getElementById(id);
      return el ? el.value : dflt;
    };
    st.base = String(g("rf-base", st.base) || st.base).trim().replace(/\/$/, "");
    st.role = String(g("rf-role", st.role) || st.role).trim();
    st.perDim = Number(g("rf-perdim", st.perDim)) || 2;
    st.generations = Number(g("rf-gens", st.generations)) || 3;
    st.variantsPerGen = Number(g("rf-pop", st.variantsPerGen)) || 6;
    st.reps = Number(g("rf-reps", st.reps)) || 1;
    st.concurrency = Number(g("rf-conc", st.concurrency)) || 24;
    st.scoringMode = String(g("rf-mode", st.scoringMode) || "objective");
    save();
  }

  async function start() {
    readForm();
    if (!st.role) {
      toast("先填角色名");
      return;
    }
    st.busy = true;
    st.error = null;
    st.report = null;
    rerender();
    try {
      const r = await api("/api/run", {
        method: "POST",
        body: JSON.stringify({
          role: st.role,
          per_dim: st.perDim,
          generations: st.generations,
          variants_per_gen: st.variantsPerGen,
          reps: st.reps,
          concurrency: st.concurrency,
          scoring_mode: st.scoringMode,
          judge_shadow: true,
        }),
      });
      st.runId = r.run_id;
      save();
      toast(`已启动 ${r.run_id}`);
      poll();
    } catch (e) {
      st.error = e.message;
    }
    st.busy = false;
    rerender();
  }

  async function abort() {
    if (!st.runId) return;
    try {
      await api(`/api/run/${st.runId}/abort`, { method: "POST" });
      toast("已请求中止");
    } catch (e) {
      toast(`中止失败：${e.message}`);
    }
  }

  function stopPoll() {
    if (st.timer) {
      clearTimeout(st.timer);
      st.timer = null;
    }
  }

  async function poll() {
    stopPoll();
    if (!st.runId) return;
    try {
      // full=true 才带题组与基因库；完成态 run 是从磁盘 state.json 读回来的，默认会被裁掉
      st.run = await api(`/api/run/${st.runId}?full=true`);
      st.error = null;
      if (st.run.status === "done" || st.run.status === "aborted") {
        try {
          st.report = await api(`/api/run/${st.runId}/report`);
        } catch {
          st.report = null;
        }
        try {
          st.shadow = await api(`/api/run/${st.runId}/shadow`);
        } catch {
          st.shadow = null;
        }
        loadRuns();
      }
    } catch (e) {
      st.error = e.message;
    }
    rerender();
    if (st.run && st.run.status === "running") st.timer = setTimeout(poll, 4000);
  }

  async function openRun(id) {
    st.runId = id;
    st.report = null;
    save();
    poll();
  }

  // ---------------------------------------------------------------- 渲染

  function pill(ok, text) {
    const c = ok ? "#30d158" : "#ff453a";
    return `<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:${c}">
      <span style="width:8px;height:8px;border-radius:50%;background:${c}"></span>${esc(text)}</span>`;
  }

  function stepper(run) {
    const idx = run ? PHASES.findIndex(([k]) => k === run.phase) : -1;
    return `<div style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0">
      ${PHASES.map(([k, label], i) => {
        const done = idx > i || (run && run.status === "done");
        const cur = idx === i && run && run.status === "running";
        const bg = done ? "rgba(48,209,88,.16)" : cur ? "rgba(94,200,255,.18)" : "rgba(255,255,255,.05)";
        const fg = done ? "#30d158" : cur ? "#5ec8ff" : "#8e8e93";
        return `<span style="padding:4px 10px;border-radius:999px;background:${bg};color:${fg};font-size:12px">
          ${i + 1}. ${esc(label)}${cur ? " …" : ""}</span>`;
      }).join("")}
    </div>`;
  }

  function metrics(run) {
    if (!run) return "";
    const llm = run.llm || {};
    const p = run.progress || {};
    const cells = [
      ["状态", `${run.status}${run.error ? ` · ${run.error}` : ""}`],
      ["用时", `${num(run.wall_seconds)}s`],
      ["评测", `${num(p.eval_done)}/${num(p.eval_total)}${p.eval_failed ? ` (失败${p.eval_failed})` : ""}`],
      ["API 调用", `${num(llm.api_calls)}（缓存命中 ${num(llm.cache_hits)}）`],
      ["吞吐", `${num(llm.calls_per_second)} 次/秒`],
      ["延时 p50/p90", `${num(llm.latency_p50)} / ${num(llm.latency_p90)} s`],
      ["tokens", num(llm.total_tokens)],
      ["并发", num(llm.concurrency)],
    ];
    return `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:8px 0">
      ${cells
        .map(
          ([k, v]) =>
            `<div style="background:rgba(255,255,255,.04);border-radius:10px;padding:8px 10px">
              <div style="font-size:11px;color:#8e8e93">${esc(k)}</div>
              <div style="font-size:13px;color:#e8e8ea;margin-top:2px">${esc(v)}</div></div>`
        )
        .join("")}
    </div>`;
  }

  function scoreBar(label, value, delta) {
    const v = value === null || value === undefined ? 0 : Number(value);
    const w = Math.max(0, Math.min(100, v));
    const d =
      delta === null || delta === undefined
        ? ""
        : `<span style="color:${delta >= 0 ? "#30d158" : "#ff453a"};font-size:12px">${
            delta >= 0 ? "+" : ""
          }${delta}</span>`;
    return `<div style="margin:6px 0">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#c7c7cc">
        <span>${esc(label)}</span><span>${num(value)} ${d}</span></div>
      <div style="height:6px;border-radius:3px;background:rgba(255,255,255,.08);margin-top:4px">
        <div style="height:6px;border-radius:3px;width:${w}%;background:linear-gradient(90deg,#5ec8ff,#30d158)"></div></div>
    </div>`;
  }

  function panelBlueprint(run) {
    const bp = run.blueprint || {};
    const dims = bp.dimensions || [];
    if (!dims.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">能力维度（${dims.length}）</div>
      <div style="font-size:12px;color:#8e8e93;margin-bottom:8px">${esc(bp.one_line || "")}</div>
      ${dims
        .map(
          (d) => `<div style="border-top:1px solid rgba(255,255,255,.06);padding:8px 0">
            <div style="display:flex;justify-content:space-between">
              <span style="color:#e8e8ea">${esc(d.name)}</span>
              <span style="color:#5ec8ff;font-size:12px">权重 ${num(d.weight)}</span></div>
            <div style="font-size:12px;color:#8e8e93;margin-top:3px">${esc(d.why || "")}</div>
            <div style="font-size:12px;color:#6e6e73;margin-top:3px">易错：${esc((d.failure_modes || []).join("；"))}</div>
          </div>`
        )
        .join("")}</div>`;
  }

  function panelAnchors(run) {
    const items = run.anchors || [];
    if (!items.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">benchmark 锚点（${items.length}）</div>
      <div style="font-size:12px;color:#8e8e93;margin-bottom:6px">只借题型与判分口径，不抄题面；原题实跑需数据文件与代码沙箱。</div>
      ${items
        .map(
          (a) => `<div style="border-top:1px solid rgba(255,255,255,.06);padding:6px 0;font-size:12px">
            <span style="color:#e8e8ea">${esc(a.id)}</span>
            <span style="color:#8e8e93"> · ${esc(a.task_shape || "")} · 判分 ${esc(a.scoring || "")}</span>
            <span style="color:${a.runnable_here ? "#30d158" : "#ff9f0a"}"> · ${a.runnable_here ? "可实跑" : "仅锚点"}</span>
          </div>`
        )
        .join("")}</div>`;
  }

  function panelScoring(run) {
    // 旧快照里没有 scoring 字段，回落到报告里的同名段
    const sc = run.scoring || (st.report && st.report.scoring) || {};
    if (!sc.mode) return "";
    const types = sc.check_types || {};
    const oa = sc.objective_spread_arms || {};
    const ja = sc.judge_shadow_spread_arms || {};
    const ov = sc.objective_spread_variants || {};
    return `<div class="card" style="margin-top:10px">
      <div style="font-weight:600;margin-bottom:6px">评分体系 · ${sc.mode === "objective" ? "客观（程序校验）" : "主观（LLM 裁判）"}</div>
      <div style="font-size:12px;color:#8e8e93">${esc(sc.how || "")}</div>
      ${
        Object.keys(types).length
          ? `<div style="font-size:12px;color:#c7c7cc;margin-top:8px">断言构成：${Object.entries(types)
              .map(([k, v]) => `${k} ×${v.count}（权重合 ${v.weight_sum}）`)
              .join("｜")}</div>`
          : ""
      }
      <div style="font-size:12px;color:#c7c7cc;margin-top:4px">出题自校通过：${num(sc.verified_cases)} 题</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-top:8px">
        <div style="background:rgba(255,255,255,.04);border-radius:10px;padding:8px 10px">
          <div style="font-size:11px;color:#8e8e93">客观分跨度（对照臂）</div>
          <div style="font-size:13px;color:#e8e8ea">${num(oa.min)} – ${num(oa.max)}（跨度 ${num(oa.spread)}）</div></div>
        <div style="background:rgba(255,255,255,.04);border-radius:10px;padding:8px 10px">
          <div style="font-size:11px;color:#8e8e93">客观分跨度（全部变体）</div>
          <div style="font-size:13px;color:#e8e8ea">${num(ov.min)} – ${num(ov.max)}（跨度 ${num(ov.spread)}）</div></div>
        <div style="background:rgba(255,255,255,.04);border-radius:10px;padding:8px 10px">
          <div style="font-size:11px;color:#8e8e93">影子裁判跨度（不参与选种）</div>
          <div style="font-size:13px;color:#e8e8ea">${num(ja.min)} – ${num(ja.max)}（跨度 ${num(ja.spread)}）</div></div>
      </div>
      <div style="font-size:11px;color:#6e6e73;margin-top:6px">跨度越大 = 该口径越能把好坏拉开。两者并列看，就能判断主观裁判是否被天花板压平。</div>
      ${shadowBlock()}
    </div>`;
  }

  function shadowBlock() {
    const sh = st.shadow;
    if (!sh || !sh.arms) return "";
    const rows = Object.entries(sh.arms);
    return `<div style="margin-top:10px;border-top:1px solid rgba(255,255,255,.08);padding-top:8px">
      <div style="font-size:12px;color:#e8e8ea;margin-bottom:4px">口径对照（同一批 ${num(
        sh.rows_judged
      )} 条回答补跑裁判）</div>
      ${rows
        .map(
          ([arm, v]) =>
            `<div style="font-size:12px;color:#8e8e93;display:flex;justify-content:space-between;gap:8px;padding:3px 0">
              <span>${esc(arm === "baseline" ? "基线" : "冠军")}（n=${num(v.n)}）</span>
              <span style="color:#c7c7cc">客观 ${num(v.objective_mean)}（${num(v.objective_min)}–${num(
              v.objective_max
            )}）｜裁判 ${num(v.judge_mean)}（${num(v.judge_min)}–${num(v.judge_max)}）</span>
            </div>`
        )
        .join("")}
      <div style="font-size:12px;color:#c7c7cc;margin-top:4px">
        臂间差：客观 <span style="color:#30d158">${num(sh.arm_gap_objective)}</span>
        ｜裁判 <span style="color:#ff9f0a">${num(sh.arm_gap_judge)}</span>
        ｜行级相关 ${num(sh.row_correlation)}｜裁判放水条数 ${num(sh.judge_high_objective_low)}
      </div>
    </div>`;
  }

  function panelCases(run) {
    const cases = run.cases || [];
    if (!cases.length) return `<div class="card" style="margin-top:10px"><div class="empty">题组还没生成完</div></div>`;
    const hold = new Set(run.holdout_ids || []);
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">题组 + 裁判（${cases.length}）</div>
      ${cases
        .map(
          (c) => `<div style="border-top:1px solid rgba(255,255,255,.06);padding:8px 0">
            <div style="display:flex;justify-content:space-between;gap:8px">
              <span style="color:#e8e8ea">${esc(c.title)}</span>
              <span style="font-size:11px;color:${hold.has(c.id) ? "#ff9f0a" : "#5ec8ff"}">${
                hold.has(c.id) ? "holdout" : "进化集"
              } · ${esc(c.level)}</span></div>
            <div style="font-size:12px;color:#8e8e93;margin-top:3px">${esc(c.dimension)}｜${esc(c.description || "")}</div>
            <div style="font-size:12px;color:#6e6e73;margin-top:3px">陷阱：${esc(c.trap || "—")}</div>
            ${
              (c.checks || []).length
                ? `<div style="font-size:12px;color:#6e6e73;margin-top:3px">客观断言：${esc(
                    (c.checks || []).map((k) => `${k.type}(${k.weight})`).join("、")
                  )}</div>
                   <div style="font-size:12px;color:#6e6e73;margin-top:3px">关键答案：${esc(
                     (c.ground_truth || {}).key_number || "—"
                   )}</div>`
                : `<div style="font-size:12px;color:#6e6e73;margin-top:3px">评分维度：${esc(
                    Object.entries(c.criteria || {})
                      .map(([k, v]) => `${k}(${v.weight})`)
                      .join("、")
                  )}</div>`
            }
          </div>`
        )
        .join("")}</div>`;
  }

  function panelBank(run) {
    const bank = run.bank_summary || {};
    const slots = Object.keys(bank);
    if (!slots.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">基因库（G1–G5 等位）</div>
      ${slots
        .map(
          (s) => `<div style="border-top:1px solid rgba(255,255,255,.06);padding:6px 0;font-size:12px">
            <span style="color:#5ec8ff">${esc(s)}</span>
            ${(bank[s] || [])
              .map(
                (a) =>
                  ` <span style="padding:2px 8px;border-radius:999px;margin-left:4px;background:${
                    a.strength === "weak" ? "rgba(255,159,10,.15)" : "rgba(48,209,88,.15)"
                  };color:${a.strength === "weak" ? "#ff9f0a" : "#30d158"}">${esc(a.label)}</span>`
              )
              .join("")}
          </div>`
        )
        .join("")}</div>`;
  }

  function panelGenerations(run) {
    const gens = run.generations || [];
    if (!gens.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">进化过程（${gens.length} 代）</div>
      ${gens
        .map(
          (g) => `<div style="border-top:1px solid rgba(255,255,255,.06);padding:8px 0">
            <div style="display:flex;justify-content:space-between;font-size:12px">
              <span style="color:#e8e8ea">第 ${g.gen} 代 · ${g.evaluated} 个变体 · ${g.seconds}s</span>
              <span style="color:#30d158">最优 composite ${num(g.best)}（均值 ${num(g.mean)}）</span></div>
            ${(g.variants || [])
              .map(
                (v) =>
                  `<div style="font-size:12px;color:#8e8e93;margin-top:4px;display:flex;justify-content:space-between;gap:8px">
                    <span>${esc(v.origin)}｜${esc(Object.values(v.labels || {}).join(" / "))}</span>
                    <span style="white-space:nowrap;color:#c7c7cc">加权 ${num(v.weighted)}｜σ ${num(v.std)}｜最低题 ${num(
                    v.min_case
                  )}</span></div>`
              )
              .join("")}
          </div>`
        )
        .join("")}</div>`;
  }

  function panelChampion(run) {
    const ch = run.champion || {};
    const base = run.baseline || {};
    const weak = run.all_weak || {};
    const hd = run.holdout || {};
    if (!ch.id) return "";
    const dTrain =
      ch.weighted != null && base.weighted != null ? Math.round((ch.weighted - base.weighted) * 100) / 100 : null;
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">冠军基因组</div>
      ${scoreBar("冠军（进化集加权）", ch.weighted, dTrain)}
      ${scoreBar("基线（无基因）", base.weighted, null)}
      ${scoreBar("全弱基因对照", weak.weighted, null)}
      ${hd.champion ? scoreBar("冠军（holdout · 未参与选种）", hd.champion.weighted, hd.delta_weighted) : ""}
      ${hd.baseline ? scoreBar("基线（holdout）", hd.baseline.weighted, null) : ""}
      <div style="font-size:12px;color:#8e8e93;margin-top:6px">
        σ ${num(ch.std)}｜题级跨度 ${num(ch.spread)}｜最低题 ${num(ch.min_case)}｜断言全通率 ${num(ch.check_pass_rate)}
        ${hd.generalization_gap != null ? `｜泛化差 ${hd.generalization_gap}` : ""}
      </div>
      ${
        ch.judge_shadow != null || base.judge_shadow != null
          ? `<div style="font-size:12px;color:#8e8e93;margin-top:4px">影子裁判（不参与选种）：冠军 ${num(
              ch.judge_shadow
            )}｜基线 ${num(base.judge_shadow)}</div>`
          : ""
      }
      <div style="font-size:12px;color:#c7c7cc;margin-top:8px">槽位：${esc(
        Object.entries(ch.labels || {})
          .map(([k, v]) => `${k}=${v}`)
          .join("｜")
      )}</div>
      <pre style="white-space:pre-wrap;background:rgba(255,255,255,.04);border-radius:8px;padding:10px;margin-top:8px;font-size:12px;color:#c7c7cc;max-height:340px;overflow:auto">${esc(
        ch.system || ""
      )}</pre>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn" type="button" data-rf="copy-genome">复制基因组</button>
        <a class="btn" href="${esc(st.base)}/api/run/${esc(run.run_id)}/report" target="_blank" rel="noreferrer">下载报告 JSON</a>
      </div>
    </div>`;
  }

  function panelDims(run) {
    const ch = run.champion || {};
    const base = run.baseline || {};
    const dims = (run.blueprint || {}).dimensions || [];
    if (!ch.by_dimension || !dims.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">维度对比（冠军 vs 基线）</div>
      ${dims
        .map((d) => {
          const c = (ch.by_dimension || {})[d.key];
          const b = (base.by_dimension || {})[d.key];
          const delta = c != null && b != null ? Math.round((c - b) * 100) / 100 : null;
          return `<div style="display:flex;justify-content:space-between;font-size:12px;padding:5px 0;border-top:1px solid rgba(255,255,255,.06)">
            <span style="color:#e8e8ea">${esc(d.name)}</span>
            <span style="color:#c7c7cc">冠军 ${num(c)}｜基线 ${num(b)}${
              delta != null
                ? ` <span style="color:${delta >= 0 ? "#30d158" : "#ff453a"}">${delta >= 0 ? "+" : ""}${delta}</span>`
                : ""
            }</span></div>`;
        })
        .join("")}</div>`;
  }

  function panelLogs(run) {
    const logs = run.logs || [];
    if (!logs.length) return "";
    return `<div class="card" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">运行日志</div>
      <pre style="white-space:pre-wrap;font-size:11px;color:#8e8e93;max-height:240px;overflow:auto;margin:0">${esc(
        logs.join("\n")
      )}</pre></div>`;
  }

  function render() {
    if (st.health === null && !st.error) probe();
    if (!st.runs.length) loadRuns();
    const h = st.health;
    const run = st.run;
    const tabs = [
      ["overview", "总览"],
      ["cases", "题组"],
      ["gens", "进化"],
      ["logs", "日志"],
    ];
    return `<div class="pad">
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
          <div>
            <div style="font-weight:600">高性能角色工厂 · 实跑</div>
            <div style="font-size:12px;color:#8e8e93">独立容器 rolefactory：并行出题、并行评测、多代进化、holdout 鉴定，分数全部实跑。</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            ${h ? pill(true, `${h.model} · 并发 ${h.concurrency} · Key ${h.key_present ? "已挂载" : "缺失"}`) : pill(false, "服务未连接")}
            <button class="btn" type="button" data-rf="probe">重连</button>
          </div>
        </div>
        ${st.error ? `<div style="margin-top:8px;color:#ff453a;font-size:12px">${esc(st.error)}</div>` : ""}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:12px">
          <label style="font-size:11px;color:#8e8e93">服务地址<input id="rf-base" value="${esc(st.base)}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">角色名<input id="rf-role" value="${esc(st.role)}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">每维题数<input id="rf-perdim" type="number" min="1" max="4" value="${st.perDim}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">代数<input id="rf-gens" type="number" min="1" max="6" value="${st.generations}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">每代变体<input id="rf-pop" type="number" min="2" max="12" value="${st.variantsPerGen}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">重复采样<input id="rf-reps" type="number" min="1" max="3" value="${st.reps}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">并发<input id="rf-conc" type="number" min="1" max="48" value="${st.concurrency}" style="width:100%"></label>
          <label style="font-size:11px;color:#8e8e93">判分口径<select id="rf-mode" style="width:100%">
            <option value="objective" ${st.scoringMode === "objective" ? "selected" : ""}>客观（程序校验）</option>
            <option value="judge" ${st.scoringMode === "judge" ? "selected" : ""}>主观（LLM 裁判）</option>
          </select></label>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
          <button class="btn primary" type="button" data-rf="start" ${st.busy ? "disabled" : ""}>${
            st.busy ? "启动中…" : "开始实跑"
          }</button>
          <button class="btn" type="button" data-rf="refresh">刷新</button>
          <button class="btn" type="button" data-rf="abort">中止</button>
          <button class="btn" type="button" data-rf="perf">并发压测</button>
        </div>
      </div>

      ${
        run
          ? `<div class="card" style="margin-top:10px">
              <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="font-weight:600">${esc(run.role)} <span style="font-size:12px;color:#8e8e93">${esc(run.run_id)}</span></div>
                <div style="display:flex;gap:6px">${tabs
                  .map(
                    ([k, label]) =>
                      `<button class="btn ${st.tab === k ? "primary" : ""}" type="button" data-rf="tab" data-tab="${k}">${label}</button>`
                  )
                  .join("")}</div>
              </div>
              ${stepper(run)}
              ${metrics(run)}
            </div>
            ${
              st.tab === "overview"
                ? panelChampion(run) + panelScoring(run) + panelDims(run) + panelBlueprint(run) + panelBank(run) + panelAnchors(run)
                : st.tab === "cases"
                  ? panelCases(run)
                  : st.tab === "gens"
                    ? panelGenerations(run)
                    : panelLogs(run)
            }`
          : `<div class="card" style="margin-top:10px"><div class="empty">还没有实跑记录。填角色名 → 开始实跑。</div></div>`
      }

      <div class="card" style="margin-top:10px">
        <div style="font-weight:600;margin-bottom:6px">历史 run（${st.runs.length}）</div>
        ${
          st.runs.length
            ? st.runs
                .map(
                  (r) => `<div style="display:flex;justify-content:space-between;gap:8px;padding:6px 0;border-top:1px solid rgba(255,255,255,.06);font-size:12px">
                    <button class="btn" type="button" data-rf="open" data-id="${esc(r.run_id)}">${esc(r.run_id)}</button>
                    <span style="color:#8e8e93">${esc(r.role || "")} · ${esc(r.status || "")} · ${num(r.wall_seconds)}s</span>
                    <span style="color:#c7c7cc">冠军 ${num(r.champion_score)}｜基线 ${num(r.baseline_score)}｜tokens ${num(
                      r.total_tokens
                    )}</span>
                  </div>`
                )
                .join("")
            : `<div class="empty">暂无</div>`
        }
      </div>
    </div>`;
  }

  async function perf() {
    readForm();
    toast("并发压测中…");
    try {
      const r = await api("/api/perf/probe", {
        method: "POST",
        body: JSON.stringify({ n: 12, concurrency: st.concurrency, max_tokens: 128 }),
      });
      toast(`吞吐 ${r.throughput_rps} 次/秒｜p50 ${r.latency_p50}s｜并行加速 ${r.speedup_vs_serial}×`);
    } catch (e) {
      toast(`压测失败：${e.message}`);
    }
  }

  function handleClick(e) {
    const btn = e.target.closest("[data-rf]");
    if (!btn) return false;
    const act = btn.getAttribute("data-rf");
    if (act === "start") start();
    else if (act === "probe") {
      readForm();
      probe();
      loadRuns();
    } else if (act === "refresh") poll();
    else if (act === "abort") abort();
    else if (act === "perf") perf();
    else if (act === "tab") {
      st.tab = btn.getAttribute("data-tab") || "overview";
      rerender();
    } else if (act === "open") openRun(btn.getAttribute("data-id"));
    else if (act === "copy-genome") {
      const txt = ((st.run || {}).champion || {}).system || "";
      if (navigator.clipboard && txt) navigator.clipboard.writeText(txt).then(() => toast("已复制基因组"));
    } else return false;
    return true;
  }

  return { render, handleClick, poll };
})();
