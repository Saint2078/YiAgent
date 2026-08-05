/**
 * 知识库管理：SQLite 正文 + Markdown 可视化
 */
const KbManage = (() => {
  const CAT_LABEL = {
    taxonomy: "分类",
    scoring: "评分",
    general: "通用",
  };

  const st = {
    docs: [],
    selectedId: null,
    doc: null,
    q: "",
    category: "",
    loading: false,
    editing: false,
    draftTitle: "",
    draftBody: "",
    draftCategory: "general",
    error: null,
    notice: null,
  };

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
    const res = await fetch(`/api/kb${path}`, {
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
      const detail = data?.error || data?.detail || text || `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  /** 轻量 Markdown → HTML（标题/列表/表格/代码/强调） */
  function mdToHtml(src) {
    const lines = String(src || "").replace(/\r\n/g, "\n").split("\n");
    const out = [];
    let i = 0;
    let inCode = false;
    let codeBuf = [];
    let listType = null;

    function flushList() {
      if (!listType) return;
      out.push(listType === "ol" ? "</ol>" : "</ul>");
      listType = null;
    }

    function inline(s) {
      let t = esc(s);
      t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
      t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      t = t.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      return t;
    }

    while (i < lines.length) {
      const line = lines[i];
      if (line.trim().startsWith("```")) {
        if (inCode) {
          out.push(`<pre class="kb-md-pre"><code>${esc(codeBuf.join("\n"))}</code></pre>`);
          codeBuf = [];
          inCode = false;
        } else {
          flushList();
          inCode = true;
        }
        i += 1;
        continue;
      }
      if (inCode) {
        codeBuf.push(line);
        i += 1;
        continue;
      }

      // table block
      if (
        line.includes("|") &&
        i + 1 < lines.length &&
        /^\s*\|?\s*[-:]+/.test(lines[i + 1])
      ) {
        flushList();
        const rows = [];
        while (i < lines.length && lines[i].includes("|")) {
          if (/^\s*\|?\s*[-:| ]+\|?\s*$/.test(lines[i])) {
            i += 1;
            continue;
          }
          const cells = lines[i]
            .trim()
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map((c) => c.trim());
          rows.push(cells);
          i += 1;
        }
        if (rows.length) {
          const head = rows[0];
          const body = rows.slice(1);
          out.push("<table class='kb-md-table'><thead><tr>");
          head.forEach((c) => out.push(`<th>${inline(c)}</th>`));
          out.push("</tr></thead><tbody>");
          body.forEach((row) => {
            out.push("<tr>");
            row.forEach((c) => out.push(`<td>${inline(c)}</td>`));
            out.push("</tr>");
          });
          out.push("</tbody></table>");
        }
        continue;
      }

      const h = /^(#{1,4})\s+(.+)$/.exec(line);
      if (h) {
        flushList();
        const n = h[1].length;
        out.push(`<h${n} class="kb-md-h">${inline(h[2])}</h${n}>`);
        i += 1;
        continue;
      }

      const ul = /^[-*]\s+(.+)$/.exec(line);
      if (ul) {
        if (listType !== "ul") {
          flushList();
          out.push("<ul class='kb-md-list'>");
          listType = "ul";
        }
        out.push(`<li>${inline(ul[1])}</li>`);
        i += 1;
        continue;
      }

      const ol = /^(\d+)\.\s+(.+)$/.exec(line);
      if (ol) {
        if (listType !== "ol") {
          flushList();
          out.push("<ol class='kb-md-list'>");
          listType = "ol";
        }
        out.push(`<li>${inline(ol[2])}</li>`);
        i += 1;
        continue;
      }

      if (!line.trim()) {
        flushList();
        i += 1;
        continue;
      }

      flushList();
      out.push(`<p class="kb-md-p">${inline(line)}</p>`);
      i += 1;
    }
    flushList();
    if (inCode) {
      out.push(`<pre class="kb-md-pre"><code>${esc(codeBuf.join("\n"))}</code></pre>`);
    }
    return out.join("\n");
  }

  async function loadList() {
    st.loading = true;
    st.error = null;
    requestRender();
    try {
      const qs = new URLSearchParams();
      if (st.category) qs.set("category", st.category);
      if (st.q.trim()) qs.set("q", st.q.trim());
      const data = await api(`/docs?${qs.toString()}`);
      st.docs = data.docs || [];
      if (st.selectedId && !st.docs.some((d) => d.id === st.selectedId)) {
        st.selectedId = null;
        st.doc = null;
      }
      if (!st.selectedId && st.docs.length) {
        await selectDoc(st.docs[0].id);
        return;
      }
      if (st.selectedId) await selectDoc(st.selectedId);
    } catch (e) {
      st.error = String(e.message || e);
    } finally {
      st.loading = false;
      requestRender();
    }
  }

  async function selectDoc(id) {
    st.selectedId = id;
    st.editing = false;
    st.error = null;
    try {
      const data = await api(`/docs/${encodeURIComponent(id)}`);
      st.doc = data.doc;
      st.draftTitle = data.doc.title || "";
      st.draftBody = data.doc.body_md || "";
      st.draftCategory = data.doc.category || "general";
    } catch (e) {
      st.error = String(e.message || e);
      st.doc = null;
    }
    requestRender();
  }

  async function importMd() {
    st.loading = true;
    st.error = null;
    requestRender();
    try {
      const r = await api("/import", { method: "POST", body: "{}" });
      st.notice = `已导入 ${r.imported || 0} 篇`;
      toast(st.notice);
      await loadList();
    } catch (e) {
      st.error = String(e.message || e);
      st.loading = false;
      requestRender();
    }
  }

  async function createDoc() {
    st.loading = true;
    try {
      const data = await api("/docs", {
        method: "POST",
        body: JSON.stringify({
          title: "新知识条目",
          category: st.category || "general",
          body_md: "# 新知识条目\n\n在此编写 Markdown。\n",
          visibility: "human_only",
        }),
      });
      toast("已新建");
      st.editing = true;
      await loadList();
      if (data.doc?.id) await selectDoc(data.doc.id);
      st.editing = true;
      requestRender();
    } catch (e) {
      st.error = String(e.message || e);
      st.loading = false;
      requestRender();
    }
  }

  async function saveDoc() {
    if (!st.selectedId) return;
    st.loading = true;
    try {
      const data = await api(`/docs/${encodeURIComponent(st.selectedId)}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: st.draftTitle,
          body_md: st.draftBody,
          category: st.draftCategory,
        }),
      });
      st.doc = data.doc;
      st.editing = false;
      toast("已保存到 SQLite");
      await loadList();
    } catch (e) {
      st.error = String(e.message || e);
      st.loading = false;
      requestRender();
    }
  }

  async function deleteDoc() {
    if (!st.selectedId) return;
    if (!confirm("确认删除该知识条目？")) return;
    st.loading = true;
    try {
      await api(`/docs/${encodeURIComponent(st.selectedId)}`, { method: "DELETE" });
      st.selectedId = null;
      st.doc = null;
      toast("已删除");
      await loadList();
    } catch (e) {
      st.error = String(e.message || e);
      st.loading = false;
      requestRender();
    }
  }

  function ensureLoaded() {
    if (!st.docs.length && !st.loading && !st.error) {
      loadList();
    }
  }

  function render() {
    ensureLoaded();
    const doc = st.doc;
    return `<div class="kb-manage">
      <div class="card fb-hero">
        <div class="fb-run-top">
          <div class="tags">
            <span class="tag orange">知识库管理</span>
            <span class="tag">SQLite</span>
            ${st.loading ? `<span class="tag">加载中…</span>` : ""}
          </div>
          <div class="list proj-actions">
            <button class="chip-btn" type="button" data-km-action="import" ${st.loading ? "disabled" : ""}>从 MD 导入</button>
            <button class="btn primary" type="button" data-km-action="create" ${st.loading ? "disabled" : ""}>新建</button>
          </div>
        </div>
        <h2>文档库</h2>
        <div class="meta">Markdown 入库后可视化阅读 / 编辑；正文存 opc.sqlite · kb_doc</div>
        ${st.error ? `<div class="fb-error">${esc(st.error)}</div>` : ""}
        ${st.notice ? `<div class="meta" style="margin-top:8px">${esc(st.notice)}</div>` : ""}
      </div>

      <div class="kb-manage-toolbar card" style="margin-top:14px">
        <input class="kb-manage-search" id="km-q" type="search" placeholder="搜索标题 / 正文" value="${esc(st.q)}" />
        <select id="km-cat" class="kb-manage-select">
          <option value="" ${!st.category ? "selected" : ""}>全部分类</option>
          <option value="taxonomy" ${st.category === "taxonomy" ? "selected" : ""}>分类</option>
          <option value="scoring" ${st.category === "scoring" ? "selected" : ""}>评分</option>
          <option value="general" ${st.category === "general" ? "selected" : ""}>通用</option>
        </select>
        <button class="chip-btn" type="button" data-km-action="search">筛选</button>
      </div>

      <div class="kb-manage-grid">
        <aside class="card kb-manage-list" aria-label="文档列表">
          ${
            st.docs.length
              ? st.docs
                  .map(
                    (d) => `<button type="button" class="kb-manage-item ${
                      d.id === st.selectedId ? "active" : ""
                    }" data-km-open="${esc(d.id)}">
                      <div class="row-title">${esc(d.title)}</div>
                      <div class="row-desc">${esc(d.excerpt || d.source_path || "")}</div>
                      <div class="tags" style="margin-top:6px">
                        <span class="tag">${esc(CAT_LABEL[d.category] || d.category)}</span>
                        ${d.source_path ? `<span class="tag blue">md</span>` : ""}
                      </div>
                    </button>`
                  )
                  .join("")
              : `<div class="empty" style="padding:20px">暂无文档 · 点「从 MD 导入」</div>`
          }
        </aside>

        <section class="card kb-manage-detail">
          ${
            !doc
              ? `<div class="empty" style="padding:24px">选择左侧文档查看可视化内容</div>`
              : st.editing
                ? `<div class="kb-manage-edit">
                    <label class="fb-field"><span>标题</span>
                      <input id="km-title" type="text" value="${esc(st.draftTitle)}" />
                    </label>
                    <label class="fb-field"><span>分类</span>
                      <select id="km-draft-cat">
                        <option value="taxonomy" ${st.draftCategory === "taxonomy" ? "selected" : ""}>分类</option>
                        <option value="scoring" ${st.draftCategory === "scoring" ? "selected" : ""}>评分</option>
                        <option value="general" ${st.draftCategory === "general" ? "selected" : ""}>通用</option>
                      </select>
                    </label>
                    <label class="fb-field"><span>Markdown 正文</span>
                      <textarea id="km-body" class="fb-textarea" rows="18">${esc(st.draftBody)}</textarea>
                    </label>
                    <div class="list proj-actions" style="margin-top:12px">
                      <button class="btn primary" type="button" data-km-action="save">保存到 SQLite</button>
                      <button class="btn ghost" type="button" data-km-action="cancel-edit">取消</button>
                    </div>
                  </div>`
                : `<div class="kb-manage-view">
                    <div class="fb-run-top">
                      <div class="tags">
                        <span class="tag">${esc(CAT_LABEL[doc.category] || doc.category)}</span>
                        <span class="tag">${esc(doc.visibility)}</span>
                        ${doc.source_path ? `<span class="tag blue mono">${esc(doc.source_path)}</span>` : ""}
                      </div>
                      <div class="list proj-actions">
                        <button class="chip-btn" type="button" data-km-action="edit">编辑</button>
                        <button class="chip-btn" type="button" data-km-action="delete">删除</button>
                      </div>
                    </div>
                    <div class="kb-md">${mdToHtml(doc.body_md || "")}</div>
                  </div>`
          }
        </section>
      </div>
    </div>`;
  }

  function readFiltersFromDom() {
    const q = document.getElementById("km-q");
    const cat = document.getElementById("km-cat");
    if (q) st.q = q.value;
    if (cat) st.category = cat.value;
  }

  function readDraftFromDom() {
    const t = document.getElementById("km-title");
    const b = document.getElementById("km-body");
    const c = document.getElementById("km-draft-cat");
    if (t) st.draftTitle = t.value;
    if (b) st.draftBody = b.value;
    if (c) st.draftCategory = c.value;
  }

  function handleClick(e) {
    const open = e.target.closest("[data-km-open]");
    if (open) {
      e.preventDefault();
      selectDoc(open.getAttribute("data-km-open"));
      return true;
    }
    const act = e.target.closest("[data-km-action]");
    if (!act) return false;
    e.preventDefault();
    switch (act.getAttribute("data-km-action")) {
      case "import":
        importMd();
        break;
      case "create":
        createDoc();
        break;
      case "search":
        readFiltersFromDom();
        loadList();
        break;
      case "edit":
        st.editing = true;
        requestRender();
        break;
      case "cancel-edit":
        st.editing = false;
        if (st.doc) {
          st.draftTitle = st.doc.title || "";
          st.draftBody = st.doc.body_md || "";
          st.draftCategory = st.doc.category || "general";
        }
        requestRender();
        break;
      case "save":
        readDraftFromDom();
        saveDoc();
        break;
      case "delete":
        deleteDoc();
        break;
      default:
        return false;
    }
    return true;
  }

  return {
    render,
    handleClick,
    loadList,
    get state() {
      return st;
    },
  };
})();
