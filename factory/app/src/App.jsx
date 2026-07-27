import { useEffect, useMemo, useState } from "react";

const SLOT_ORDER = ["G1", "G2", "G3", "G4", "G5"];

const copy = {
  zh: {
    brand: "YiAgent",
    brandSub: "基因级 Agent",
    lang: "EN",
    hook: "别人调 prompt；我们改基因组，并用分槽鉴定决定晋升。",
    hookEn: "They tune prompts. We edit the genome — and promote only with a slot-level verdict.",
    enter: "进入工厂",
    pipeline: ["取基因", "组装载体", "导入", "检测鉴定"],
    roleKicker: "Step 01 · 任务卡",
    roleTitle: "选一场鉴定主戏",
    roleLead: "客户向主戏用批判思维——基线易翻车，基因骨架抬分与收波动最戏剧。",
    continue: "继续组装",
    primaryTag: "主戏 · XSCT 真分",
    sideTag: "附表",
    factoryKicker: "Step 02 · 工厂",
    factoryTitle: "并排出基因组变体",
    factoryLead: "G1 身份固定；交叉 G2 边界、G4 能力、G5 经验。每一个可哈希、可追踪。",
    assembling: "正在装配等位基因…",
    runDuel: "开始对决鉴定",
    duelKicker: "Step 03 · 对决",
    duelTitle: "分槽打分，不只总分",
    duelLead: "同一题、同一裁判口径。回答：该不该晋升？强在哪一段基因？",
    vsBaseline: "相对基线",
    mean: "均值",
    sd: "标准差",
    toVerdict: "进入裁决仪式",
    verdictKicker: "Step 04 · 裁决",
    verdictTitle: "晋升门禁三态",
    verdictLead: "没有这一步，就不叫基因工程——只是随机改配置。",
    promote: "晋升",
    reject: "驳回",
    noise: "噪声不足",
    toCompare: "看 A vs C 收束",
    compareKicker: "Step 05 · 收束",
    compareTitle: "基线 vs 基因骨架",
    compareLead: "分区基因骨架 ≠ 把评分标准整份塞进 prompt。",
    baseline: "基线 A",
    genome: "基因骨架 C",
    restart: "再跑一遍",
    disclaimer:
      "主戏 A/C 总分为 XSCT 已公布跑次。其余变体分为仪式编排。分槽条为评分维→槽映射演示，非独立槽裁判实测。",
    provenanceReal: "XSCT 已公布",
    provenanceDemo: "仪式编排",
    incumbent: "Incumbent · 基线",
  },
  en: {
    brand: "YiAgent",
    brandSub: "Gene-Level Agent",
    lang: "中文",
    hook: "They tune prompts. We edit the genome — and promote only with a slot-level verdict.",
    hookEn: "别人调 prompt；我们改基因组，并用分槽鉴定决定晋升。",
    enter: "Enter the factory",
    pipeline: ["Extract genes", "Assemble vector", "Transfect", "Assay & promote"],
    roleKicker: "Step 01 · Task",
    roleTitle: "Pick the assay",
    roleLead: "Critical thinking is the customer-facing lead: baseline variance collapses under a gene skeleton.",
    continue: "Assemble genomes",
    primaryTag: "Lead · published XSCT",
    sideTag: "Annex",
    factoryKicker: "Step 02 · Factory",
    factoryTitle: "Emit genome variants",
    factoryLead: "G1 fixed; cross G2 / G4 / G5. Every candidate is hashable.",
    assembling: "Assembling alleles…",
    runDuel: "Run the duel",
    duelKicker: "Step 03 · Duel",
    duelTitle: "Slot bars, not just a total",
    duelLead: "Same task, same judge scale. Should it promote? Which gene slot got stronger?",
    vsBaseline: "vs baseline",
    mean: "mean",
    sd: "sd",
    toVerdict: "Open the gate",
    verdictKicker: "Step 04 · Verdict",
    verdictTitle: "Three gate outcomes",
    verdictLead: "Skip this step and it is not gene engineering — just random config edits.",
    promote: "PROMOTE",
    reject: "REJECT",
    noise: "NOISE",
    toCompare: "Baseline vs gene",
    compareKicker: "Step 05 · Close",
    compareTitle: "Baseline vs gene skeleton",
    compareLead: "A partitioned genome ≠ stuffing the full rubric into the prompt.",
    baseline: "Baseline A",
    genome: "Gene skeleton C",
    restart: "Run again",
    disclaimer:
      "Primary A/C totals are published XSCT trials. Other variant scores are ritual orchestration. Slot bars are dimension→slot demos, not independent slot judges.",
    provenanceReal: "XSCT published",
    provenanceDemo: "Orchestrated",
    incumbent: "Incumbent · baseline",
  },
};

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export default function App() {
  const [lang, setLang] = useState("zh");
  const t = copy[lang];
  const [step, setStep] = useState("splash");
  const [bank, setBank] = useState(null);
  const [run, setRun] = useState(null);
  const [script, setScript] = useState(null);
  const [assembled, setAssembled] = useState(0);
  const [activeVariant, setActiveVariant] = useState(null);
  const [barsOn, setBarsOn] = useState(false);
  const [verdictFocus, setVerdictFocus] = useState("promote");

  useEffect(() => {
    Promise.all([
      fetch("/fixtures/alleles/bank.json").then((r) => r.json()),
      fetch("/fixtures/scorecards/demo_run.json").then((r) => r.json()),
      fetch("/fixtures/scorecards/verdict_script.json").then((r) => r.json()),
    ]).then(([b, s, v]) => {
      setBank(b);
      setRun(s);
      setScript(v);
    });
  }, []);

  const resultsById = useMemo(() => {
    if (!run) return {};
    return Object.fromEntries(run.variant_results.map((r) => [r.variant_id, r]));
  }, [run]);

  const primaryCase = run?.cases?.find((c) => c.primary);

  useEffect(() => {
    if (step !== "factory" || !bank) return;
    setAssembled(0);
    let cancelled = false;
    (async () => {
      for (let i = 1; i <= bank.variants.length; i++) {
        await sleep(220);
        if (cancelled) return;
        setAssembled(i);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, bank]);

  useEffect(() => {
    if (step !== "duel" || !run) return;
    const first = run.variant_results.find((r) => r.variant_id === "var.champion") || run.variant_results[0];
    setActiveVariant(first.variant_id);
    setBarsOn(false);
    const id = requestAnimationFrame(() => setBarsOn(true));
    return () => cancelAnimationFrame(id);
  }, [step, run]);

  useEffect(() => {
    if (step !== "verdict" || !script) return;
    setVerdictFocus("promote");
  }, [step, script]);

  if (!bank || !run || !script) {
    return (
      <div className="app-shell">
        <div className="loading">loading factory fixtures…</div>
      </div>
    );
  }

  const activeResult = resultsById[activeVariant] || run.variant_results[0];
  const delta = (activeResult.mean - run.incumbent.mean).toFixed(1);

  const spotlight = {
    promote: resultsById["var.champion"],
    reject: resultsById["var.reject_regress"],
    noise: resultsById["var.noise"],
  };
  const stampResult = spotlight[verdictFocus];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">
          Yi<span>Agent</span> · {t.brandSub}
        </div>
        <button className="lang-toggle" type="button" onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
          {t.lang}
        </button>
      </header>

      <main className="stage">
        {step === "splash" && (
          <section className="hero">
            <h1 className="hero-brand">
              Yi<em>Agent</em>
            </h1>
            <p className="hook">{t.hook}</p>
            <p className="hook-en">{t.hookEn}</p>
            <div className="pipeline">
              {t.pipeline.map((p) => (
                <span key={p}>{p}</span>
              ))}
            </div>
            <div className="cta-row">
              <button className="btn-primary" type="button" onClick={() => setStep("role")}>
                {t.enter}
              </button>
            </div>
          </section>
        )}

        {step === "role" && (
          <section>
            <p className="section-kicker">{t.roleKicker}</p>
            <h2 className="section-title">{t.roleTitle}</h2>
            <p className="section-lead">{t.roleLead}</p>
            <div className="task-grid">
              {run.cases.map((c) => (
                <div key={c.id} className={`task-option ${c.primary ? "active" : ""}`}>
                  <strong>{c.title}</strong>
                  <p>
                    A {c.A.mean.toFixed(1)} → C {c.C.mean.toFixed(1)} · sd {c.A.sd.toFixed(2)} →{" "}
                    {c.C.sd.toFixed(2)}
                  </p>
                  <span className="tag">{c.primary ? t.primaryTag : t.sideTag}</span>
                </div>
              ))}
            </div>
            <div className="cta-row">
              <button className="btn-primary" type="button" onClick={() => setStep("factory")}>
                {t.continue}
              </button>
              <button className="btn-ghost" type="button" onClick={() => setStep("splash")}>
                ←
              </button>
            </div>
          </section>
        )}

        {step === "factory" && (
          <section>
            <p className="section-kicker">{t.factoryKicker}</p>
            <h2 className="section-title">{t.factoryTitle}</h2>
            <p className="section-lead">{t.factoryLead}</p>
            <div className="assemble-meter" aria-hidden>
              <i />
            </div>
            <p className="score-meta" style={{ marginBottom: "0.75rem" }}>
              {t.assembling} {assembled}/{bank.variants.length}
            </p>
            <div className="factory-rail">
              {bank.variants.slice(0, assembled).map((v, idx) => (
                <div
                  key={v.id}
                  className="variant-row"
                  style={{ animationDelay: `${idx * 0.05}s` }}
                >
                  <div className="variant-hash">{v.hash}</div>
                  <div>
                    <div className="variant-title">{v.title}</div>
                    <div className="slot-chips">
                      {SLOT_ORDER.map((s) => (
                        <span key={s}>
                          {s}:{v.slots[s].split(".").slice(-1)[0]}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="score-meta">{v.role_in_demo}</div>
                </div>
              ))}
            </div>
            <div className="cta-row" style={{ marginTop: "1.5rem" }}>
              <button
                className="btn-primary"
                type="button"
                disabled={assembled < bank.variants.length}
                onClick={() => setStep("duel")}
              >
                {t.runDuel}
              </button>
            </div>
          </section>
        )}

        {step === "duel" && (
          <section>
            <p className="section-kicker">{t.duelKicker}</p>
            <h2 className="section-title">{t.duelTitle}</h2>
            <p className="section-lead">{t.duelLead}</p>
            <div className="duel-layout">
              <div className="score-board">
                <div className="score-meta">{activeResult.label}</div>
                <div className="score-big">{activeResult.mean.toFixed(1)}</div>
                <div className="score-meta">
                  {t.mean} · {t.sd} {activeResult.sd.toFixed(2)} · {t.vsBaseline}{" "}
                  {delta >= 0 ? "+" : ""}
                  {delta}
                </div>
                <div className="score-meta" style={{ marginTop: "0.35rem" }}>
                  {activeResult.provenance === "xsct_published" ? t.provenanceReal : t.provenanceDemo}
                </div>
                <div className="slot-bars">
                  {SLOT_ORDER.map((s) => {
                    const val = activeResult.slots[s];
                    const base = run.incumbent.slots[s];
                    return (
                      <div className="slot-row" key={s}>
                        <span>{s}</span>
                        <div className="bar-track">
                          <div
                            className={`bar-fill ${val >= base ? "" : "warm"}`}
                            style={{ width: barsOn ? `${val}%` : "0%" }}
                          />
                        </div>
                        <span>{val}</span>
                      </div>
                    );
                  })}
                </div>
                <p className="disclaimer">{t.disclaimer}</p>
              </div>
              <div className="variant-list">
                <div className="variant-pill" style={{ opacity: 0.7 }}>
                  <span>{t.incumbent}</span>
                  <span className="mean">{run.incumbent.mean.toFixed(1)}</span>
                </div>
                {run.variant_results.map((r) => (
                  <button
                    key={r.variant_id}
                    type="button"
                    className={`variant-pill ${activeVariant === r.variant_id ? "active" : ""}`}
                    onClick={() => {
                      setBarsOn(false);
                      setActiveVariant(r.variant_id);
                      requestAnimationFrame(() => setBarsOn(true));
                    }}
                  >
                    <span>{r.label}</span>
                    <span className="mean">{r.mean.toFixed(1)}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="cta-row" style={{ marginTop: "1.5rem" }}>
              <button className="btn-primary" type="button" onClick={() => setStep("verdict")}>
                {t.toVerdict}
              </button>
            </div>
          </section>
        )}

        {step === "verdict" && stampResult && (
          <section>
            <p className="section-kicker">{t.verdictKicker}</p>
            <h2 className="section-title">{t.verdictTitle}</h2>
            <p className="section-lead">{t.verdictLead}</p>
            <div className="verdict-tabs">
              {["promote", "reject", "noise"].map((k) => (
                <button
                  key={k}
                  type="button"
                  className={verdictFocus === k ? "active" : ""}
                  onClick={() => setVerdictFocus(k)}
                >
                  {t[k]}
                </button>
              ))}
            </div>
            <div className="verdict-stage" key={verdictFocus}>
              <div className={`stamp ${verdictFocus}`}>{t[verdictFocus]}</div>
              <p className="score-meta" style={{ marginTop: "1rem" }}>
                {stampResult.label} · mean {stampResult.mean.toFixed(1)}
              </p>
              <p className="verdict-reason">{stampResult.reason}</p>
            </div>
            <div className="cta-row" style={{ justifyContent: "center" }}>
              <button className="btn-primary" type="button" onClick={() => setStep("compare")}>
                {t.toCompare}
              </button>
            </div>
          </section>
        )}

        {step === "compare" && primaryCase && (
          <section>
            <p className="section-kicker">{t.compareKicker}</p>
            <h2 className="section-title">{t.compareTitle}</h2>
            <p className="section-lead">{t.compareLead}</p>
            <div className="compare-grid">
              <div className="compare-card">
                <h3>{t.baseline}</h3>
                <div className="num">{primaryCase.A.mean.toFixed(1)}</div>
                <div className="sd">
                  {t.sd} {primaryCase.A.sd.toFixed(2)} · n=5 · XSCT
                </div>
              </div>
              <div className="compare-card win">
                <h3>{t.genome}</h3>
                <div className="num">{primaryCase.C.mean.toFixed(1)}</div>
                <div className="sd">
                  {t.sd} {primaryCase.C.sd.toFixed(2)} · n=5 · XSCT
                </div>
              </div>
            </div>
            <div className="side-cases">
              {run.cases
                .filter((c) => !c.primary)
                .map((c) => (
                  <div className="side-case" key={c.id}>
                    <div>
                      {c.title} · A {c.A.mean.toFixed(1)} → C {c.C.mean.toFixed(1)}
                    </div>
                    <span>
                      sd {c.A.sd.toFixed(2)} → {c.C.sd.toFixed(2)}
                    </span>
                  </div>
                ))}
            </div>
            <p className="footer-note">{run.disclaimer}</p>
            <div className="cta-row">
              <button
                className="btn-primary"
                type="button"
                onClick={() => {
                  setAssembled(0);
                  setStep("splash");
                }}
              >
                {t.restart}
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

