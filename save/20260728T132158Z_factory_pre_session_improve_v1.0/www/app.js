const WORKER_OPTIONS = [2, 4, 6, 8];
const BASELINE_REP_OPTIONS = [3, 5, 8];
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
  provider: sessionStorage.getItem("yiagent_provider") || "",
  apiKeys: loadApiKeys(),
  apiKey: "", // active provider key (synced from apiKeys)
  model: sessionStorage.getItem("yiagent_model") || "kimi-k2.5",
  workers: Number(sessionStorage.getItem("yiagent_workers")) || 4,
  championMark: sessionStorage.getItem("yiagent_champion_mark") || "balanced",
  oral: "",
  sessionId: null,
  snap: null,
  targetText: "",
  criteriaText: "",
  passMean: 70,
  qualifyTarget: 3,
  baselineReps: 5,
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
  settingsOpen: false,
  showLogs: false,
  focusStep: 1,
  caseSource: "library", // library | oral
  caseMeta: null,
  caseItems: [],
  caseTotal: 0,
  caseSuite: "xsct-l",
  caseDimension: "",
  caseQuery: "",
  caseLevel: "basic",
  caseSelectedId: "",
  caseLoading: false,
  baselineCache: null,
  copyEditOpen: false,
  copyOverrides: { zh: {}, en: {} },
};

function loadApiKeys() {
  try {
    const raw = sessionStorage.getItem("yiagent_api_keys");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") return parsed;
    }
  } catch {
    /* ignore */
  }
  const legacy = sessionStorage.getItem("yiagent_api_key") || "";
  return legacy ? { _legacy: legacy } : {};
}

const COPY_STORAGE_KEY = "yiagent_factory_copy_v1";

function loadCopyOverrides() {
  try {
    const raw = localStorage.getItem(COPY_STORAGE_KEY);
    if (!raw) return { zh: {}, en: {} };
    const parsed = JSON.parse(raw);
    return {
      zh: parsed.zh && typeof parsed.zh === "object" ? parsed.zh : {},
      en: parsed.en && typeof parsed.en === "object" ? parsed.en : {},
    };
  } catch {
    return { zh: {}, en: {} };
  }
}

state.copyOverrides = loadCopyOverrides();

function persistCopyOverrides() {
  localStorage.setItem(COPY_STORAGE_KEY, JSON.stringify(state.copyOverrides));
}

function effectiveBundle(lang) {
  const base = i18n[lang] || {};
  const ov = state.copyOverrides[lang] || {};
  const merged = { ...base, ...ov };
  if (Array.isArray(ov.steps)) merged.steps = ov.steps.slice();
  else merged.steps = (base.steps || []).slice();
  if (Array.isArray(ov.oralExamples)) merged.oralExamples = ov.oralExamples.slice();
  else {
    merged.oralExamples = (lang === "zh" ? ORAL_EXAMPLES_ZH : ORAL_EXAMPLES_EN).slice();
  }
  return merged;
}

function t() {
  return effectiveBundle(state.lang);
}

function oralExamplesList() {
  return t().oralExamples || (state.lang === "zh" ? ORAL_EXAMPLES_ZH : ORAL_EXAMPLES_EN);
}

function selectedModelMeta() {
  return (state.models || []).find((m) => m.id === state.model) || null;
}

function modelCatalog() {
  return state.models && state.models.length
    ? state.models
    : [
        {
          id: "kimi-k2.5",
          label: "Kimi K2.5",
          provider: "kimi",
          provider_label: "Kimi 开放平台",
          key_hint: "Kimi 开放平台 Key (platform.kimi.com)",
        },
        {
          id: "kimi-k2.6",
          label: "Kimi K2.6",
          provider: "kimi",
          provider_label: "Kimi 开放平台",
          key_hint: "Kimi 开放平台 Key (platform.kimi.com)",
        },
        {
          id: "plan/k3",
          label: "Kimi 3",
          provider: "kimi-plan",
          provider_label: "Kimi Plan",
          key_hint: "Kimi Plan Key",
        },
      ];
}

function providersList() {
  const map = new Map();
  for (const m of modelCatalog()) {
    let id = m.provider || "other";
    // Migrate legacy provider ids in saved sessions
    if (id === "moonshot") id = "kimi";
    if (id === "kimi-coding") id = "kimi-plan";
    if (!map.has(id)) {
      map.set(id, {
        id,
        label: m.provider_label || id,
        key_hint: m.key_hint || "API Key",
      });
    }
  }
  return [...map.values()];
}

function ensureProviderModel() {
  const catalog = modelCatalog();
  // Migrate legacy saved provider/model
  if (state.provider === "moonshot") state.provider = "kimi";
  if (state.provider === "kimi-coding") state.provider = "kimi-plan";
  if (state.apiKeys?.moonshot && !state.apiKeys.kimi) {
    state.apiKeys.kimi = state.apiKeys.moonshot;
  }
  if (state.apiKeys?.["kimi-coding"] && !state.apiKeys["kimi-plan"]) {
    state.apiKeys["kimi-plan"] = state.apiKeys["kimi-coding"];
  }
  let meta = catalog.find((m) => m.id === state.model);
  if (!state.provider) {
    state.provider = meta?.provider || catalog[0]?.provider || "kimi";
  }
  if (state.provider === "moonshot") state.provider = "kimi";
  if (state.provider === "kimi-coding") state.provider = "kimi-plan";
  const inProvider = catalog.filter((m) => {
    const p = m.provider === "moonshot" ? "kimi" : m.provider === "kimi-coding" ? "kimi-plan" : m.provider;
    return p === state.provider;
  });
  if (!meta || (meta.provider !== state.provider && !(meta.provider === "moonshot" && state.provider === "kimi") && !(meta.provider === "kimi-coding" && state.provider === "kimi-plan"))) {
    state.model = inProvider[0]?.id || catalog[0]?.id || "kimi-k2.5";
    meta = catalog.find((m) => m.id === state.model);
  }
  if (meta?.provider) {
    let p = meta.provider;
    if (p === "moonshot") p = "kimi";
    if (p === "kimi-coding") p = "kimi-plan";
    state.provider = p;
  }
  syncActiveApiKey();
}

function syncActiveApiKey() {
  const pid = state.provider || selectedModelMeta()?.provider || "";
  const fromMap = (state.apiKeys && state.apiKeys[pid]) || "";
  const legacy = state.apiKeys?._legacy || "";
  state.apiKey = fromMap || legacy || "";
}

function apiKeyLabel() {
  const p = providersList().find((x) => x.id === state.provider);
  if (p?.key_hint) return p.key_hint;
  const m = selectedModelMeta();
  if (m?.key_hint) return m.key_hint;
  if (p?.label) return `${p.label} API Key`;
  return t().apiKey;
}

function persistSettings() {
  ensureProviderModel();
  const pid = state.provider || "";
  if (!state.apiKeys || typeof state.apiKeys !== "object") state.apiKeys = {};
  if (pid) {
    if (state.apiKey) state.apiKeys[pid] = state.apiKey;
    else delete state.apiKeys[pid];
  }
  sessionStorage.setItem("yiagent_api_keys", JSON.stringify(state.apiKeys));
  if (state.apiKey) sessionStorage.setItem("yiagent_api_key", state.apiKey);
  else sessionStorage.removeItem("yiagent_api_key");
  sessionStorage.setItem("yiagent_provider", state.provider || "");
  sessionStorage.setItem("yiagent_model", state.model || "k3");
  sessionStorage.setItem("yiagent_workers", String(state.workers || 4));
  sessionStorage.setItem("yiagent_champion_mark", state.championMark || "balanced");
}

function settingsConfigured() {
  ensureProviderModel();
  return !!(state.apiKey && state.apiKey.length >= 8 && state.model && state.provider);
}

function settingsSummaryHtml(c) {
  ensureProviderModel();
  const m = selectedModelMeta();
  const p = providersList().find((x) => x.id === state.provider);
  const providerLabel = p?.label || m?.provider_label || state.provider || "—";
  const modelLabel = m?.label || state.model || "—";
  const keyOk = state.apiKey && state.apiKey.length >= 8;
  const status = keyOk ? c.settingsReady : c.settingsNeedKey;
  return `<div class="settings-summary">
    <div class="settings-summary-main">
      <span class="settings-pill ${keyOk ? "is-ready" : "is-warn"}">${escapeHtml(status)}</span>
      <span class="mono">${escapeHtml(providerLabel)}</span>
      <span class="dim">/</span>
      <span class="mono">${escapeHtml(modelLabel)}</span>
      <span class="dim tiny">· workers ${state.workers}</span>
    </div>
    <button type="button" class="btn-ghost btn-compact" id="btn-open-settings">${escapeHtml(c.settings)}</button>
  </div>`;
}

function providerOptionsHtml() {
  return providersList()
    .map(
      (p) =>
        `<option value="${escapeHtml(p.id)}" ${
          state.provider === p.id ? "selected" : ""
        }>${escapeHtml(p.label)}</option>`
    )
    .join("");
}

function modelOptionsForProviderHtml() {
  const list = modelCatalog().filter((m) => m.provider === state.provider);
  if (!list.length) {
    return `<option value="">${escapeHtml(t().modelEmpty || "—")}</option>`;
  }
  return list
    .map(
      (m) =>
        `<option value="${escapeHtml(m.id)}" ${state.model === m.id ? "selected" : ""}>${escapeHtml(
          m.label || m.id
        )}</option>`
    )
    .join("");
}

function settingsModalHtml(c, running) {
  if (!state.settingsOpen) return "";
  ensureProviderModel();
  const marks = [
    { id: "balanced", label: c.markBalanced },
    { id: "perf", label: c.markPerf },
    { id: "stable", label: c.markStable },
  ];
  const p = providersList().find((x) => x.id === state.provider);
  return `<div class="settings-backdrop" id="settings-backdrop" role="presentation">
    <div class="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div class="settings-head">
        <h2 id="settings-title">${escapeHtml(c.settingsTitle)}</h2>
        <button type="button" class="btn-ghost btn-compact" id="btn-close-settings">${escapeHtml(c.settingsClose)}</button>
      </div>
      <p class="field-hint">${escapeHtml(c.settingsHelp)}</p>
      <div class="provider-form">
        <div class="run-field">
          <label class="field-label" for="provider-select">${escapeHtml(c.provider)}</label>
          <select id="provider-select" ${running ? "disabled" : ""}>${providerOptionsHtml()}</select>
        </div>
        <div class="run-field">
          <label class="field-label" for="model-select">${escapeHtml(c.model)}</label>
          <select id="model-select" ${running ? "disabled" : ""}>${modelOptionsForProviderHtml()}</select>
          <p class="field-hint">${escapeHtml(c.modelHelp)}</p>
        </div>
        <div class="run-field">
          <label class="field-label" for="api-key">${escapeHtml(apiKeyLabel())}</label>
          <input id="api-key" type="password" autocomplete="off" placeholder="sk-..." value="${escapeHtml(
            state.apiKey
          )}" ${running ? "disabled" : ""} />
          <p class="field-hint">${escapeHtml(
            (c.apiKeyHelpProvider || c.apiKeyHelp).replace("{provider}", p?.label || state.provider || "")
          )}</p>
        </div>
      </div>
      <div class="run-field" style="margin-top:1rem">
        <label class="field-label">${escapeHtml(c.workers)}</label>
        <div class="rep-pills">${pills(WORKER_OPTIONS, state.workers, "workers", running)}</div>
      </div>
      <div class="run-field" style="margin-top:1rem">
        <label class="field-label">${escapeHtml(c.championMark)}</label>
        <div class="rep-pills">
          ${marks
            .map(
              (m) =>
                `<button type="button" class="rep-pill ${
                  state.championMark === m.id ? "active" : ""
                }" data-champion-mark="${m.id}" ${running ? "disabled" : ""}>${escapeHtml(m.label)}</button>`
            )
            .join("")}
        </div>
        <p class="field-hint">${escapeHtml(c.championMarkHelp)}</p>
      </div>
      <div class="stage-actions">
        <button type="button" class="btn-primary" id="btn-save-settings" ${running ? "disabled" : ""}>${escapeHtml(
          c.settingsSave
        )}</button>
      </div>
    </div>
  </div>`;
}

function modelOptionsHtml() {
  return modelOptionsForProviderHtml();
}

function copyKeysForLang(lang) {
  const base = i18n[lang] || {};
  return Object.keys(base)
    .filter((k) => k !== "steps" && typeof base[k] === "string")
    .sort();
}

function exportCopyPayload() {
  return {
    zh: effectiveBundle("zh"),
    en: effectiveBundle("en"),
  };
}

function setCopyField(lang, key, value) {
  if (!state.copyOverrides[lang]) state.copyOverrides[lang] = {};
  const base = i18n[lang] || {};
  if (key === "steps" || key === "oralExamples") {
    state.copyOverrides[lang][key] = value;
  } else if (value === (base[key] ?? "")) {
    delete state.copyOverrides[lang][key];
  } else {
    state.copyOverrides[lang][key] = value;
  }
  persistCopyOverrides();
}

function syncCopyEditor(forceRebuild = false) {
  const host = document.getElementById("copy-editor");
  if (!host) return;
  if (!state.copyEditOpen) {
    host.hidden = true;
    host.innerHTML = "";
    host.dataset.built = "";
    document.body.classList.remove("copy-edit-open");
    return;
  }
  document.body.classList.add("copy-edit-open");
  host.hidden = false;
  const lang = state.lang;
  if (!forceRebuild && host.dataset.built === lang && host.querySelector(".copy-editor-panel")) {
    return;
  }
  const bundle = effectiveBundle(lang);
  const keys = copyKeysForLang(lang);
  host.innerHTML = `
    <aside class="copy-editor-panel" aria-label="copy editor">
      <header class="copy-editor-head">
        <div>
          <strong>编辑文案</strong>
          <p class="dim tiny">左侧改字会立刻反映到页面。改完点「导出 JSON」或「复制」发给我固化。当前：${
            lang === "zh" ? "中文" : "English"
          }</p>
        </div>
        <div class="copy-editor-actions">
          <button type="button" class="btn-ghost btn-compact" id="btn-copy-export">导出 JSON</button>
          <button type="button" class="btn-ghost btn-compact" id="btn-copy-clipboard">复制</button>
          <button type="button" class="btn-ghost btn-compact" id="btn-copy-reset">恢复默认</button>
          <button type="button" class="btn-primary btn-compact" id="btn-copy-close">完成</button>
        </div>
      </header>
      <div class="copy-editor-body">
        <section class="copy-editor-section">
          <h3>步骤条 steps</h3>
          ${(bundle.steps || [])
            .map(
              (s, i) => `<label class="copy-field">
                <span class="mono tiny">steps[${i}]</span>
                <input type="text" data-copy-key="steps" data-copy-idx="${i}" value="${escapeHtml(s)}" />
              </label>`
            )
            .join("")}
        </section>
        <section class="copy-editor-section">
          <h3>口述示例 oralExamples</h3>
          ${(bundle.oralExamples || [])
            .map(
              (s, i) => `<label class="copy-field">
                <span class="mono tiny">oralExamples[${i}]</span>
                <input type="text" data-copy-key="oralExamples" data-copy-idx="${i}" value="${escapeHtml(s)}" />
              </label>`
            )
            .join("")}
        </section>
        <section class="copy-editor-section">
          <h3>界面文案</h3>
          ${keys
            .map((k) => {
              const val = bundle[k] ?? "";
              const rows = String(val).length > 60 ? 3 : 2;
              return `<label class="copy-field">
                <span class="mono tiny">${escapeHtml(k)}</span>
                <textarea data-copy-key="${escapeHtml(k)}" rows="${rows}">${escapeHtml(val)}</textarea>
              </label>`;
            })
            .join("")}
        </section>
      </div>
    </aside>`;
  host.dataset.built = lang;

  host.querySelector("#btn-copy-close")?.addEventListener("click", () => {
    state.copyEditOpen = false;
    render();
  });
  host.querySelector("#btn-copy-reset")?.addEventListener("click", () => {
    if (!window.confirm("清除本机已改文案，恢复代码默认？")) return;
    state.copyOverrides = { zh: {}, en: {} };
    persistCopyOverrides();
    host.dataset.built = "";
    render();
    syncCopyEditor(true);
  });
  const doExport = async (toClipboard) => {
    const payload = JSON.stringify(exportCopyPayload(), null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `yiagent-factory-copy-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    if (toClipboard && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(payload);
        showToast("已导出并复制到剪贴板");
      } catch {
        showToast("已下载 JSON");
      }
    } else {
      showToast("已下载 JSON，发给我即可固化");
    }
    render();
  };
  host.querySelector("#btn-copy-export")?.addEventListener("click", () => doExport(false));
  host.querySelector("#btn-copy-clipboard")?.addEventListener("click", () => doExport(true));

  const onEdit = (el) => {
    const key = el.dataset.copyKey;
    if (!key) return;
    if (key === "steps" || key === "oralExamples") {
      const idx = Number(el.dataset.copyIdx);
      const arr = (effectiveBundle(lang)[key] || []).slice();
      arr[idx] = el.value;
      setCopyField(lang, key, arr);
    } else {
      setCopyField(lang, key, el.value);
    }
    render();
  };
  host.querySelectorAll("[data-copy-key]").forEach((el) => {
    el.addEventListener("input", () => onEdit(el));
  });
}

const i18n = {
  zh: {
    brandSub: "测试流水线",
    companion: "YiAgent 基因筛选台",
    lang: "EN",
    title: "通过基因组定义Agent，并通过变异、筛选等基因工程手段获得最符合你心意的Agent（再也不用调 Prompt）",
    lead: "口述场景 → 生成考题与裁判 → 建立 A/B 标准基线 → 组装 G1–G5 候选 → 初筛 → 冠军终筛（效果 / 稳定 / 均衡）。",
    hook: "用基因工程定义Agent",
    steps: ["口述", "题目", "基线", "基因组", "初筛", "冠军", "终筛"],
    s1: "选题或口述筛选意图",
    s1help: "优先从 XSCT 用例库选现成题（含评分标准）；也可口述让模型从 0 生成。",
    caseSourceLibrary: "用例库",
    caseSourceOral: "口述生成",
    caseSuite: "套件",
    caseDimension: "维度",
    caseLevel: "难度",
    caseSearch: "搜索",
    caseSearchPh: "标题 / id / 描述…",
    casePick: "选择用例",
    caseLoad: "载入本题",
    caseAllDims: "全部维度",
    caseEmpty: "没有匹配用例",
    caseNeedPick: "请先从用例库选择一道题",
    caseLoaded: "已从用例库载入",
    caseCount: "共 {n} 题",
    oral: "场景口述",
    oralPh: "例如：客服在用户套取订单隐私或越权操作时，应如何拒答并引导合规路径…",
    examples: "试试这些",
    model: "模型",
    provider: "Provider",
    modelHelp: "仅显示当前 Provider 下的可用模型。",
    modelEmpty: "该 Provider 暂无模型",
    apiKey: "API Key",
    apiKeyHelp: "按所选厂商填写对应 Key；仅保存在本机浏览器会话，不会写入服务器磁盘。",
    apiKeyHelpProvider: "用于 {provider}；切换 Provider 会换用各自已存的 Key。",
    settings: "设置",
    settingsTitle: "运行设置",
    settingsHelp: "先选 Provider，再选模型并填写该厂商 Key。",
    settingsClose: "关闭",
    settingsSave: "保存设置",
    settingsReady: "已配置",
    settingsNeedKey: "未配置 Key",
    championMark: "全自动最优标记",
    championMarkHelp: "全自动终筛后默认取哪块金牌写入最优基因。",
    workers: "并发线程",
    advanced: "高级选项",
    genCase: "生成题目与标准",
    demo: "载入冻结演示",
    demoHint: "载入已固化的批判思维演示包（含 A/B 与终筛结果），不调用模型。要实跑请用「生成题目」或逐步点基线按钮。",
    autoRun: "全自动跑出最优基因",
    autoHint: "一键串起：载入/生成题 → A/B → 基因组 → 初筛 → 终筛；默认取均衡最优并写入 save/。",
    autoNeedCase: "用例库模式请先选中一道题",
    toastAutoStart: "全自动已启动，无需逐步点击",
    toastAutoDone: "全自动完成 · 最优基因已落盘",
    autoStepCase: "全自动 · 准备题目",
    autoStepBaseline: "全自动 · A/B 基线",
    autoStepGenomes: "全自动 · 生成基因组",
    autoStepPrefilter: "全自动 · 初筛",
    autoStepChampion: "全自动 · 终筛",
    autoStepSave: "全自动 · 保存",
    autoStepDone: "全自动 · 完成",
    bestGenome: "本轮最优基因",
    bestGenomePath: "落盘",
    saveRun: "保存会话",
    freezeDemo: "固化为演示",
    saveNeedSession: "请先有一个会话再保存",
    toastSaveOk: "已写入 save/（含运行日志）",
    toastFreezeOk: "已写入 save/ 并固化 fixtures/demo_pack.json",
    s2: "核对题目与评分标准",
    s2help: "左侧是给选手看的原题；右侧是裁判标准，不会装进基因组。可直接改字。",
    target: "筛选目标 · 原题",
    criteria: "筛选标准 · 裁判",
    saveCase: "保存修改",
    nextBaseline: "下一步：建立标准基线",
    s3: "建立标准基线（A / B）",
    s3help: "A 组只用原题 system；B 组在 system 中灌入完整评分标准（对照上界）。各测若干次，按并发线程并行打分，作为后续基因组筛选的参照。",
    baselineArmA: "A · 原题对照（最低标准）",
    baselineArmB: "B · 带入标准（理论上限）",
    baselineReps: "每组测几次",
    startBaseline: "开始 A/B 基线",
    skipBaseline: "跳过基线",
    baselineGap: "B − A（均分差）",
    baselineDemoSkip: "冻结演示包含已测 A/B；要重测请新会话实跑。",
    baselineStale: "题目/标准已改，下列为上次基线结果（未自动清空）",
    baselineKeep: "A/B 基线（保留）",
    nextGenome: "下一步：生成基因组",
    s4: "生成初始基因组",
    s4help: "按 G1 身份 · G2 边界 · G3 知识 · G4 能力 · G5 经验 生成多套候选组合。",
    genGenome: "生成完整基因组",
    genomes: "候选基因组",
    genomeCount: "套候选",
    nextPre: "下一步：初筛",
    s5: "初筛",
    s5help: "每套基因组测若干次；均分达到合格线即记为合格。凑够合格数就提前结束，省时间。",
    qualify: "要凑齐几个合格",
    preReps: "每套测几次",
    passMean: "合格线（均分）",
    startPre: "开始初筛",
    abort: "停止",
    early: "已提前结束",
    passed: "合格",
    failed: "未过",
    s6: "挑选冠军池",
    s6help: "初筛合格的默认勾选。你也可以把有潜力的未过项加进来，或去掉不想比的。",
    poolSelected: "已选入池",
    selectPassed: "一键只留合格",
    selectAll: "全选",
    clearPool: "清空",
    champReps: "终筛测试次数",
    startChamp: "开始终筛",
    s7: "终筛结果",
    s7help: "三块金牌可以落在不同基因组上——效果看均分，稳定看波动，均衡看均分减波动。",
    markPerf: "效果最优",
    markStable: "稳定最优",
    markBalanced: "均衡最优",
    markPerfDesc: "均分最高",
    markStableDesc: "波动最小",
    markBalancedDesc: "均分 − 1.5×波动",
    progress: "进度",
    tokens: "Token",
    tokensLine: "Token · 入 {in} · 出 {out} · 合计 {total} · {calls} 次调用",
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
    toastBaseline: "标准基线已建立，可以生成基因组",
    toastBaselineSkip: "已跳过基线",
    toastGenome: "基因组已生成，可以开始初筛",
    toastPre: "初筛完成，请确认冠军池",
    toastChamp: "终筛完成，三标已出",
    toastDemo: "已载入批判思维原题，请手动跑 A/B",
    toastDemoPack: "已载入冻结演示包（含 A/B）",
    toastDemoSeed: "已载入批判思维原题，请跑 A/B 基线",
    toastSaved: "已保存文案",
    keyNeed: "请填写有效的Key",
    oralNeed: "请先写一句口述意图（或点示例）",
    footer: "YiAgent 基因组工作台",
  },
  en: {
    brandSub: "Assemble Factory",
    companion: "Companion desk for YiAgent",
    lang: "中文",
    title: "Screen agents by genome — not by one prompt",
    lead: "Brief → task & rubric → A/B baseline → G1–G5 genomes → prefilter → champion finals (performance / stability / balance).",
    hook: "They tune prompts. We edit the genome.",
    steps: ["Brief", "Task", "Baseline", "Genome", "Pre", "Pool", "Final"],
    s1: "Pick a case or describe intent",
    s1help: "Prefer a ready XSCT case (with rubric). Or brief the model to generate from scratch.",
    caseSourceLibrary: "Case library",
    caseSourceOral: "Generate from brief",
    caseSuite: "Suite",
    caseDimension: "Dimension",
    caseLevel: "Level",
    caseSearch: "Search",
    caseSearchPh: "title / id / description…",
    casePick: "Select case",
    caseLoad: "Load case",
    caseAllDims: "All dimensions",
    caseEmpty: "No matching cases",
    caseNeedPick: "Pick a case from the library first",
    caseLoaded: "Loaded from case library",
    caseCount: "{n} cases",
    oral: "Scenario brief",
    oralPh: "e.g. How support should refuse privacy fishing or out-of-scope asks…",
    examples: "Try these",
    model: "Model",
    provider: "Provider",
    modelHelp: "Only models for the selected provider.",
    modelEmpty: "No models for this provider",
    apiKey: "API Key",
    apiKeyHelp: "Use the key for the selected provider. Stored in this browser session only — never written to disk.",
    apiKeyHelpProvider: "For {provider}. Switching provider uses that provider’s saved key.",
    settings: "Settings",
    settingsTitle: "Run settings",
    settingsHelp: "Pick a provider first, then its model and API key.",
    settingsClose: "Close",
    settingsSave: "Save settings",
    settingsReady: "Ready",
    settingsNeedKey: "Key missing",
    championMark: "Auto champion mark",
    championMarkHelp: "Which finals medal to save as the best genome after auto runs.",
    workers: "Workers",
    advanced: "Advanced",
    genCase: "Generate task & rubric",
    demo: "Load frozen demo",
    demoHint: "Load the frozen CT demo pack (A/B + finals). No model calls. For a live run, generate a case or click baseline yourself.",
    autoRun: "Auto: best genome",
    autoHint: "Unattended: case → A/B → genomes → prefilter → finals; default balanced champion → save/.",
    autoNeedCase: "Pick a library case first",
    toastAutoStart: "Auto pipeline started — no manual steps",
    toastAutoDone: "Auto done · best genome saved",
    autoStepCase: "Auto · case",
    autoStepBaseline: "Auto · A/B baseline",
    autoStepGenomes: "Auto · genomes",
    autoStepPrefilter: "Auto · prefilter",
    autoStepChampion: "Auto · finals",
    autoStepSave: "Auto · save",
    autoStepDone: "Auto · done",
    bestGenome: "Best genome this run",
    bestGenomePath: "Saved",
    saveRun: "Save session",
    freezeDemo: "Freeze as demo",
    saveNeedSession: "Start a session before saving",
    toastSaveOk: "Wrote save/ (incl. run log)",
    toastFreezeOk: "Wrote save/ and froze fixtures/demo_pack.json",
    s2: "Review task & rubric",
    s2help: "Left = contestant task. Right = judge rubric (never loaded into the genome). Edit freely.",
    target: "Target · task",
    criteria: "Criteria · judge",
    saveCase: "Save edits",
    nextBaseline: "Next: A/B baseline",
    s3: "Standard baseline (A / B)",
    s3help: "A = original system only. B = host + full scoring criteria dump (upper bound). Run a few reps each in parallel workers as the reference before genomes.",
    baselineArmA: "A · original task",
    baselineArmB: "B · criteria dump",
    baselineReps: "Reps per arm",
    startBaseline: "Run A/B baseline",
    skipBaseline: "Skip baseline",
    baselineGap: "B − A (mean gap)",
    baselineDemoSkip: "Frozen demo includes measured A/B. Start a new session to re-run.",
    baselineStale: "Task/rubric changed — showing last A/B results (kept)",
    baselineKeep: "A/B baseline (kept)",
    nextGenome: "Next: genomes",
    s4: "Generate genomes",
    s4help: "G1 identity · G2 boundaries · G3 knowledge · G4 capability · G5 experience.",
    genGenome: "Generate G1–G5 genomes",
    genomes: "Candidates",
    genomeCount: "candidates",
    nextPre: "Next: prefilter",
    s5: "Prefilter",
    s5help: "Test each genome a few times. Pass when mean ≥ threshold. Stop early once enough pass.",
    qualify: "Pass count to stop",
    preReps: "Reps per genome",
    passMean: "Pass line (mean)",
    startPre: "Start prefilter",
    abort: "Stop",
    early: "Early stop",
    passed: "Pass",
    failed: "Fail",
    s6: "Champion pool",
    s6help: "Passed genomes are checked by default. Add or remove freely.",
    poolSelected: "In pool",
    selectPassed: "Passed only",
    selectAll: "Select all",
    clearPool: "Clear",
    champReps: "Final reps",
    startChamp: "Start finals",
    s7: "Final marks",
    s7help: "Three medals may land on different genomes.",
    markPerf: "Best performance",
    markStable: "Best stability",
    markBalanced: "Best balanced",
    markPerfDesc: "Highest mean",
    markStableDesc: "Lowest variance",
    markBalancedDesc: "mean − 1.5×sdv",
    progress: "Progress",
    tokens: "Tokens",
    tokensLine: "Tokens · in {in} · out {out} · total {total} · {calls} calls",
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
    toastBaseline: "Baseline ready — generate genomes",
    toastBaselineSkip: "Baseline skipped",
    toastGenome: "Genomes ready — start prefilter",
    toastPre: "Prefilter done — confirm the pool",
    toastChamp: "Finals done — medals ready",
    toastDemo: "CT fixture loaded — run A/B yourself",
    toastDemoPack: "Frozen demo pack loaded (with A/B)",
    toastDemoSeed: "CT fixture loaded — run A/B baseline",
    toastSaved: "Saved",
    keyNeed: "Enter a valid API Key for the selected provider",
    oralNeed: "Add a brief (or tap an example)",
    footer: "YiAgent companion · Assemble Factory · session-local results",
  },
};

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

/** Map phase → UX step 1..7 */
function currentStep(phase) {
  const r = phaseRank(phase);
  if (r <= 0) return 1;
  if (r === 1) return 3; // case_ready → baseline
  if (r === 2) return 3; // baselining
  if (r === 3) return 4; // baseline_done → genomes
  if (r === 4) return 5; // genomes_ready → pre
  if (r === 5) return 5; // prefiltering
  if (r === 6) return 6; // prefilter_done → pool
  if (r === 7) return 7; // championing
  if (r >= 8) return 7;
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

function isAutoActive(snap) {
  if (!snap?.auto || !snap.auto_step) return false;
  if (snap.phase === "error" || snap.status === "aborted" || snap.status === "error") return false;
  return !["done", "error"].includes(snap.auto_step);
}

function autoStepLabel(step, c) {
  const map = {
    case: c.autoStepCase,
    baseline: c.autoStepBaseline,
    genomes: c.autoStepGenomes,
    prefilter: c.autoStepPrefilter,
    champion: c.autoStepChampion,
    save: c.autoStepSave,
    done: c.autoStepDone,
  };
  return map[step] || c.autoRun || c.wait;
}

function applySnap(snap, { syncFocus = false } = {}) {
  state.snap = snap;
  state.sessionId = snap.id;
  if (snap.target_text != null) state.targetText = snap.target_text;
  if (snap.criteria_text != null) state.criteriaText = snap.criteria_text;
  if (Array.isArray(snap.pool)) state.pool = new Set(snap.pool);
  if (snap.pass_mean != null) state.passMean = snap.pass_mean;
  if (snap.qualify_target != null) state.qualifyTarget = snap.qualify_target;
  if (snap.baseline_reps != null) state.baselineReps = snap.baseline_reps;
  if (snap.pre_reps != null) state.preReps = snap.pre_reps;
  if (snap.champ_reps != null) state.champReps = snap.champ_reps;
  if (snap.workers != null) state.workers = snap.workers;
  if (snap.model && snap.model !== "demo") state.model = snap.model;
  const liveBaseline = snap.baseline_summaries || [];
  if (liveBaseline.some((r) => (r.n || 0) > 0)) {
    state.baselineCache = liveBaseline.map((r) => ({ ...r }));
  }
  if (syncFocus) {
    state.focusStep = currentStep(snap.phase);
  }
}

function baselineSummariesOf(snap) {
  const live = snap?.baseline_summaries || [];
  if (live.some((r) => (r.n || 0) > 0)) return live;
  return state.baselineCache || [];
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
      if (isAutoActive(snap)) {
        state.busy = true;
        state.localBusyLabel = autoStepLabel(snap.auto_step, t());
        state.focusStep = currentStep(snap.phase);
      }
      render();
      if (snap.status !== "running" && !isAutoActive(snap)) {
        stopPoll();
        state.busy = false;
        state.localBusyLabel = "";
        const c = t();
        if (snap.auto && snap.auto_step === "done" && snap.phase === "done") {
          const title = snap.best_genome?.title || snap.best_genome?.variant_id || "";
          showToast(title ? `${c.toastAutoDone} · ${title}` : c.toastAutoDone);
        } else if (snap.phase === "baseline_done") showToast(c.toastBaseline);
        else if (snap.phase === "prefilter_done") showToast(c.toastPre);
        else if (snap.phase === "done") showToast(c.toastChamp);
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
  const provider = document.getElementById("provider-select");
  const key = document.getElementById("api-key");
  const model = document.getElementById("model-select");
  const target = document.getElementById("target-text");
  const criteria = document.getElementById("criteria-text");
  const passMean = document.getElementById("pass-mean");
  if (oral) state.oral = oral.value;
  if (provider) {
    state.provider = provider.value;
  }
  if (key) {
    state.apiKey = key.value.trim();
  }
  if (model) {
    state.model = model.value;
  }
  persistSettings();
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
    state.settingsOpen = true;
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

function suiteOptionsHtml() {
  const suites = state.caseMeta?.suites || { "xsct-l": 0, "xsct-vg": 0, "xsct-w": 0 };
  return Object.keys(suites)
    .sort()
    .map(
      (s) =>
        `<option value="${escapeHtml(s)}" ${state.caseSuite === s ? "selected" : ""}>${escapeHtml(
          s
        )} (${suites[s]})</option>`
    )
    .join("");
}

function dimensionOptionsForSuite() {
  const dims = state.caseMeta?.dimensions || [];
  const suite = state.caseSuite || "";
  if (suite === "xsct-l") return dims.filter((d) => d.startsWith("L-"));
  if (suite === "xsct-vg") return dims.filter((d) => d.startsWith("VG-") || d.startsWith("P-"));
  if (suite === "xsct-w") return dims.filter((d) => d.startsWith("W-"));
  return dims;
}

function selectedCaseHintHtml() {
  const it = (state.caseItems || []).find((x) => x.id === state.caseSelectedId);
  if (!it) return "";
  const desc = (it.description || "").slice(0, 180);
  return `<p class="field-hint mono">${escapeHtml(it.id)} · ${escapeHtml(it.title)}${
    desc ? "<br/>" + escapeHtml(desc) : ""
  }</p>`;
}

let _caseQueryTimer = null;

async function ensureCaseMeta() {
  if (state.caseMeta) return;
  try {
    state.caseMeta = await api("/api/cases/meta");
    const suites = state.caseMeta?.suites || {};
    if (!state.caseSuite || !(state.caseSuite in suites)) {
      state.caseSuite = Object.keys(suites).sort()[0] || "xsct-l";
    }
  } catch (e) {
    state.caseMeta = { ok: false, suites: {}, dimensions: [], count: 0 };
    state.error = String(e.message || e);
  }
}

async function refreshCaseLibrary() {
  state.caseLoading = true;
  render();
  try {
    await ensureCaseMeta();
    const params = new URLSearchParams();
    if (state.caseSuite) params.set("suite", state.caseSuite);
    if (state.caseDimension) params.set("dimension", state.caseDimension);
    if (state.caseQuery.trim()) params.set("q", state.caseQuery.trim());
    params.set("limit", "120");
    const data = await api(`/api/cases?${params.toString()}`);
    state.caseItems = data.items || [];
    state.caseTotal = data.total || 0;
    if (
      state.caseSelectedId &&
      !state.caseItems.some((it) => it.id === state.caseSelectedId)
    ) {
      state.caseSelectedId = state.caseItems[0]?.id || "";
    } else if (!state.caseSelectedId && state.caseItems[0]) {
      state.caseSelectedId = state.caseItems[0].id;
    }
  } catch (e) {
    state.caseItems = [];
    state.caseTotal = 0;
    state.error = String(e.message || e);
  } finally {
    state.caseLoading = false;
    render();
  }
}

async function onLoadLibraryCase() {
  const c = t();
  readFormIntoState();
  const pick = document.getElementById("case-pick");
  if (pick) state.caseSelectedId = pick.value || state.caseSelectedId;
  const levelEl = document.getElementById("case-level");
  if (levelEl) state.caseLevel = levelEl.value || state.caseLevel;
  if (!state.caseSelectedId) {
    state.error = c.caseNeedPick;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.caseLoad;
  state.error = null;
  render();
  try {
    const snap = await api("/api/session/case/library", {
      method: "POST",
      body: JSON.stringify({
        suite: state.caseSuite,
        id: state.caseSelectedId,
        level: state.caseLevel || "basic",
        model: state.model,
      }),
    });
    applySnap(snap);
    state.focusStep = 2;
    showToast(c.caseLoaded);
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
  readFormIntoState();
  state.busy = true;
  state.error = null;
  render();
  try {
    // Always prefer frozen demo_pack (show recorded A/B + finals). Never auto-start a live run.
    const snap = await api("/api/session/demo", {
      method: "POST",
      body: JSON.stringify({ fresh: false }),
    });
    applySnap(snap);
    const hasBaseline = (snap.baseline_summaries || []).some((r) => (r.n || 0) > 0);
    const frozen = snap.frozen_demo === true;
    state.focusStep = hasBaseline || frozen ? 3 : 2;
    showToast(frozen || hasBaseline ? c.toastDemoPack : c.toastDemoSeed);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    state.localBusyLabel = "";
    render();
    scrollToStep(state.focusStep);
  }
}

async function onSaveRun(freeze) {
  const c = t();
  if (!state.sessionId) {
    state.error = c.saveNeedSession;
    render();
    return;
  }
  if (state.snap?.status === "running") {
    state.error = c.wait;
    render();
    return;
  }
  state.busy = true;
  state.error = null;
  render();
  try {
    const res = await api(`/api/session/${state.sessionId}/save`, {
      method: "POST",
      body: JSON.stringify({
        freeze_demo: !!freeze,
        label: freeze ? "demo_capture" : "session",
        version_tag: "v1.0",
      }),
    });
    showToast(freeze ? c.toastFreezeOk : c.toastSaveOk);
    if (res?.pack_path) {
      console.info("[yiagent save]", res);
    }
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    render();
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

async function onBaseline() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    state.settingsOpen = true;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.startBaseline;
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
    const snap = await api(`/api/session/${state.sessionId}/baseline/start`, {
      method: "POST",
      body: JSON.stringify({
        api_key: state.apiKey,
        baseline_reps: state.baselineReps,
        workers: state.workers,
        model: state.model,
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

async function onSkipBaseline() {
  if (!state.sessionId) return;
  const c = t();
  state.busy = true;
  state.error = null;
  render();
  try {
    const snap = await api(`/api/session/${state.sessionId}/baseline/skip`, {
      method: "POST",
      body: "{}",
    });
    applySnap(snap);
    state.focusStep = 4;
    showToast(c.toastBaselineSkip);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    render();
    scrollToStep(4);
  }
}

async function onGenGenomes() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    state.settingsOpen = true;
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
    state.focusStep = 5;
    showToast(c.toastGenome);
  } catch (e) {
    state.error = String(e.message || e);
  } finally {
    state.busy = false;
    state.localBusyLabel = "";
    render();
    scrollToStep(5);
  }
}

async function onPrefilter() {
  if (!state.sessionId) return;
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    state.settingsOpen = true;
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

async function onAutoRun() {
  const c = t();
  readFormIntoState();
  if (!state.apiKey || state.apiKey.length < 8) {
    state.error = c.keyNeed;
    state.settingsOpen = true;
    render();
    return;
  }
  const source = state.caseSource === "oral" ? "oral" : "library";
  if (source === "library" && !state.caseSelectedId) {
    state.error = c.autoNeedCase;
    render();
    return;
  }
  if (source === "oral" && (!state.oral.trim() || state.oral.trim().length < 4)) {
    state.error = c.oralNeed;
    render();
    return;
  }
  state.busy = true;
  state.localBusyLabel = c.autoRun;
  state.error = null;
  state.baselineCache = null;
  render();
  try {
    const body = {
      api_key: state.apiKey,
      model: state.model,
      source,
      baseline_reps: state.baselineReps,
      pre_reps: state.preReps,
      champ_reps: state.champReps,
      qualify_target: state.qualifyTarget,
      pass_mean: state.passMean,
      workers: state.workers,
      champion_mark: state.championMark || "balanced",
      save: true,
    };
    if (source === "library") {
      body.suite = state.caseSuite;
      body.id = state.caseSelectedId;
      body.level = state.caseLevel || "basic";
    } else {
      body.oral = state.oral.trim();
    }
    const snap = await api("/api/session/auto", {
      method: "POST",
      body: JSON.stringify(body),
    });
    applySnap(snap, { syncFocus: true });
    state.localBusyLabel = autoStepLabel(snap.auto_step, c);
    showToast(c.toastAutoStart);
    startPoll();
  } catch (e) {
    state.error = String(e.message || e);
    state.busy = false;
    state.localBusyLabel = "";
  }
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
    state.settingsOpen = true;
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
  state.baselineCache = null;
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
        return `${i > 0 ? '<span class="stepper-gap" aria-hidden="true"></span>' : ""}
        <button type="button" class="stepper-item ${active ? "active" : ""} ${done ? "done" : ""} ${
          locked ? "locked" : ""
        }" data-goto="${n}" ${locked ? "disabled" : ""}>
          <span class="stepper-num">${done ? "✓" : String(n).padStart(2, "0")}</span>
          <span class="stepper-label">${escapeHtml(label)}</span>
        </button>`;
      })
      .join("")}
  </nav>`;
}

function progressBar(done, total) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return `<div class="progress-block">
    <div class="progress-meta mono">${done} / ${total} · ${pct}%</div>
    <div class="progress-track"><i style="width:${pct}%"></i></div>
  </div>`;
}

/** Inline run progress inside a stage panel (in addition to top sticky). */
function stageProgressHtml({ active, label, snap, c, withAbort = false }) {
  if (!active) return "";
  const serverRunning = snap?.status === "running";
  const done = snap?.done || 0;
  const total = snap?.total || 0;
  return `<div class="stage-progress" role="status">
    <div class="stage-progress-head">
      <strong>${escapeHtml(label || c.wait)}</strong>
      <span class="dim"> · ${escapeHtml(c.progress)}</span>
    </div>
    ${
      serverRunning && total > 0
        ? progressBar(done, total)
        : `<div class="spinner" aria-hidden="true"></div>`
    }
    ${tokenUsageHtml(snap?.token_usage, c)}
    ${
      withAbort && serverRunning
        ? `<button class="btn-ghost btn-abort btn-compact" type="button" data-abort-inline="1">${escapeHtml(
            c.abort
          )}</button>`
        : ""
    }
  </div>`;
}

function formatTokenCount(n) {
  const v = Number(n) || 0;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 10_000) return `${(v / 1000).toFixed(1)}k`;
  if (v >= 1000) return `${(v / 1000).toFixed(2)}k`;
  return String(v);
}

function tokenUsageHtml(usage, c) {
  if (!usage || !(usage.calls > 0 || usage.total_tokens > 0)) return "";
  const line = (c.tokensLine || "")
    .replace("{in}", formatTokenCount(usage.prompt_tokens))
    .replace("{out}", formatTokenCount(usage.completion_tokens))
    .replace("{total}", formatTokenCount(usage.total_tokens))
    .replace("{calls}", String(usage.calls || 0));
  return `<div class="token-usage mono" title="${escapeHtml(c.tokens || "Token")}">${escapeHtml(line)}</div>`;
}

function unlockedMax(rank, snap) {
  if (rank >= 7) return 7; // championing / done
  if (rank >= 6) return 7; // prefilter_done
  if (rank >= 4) return 5; // genomes_ready / prefiltering
  if (rank >= 3) return 4; // baseline_done
  if (rank >= 1) return 3; // case_ready / baselining
  if (snap) return 2;
  return 1;
}

function render() {
  const root = document.getElementById("root");
  const c = t();
  const snap = state.snap;
  const phase = snap?.phase || "idle";
  const rank = phaseRank(phase);
  const autoBusy = isAutoActive(snap);
  const running = snap?.status === "running" || state.busy || autoBusy;
  const unlock = unlockedMax(rank, snap);
  const focus = Math.min(state.focusStep, unlock);
  const examples = oralExamplesList();
  const demoFrozen = snap?.frozen_demo === true;
  const baselineRows = baselineSummariesOf(snap);
  const hasBaseline = baselineRows.some((r) => (r.n || 0) > 0);
  const stickyLabel = autoBusy
    ? autoStepLabel(snap.auto_step, c)
    : state.localBusyLabel || c.wait;
  const isBaselining =
    phase === "baselining" || (running && state.localBusyLabel === c.startBaseline) || (autoBusy && snap.auto_step === "baseline");
  const isGenomesBusy =
    (running && state.localBusyLabel === c.genGenome) || (autoBusy && snap.auto_step === "genomes");
  const isPrefiltering =
    phase === "prefiltering" || (running && state.localBusyLabel === c.startPre) || (autoBusy && snap.auto_step === "prefilter");
  const isChampioning =
    phase === "championing" || (running && state.localBusyLabel === c.startChamp) || (autoBusy && snap.auto_step === "champion");
  const isCaseBusy =
    (running &&
      (state.localBusyLabel === c.genCase ||
        state.localBusyLabel === c.caseLoad ||
        state.localBusyLabel === c.wait ||
        state.localBusyLabel === c.autoRun)) ||
    (autoBusy && snap.auto_step === "case");

  root.className = "app-shell console ux";
  root.innerHTML = `
    <header class="topbar">
      <div class="brand-block">
        <div class="brand-mark">Yi<span>Agent</span></div>
        <div class="brand-sub">${escapeHtml(c.brandSub)}</div>
      </div>
      <div class="topbar-actions">
        <button class="btn-ghost btn-compact" type="button" id="btn-settings">${escapeHtml(c.settings)}</button>
        <button class="lang-toggle" type="button" id="btn-lang">${c.lang}</button>
        <button class="btn-ghost btn-compact" type="button" id="btn-save-run" ${
          !state.sessionId || running ? "disabled" : ""
        }>${escapeHtml(c.saveRun)}</button>
        <button class="btn-ghost btn-compact" type="button" id="btn-freeze-demo" ${
          !state.sessionId || running ? "disabled" : ""
        }>${escapeHtml(c.freezeDemo)}</button>
        <button class="btn-ghost btn-compact" type="button" id="btn-reset">${c.reset}</button>
      </div>
    </header>

    ${settingsModalHtml(c, running)}

    ${
      running
        ? `<div class="run-sticky" role="status">
            <div>
              <strong>${escapeHtml(stickyLabel)}</strong>
              <span class="dim"> · ${escapeHtml(autoBusy ? c.autoHint : c.runningHint)}</span>
            </div>
            ${
              snap?.status === "running"
                ? `${progressBar(snap.done || 0, snap.total || 0)}
                   ${tokenUsageHtml(snap.token_usage, c)}
                   <button class="btn-ghost btn-abort btn-compact" type="button" id="btn-abort">${c.abort}</button>`
                : `<div class="spinner" aria-hidden="true"></div>
                   ${tokenUsageHtml(snap?.token_usage, c)}`
            }
          </div>`
        : ""
    }

    ${state.toast ? `<div class="toast" id="toast" role="status">${escapeHtml(state.toast)}</div>` : ""}
    ${
      !running && snap?.token_usage && (snap.token_usage.calls > 0 || snap.token_usage.total_tokens > 0)
        ? `<div class="token-bar">${tokenUsageHtml(snap.token_usage, c)}</div>`
        : ""
    }
    ${
      hasBaseline && focus !== 3
        ? `<div class="baseline-keep">
            <button type="button" class="baseline-keep-btn" id="btn-jump-baseline">${escapeHtml(c.baselineKeep)}</button>
            <span class="mono dim">${baselineRows
              .map((r) => `${r.arm || r.variant_id}: ${r.mean ?? "—"}`)
              .join(" · ")}${
              baselineRows[0]?.gap_b_minus_a != null
                ? ` · Δ ${baselineRows[0].gap_b_minus_a}`
                : ""
            }</span>
            ${
              snap?.baseline_stale
                ? `<span class="dim tiny">${escapeHtml(c.baselineStale)}</span>`
                : ""
            }
          </div>`
        : ""
    }

    <main class="desk">
      <section class="hero-lite">
        <div class="hero-copy">
          <p class="hero-kicker">${escapeHtml(c.companion)}</p>
          <h1 class="console-title">${escapeHtml(c.title)}</h1>
          <p class="hook-line">${escapeHtml(c.hook)}</p>
          <p class="section-lead">${escapeHtml(c.lead)}</p>
        </div>
        <div class="hero-rail">
          ${stepperHtml(c, focus, unlock)}
        </div>
        ${state.error ? `<div class="error-banner" role="alert"><strong>提示</strong> ${escapeHtml(state.error)}</div>` : ""}
      </section>

      <section class="panel stage-panel ${focus === 1 ? "is-focus" : ""} ${unlock < 1 ? "stage-locked" : ""}" id="step-panel-1">
        <div class="stage-head">
          <p class="section-kicker">01</p>
          <h2 class="stage-title">${escapeHtml(c.s1)}</h2>
          <p class="stage-help">${escapeHtml(c.s1help)}</p>
        </div>
        ${stageProgressHtml({
          active: isCaseBusy,
          label: state.localBusyLabel || c.wait,
          snap,
          c,
        })}
        <div class="source-pills" role="tablist">
          <button type="button" class="chip ${state.caseSource === "library" ? "chip-active" : ""}" data-case-source="library" ${
            running ? "disabled" : ""
          }>${escapeHtml(c.caseSourceLibrary)}</button>
          <button type="button" class="chip ${state.caseSource === "oral" ? "chip-active" : ""}" data-case-source="oral" ${
            running ? "disabled" : ""
          }>${escapeHtml(c.caseSourceOral)}</button>
        </div>
        ${
          state.caseSource === "library"
            ? `<div class="case-lib">
                <div class="cred-grid">
                  <div class="run-field">
                    <label class="field-label">${escapeHtml(c.caseSuite)}</label>
                    <select id="case-suite" ${running || state.caseLoading ? "disabled" : ""}>
                      ${suiteOptionsHtml()}
                    </select>
                  </div>
                  <div class="run-field">
                    <label class="field-label">${escapeHtml(c.caseLevel)}</label>
                    <select id="case-level" ${running ? "disabled" : ""}>
                      ${["basic", "medium", "hard"]
                        .map(
                          (lv) =>
                            `<option value="${lv}" ${state.caseLevel === lv ? "selected" : ""}>${lv}</option>`
                        )
                        .join("")}
                    </select>
                  </div>
                  <div class="run-field run-field-wide">
                    <label class="field-label">${escapeHtml(c.caseDimension)}</label>
                    <select id="case-dimension" ${running || state.caseLoading ? "disabled" : ""}>
                      <option value="">${escapeHtml(c.caseAllDims)}</option>
                      ${dimensionOptionsForSuite()
                        .map(
                          (d) =>
                            `<option value="${escapeHtml(d)}" ${
                              state.caseDimension === d ? "selected" : ""
                            }>${escapeHtml(d)}</option>`
                        )
                        .join("")}
                    </select>
                  </div>
                </div>
                <div class="run-field" style="margin-top:0.75rem">
                  <label class="field-label">${escapeHtml(c.caseSearch)}</label>
                  <input id="case-query" type="search" class="brief-input brief-input-sm" placeholder="${escapeHtml(
                    c.caseSearchPh
                  )}" value="${escapeHtml(state.caseQuery)}" ${running || state.caseLoading ? "disabled" : ""} />
                </div>
                <p class="field-hint">${escapeHtml(
                  (c.caseCount || "").replace("{n}", String(state.caseTotal || 0))
                )}${state.caseMeta?.ok === false ? " · library offline" : ""}</p>
                <label class="field-label">${escapeHtml(c.casePick)}</label>
                <select id="case-pick" size="8" class="case-pick" ${
                  running || state.caseLoading ? "disabled" : ""
                }>
                  ${(state.caseItems || [])
                    .map((it) => {
                      const label = `${it.id} · ${it.title}${it.dimension ? " · " + it.dimension : ""}`;
                      return `<option value="${escapeHtml(it.id)}" ${
                        state.caseSelectedId === it.id ? "selected" : ""
                      }>${escapeHtml(label)}</option>`;
                    })
                    .join("")}
                </select>
                ${
                  !(state.caseItems || []).length
                    ? `<p class="empty-hint">${escapeHtml(c.caseEmpty)}</p>`
                    : selectedCaseHintHtml()
                }
                ${settingsSummaryHtml(c)}
                <div class="stage-actions">
                  <button class="btn-primary" type="button" id="btn-load-case" ${
                    running || state.caseLoading ? "disabled" : ""
                  }>${escapeHtml(c.caseLoad)}</button>
                  <button class="btn-primary" type="button" id="btn-auto" ${
                    running || state.caseLoading ? "disabled" : ""
                  }>${escapeHtml(c.autoRun)}</button>
                  <button class="btn-ghost" type="button" id="btn-demo" ${running ? "disabled" : ""}>${escapeHtml(
                    c.demo
                  )}</button>
                </div>
                <p class="field-hint">${escapeHtml(c.autoHint)}</p>
                <p class="field-hint">${escapeHtml(c.demoHint)}</p>
              </div>`
            : `<label class="field-label">${escapeHtml(c.oral)}</label>
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
        ${settingsSummaryHtml(c)}
        <div class="stage-actions">
          <button class="btn-primary" type="button" id="btn-gen-case" ${running ? "disabled" : ""}>${escapeHtml(
            c.genCase
          )}</button>
          <button class="btn-primary" type="button" id="btn-auto" ${running ? "disabled" : ""}>${escapeHtml(
            c.autoRun
          )}</button>
          <button class="btn-ghost" type="button" id="btn-demo" ${running ? "disabled" : ""}>${escapeHtml(
            c.demo
          )}</button>
        </div>
        <p class="field-hint">${escapeHtml(c.autoHint)}</p>
        <p class="field-hint">${escapeHtml(c.demoHint)}</p>`
        }
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
                  c.nextBaseline
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
            ? `${
                demoFrozen
                  ? `<p class="field-hint">${escapeHtml(c.baselineDemoSkip)}</p>`
                  : ""
              }
              <div class="param-grid">
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.baselineReps)}</label>
                  <div class="rep-pills">${pills(BASELINE_REP_OPTIONS, state.baselineReps, "baselinereps", running)}</div>
                </div>
                <div class="run-field">
                  <label class="field-label">${escapeHtml(c.workers)}</label>
                  <div class="rep-pills">${pills(WORKER_OPTIONS, state.workers, "workers", running)}</div>
                </div>
              </div>
              <div class="stage-actions">
                <button class="btn-primary" type="button" id="btn-baseline" ${
                  running || demoFrozen ? "disabled" : ""
                }>${escapeHtml(c.startBaseline)}</button>
                <button class="btn-ghost" type="button" id="btn-skip-baseline" ${
                  running || demoFrozen ? "disabled" : ""
                }>${escapeHtml(c.skipBaseline)}</button>
                ${
                  hasBaseline ||
                  phase === "baseline_done" ||
                  demoFrozen
                    ? `<button class="btn-primary" type="button" id="btn-goto-4">${escapeHtml(c.nextGenome)}</button>`
                    : ""
                }
              </div>
              ${stageProgressHtml({
                active: isBaselining,
                label: c.startBaseline,
                snap,
                c,
                withAbort: true,
              })}
              ${
                hasBaseline
                  ? `${
                      snap?.baseline_stale
                        ? `<p class="field-hint">${escapeHtml(c.baselineStale)}</p>`
                        : ""
                    }
                    ${
                      baselineRows[0]?.gap_b_minus_a != null
                        ? `<p class="ok-chip">${escapeHtml(c.baselineGap)} · <span class="mono">${
                            baselineRows[0].gap_b_minus_a
                          }</span></p>`
                        : ""
                    }
                    ${summaryTable(baselineRows, c, null)}`
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
            ? `              <div class="stage-actions">
                <button class="btn-primary" type="button" id="btn-gen-genome" ${
                  running || demoFrozen ? "disabled" : ""
                }>${escapeHtml(c.genGenome)}</button>
                ${
                  demoFrozen
                    ? `<span class="ok-chip">${escapeHtml(c.toastDemoPack)}</span>
                       <button class="btn-primary" type="button" id="btn-goto-5">${escapeHtml(c.nextPre)}</button>`
                    : snap?.variants?.length
                      ? `<button class="btn-primary" type="button" id="btn-goto-5">${escapeHtml(c.nextPre)}</button>`
                      : ""
                }
              </div>
              ${stageProgressHtml({
                active: isGenomesBusy,
                label: c.genGenome,
                snap,
                c,
              })}
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

      <section class="panel stage-panel ${focus === 5 ? "is-focus" : ""} ${unlock < 5 ? "stage-locked" : ""}" id="step-panel-5">
        <div class="stage-head">
          <p class="section-kicker">05</p>
          <h2 class="stage-title">${escapeHtml(c.s5)}</h2>
          <p class="stage-help">${unlock < 5 ? escapeHtml(c.locked) : escapeHtml(c.s5help)}</p>
        </div>
        ${
          unlock >= 5
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
              ${stageProgressHtml({
                active: isPrefiltering,
                label: c.startPre,
                snap,
                c,
                withAbort: true,
              })}
              ${
                (snap?.pre_summaries || []).length
                  ? summaryTable(snap.pre_summaries, c, null)
                  : ""
              }`
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

      <section class="panel stage-panel ${focus === 7 ? "is-focus" : ""} ${unlock < 7 ? "stage-locked" : ""}" id="step-panel-7">
        <div class="stage-head">
          <p class="section-kicker">07</p>
          <h2 class="stage-title">${escapeHtml(c.s7)}</h2>
          <p class="stage-help">${unlock < 7 ? escapeHtml(c.locked) : escapeHtml(c.s7help)}</p>
        </div>
        ${
          unlock >= 7
            ? `${stageProgressHtml({
                active: isChampioning,
                label: c.startChamp,
                snap,
                c,
                withAbort: true,
              })}
              ${
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
                  : ""
              }
              ${
                snap?.best_genome
                  ? `<div class="panel-inset best-genome" style="margin-top:1rem">
                      <p class="field-label">${escapeHtml(c.bestGenome)}</p>
                      <p><strong>${escapeHtml(snap.best_genome.title || snap.best_genome.variant_id || "")}</strong>
                        <span class="dim mono"> · ${escapeHtml(snap.best_genome.champion_mark || "")}
                        · ${escapeHtml(snap.best_genome.variant_id || "")}</span></p>
                      ${
                        snap.auto_save?.best_genome_path
                          ? `<p class="field-hint mono">${escapeHtml(c.bestGenomePath)}: ${escapeHtml(
                              snap.auto_save.best_genome_path
                            )}</p>`
                          : ""
                      }
                    </div>`
                  : ""
              }
              ${summaryTable(snap?.champ_summaries, c, snap?.marks)}`
            : ""
        }
      </section>

      ${
        (snap?.logs || []).length
          ? `<section class="panel logs-panel">
              ${tokenUsageHtml(snap?.token_usage, c)}
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
                          .map((l) => {
                            const stageLabel =
                              l.stage === "champ"
                                ? c.s7
                                : l.stage === "baseline"
                                  ? c.s3
                                  : c.s5;
                            return `<tr>
                              <td class="mono">${l.n ?? ""}</td>
                              <td>${escapeHtml(stageLabel)}</td>
                              <td>${escapeHtml(l.title || l.variant_id || "")}</td>
                              <td class="mono">${l.rep ?? ""}/${l.reps ?? ""}</td>
                              <td class="mono">${l.score ?? l.error ?? ""}</td>
                              <td class="mono">${l.mean_so_far ?? ""}</td>
                            </tr>`;
                          })
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
  syncCopyEditor();
}

function wire(running, unlock) {
  document.getElementById("btn-lang")?.addEventListener("click", () => {
    state.lang = state.lang === "zh" ? "en" : "zh";
    const host = document.getElementById("copy-editor");
    if (host) host.dataset.built = "";
    render();
  });
  const openSettings = () => {
    state.settingsOpen = true;
    render();
  };
  const closeSettings = () => {
    readFormIntoState();
    persistSettings();
    state.settingsOpen = false;
    render();
  };
  document.getElementById("btn-settings")?.addEventListener("click", openSettings);
  document.getElementById("btn-open-settings")?.addEventListener("click", openSettings);
  document.getElementById("btn-close-settings")?.addEventListener("click", closeSettings);
  document.getElementById("btn-save-settings")?.addEventListener("click", () => {
    readFormIntoState();
    persistSettings();
    state.settingsOpen = false;
    showToast(t().toastSaved);
    render();
  });
  document.getElementById("settings-backdrop")?.addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeSettings();
  });
  document.querySelectorAll("[data-champion-mark]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (running) return;
      state.championMark = btn.getAttribute("data-champion-mark") || "balanced";
      persistSettings();
      render();
    });
  });
  document.getElementById("btn-reset")?.addEventListener("click", onReset);
  document.getElementById("btn-save-run")?.addEventListener("click", () => onSaveRun(false));
  document.getElementById("btn-freeze-demo")?.addEventListener("click", () => onSaveRun(true));
  document.getElementById("btn-gen-case")?.addEventListener("click", onGenCase);
  document.getElementById("btn-load-case")?.addEventListener("click", onLoadLibraryCase);
  document.getElementById("btn-auto")?.addEventListener("click", onAutoRun);
  document.getElementById("btn-demo")?.addEventListener("click", onDemo);
  document.getElementById("btn-save-case")?.addEventListener("click", onSaveCase);
  document.getElementById("btn-baseline")?.addEventListener("click", onBaseline);
  document.getElementById("btn-skip-baseline")?.addEventListener("click", onSkipBaseline);
  document.getElementById("btn-gen-genome")?.addEventListener("click", onGenGenomes);
  document.getElementById("btn-pre")?.addEventListener("click", onPrefilter);
  document.getElementById("btn-abort")?.addEventListener("click", onAbort);
  document.querySelectorAll("[data-abort-inline]").forEach((btn) => {
    btn.addEventListener("click", onAbort);
  });
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
  document.getElementById("btn-jump-baseline")?.addEventListener("click", () => {
    state.focusStep = 3;
    render();
    scrollToStep(3);
  });
  document.getElementById("btn-goto-5")?.addEventListener("click", () => {
    state.focusStep = 5;
    render();
    scrollToStep(5);
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
      const list = oralExamplesList();
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
    persistSettings();
  });
  document.getElementById("provider-select")?.addEventListener("change", (e) => {
    // Save current key under old provider before switching
    const prev = state.provider;
    if (prev && state.apiKey) {
      state.apiKeys[prev] = state.apiKey;
    }
    state.provider = e.target.value;
    const models = modelCatalog().filter((m) => m.provider === state.provider);
    state.model = models[0]?.id || state.model;
    syncActiveApiKey();
    persistSettings();
    render();
  });
  document.getElementById("model-select")?.addEventListener("change", (e) => {
    state.model = e.target.value;
    const meta = selectedModelMeta();
    if (meta?.provider) state.provider = meta.provider;
    persistSettings();
    render();
  });
  document.querySelectorAll("[data-case-source]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.caseSource = btn.getAttribute("data-case-source") || "library";
      state.error = null;
      render();
      if (state.caseSource === "library") await refreshCaseLibrary();
    });
  });
  document.getElementById("case-suite")?.addEventListener("change", async (e) => {
    state.caseSuite = e.target.value;
    state.caseSelectedId = "";
    await refreshCaseLibrary();
  });
  document.getElementById("case-dimension")?.addEventListener("change", async (e) => {
    state.caseDimension = e.target.value;
    state.caseSelectedId = "";
    await refreshCaseLibrary();
  });
  document.getElementById("case-level")?.addEventListener("change", (e) => {
    state.caseLevel = e.target.value;
  });
  document.getElementById("case-pick")?.addEventListener("change", (e) => {
    state.caseSelectedId = e.target.value;
    render();
  });
  document.getElementById("case-query")?.addEventListener("input", (e) => {
    state.caseQuery = e.target.value;
    clearTimeout(_caseQueryTimer);
    _caseQueryTimer = setTimeout(() => refreshCaseLibrary(), 280);
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
      persistSettings();
      render();
    })
  );
  document.querySelectorAll("[data-baselinereps]").forEach((btn) =>
    btn.addEventListener("click", () => {
      if (running) return;
      state.baselineReps = Number(btn.dataset.baselinereps);
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

function toggleCopyEditor(force) {
  state.copyEditOpen = typeof force === "boolean" ? force : !state.copyEditOpen;
  const host = document.getElementById("copy-editor");
  if (host) host.dataset.built = "";
  render();
}

async function boot() {
  try {
    const modelsResp = await fetch("/api/models").then((r) => r.json());
    state.models = modelsResp.models || [];
  } catch {
    state.models = [
      {
        id: "kimi-k2.5",
        label: "Kimi K2.5",
        provider: "kimi",
        provider_label: "Kimi 开放平台",
        key_hint: "Kimi 开放平台 Key (platform.kimi.com)",
      },
      {
        id: "kimi-k2.6",
        label: "Kimi K2.6",
        provider: "kimi",
        provider_label: "Kimi 开放平台",
        key_hint: "Kimi 开放平台 Key (platform.kimi.com)",
      },
      {
        id: "plan/k3",
        label: "Kimi 3",
        provider: "kimi-plan",
        provider_label: "Kimi Plan",
        key_hint: "Kimi Plan Key",
      },
    ];
  }
  ensureProviderModel();
  persistSettings();
  // Hidden copy editor: Ctrl/⌘+Shift+E, or ?copyEdit=1
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "E" || e.key === "e")) {
      e.preventDefault();
      toggleCopyEditor();
    }
  });
  try {
    if (new URLSearchParams(location.search).get("copyEdit") === "1") {
      state.copyEditOpen = true;
    }
  } catch {
    /* ignore */
  }
  render();
  if (state.caseSource === "library") {
    refreshCaseLibrary().catch(() => {});
  }
}

boot();
