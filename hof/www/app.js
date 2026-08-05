/* YiAgent 名人堂工作台 —— vanilla JS，与 factory www 同风格（fetch + 直接 DOM 渲染） */

const $ = (sel) => document.querySelector(sel);

const state = {
  view: "leaderboard",
  lb: { items: [], expandedHash: null },
};

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.hidden = true), 2600);
}

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function setStatus(sel, msg, isError = false) {
  const el = $(sel);
  el.textContent = msg || "";
  el.classList.toggle("error", isError);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );
}

function shortHash(h) {
  return (h || "").slice(0, 8);
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("zh-CN", { hour12: false });
}

// ---------------- 视图切换 ----------------

$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  state.view = btn.dataset.view;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === btn));
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== `view-${state.view}`));
  if (state.view === "leaderboard") loadLeaderboard();
  if (state.view === "alleles") loadAlleles();
  if (state.view === "submissions") loadSubmissions();
  if (state.view === "overview") loadOverview();
});

// ---------------- 排行榜 ----------------

async function loadLeaderboard() {
  const params = new URLSearchParams();
  const dim = $("#f-dimension").value.trim();
  const model = $("#f-model").value.trim();
  const suite = $("#f-suite").value.trim();
  const minN = $("#f-min-n").value || "3";
  if (dim) params.set("dimension", dim);
  if (model) params.set("model", model);
  if (suite) params.set("suite", suite);
  params.set("min_n", minN);
  params.set("limit", "50");
  setStatus("#lb-status", "加载中…");
  try {
    const data = await api(`/api/hof/leaderboard?${params}`);
    state.lb.items = data.items || [];
    state.lb.expandedHash = null;
    renderLeaderboard();
    setStatus("#lb-status", `共 ${state.lb.items.length} 条上榜基因组（min_n=${data.min_n}）`);
  } catch (e) {
    setStatus("#lb-status", `加载失败：${e.message}`, true);
  }
}

function renderLeaderboard() {
  const body = $("#lb-body");
  body.innerHTML = "";
  state.lb.items.forEach((item, i) => {
    const tr = document.createElement("tr");
    if (item.gene_hash === state.lb.expandedHash) tr.classList.add("expanded");
    tr.innerHTML = `
      <td class="num">${i + 1}</td>
      <td class="shrunk">${item.shrunk.toFixed(2)}</td>
      <td class="num">${item.mean.toFixed(1)} ± ${item.sdv.toFixed(1)}</td>
      <td class="num">${item.n}</td>
      <td class="mono">${esc(item.model)}</td>
      <td>${(item.demand_tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("") || "—"}</td>
      <td class="mono">${esc(item.contributor_id)}</td>
      <td class="mono" title="${esc(item.gene_hash)}">${esc(shortHash(item.gene_hash))}</td>
      <td class="mono">${esc(fmtTime(item.last_seen))}</td>`;
    tr.addEventListener("click", () => toggleGenome(item.gene_hash));
    body.appendChild(tr);
  });
  if (!state.lb.items.length) {
    body.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--mist)">暂无上榜数据</td></tr>`;
  }
  $("#genome-detail").hidden = true;
}

async function toggleGenome(geneHash) {
  const panel = $("#genome-detail");
  if (state.lb.expandedHash === geneHash) {
    state.lb.expandedHash = null;
    renderLeaderboard();
    return;
  }
  state.lb.expandedHash = geneHash;
  renderLeaderboard();
  panel.hidden = false;
  panel.innerHTML = `<p class="hint">加载基因组 ${esc(shortHash(geneHash))}…</p>`;
  try {
    const g = await api(`/api/hof/genome/${encodeURIComponent(geneHash)}`);
    renderGenomeDetail(g);
  } catch (e) {
    panel.innerHTML = `<p class="status error">加载失败：${esc(e.message)}</p>`;
  }
}

function renderGenomeDetail(g) {
  const panel = $("#genome-detail");
  const slots = ["G1", "G2", "G3", "G4", "G5"].filter((s) => (g.slot_texts || {})[s]);
  const slotHtml = slots
    .map((slot) => {
      const st = g.slot_texts[slot] || {};
      const allele = st.allele || {};
      return `
        <div class="slot-block">
          <div class="slot-name">${esc(slot)} · <span class="mono">${esc(st.allele_id || "")}</span></div>
          <div class="allele-label">${esc(allele.label || "（无文本）")}</div>
          ${allele.text ? `<div class="allele-text">${esc(allele.text)}</div>` : ""}
        </div>`;
    })
    .join("");
  panel.innerHTML = `
    <h3>${esc(g.title || "未命名基因组")}</h3>
    <div class="meta mono">
      gene_hash: ${esc(g.gene_hash)} · variant: ${esc(g.variant_id || "—")} ·
      上报 ${g.n_submissions} 次 · 最近 ${esc(fmtTime(g.last_seen))}
    </div>
    ${slotHtml || '<p class="hint">该基因组没有可展示的槽位文本。</p>'}
    <div style="margin-top:0.9rem">
      <button class="btn-primary" id="dl-seed">下载 seed JSON</button>
      <span class="hint" style="display:inline;margin-left:0.7rem">
        下载后可作为 factory evolve/start 的 seed（含 bank + variant + slots/slot_texts）
      </span>
    </div>`;
  panel.hidden = false;
  $("#dl-seed").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(g, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `yiagent-hof-seed-${shortHash(g.gene_hash)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("seed JSON 已下载");
  });
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

$("#f-apply").addEventListener("click", loadLeaderboard);

// ---------------- 等位表现 ----------------

async function loadAlleles() {
  const slot = $("#a-slot").value;
  const params = new URLSearchParams({ limit: "50" });
  if (slot) params.set("slot", slot);
  setStatus("#al-status", "加载中…");
  try {
    const data = await api(`/api/hof/alleles?${params}`);
    renderAlleles(data.items || []);
    setStatus("#al-status", `共 ${(data.items || []).length} 条等位`);
  } catch (e) {
    setStatus("#al-status", `加载失败：${e.message}`, true);
  }
}

function renderAlleles(items) {
  const list = $("#al-list");
  if (!items.length) {
    list.innerHTML = `<p class="hint">暂无等位数据</p>`;
    return;
  }
  const max = Math.max(...items.map((i) => i.composite ?? 0), 1);
  list.innerHTML = items
    .map((i) => {
      const pct = i.composite != null ? Math.max((i.composite / max) * 100, 2) : 0;
      return `
      <div class="allele-row">
        <span class="mono" style="color:var(--copper-hot)">${esc(i.slot)}</span>
        <div>
          <div class="mono">${esc(i.allele_id)}</div>
          <div class="bar-track" style="margin-top:0.3rem"><div class="bar-fill" style="width:${pct}%"></div></div>
        </div>
        <span class="num">avg ${i.composite != null ? i.composite.toFixed(2) : "—"}</span>
        <span class="mono" style="color:var(--mist)">${i.n_genomes} 基因组 / ${i.appearances} 次</span>
      </div>`;
    })
    .join("");
}

$("#a-apply").addEventListener("click", loadAlleles);

// ---------------- 提交流水 ----------------

async function loadSubmissions() {
  setStatus("#sub-status", "加载中…");
  try {
    const data = await api("/api/hof/submissions?limit=50");
    const body = $("#sub-body");
    body.innerHTML = "";
    (data.items || []).forEach((s) => {
      const tr = document.createElement("tr");
      const ok = s.status === "accepted";
      tr.innerHTML = `
        <td class="mono">${esc(fmtTime(s.submitted_at))}</td>
        <td class="mono">${esc(s.contributor_id)}</td>
        <td class="mono" title="${esc(s.gene_hash)}">${esc(shortHash(s.gene_hash)) || "—"}</td>
        <td class="mono">${esc(s.model || "—")}</td>
        <td class="num">${s.composite != null ? Number(s.composite).toFixed(1) : "—"}</td>
        <td class="${ok ? "pill-ok" : "pill-bad"}">${ok ? "接收" : "拒绝"}</td>
        <td style="white-space:normal;max-width:22rem">${esc(s.reason || "")}</td>`;
      body.appendChild(tr);
    });
    if (!(data.items || []).length) {
      body.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--mist)">暂无提交</td></tr>`;
    }
    setStatus("#sub-status", `最近 ${(data.items || []).length} 条`);
  } catch (e) {
    setStatus("#sub-status", `加载失败：${e.message}`, true);
  }
}

$("#s-refresh").addEventListener("click", loadSubmissions);

// ---------------- 概览 ----------------

async function loadOverview() {
  const cards = $("#ov-cards");
  try {
    const s = await api("/api/hof/stats");
    const modelDist = Object.entries(s.models || {})
      .map(([m, c]) => `${m}: ${c}`)
      .join(" · ");
    cards.innerHTML = `
      <div class="stat-card"><div class="value">${s.submissions_total}</div><div class="label">总提交数</div>
        <div class="sub">接收 ${s.submissions_accepted} / 拒绝 ${s.submissions_rejected}</div></div>
      <div class="stat-card"><div class="value">${s.genomes}</div><div class="label">独立基因组</div></div>
      <div class="stat-card"><div class="value">${s.contributors}</div><div class="label">匿名贡献者</div></div>
      <div class="stat-card"><div class="value">${Object.keys(s.models || {}).length}</div><div class="label">覆盖模型</div>
        <div class="sub">${esc(modelDist || "—")}</div></div>`;
  } catch (e) {
    cards.innerHTML = `<p class="status error">加载失败：${esc(e.message)}</p>`;
  }
}

// ---------------- 启动 ----------------

loadLeaderboard();
