/**
 * US-004 · 可调用实体（类 Hermes）产品可交互原型
 * 加载基因组 → 会话一轮；mock 回复；经 console Docker 提供。
 */
const AgentRunBench = (() => {
  const LS = "yiagent-agent-run-bench-v1";
  const GENOMES = [
    {
      id: "var.knowledge_deep",
      title: "深搜详解知识助手",
      blurb: "G3 deep_cite · G5 edge_cases",
      genome_id: "gw.ka.v1.deep",
      from_selection: true,
      winner_mark: "balanced",
      slots: {
        G1: "g1.persona.analyst",
        G2: "g2.structured",
        G3: "g3.deep_cite",
        G4: "g4.multi_hop",
        G5: "g5.edge_cases",
      },
      trace_ref: "selection:gw.ka.v1.deep@ka-demo-001",
    },
    {
      id: "var.balanced_philosopher",
      title: "哲思解构者（冻结演示）",
      blurb: "批判思维金牌基因组",
      genome_id: "gw.philosopher.v1",
      slots: { G1: "g1.critical", G3: "g3.socratic", G5: "g5.edge_cases" },
      trace_ref: "freeze:philosopher-demo",
    },
    {
      id: "ai_architect",
      title: "AI 架构师",
      blurb: "DNA 图谱样例基因组",
      genome_id: "gw.ai_architect",
      slots: { G1: "g1.software_architect", G4: "g4.structured_tools", G5: "g5.spec_gate" },
      trace_ref: "dna-graph:ai_architect",
    },
  ];

  const st = {
    genomeId: null,
    loaded: false,
    messages: [],
    draft: "",
  };

  function load() {
    try {
      const o = JSON.parse(localStorage.getItem(LS) || "{}");
      if (o.genomeId) st.genomeId = o.genomeId;
      if (o.loaded) st.loaded = !!o.loaded;
      if (Array.isArray(o.messages)) st.messages = o.messages;
    } catch {
      /* ignore */
    }
  }
  function save() {
    try {
      localStorage.setItem(
        LS,
        JSON.stringify({
          genomeId: st.genomeId,
          loaded: st.loaded,
          messages: st.messages.slice(-40),
        })
      );
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

  function mockReply(text) {
    const g = GENOMES.find((x) => x.id === st.genomeId);
    const name = g?.title || st.genomeId;
    if (/检索|深搜|依据/.test(text)) {
      return `【${name}】多跳检索示意：跳1 定位实体 → 跳2 拉取依据。\n依据A · 依据B\n(mock · 未调用模型 API)`;
    }
    if (/总结|压缩/.test(text)) {
      return `【${name}】结构化摘要：要点1 / 要点2 / 边界。\n(mock)`;
    }
    return `【${name}】已收到：「${text.slice(0, 80)}${text.length > 80 ? "…" : ""}」\n本原型演示「基因组加载后可直接对话」；正式推理走 Docker 内服务。\n(mock)`;
  }

  function render() {
    const g = GENOMES.find((x) => x.id === st.genomeId);
    return `<div class="pad run-bench">
      <div class="tags" style="margin-bottom:12px">
        <span class="tag blue">US-004</span>
        <span class="tag">产品 · 可交互原型</span>
        <span class="tag">类 Hermes</span>
      </div>
      <div class="card" style="margin-bottom:12px">
        <h3 style="margin:0 0 8px;font-size:15px">1. 加载基因组</h3>
        <div class="list" style="flex-direction:column;align-items:stretch;gap:8px">
          ${GENOMES.map(
            (x) => `<button type="button" class="btn ${st.genomeId === x.id ? "primary" : "ghost"}" data-run-genome="${esc(x.id)}" style="justify-content:space-between;text-align:left">
              <span><strong>${esc(x.title)}</strong>${
              x.from_selection
                ? ` <span class="tag" style="margin-left:6px">选优 winner · ${esc(x.winner_mark || "balanced")}</span>`
                : ""
            }<br/><span class="meta">${esc(x.id)} · ${esc(x.blurb)}</span></span>
            </button>`
          ).join("")}
        </div>
        <div class="list proj-actions" style="margin-top:12px">
          <button class="btn primary" type="button" data-run-load ${st.genomeId ? "" : "disabled"}>加载并启动会话</button>
          <button class="btn ghost" type="button" data-run-unload ${st.loaded ? "" : "disabled"}>卸载</button>
        </div>
        <p class="meta" style="margin-top:10px">${
          st.loaded
            ? `ready · entity <code>${esc(st.genomeId)}</code> · genome <code>${esc(
                g?.genome_id || ""
              )}</code> · session s_proto_004`
            : "未加载：选择基因组后点「加载并启动会话」"
        }</p>
        ${
          st.loaded && g
            ? `<p class="meta">溯源 <code>${esc(g.trace_ref)}</code> · 槽位 ${esc(
                Object.entries(g.slots || {})
                  .map(([k, v]) => `${k}=${v}`)
                  .join(" · ")
              )}</p>
            <button class="btn ghost" type="button" data-run-export style="margin-top:8px">复制 E1 实体契约</button>`
            : ""
        }
      </div>
      <div class="card">
        <h3 style="margin:0 0 8px;font-size:15px">2. 直接调用（会话）</h3>
        <div class="run-log" id="run-log" style="min-height:160px;max-height:320px;overflow:auto;background:rgba(0,0,0,.25);border-radius:10px;padding:12px;font-family:ui-monospace,Consolas,monospace;font-size:13px;line-height:1.45">
          ${
            st.messages.length
              ? st.messages
                  .map(
                    (m) =>
                      `<div style="margin:0 0 10px"><span class="meta">${m.role === "user" ? "you>" : "agent>"}</span> ${esc(m.text).replace(/\n/g, "<br/>")}</div>`
                  )
                  .join("")
              : `<div class="meta">加载基因组后，在下方输入并发送。</div>`
          }
        </div>
        <form id="run-form" style="margin-top:12px;display:flex;gap:8px" ${st.loaded ? "" : "aria-disabled=true"}>
          <input class="input" id="run-input" type="text" placeholder="${st.loaded ? "对 Agent 说话…" : "请先加载基因组"}" ${st.loaded ? "" : "disabled"} style="flex:1" />
          <button class="btn primary" type="submit" ${st.loaded ? "" : "disabled"}>发送</button>
          <button class="btn ghost" type="button" data-run-demo ${st.loaded ? "" : "disabled"}>演示一轮</button>
        </form>
      </div>
    </div>`;
  }

  function handleClick(e) {
    const g = e.target.closest("[data-run-genome]");
    if (g) {
      st.genomeId = g.getAttribute("data-run-genome");
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-run-load]")) {
      if (!st.genomeId) return true;
      st.loaded = true;
      st.messages = [
        {
          role: "agent",
          text: `loaded genome: ${st.genomeId}\nready · session s_proto_004`,
        },
      ];
      save();
      if (typeof window.toast === "function") window.toast("基因组已加载");
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-run-unload]")) {
      st.loaded = false;
      st.messages = [];
      save();
      if (typeof window.render === "function") window.render();
      return true;
    }
    if (e.target.closest("[data-run-export]")) {
      const g = GENOMES.find((x) => x.id === st.genomeId);
      if (!g) return true;
      const lastUser = [...st.messages].reverse().find((m) => m.role === "user");
      const lastAgent = [...st.messages].reverse().find((m) => m.role === "agent");
      const payload = {
        entity_id: `agent.${g.id}`,
        genome_id: g.genome_id,
        slots: g.slots,
        invoke: {
          input: lastUser?.text || "（尚未发送）",
          output_preview: (lastAgent?.text || "").slice(0, 200),
          trace_ref: g.trace_ref,
        },
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(JSON.stringify(payload, null, 2)).then(
          () => typeof window.toast === "function" && window.toast("已复制 US-004 契约"),
          () => typeof window.toast === "function" && window.toast("复制失败")
        );
      }
      return true;
    }
    if (e.target.closest("[data-run-demo]")) {
      if (!st.loaded) return true;
      const text = "请做一次深搜并给出依据";
      st.messages.push({ role: "user", text });
      const out = mockReply(text);
      st.messages.push({ role: "agent", text: out });
      save();
      if (typeof window.toast === "function") window.toast("已演示一轮调用");
      if (typeof window.render === "function") window.render();
      return true;
    }
    return false;
  }

  function bindForm() {
    const form = document.getElementById("run-form");
    if (!form || form.dataset.bound === "1") return;
    form.dataset.bound = "1";
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!st.loaded) return;
      const input = document.getElementById("run-input");
      const text = (input?.value || "").trim();
      if (!text) return;
      st.messages.push({ role: "user", text });
      st.messages.push({ role: "agent", text: mockReply(text) });
      if (input) input.value = "";
      save();
      if (typeof window.render === "function") window.render();
    });
  }

  const _render = render;
  return {
    render() {
      const html = _render();
      queueMicrotask(bindForm);
      return html;
    },
    handleClick,
  };
})();
