/** 榜单区 · 编程榜（GOAL-CODEBENCH-B-001） */
const CodeBenchBoard = (() => {
  const st = {
    base: "http://127.0.0.1:8791",
    health: null,
    goal: null,
    role: null,
    sample: null,
    report: null,
    compare: null,
    run: null,
    runId: "",
    err: "",
    busy: false,
    pollTimer: null,
    lastExec: null,
  };

  async function api(path, opts) {
    const r = await fetch(st.base + path, {
      ...opts,
      headers: { "Content-Type": "application/json", ...(opts && opts.headers) },
    });
    const t = await r.text();
    let j = null;
    try {
      j = t ? JSON.parse(t) : null;
    } catch {
      throw new Error("非 JSON：" + t.slice(0, 120));
    }
    if (!r.ok) throw new Error((j && (j.detail || j.error)) || t.slice(0, 200) || r.status);
    return j;
  }

  async function refresh() {
    st.busy = true;
    st.err = "";
    try {
      st.health = await api("/healthz");
      st.goal = await api("/api/goal");
      try {
        st.role = await api("/api/role");
      } catch {
        st.role = null;
      }
      try {
        st.sample = await api("/api/sample");
      } catch {
        st.sample = null;
      }
      try {
        const lr = await api("/api/report/latest");
        st.report = lr && lr.report ? lr.report : null;
      } catch {
        st.report = null;
      }
      try {
        const cr = await api("/api/report/compare");
        st.compare = cr && cr.compare ? cr.compare : null;
      } catch {
        st.compare = null;
      }
    } catch (e) {
      st.health = null;
      st.err = String(e.message || e);
    } finally {
      st.busy = false;
    }
  }

  async function probeGold() {
    st.busy = true;
    st.err = "";
    try {
      st.lastExec = await api("/api/exec", {
        method: "POST",
        body: JSON.stringify({
          language: "python",
          code: "def two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i\n    return []\n",
          tests: "assert two_sum([2,7,11,15],9)==[0,1]\nassert two_sum([3,2,4],6)==[1,2]\n",
        }),
      });
    } catch (e) {
      st.lastExec = null;
      st.err = String(e.message || e);
    } finally {
      st.busy = false;
    }
  }

  function stopPoll() {
    if (st.pollTimer) {
      clearInterval(st.pollTimer);
      st.pollTimer = null;
    }
  }

  async function pollRun() {
    if (!st.runId) return;
    try {
      st.run = await api("/api/run/" + encodeURIComponent(st.runId));
      if (st.run.status === "done" || st.run.status === "error") {
        stopPoll();
        const lr = await api("/api/report/latest");
        if (lr && lr.report) st.report = lr.report;
        const cr = await api("/api/report/compare");
        if (cr && cr.compare) st.compare = cr.compare;
      }
    } catch (e) {
      st.err = String(e.message || e);
    }
    if (typeof render === "function") render();
  }

  async function startRun(limit, roleId) {
    st.busy = true;
    st.err = "";
    stopPoll();
    try {
      const body = { rebuild_sample: false };
      if (limit != null) body.limit = limit;
      if (roleId) body.role_id = roleId;
      const r = await api("/api/run", { method: "POST", body: JSON.stringify(body) });
      st.runId = r.run_id;
      st.run = { status: "starting", run_id: st.runId, progress: { done: 0, total: limit || 50 } };
      st.pollTimer = setInterval(pollRun, 2500);
      await pollRun();
    } catch (e) {
      st.err = String(e.message || e);
    } finally {
      st.busy = false;
    }
  }

  async function startCompare(limit) {
    st.busy = true;
    st.err = "";
    stopPoll();
    try {
      const body = { rebuild_sample: true };
      if (limit != null) body.limit = limit;
      const r = await api("/api/run/compare", { method: "POST", body: JSON.stringify(body) });
      st.runId = r.run_id;
      st.run = {
        status: "starting",
        run_id: st.runId,
        mode: "compare",
        progress: { done: 0, total: (limit || 50) * 2 },
      };
      st.pollTimer = setInterval(pollRun, 2500);
      await pollRun();
    } catch (e) {
      st.err = String(e.message || e);
    } finally {
      st.busy = false;
    }
  }

  function pill(ok, label) {
    const c = ok ? "#30d158" : "#ff453a";
    return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:${c}22;color:${c};font-size:12px">${label}</span>`;
  }

  function byLine(by) {
    return ["easy", "medium", "hard"]
      .filter((d) => by && by[d])
      .map((d) => `${d} ${by[d].pass}/${by[d].total}`)
      .join(" · ");
  }

  function compareTable(cmp) {
    if (!cmp) {
      return `<div class="empty" style="padding:16px">暂无对照。点「基因组 vs 裸跑」重建抽样并双臂跑满。</div>`;
    }
    const g = cmp.genome || {};
    const b = cmp.bare || {};
    const meta = cmp.sample_meta || {};
    const rows = (cmp.per_problem || [])
      .map(
        (r, i) => `<tr>
        <td style="padding:4px 8px 4px 0">${i + 1}</td>
        <td style="padding:4px 8px">${r.difficulty || ""}</td>
        <td style="padding:4px 8px">${r.genome_passed ? "✅" : "❌"}</td>
        <td style="padding:4px 8px">${r.bare_passed ? "✅" : "❌"}</td>
        <td style="padding:4px 8px;opacity:.6">${r.n_tests ?? ""}</td>
        <td style="padding:4px 0;font-size:12px">${(r.question_title || r.question_id || "").slice(0, 42)}</td>
      </tr>`
      )
      .join("");
    return `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;font-size:14px">
        <div>
          <div style="opacity:.6;font-size:12px">基因组 · ${g.role_id || "coding_board_racer"}</div>
          <div><b>pass@1 = ${g.pass_at_1 ?? "—"}%</b> <span style="opacity:.7">（${g.n_pass ?? "—"}/${g.n_total ?? "—"}）</span></div>
          <div style="opacity:.7;font-size:12px;margin-top:4px">${byLine(g.by_difficulty)}</div>
        </div>
        <div>
          <div style="opacity:.6;font-size:12px">裸跑 · ${b.role_id || "coding_board_bare"}</div>
          <div><b>pass@1 = ${b.pass_at_1 ?? "—"}%</b> <span style="opacity:.7">（${b.n_pass ?? "—"}/${b.n_total ?? "—"}）</span></div>
          <div style="opacity:.7;font-size:12px;margin-top:4px">${byLine(b.by_difficulty)}</div>
        </div>
      </div>
      <div style="opacity:.65;font-size:12px;margin-bottom:10px">
        Δ(基因组−裸跑)=${cmp.delta_pass_at_1 ?? "—"} pp · tests=${meta.tests || "?"} · tag=${meta.sample_tag || "?"}
        · dates ${meta.contest_date_min || "?"} → ${meta.contest_date_max || "?"}
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="opacity:.55;text-align:left"><th>#</th><th>难度</th><th>基因组</th><th>裸跑</th><th>测例</th><th>题</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="6" style="padding:12px;opacity:.6">对照进行中或尚无逐题结果</td></tr>`}</tbody>
      </table>`;
  }

  function boardTable(report) {
    if (!report || !report.results) {
      return `<div class="empty" style="padding:16px">暂无单臂报告。</div>`;
    }
    const rows = (report.results || [])
      .map(
        (r, i) => `<tr>
        <td style="padding:4px 8px 4px 0">${i + 1}</td>
        <td style="padding:4px 8px">${r.difficulty || ""}</td>
        <td style="padding:4px 8px">${r.passed ? "✅" : "❌"}</td>
        <td style="padding:4px 8px;opacity:.6">${r.n_tests ?? ""}</td>
        <td style="padding:4px 0;font-size:12px">${(r.question_title || r.question_id || "").slice(0, 48)}</td>
      </tr>`
      )
      .join("");
    return `
      <div style="margin-bottom:10px;font-size:14px">
        <b>pass@1 = ${report.pass_at_1 ?? "—"}%</b>
        <span style="opacity:.7">（${report.n_pass ?? "—"}/${report.n_total ?? "—"}）</span>
        <div style="opacity:.7;margin-top:4px;font-size:12px">${byLine(report.by_difficulty)}</div>
        <div style="opacity:.55;font-size:12px;margin-top:4px">run ${report.run_id || ""} · mode ${
          report.mode || ""
        } · role ${(report.role && report.role.role_id) || ""}</div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="opacity:.55;text-align:left"><th>#</th><th>难度</th><th>过</th><th>测例</th><th>题</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function render() {
    const h = st.health;
    const role = st.role;
    const prog = (st.run && st.run.progress) || {};
    const status = h
      ? pill(true, "codebench · " + (h.milestone || "M2"))
      : pill(false, st.err ? "服务未连通" : "未探测");
    const runStatus = st.run
      ? `<div style="margin-top:8px;font-size:13px">运行 <code>${st.runId}</code> · ${st.run.status} · ${
          prog.done || 0
        }/${prog.total || "?"}${st.run.mode === "compare" || (st.runId || "").includes("-cmp-") ? "（双臂）" : ""}</div>`
      : "";

    const genome = role && role.genome
      ? Object.entries(role.genome)
          .map(([k, v]) => `<div style="margin:4px 0"><b>${k}</b> · ${v}</div>`)
          .join("")
      : `<div class="empty">角色未加载</div>`;

    const meta = st.sample && st.sample.meta;
    const sampleLine =
      st.sample && st.sample.built
        ? `抽样 n=${st.sample.n} · tests=${(meta && meta.tests) || "?"} · tag=${
            (meta && meta.sample_tag) || "?"
          } · ${JSON.stringify(meta && meta.counts)}`
        : "抽样未构建（对照跑会重建 r2：全量分层 + public+private）";

    return `
    <div class="pad">
      <div class="card" style="margin-bottom:12px">
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between">
          <div>
            <div style="font-weight:600;font-size:16px">编程榜</div>
            <div style="opacity:.7;font-size:13px;margin-top:4px">Kimi × LCB 50 · public+private · 基因组 vs 裸跑</div>
          </div>
          <div>${status}</div>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn ghost" type="button" data-cb="refresh" ${st.busy ? "disabled" : ""}>探测/刷新</button>
          <button class="btn ghost" type="button" data-cb="gold" ${st.busy || !h ? "disabled" : ""}>金标 two_sum</button>
          <button class="btn ghost" type="button" data-cb="smoke" ${st.busy || !h ? "disabled" : ""}>冒烟 5（基因组）</button>
          <button class="btn ghost" type="button" data-cb="bare5" ${st.busy || !h ? "disabled" : ""}>冒烟 5（裸跑）</button>
          <button class="btn primary" type="button" data-cb="compare" ${st.busy || !h ? "disabled" : ""}>基因组 vs 裸跑 ×50</button>
          <span style="opacity:.55;font-size:12px;align-self:center">API ${st.base}</span>
        </div>
        ${runStatus}
        ${st.err ? `<div style="margin-top:10px;color:#ff453a;font-size:13px">${st.err}</div>` : ""}
        <div style="margin-top:8px;font-size:12px;opacity:.65">${sampleLine}</div>
      </div>

      <div class="card" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px">对照榜 · 基因组 vs 裸跑</div>
        ${compareTable(st.compare)}
      </div>

      <div class="card" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px">榜单角色 · ${
          (role && role.title) || "编程榜选手"
        }</div>
        <div style="font-size:13px;line-height:1.45">${genome}</div>
      </div>

      <div class="card" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px">最近单臂报告</div>
        ${boardTable(st.report)}
      </div>

      <div class="card">
        <div style="font-weight:600;margin-bottom:8px">M0 金标探针</div>
        ${
          st.lastExec
            ? `<pre class="mono" style="margin:0;white-space:pre-wrap;font-size:12px">${JSON.stringify(
                st.lastExec,
                null,
                2
              )}</pre>`
            : `<div class="empty" style="padding:12px">尚未跑金标</div>`
        }
      </div>
    </div>`;
  }

  function handleClick(e) {
    const t = e.target.closest("[data-cb]");
    if (!t) return false;
    const act = t.getAttribute("data-cb");
    const done = () => {
      if (typeof render === "function") render();
    };
    if (act === "refresh") {
      refresh().then(done).catch(done);
      return true;
    }
    if (act === "gold") {
      probeGold().then(done).catch(done);
      return true;
    }
    if (act === "smoke") {
      startRun(5, "coding_board_racer").then(done).catch(done);
      return true;
    }
    if (act === "bare5") {
      startRun(5, "coding_board_bare").then(done).catch(done);
      return true;
    }
    if (act === "compare") {
      startCompare(null).then(done).catch(done);
      return true;
    }
    return false;
  }

  return { render, handleClick, refresh, st };
})();
