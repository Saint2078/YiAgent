#!/usr/bin/env node
/**
 * CEO 工作台 · Agent bridge（DEC-044）
 * Compose 容器内跑 SDK/API；工作目录 bind-mount → /workbench；密钥挂宿主机文件。
 */
import http from "node:http";
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Agent, CursorAgentError } from "@cursor/sdk";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ENV_PATH = path.join(__dirname, ".env");
const PROVIDERS_PATH = path.join(__dirname, "providers.json");

const PROVIDER_CATALOG = [
  {
    id: "cursor",
    name: "Cursor",
    kind: "agent_sdk",
    wired: true,
    docsUrl: "https://cursor.com/dashboard/api",
    help: "User API Key · Dashboard → API Keys",
    models: ["composer-2.5", "auto"],
    keyEnv: "CURSOR_API_KEY",
  },
  {
    id: "kimi",
    name: "Kimi / Moonshot",
    kind: "llm",
    wired: true,
    docsUrl: "https://platform.moonshot.cn/",
    help: "开发技术席默认 · 模型 kimi-k3 · Key 可读 IT 资产 kimi-coding-plan.key",
    models: ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
    keyEnv: "KIMI_API_KEY",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    kind: "llm",
    wired: false,
    docsUrl: "https://console.anthropic.com/",
    help: "API Key 可存 · 本桥未接线",
    models: ["claude-sonnet-4", "claude-opus-4"],
    keyEnv: "ANTHROPIC_API_KEY",
  },
  {
    id: "openai",
    name: "OpenAI",
    kind: "llm",
    wired: false,
    docsUrl: "https://platform.openai.com/api-keys",
    help: "API Key 可存 · 本桥未接线",
    models: ["gpt-4.1", "gpt-4o"],
    keyEnv: "OPENAI_API_KEY",
  },
];

function loadEnvFile() {
  if (!fs.existsSync(ENV_PATH)) return;
  for (const line of fs.readFileSync(ENV_PATH, "utf8").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i <= 0) continue;
    const k = t.slice(0, i).trim();
    let v = t.slice(i + 1).trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    if (!(k in process.env)) process.env[k] = v;
  }
}

loadEnvFile();

const HOST = process.env.HOST || "0.0.0.0";
const PORT = Number(process.env.PORT || 8091);

function resolveDefaultCwd() {
  if (process.env.WORKBENCH_CWD) return path.resolve(process.env.WORKBENCH_CWD);
  if (fs.existsSync("/workbench")) return "/workbench";
  /** 宿主机调试：cursor-bridge → demo-ceo-console → v1 → engineering → 方案仓根 */
  return path.resolve(__dirname, "../../../..");
}

/** @type {{ cwd: string, model: string, kimiModel: string, activeProvider: string, keys: Record<string, string> }} */
let runtime = {
  cwd: resolveDefaultCwd(),
  model: process.env.MODEL || "composer-2.5",
  kimiModel: process.env.KIMI_MODEL || "kimi-k3",
  activeProvider: "cursor",
  keys: {},
};

/** 开发席默认 Provider：技术席 Kimi3，其余 Cursor */
const ROLE_PROVIDER = {
  Architect: "kimi",
  Dev: "kimi",
  DevOps: "kimi",
  Product: "cursor",
  PM: "cursor",
};

/** Coding Plan Key（sk-kimi-…）须走 coding 端点，与 Open Platform 不互通 */
const KIMI_BASE_URL = (process.env.KIMI_BASE_URL || "https://api.kimi.com/coding/v1").replace(
  /\/+$/,
  ""
);

function loadProvidersFile() {
  try {
    if (!fs.existsSync(PROVIDERS_PATH)) return;
    const raw = JSON.parse(fs.readFileSync(PROVIDERS_PATH, "utf8"));
    // 忽略不存在的宿主机旧路径（容器内以 WORKBENCH_CWD=/workbench 为准）
    if (raw.cwd) {
      const resolved = path.resolve(raw.cwd);
      if (fs.existsSync(resolved)) runtime.cwd = resolved;
    }
    if (raw.model) runtime.model = String(raw.model);
    if (raw.activeProvider) runtime.activeProvider = String(raw.activeProvider);
    if (raw.keys && typeof raw.keys === "object") {
      for (const [k, v] of Object.entries(raw.keys)) {
        if (typeof v === "string" && v.trim()) runtime.keys[k] = v.trim();
      }
    }
  } catch (e) {
    console.warn("[cursor-bridge] providers.json load failed:", e?.message || e);
  }
}

function saveProvidersFile() {
  const body = {
    cwd: runtime.cwd,
    model: runtime.model,
    activeProvider: runtime.activeProvider,
    keys: runtime.keys,
    updatedAt: new Date().toISOString(),
  };
  fs.writeFileSync(PROVIDERS_PATH, JSON.stringify(body, null, 2), "utf8");
}

function syncEnvKey(envName, value) {
  let lines = [];
  if (fs.existsSync(ENV_PATH)) {
    lines = fs.readFileSync(ENV_PATH, "utf8").split("\n");
  } else if (fs.existsSync(path.join(__dirname, ".env.example"))) {
    lines = fs.readFileSync(path.join(__dirname, ".env.example"), "utf8").split("\n");
  }
  let found = false;
  const next = lines.map((line) => {
    if (/^\s*#/.test(line) || !line.includes("=")) return line;
    const i = line.indexOf("=");
    const k = line.slice(0, i).trim();
    if (k !== envName) return line;
    found = true;
    return `${envName}=${value}`;
  });
  if (!found) next.push(`${envName}=${value}`);
  fs.writeFileSync(ENV_PATH, next.join("\n").replace(/\n*$/, "\n"), "utf8");
  process.env[envName] = value;
}

function maskKey(key) {
  const s = String(key || "");
  if (!s) return "";
  if (s.length <= 8) return "••••";
  return `${s.slice(0, 4)}…${s.slice(-4)}`;
}

function getProviderKey(id) {
  if (runtime.keys[id]) return runtime.keys[id];
  const cat = PROVIDER_CATALOG.find((p) => p.id === id);
  if (!cat?.keyEnv) return "";
  return (process.env[cat.keyEnv] || "").trim();
}

function setProviderKey(id, key) {
  const cat = PROVIDER_CATALOG.find((p) => p.id === id);
  if (!cat) throw Object.assign(new Error("unknown provider"), { code: "NO_PROVIDER" });
  const v = String(key || "").trim();
  if (!v) throw Object.assign(new Error("apiKey required"), { code: "BAD_KEY" });
  runtime.keys[id] = v;
  if (cat.keyEnv) syncEnvKey(cat.keyEnv, v);
  saveProvidersFile();
  if (id === "cursor") agentSessions.clear();
}

function clearProviderKey(id) {
  const cat = PROVIDER_CATALOG.find((p) => p.id === id);
  if (!cat) throw Object.assign(new Error("unknown provider"), { code: "NO_PROVIDER" });
  delete runtime.keys[id];
  if (cat.keyEnv) {
    syncEnvKey(cat.keyEnv, "");
    delete process.env[cat.keyEnv];
  }
  saveProvidersFile();
  if (id === "cursor") agentSessions.clear();
}

function listProviders() {
  return PROVIDER_CATALOG.map((p) => {
    const key = getProviderKey(p.id);
    return {
      id: p.id,
      name: p.name,
      kind: p.kind,
      wired: p.wired,
      docsUrl: p.docsUrl,
      help: p.help,
      models: p.models,
      hasKey: Boolean(key),
      keyHint: maskKey(key),
      enabled: p.id === runtime.activeProvider,
      model: p.id === "cursor" ? runtime.model : p.models?.[0] || "",
    };
  });
}

/** IT 资产正本目录（工作台挂载）· 公司资产页可读明文 */
const IT_SECRET_CATALOG = [
  {
    id: "KEY-CURSOR",
    name: "Cursor API",
    provider: "cursor",
    file: "cursor-api.key",
    role: "Agent SDK / Dashboard API Key",
    tags: ["API", "Cursor"],
  },
  {
    id: "KEY-KIMI",
    name: "Kimi Coding Plan",
    provider: "kimi",
    file: "kimi-coding-plan.key",
    role: "Moonshot / Kimi Coding Plan",
    tags: ["API", "Kimi"],
  },
];

function itSecretsDir() {
  return path.join(runtime.cwd || "/workbench", "公司资产", "IT资产");
}

function listItSecrets() {
  const dir = itSecretsDir();
  return IT_SECRET_CATALOG.map((item) => {
    const abs = path.join(dir, item.file);
    const rel = path.posix.join("公司资产", "IT资产", item.file);
    let value = "";
    let present = false;
    try {
      if (fs.existsSync(abs)) {
        value = fs.readFileSync(abs, "utf8").trim();
        present = Boolean(value);
      }
    } catch (e) {
      console.warn("[cursor-bridge] it-secret read failed:", item.file, e?.message || e);
    }
    return {
      id: item.id,
      name: item.name,
      kind: "api_key",
      provider: item.provider,
      role: item.role,
      tags: item.tags,
      file: item.file,
      path: rel,
      absPath: abs,
      present,
      keyHint: maskKey(value),
      value,
    };
  });
}

loadProvidersFile();
// seed cursor key from env if providers.json empty
if (!runtime.keys.cursor) {
  const fromEnv = (process.env.CURSOR_API_KEY || "").trim();
  if (fromEnv) runtime.keys.cursor = fromEnv;
}

function seedKeysFromItAssets() {
  const dir = path.join(runtime.cwd, "公司资产", "IT资产");
  const map = [
    ["cursor", "cursor-api.key", "CURSOR_API_KEY"],
    ["kimi", "kimi-coding-plan.key", "KIMI_API_KEY"],
  ];
  for (const [id, file, envName] of map) {
    if (runtime.keys[id]) continue;
    const abs = path.join(dir, file);
    try {
      if (!fs.existsSync(abs)) continue;
      const v = fs.readFileSync(abs, "utf8").trim();
      if (!v) continue;
      runtime.keys[id] = v;
      if (!process.env[envName]) process.env[envName] = v;
      console.log(`[cursor-bridge] seeded ${id} key from 公司资产/IT资产/${file}`);
    } catch (e) {
      console.warn(`[cursor-bridge] seed ${id} failed:`, e?.message || e);
    }
  }
  if (!runtime.keys.kimi) {
    const fromEnv = (process.env.KIMI_API_KEY || process.env.MOONSHOT_API_KEY || "").trim();
    if (fromEnv) runtime.keys.kimi = fromEnv;
  }
}
seedKeysFromItAssets();

/** @type {Map<string, { agentId: string, cwd: string }>} agentKey → session */
const agentSessions = new Map();
let sendChain = Promise.resolve();

const DEVELOP_ROLES = ["Product", "PM", "Architect", "Dev", "DevOps", "Evals"];
const PROJECT_BRIEF_FILES = ["项目信息.md", "项目计划.md", "项目登记.md"];

function agentDirName(name) {
  const s = String(name || "Agent")
    .replace(/[\\/]/g, "_")
    .replace(/\0/g, "")
    .trim();
  return s || "Agent";
}

function todayYmd() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function projectChannelRoot(projectAbs) {
  return path.join(projectAbs, "频道");
}

function projectAgentDir(projectAbs, agentName) {
  return path.join(projectChannelRoot(projectAbs), "Agents", agentDirName(agentName));
}

function developRoleDir(role, projectFolder = null) {
  if (projectFolder) {
    return path.join(runtime.cwd, projectFolder, "频道", "Agents", agentDirName(role));
  }
  return path.join(runtime.cwd, "AgentTeam", "Develop", role);
}

function legacyDevelopRoleDir(role, projectFolder) {
  return path.join(runtime.cwd, projectFolder, "AgentTeam", "Develop", role);
}

function resolveProjectAbs(projectFolder) {
  const folder = String(projectFolder || "").replace(/^\/+/, "").trim();
  if (!folder.startsWith("项目/")) {
    const err = new Error("projectFolder 必须落在 项目/ 下");
    err.code = "BAD_PROJECT";
    throw err;
  }
  const abs = path.resolve(runtime.cwd, folder);
  const root = path.resolve(runtime.cwd, "项目");
  if (abs !== root && !abs.startsWith(root + path.sep)) {
    const err = new Error("非法项目路径");
    err.code = "BAD_PROJECT";
    throw err;
  }
  if (!fs.existsSync(abs)) {
    const err = new Error(`项目文件夹不存在：${folder}`);
    err.code = "NO_PROJECT";
    throw err;
  }
  return abs;
}

/** 从项目计划抽出「当期里程碑」等节奏板，避免整文截断后丢失 */
function extractMilestonePin(projectAbs, { maxChars = 4500 } = {}) {
  const planPath = path.join(projectAbs, "项目计划.md");
  if (!fs.existsSync(planPath)) return "";
  let text = "";
  try {
    text = fs.readFileSync(planPath, "utf8");
  } catch {
    return "";
  }
  const startRe = /#{2,3}\s*[^\n]*当期里程碑[^\n]*/;
  const m = text.match(startRe);
  if (!m) {
    // 回退：含 M0/M1 表的片段
    const i = text.search(/\|\s*\*?\*?M0\*?\*?/);
    if (i < 0) return "";
    let slice = text.slice(Math.max(0, i - 200), i + maxChars);
    if (slice.length >= maxChars) slice = slice.slice(0, maxChars) + "\n…(截断)";
    return slice.trim();
  }
  const start = text.indexOf(m[0]);
  let end = text.length;
  const rest = text.slice(start + m[0].length);
  const nextH2 = rest.search(/\n##\s+/);
  if (nextH2 >= 0) end = start + m[0].length + nextH2;
  let block = text.slice(start, end).trim();
  if (block.length > maxChars) block = block.slice(0, maxChars) + "\n…(截断)";
  return block;
}

function loadProjectBrief(projectAbs, { maxChars = 10000 } = {}) {
  const parts = [];
  let budget = maxChars;
  // 计划优先（含里程碑），再信息/登记
  const order = ["项目计划.md", "项目信息.md", "项目登记.md"];
  for (const name of order) {
    if (budget <= 200) break;
    const file = path.join(projectAbs, name);
    if (!fs.existsSync(file)) continue;
    try {
      let text = fs.readFileSync(file, "utf8").trim();
      if (!text) continue;
      // 单文件上限：计划多留，信息/登记少留
      const perFile = name === "项目计划.md" ? Math.min(budget, 7000) : Math.min(budget, 2000);
      if (text.length > perFile) text = text.slice(0, perFile) + "\n…(截断)";
      parts.push(`### ${name}\n${text}`);
      budget -= text.length;
    } catch {
      /* ignore */
    }
  }
  const researchDir = path.join(projectAbs, "项目调研");
  if (budget > 400 && fs.existsSync(researchDir)) {
    try {
      const names = fs
        .readdirSync(researchDir)
        .filter((n) => n.endsWith(".md") && n !== "README.md")
        .sort()
        .slice(0, 5);
      if (names.length) {
        parts.push(`### 项目调研/（文件名索引）\n${names.map((n) => `- ${n}`).join("\n")}`);
      }
    } catch {
      /* ignore */
    }
  }
  return parts.join("\n\n");
}

/** 把正本里程碑摘要写回本席上下文.md，避免下一轮只靠对话尾 */
function syncContextMilestonePin(projectAbs, agentName, milestonePin) {
  if (!milestonePin) return false;
  const file = path.join(projectAgentDir(projectAbs, agentName), "上下文.md");
  const digest = milestonePin
    .split("\n")
    .filter((l) => l.includes("M0") || l.includes("M1") || l.includes("M2") || l.includes("W1") || l.includes("状态") || l.startsWith("| **M"))
    .slice(0, 12)
    .join("\n");
  const bullet =
    `- ${todayYmd()}：当期里程碑以 \`项目计划.md\`「当期里程碑」为单一事实源（自动同步）。\n` +
    (digest ? `${digest}\n` : "");
  try {
    let cur = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : defaultContextMd({ title: path.basename(projectAbs), role: agentName });
    if (/## 最近要点/.test(cur)) {
      cur = cur.replace(
        /## 最近要点\n+([\s\S]*?)(?=\n## |\n*$)/,
        `## 最近要点\n\n${bullet}\n`
      );
    } else {
      cur = cur.trimEnd() + `\n\n## 最近要点\n\n${bullet}\n`;
    }
    fs.writeFileSync(file, cur, "utf8");
    return true;
  } catch (e) {
    console.warn("[cursor-bridge] sync context milestone failed:", e?.message || e);
    return false;
  }
}

function applyProjectGenomeOverlay(genome, { projectId, projectFolder, title, role }) {
  const display = genome.display_name || role;
  const agentPath = `${projectFolder}/频道/Agents/${agentDirName(role)}`;
  genome.projectId = projectId;
  genome.projectFolder = projectFolder;
  genome.projectTitle = title || "";
  genome.path = agentPath;
  genome.scope = "project";
  genome.notes = `项目「${title || projectId}」频道席 · 写仅 ${projectFolder} · 战略等只读外参（DEC-047）`;
  if (!genome.slots) genome.slots = {};
  genome.slots.G1 = {
    key: "identity",
    label: "身份",
    text:
      `role_id: ${String(role).toLowerCase().replace(/\s+/g, "_")}\n` +
      `显示名: ${display}\n` +
      `编队: 项目「${title || projectId}」· 项目频道\n` +
      `自报: ${title || projectId} · ${display}\n` +
      `工作区: ${projectFolder}\n` +
      `承接: ${agentPath}/上下文.md · 对话/\n` +
      `禁止: 把本对话当成 OPC 架构方案仓或其它项目的工作上下文`,
  };
  const g3base = String(genome.slots.G3?.text || "").replace(/\n\n【项目锁定】[\s\S]*$/, "").trim();
  genome.slots.G3 = {
    key: "knowledge",
    label: "知识",
    text:
      (g3base || "挂载优先: 本项目正本 + 本席上下文.md") +
      `\n\n【项目锁定】\nproject_id: ${projectId}\nfolder: ${projectFolder}\n` +
      `优先阅读: ${projectFolder}/项目信息.md · 项目计划.md · ${agentPath}/上下文.md\n` +
      `只读外参: 战略/公司知识/其它项目（须标明，禁止写入）`,
  };
  genome.slots.G4 = {
    key: "capability",
    label: "能力与工具",
    text:
      `规划: ①本项目正本 ②本席上下文 ③当日对话 ④阻塞/里程碑\n` +
      `产出: 写入 ${projectFolder}/（含 项目调研/、对应仓库/、频道/）\n` +
      `工具: cwd=${projectFolder}；写=仅本项目；读=本项目优先，战略等只读\n` +
      `自检: 是否锚定本项目而非 OPC 方案仓`,
  };
  return genome;
}

function defaultContextMd({ title, role }) {
  return (
    `# ${role} · 上下文\n\n` +
    `> 本文件承接「${title}」项目频道中 **${role}** 的长期记忆（DEC-047）。\n` +
    `> 对话按日写入 \`对话/YYYY-MM-DD.md\`；发送时会注入本文（截断）。\n\n` +
    `## 席位要点\n\n- 项目：${title}\n- 角色：${role}\n\n` +
    `## 最近要点\n\n（对话沉淀后可人工或 Agent 维护）\n`
  );
}

function ensureAgentSlot(projectAbs, member, { projectId, projectFolder, title }) {
  const name = member.name || member.developRole || member.id;
  const developRole = member.developRole || (DEVELOP_ROLES.includes(name) ? name : null);
  const dir = projectAgentDir(projectAbs, name);
  fs.mkdirSync(path.join(dir, "对话"), { recursive: true });
  const genomePath = path.join(dir, "genome.json");
  const ctxPath = path.join(dir, "上下文.md");
  let genome;
  if (fs.existsSync(genomePath)) {
    genome = JSON.parse(fs.readFileSync(genomePath, "utf8"));
  } else {
    const templateRole = developRole && DEVELOP_ROLES.includes(developRole) ? developRole : null;
    const src = templateRole
      ? path.join(runtime.cwd, "AgentTeam", "Develop", templateRole, "genome.json")
      : null;
    if (src && fs.existsSync(src)) {
      genome = JSON.parse(fs.readFileSync(src, "utf8"));
    } else {
      genome = {
        schema: "opc.agentteam.genome",
        version: "0.1",
        role: name,
        display_name: name,
        title: member.sub || name,
        slots: {
          G2: {
            key: "persona",
            label: "人设与决策边界",
            text: "语气: 清楚、可跟进\nmust_not:\n- 伪造进度\nhuman_gates:\n- 对外承诺变更",
          },
          G5: {
            key: "experience",
            label: "经验策略",
            text: "DO: 锚定本项目正本。\nAVOID: 把外参当成本项目事实。",
          },
        },
      };
    }
    genome.role = developRole || name;
    genome.display_name = name;
  }
  applyProjectGenomeOverlay(genome, {
    projectId,
    projectFolder,
    title: title || "",
    role: name,
  });
  if (developRole) genome.developRole = developRole;
  fs.writeFileSync(genomePath, JSON.stringify(genome, null, 2) + "\n", "utf8");
  if (!fs.existsSync(ctxPath)) {
    fs.writeFileSync(ctxPath, defaultContextMd({ title: title || projectId, role: name }), "utf8");
  }
  return {
    id: member.id || `ag-${agentDirName(name)}`,
    name,
    developRole: developRole || null,
    kind: member.kind || "agent",
    path: `${projectFolder}/频道/Agents/${agentDirName(name)}`,
    provider: ROLE_PROVIDER[developRole || ""] || genome.provider || "cursor",
  };
}

function readProjectChannelJson(projectAbs) {
  const file = path.join(projectChannelRoot(projectAbs), "channel.json");
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function migrateLegacyDevelopIfNeeded(projectAbs, { projectId, projectFolder, title }) {
  const chRoot = projectChannelRoot(projectAbs);
  if (fs.existsSync(path.join(chRoot, "channel.json"))) return null;
  const legacyRoot = path.join(projectAbs, "AgentTeam", "Develop");
  if (!fs.existsSync(legacyRoot)) return null;
  const members = [];
  for (const role of DEVELOP_ROLES) {
    const legacyGenome = path.join(legacyRoot, role, "genome.json");
    if (!fs.existsSync(legacyGenome)) continue;
    members.push({ id: `ag-${role.toLowerCase()}`, name: role, developRole: role, kind: "agent" });
    const destDir = projectAgentDir(projectAbs, role);
    fs.mkdirSync(path.join(destDir, "对话"), { recursive: true });
    const destGenome = path.join(destDir, "genome.json");
    if (!fs.existsSync(destGenome)) {
      fs.copyFileSync(legacyGenome, destGenome);
    }
    ensureAgentSlot(projectAbs, { name: role, developRole: role }, { projectId, projectFolder, title });
  }
  if (!members.length) return null;
  const channel = {
    projectId,
    projectFolder,
    projectTitle: title || "",
    name: "项目频道",
    importedFrom: "legacy-AgentTeam/Develop",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    members,
  };
  fs.mkdirSync(chRoot, { recursive: true });
  fs.writeFileSync(
    path.join(chRoot, "channel.json"),
    JSON.stringify(channel, null, 2) + "\n",
    "utf8"
  );
  return channel;
}

function upsertProjectChannel({
  projectId,
  projectFolder,
  title,
  name = "项目频道",
  members = [],
  importedFrom = null,
}) {
  const projectAbs = resolveProjectAbs(projectFolder);
  const chRoot = projectChannelRoot(projectAbs);
  fs.mkdirSync(path.join(chRoot, "Agents"), { recursive: true });
  fs.writeFileSync(
    path.join(chRoot, "README.md"),
    `# ${title || projectId} · 项目频道（DEC-047）\n\n` +
      `- 只服务本项目：写操作仅限 \`${projectFolder}/\`\n` +
      `- 战略/公司知识/其它项目：只读外参\n` +
      `- 每位 Agent：\`Agents/<名>/上下文.md\` + \`对话/YYYY-MM-DD.md\`\n`,
    "utf8"
  );
  const normalized = (Array.isArray(members) ? members : [])
    .map((m) => ({
      id: m.id || `ag-${agentDirName(m.name || m.developRole || "agent")}`,
      name: String(m.name || m.developRole || "").trim(),
      developRole: m.developRole || null,
      kind: m.kind || "agent",
      sub: m.sub || "",
    }))
    .filter((m) => m.name);
  if (!normalized.length) {
    const err = new Error("频道至少需要一名成员");
    err.code = "NO_MEMBERS";
    throw err;
  }
  const ensuredMembers = normalized.map((m) =>
    ensureAgentSlot(projectAbs, m, { projectId, projectFolder, title: title || "" })
  );
  const prev = readProjectChannelJson(projectAbs);
  const channel = {
    projectId,
    projectFolder,
    projectTitle: title || "",
    name: name || "项目频道",
    importedFrom: importedFrom || prev?.importedFrom || null,
    createdAt: prev?.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    members: ensuredMembers.map((m) => ({
      id: m.id,
      name: m.name,
      developRole: m.developRole,
      kind: m.kind,
      path: m.path,
      provider: m.provider,
    })),
  };
  fs.writeFileSync(
    path.join(chRoot, "channel.json"),
    JSON.stringify(channel, null, 2) + "\n",
    "utf8"
  );
  return { projectAbs, projectFolder, channel };
}

/** 兼容：导入 Develop 五席模板（DEC-045 → DEC-047） */
function ensureProjectDevelopTeam({ projectId, projectFolder, title }) {
  return upsertProjectChannel({
    projectId,
    projectFolder,
    title,
    name: "项目频道",
    importedFrom: "template:Develop",
    members: DEVELOP_ROLES.map((role) => ({
      id: `ag-${role.toLowerCase()}`,
      name: role,
      developRole: role,
      kind: "agent",
    })),
  });
}

function getProjectChannelState(projectFolder) {
  const projectAbs = resolveProjectAbs(projectFolder);
  let channel = readProjectChannelJson(projectAbs);
  if (!channel) {
    channel = migrateLegacyDevelopIfNeeded(projectAbs, {
      projectId: "unknown",
      projectFolder,
      title: path.basename(projectAbs),
    });
  }
  return {
    ok: true,
    configured: Boolean(channel),
    projectAbs,
    projectFolder,
    channel: channel || null,
  };
}

function loadAgentContextFile(projectAbs, agentName, { maxChars = 8000 } = {}) {
  const file = path.join(projectAgentDir(projectAbs, agentName), "上下文.md");
  if (!fs.existsSync(file)) return "";
  try {
    let text = fs.readFileSync(file, "utf8").trim();
    if (text.length > maxChars) text = text.slice(0, maxChars) + "\n…(截断)";
    return text;
  } catch {
    return "";
  }
}

function loadChatTail(projectAbs, agentName, { maxChars = 6000 } = {}) {
  const file = path.join(projectAgentDir(projectAbs, agentName), "对话", `${todayYmd()}.md`);
  if (!fs.existsSync(file)) return "";
  try {
    let text = fs.readFileSync(file, "utf8").trim();
    if (text.length > maxChars) text = text.slice(-maxChars);
    return text;
  } catch {
    return "";
  }
}

function appendDailyChat(projectAbs, agentName, { userText, assistantText, from }) {
  const dir = path.join(projectAgentDir(projectAbs, agentName), "对话");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${todayYmd()}.md`);
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const header = fs.existsSync(file) ? "" : `# 对话 · ${todayYmd()}\n\n`;
  const block =
    header +
    `## ${hh}:${mm}\n\n` +
    `### 你\n\n${String(userText || "").trim()}\n\n` +
    `### ${from || agentName}\n\n${String(assistantText || "").trim()}\n\n---\n\n`;
  fs.appendFileSync(file, block, "utf8");
  return `${path.basename(dir)}/${todayYmd()}.md`;
}

function loadDevelopGenome(role, { projectFolder = null } = {}) {
  if (!projectFolder && !DEVELOP_ROLES.includes(role)) {
    const err = new Error(`未知开发席角色：${role}`);
    err.code = "BAD_ROLE";
    throw err;
  }
  if (projectFolder) {
    const primary = path.join(developRoleDir(role, projectFolder), "genome.json");
    if (fs.existsSync(primary)) return JSON.parse(fs.readFileSync(primary, "utf8"));
    if (DEVELOP_ROLES.includes(role)) {
      const legacy = path.join(legacyDevelopRoleDir(role, projectFolder), "genome.json");
      if (fs.existsSync(legacy)) return JSON.parse(fs.readFileSync(legacy, "utf8"));
    }
    const err = new Error(`未找到项目基因组：${projectFolder}/频道/Agents/${agentDirName(role)}/genome.json`);
    err.code = "NO_GENOME";
    throw err;
  }
  const file = path.join(developRoleDir(role), "genome.json");
  if (!fs.existsSync(file)) {
    const err = new Error(`未找到基因组：AgentTeam/Develop/${role}/genome.json`);
    err.code = "NO_GENOME";
    throw err;
  }
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function assembleDevelopPrompt(
  genome,
  userText,
  {
    teamChannel = false,
    projectScope = null,
    mentions = [],
    projectBrief = "",
    agentContext = "",
    chatTail = "",
    milestonePin = "",
  } = {}
) {
  const lines = [
    projectScope
      ? `你是项目「${projectScope.title}」频道席位（${genome?.display_name || genome?.role || "成员"}）。` +
        `本频道只服务该项目；不是 OPC 架构方案仓，也不是其它项目。`
      : "你是铱石智能工作台 · 开发团队（AgentTeam/Develop）数字员工（公司级频道，非某一项目沙箱）。",
    "严格按下列 G1–G5 基因组扮演；遵守 G2 must_not / human_gates；勿把评分 rubric 写进自己的基因叙事。",
    "部署与验证只谈 Docker；密钥不进回复正文。",
  ];
  const mentionList = Array.isArray(mentions)
    ? mentions.map((m) => String(m || "").trim()).filter(Boolean)
    : [];
  const myName = genome?.display_name || genome?.role || "";
  if (mentionList.length) {
    lines.push(`【@ 提及】用户点名了：${mentionList.map((m) => `@${m}`).join(" ")}。`);
    if (myName && mentionList.some((m) => m.toLowerCase() === String(myName).toLowerCase())) {
      lines.push("你在被 @ 名单中：请以被提及席位优先、直接作答，不要把球踢给未被点名的席。");
    } else {
      lines.push("本次路由点名了其他席；若仍由你应答，简要回应并标明更合适的席位。");
    }
  }
  if (projectScope) {
    lines.push(
      "【硬约束·项目隔离 · DEC-047】",
      `- 写操作 cwd / 产出路径仅限：${projectScope.folder}`,
      `- 容器绝对路径：${projectScope.abs}`,
      "- 战略信息、公司知识、其它项目、全局 AgentTeam 模板：仅只读外参；引用时标明「只读外参」，禁止写入那些目录。",
      "- 回答必须锚定本项目正本与本席「上下文.md」。若与外参冲突，以本项目正本为准。",
      "- 禁止把本项目问题答成 OPC 架构设计文档或其它项目的进度。",
      "- 问到里程碑 / 当期进度 / 节奏板：必须引用下方【必读·当期里程碑】；不得另编 OPC 或其它项目的 M0–M7。",
      teamChannel
        ? "当前是本项目频道公共区：以本席协调；可建议用户私聊本频道内其他席。"
        : "当前是本项目频道内与你的一对一。"
    );
    if (milestonePin) {
      lines.push(
        "",
        "## 【必读·当期里程碑】（摘自 项目计划.md，优先于其它记忆）",
        milestonePin,
        "",
        "（若用户问「当前里程碑 / 规划里程碑」，先复述上表 ID/状态/本周焦点，再给动作建议。）"
      );
    } else {
      lines.push(
        "",
        `## 【必读·当期里程碑】`,
        `未在 ${projectScope.folder}/项目计划.md 找到「当期里程碑」节；请先读该文件再答，禁止臆造。`
      );
    }
  } else {
    lines.push(
      teamChannel
        ? "当前是公司级开发频道（非项目沙箱）：你以本席身份协调应答；若问题属于某项目，请用户进入该项目频道。"
        : "当前是与你的一对一频道（公司级）。"
    );
  }
  lines.push("");
  for (const id of ["G1", "G2", "G3", "G4", "G5"]) {
    const slot = genome?.slots?.[id];
    if (!slot?.text) continue;
    lines.push(`## ${id} · ${slot.label || id}`, String(slot.text).trim(), "");
  }
  if (projectScope && agentContext) {
    lines.push("## 本席上下文.md（长期记忆承接）", agentContext, "");
  }
  if (projectScope && projectBrief) {
    lines.push("## 本项目正本（已注入）", projectBrief, "");
  } else if (projectScope) {
    lines.push(
      "## 本项目正本",
      `未读到正本文件，请先打开 ${projectScope.folder}/项目信息.md · 项目计划.md 再答。`,
      ""
    );
  }
  if (projectScope && chatTail) {
    lines.push("## 当日对话摘录（尾部）", chatTail, "");
  }
  lines.push("## 用户消息", String(userText).trim());
  return lines.join("\n");
}

function json(res, code, body) {
  const data = JSON.stringify(body, null, 0);
  res.writeHead(code, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

function healthPayload() {
  return {
    ok: true,
    cwd: runtime.cwd,
    cwdExists: fs.existsSync(runtime.cwd),
    hasApiKey: Boolean(getProviderKey("cursor")),
    model: runtime.model,
    activeProvider: runtime.activeProvider,
    agentId: agentSessions.get("workbench")?.agentId || null,
    developRoles: DEVELOP_ROLES.filter((r) =>
      fs.existsSync(path.join(developRoleDir(r), "genome.json"))
    ),
    providers: listProviders().map((p) => ({
      id: p.id,
      hasKey: p.hasKey,
      wired: p.wired,
      enabled: p.enabled,
    })),
  };
}

function resolveRoleProvider(role) {
  if (!role) return "cursor";
  return ROLE_PROVIDER[role] || "cursor";
}

function splitDevelopPrompt(genome, userText, opts = {}) {
  const full = assembleDevelopPrompt(genome, userText, opts);
  const marker = "## 用户消息\n";
  const i = full.lastIndexOf(marker);
  if (i < 0) return { system: full, user: String(userText || "").trim() };
  return {
    system: full.slice(0, i).trim(),
    user: full.slice(i + marker.length).trim() || String(userText || "").trim(),
  };
}

async function runKimiChat({ system, user }) {
  const API_KEY = getProviderKey("kimi");
  if (!API_KEY) {
    const err = new Error(
      "Kimi API Key 未配置 · 请将钥放入 opc/公司资产/IT资产/kimi-coding-plan.key 或设置 → Provider"
    );
    err.code = "NO_KEY";
    throw err;
  }
  const model = runtime.kimiModel || "kimi-k3";
  const url = `${KIMI_BASE_URL}/chat/completions`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      // kimi-k3 / coding 端对 temperature 限制严，默认不传
    }),
  });
  const raw = await res.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { raw };
  }
  if (!res.ok) {
    const msg = data?.error?.message || data?.message || raw || `HTTP ${res.status}`;
    const err = new Error(`Kimi API：${msg}`);
    err.code = "KIMI_API";
    throw err;
  }
  const reply =
    data?.choices?.[0]?.message?.content ||
    data?.choices?.[0]?.delta?.content ||
    "";
  return {
    status: "finished",
    result: String(reply || "(empty reply)"),
    provider: "kimi",
    model,
    runId: data?.id || null,
  };
}

async function runCursorSend(prompt, { agentKey, cwd = null, noResume = false } = {}) {
  const API_KEY = getProviderKey("cursor");
  if (!API_KEY) {
    const err = new Error("Cursor API Key 未配置 · 请到「设置 → Provider」填写");
    err.code = "NO_KEY";
    throw err;
  }

  const workCwd = cwd || runtime.cwd;
  const opts = {
    apiKey: API_KEY,
    model: { id: runtime.model },
    local: { cwd: workCwd },
  };

  const prior = agentSessions.get(agentKey) || null;
  /** @type {Awaited<ReturnType<typeof Agent.create>>} */
  let agent;
  // 项目频道：每轮带全量正本/里程碑注入，禁止 resume 旧会话冲掉当期焦点
  if (noResume) {
    agentSessions.delete(agentKey);
  } else if (prior && prior.cwd !== workCwd) {
    console.warn(
      `[cursor-bridge] cwd changed for ${agentKey}: ${prior.cwd} -> ${workCwd}; new agent (drop resume)`
    );
    agentSessions.delete(agentKey);
  }
  const canResume = !noResume && prior?.agentId && prior.cwd === workCwd && agentSessions.has(agentKey);
  if (canResume) {
    try {
      agent = await Agent.resume(prior.agentId, opts);
    } catch (e) {
      console.warn("[cursor-bridge] resume failed, creating new agent:", e?.message || e);
      agentSessions.delete(agentKey);
      agent = await Agent.create(opts);
    }
  } else {
    agent = await Agent.create(opts);
  }

  try {
    agentSessions.set(agentKey, { agentId: agent.agentId, cwd: workCwd });
    const run = await agent.send(prompt);
    const result = await run.wait();
    const runId = result.id || run.id;
    const status = result.status || "finished";
    let reply = result.result ?? run.result;
    if (reply == null || reply === "") {
      reply = status === "error" ? "Agent run failed" : "(empty reply)";
    }
    return {
      status,
      result: String(reply),
      agentId: agent.agentId,
      runId,
      provider: "cursor",
      model: runtime.model,
      cwd: workCwd,
    };
  } finally {
    try {
      if (typeof agent[Symbol.asyncDispose] === "function") {
        await agent[Symbol.asyncDispose]();
      } else if (typeof agent.close === "function") {
        await agent.close();
      }
    } catch {
      /* ignore */
    }
  }
}

async function runSend(
  text,
  {
    role = null,
    teamChannel = false,
    projectId = null,
    projectFolder = null,
    projectTitle = null,
    mentions = [],
  } = {}
) {
  if (!fs.existsSync(runtime.cwd)) {
    const err = new Error(`WORKBENCH_CWD not found: ${runtime.cwd}`);
    err.code = "NO_CWD";
    throw err;
  }

  let projectScope = null;
  let projectBrief = "";
  let agentContext = "";
  let chatTail = "";
  let milestonePin = "";
  if (projectFolder) {
    const state = getProjectChannelState(projectFolder);
    if (!state.configured) {
      const err = new Error("项目频道尚未组建 · 请先在项目详情「组建频道」");
      err.code = "NO_CHANNEL";
      throw err;
    }
    // 若点名席不在频道内但有 developRole 模板名，仍允许（向导应已落盘）
    projectScope = {
      id: projectId || state.channel?.projectId || null,
      folder: projectFolder,
      title: projectTitle || state.channel?.projectTitle || projectFolder,
      abs: state.projectAbs,
    };
    milestonePin = extractMilestonePin(state.projectAbs);
    projectBrief = loadProjectBrief(state.projectAbs);
    if (role) {
      if (milestonePin) syncContextMilestonePin(state.projectAbs, role, milestonePin);
      agentContext = loadAgentContextFile(state.projectAbs, role);
      chatTail = loadChatTail(state.projectAbs, role);
    }
  }

  let resolvedProvider = "cursor";
  let genomeMeta = null;
  let prompt = String(text || "").trim();
  let kimiParts = null;
  const mentionList = Array.isArray(mentions)
    ? mentions.map((m) => String(m || "").trim()).filter(Boolean)
    : [];
  const promptOpts = {
    teamChannel,
    projectScope,
    mentions: mentionList,
    projectBrief,
    agentContext,
    chatTail,
    milestonePin,
  };

  if (role) {
    const genome = loadDevelopGenome(role, {
      projectFolder: projectScope ? projectScope.folder : null,
    });
    const developRole = genome.developRole || (DEVELOP_ROLES.includes(role) ? role : null);
    resolvedProvider = resolveRoleProvider(developRole || role);
    genomeMeta = {
      role: genome.role || role,
      display_name: genome.display_name || role,
      path: genome.path || `AgentTeam/Develop/${role}`,
      provider: resolvedProvider,
      projectId: projectScope?.id || null,
    };
    if (resolvedProvider === "kimi") {
      kimiParts = splitDevelopPrompt(genome, prompt, promptOpts);
    } else {
      prompt = assembleDevelopPrompt(genome, prompt, promptOpts);
    }
  }

  let out;
  if (resolvedProvider === "kimi") {
    if (!getProviderKey("kimi")) {
      const err = new Error("Kimi Key 未配置");
      err.code = "NO_KEY";
      throw err;
    }
    const parts = kimiParts || { system: "你是有帮助的助手。", user: prompt };
    out = await runKimiChat(parts);
  } else {
    const agentKey = projectScope
      ? `project:${projectScope.id || projectScope.folder}:agent:${role || "workbench"}`
      : role
        ? `role:${role}`
        : "workbench";
    out = await runCursorSend(prompt, {
      agentKey,
      cwd: projectScope ? projectScope.abs : null,
      noResume: Boolean(projectScope),
    });
  }

  let chatLogPath = null;
  if (projectScope && role) {
    try {
      chatLogPath = appendDailyChat(projectScope.abs, role, {
        userText: text,
        assistantText: out.result,
        from: genomeMeta?.display_name || role,
      });
    } catch (e) {
      console.warn("[cursor-bridge] append daily chat failed:", e?.message || e);
    }
  }

  return {
    ...out,
    provider: resolvedProvider,
    cwd: projectScope ? projectScope.abs : runtime.cwd,
    projectId: projectScope?.id || null,
    projectFolder: projectScope?.folder || null,
    role: genomeMeta?.role || null,
    from: genomeMeta?.display_name || null,
    genomePath: genomeMeta?.path || null,
    chatLog: chatLogPath,
    milestonePinned: Boolean(milestonePin),
    briefChars: projectBrief ? projectBrief.length : 0,
  };
}

function enqueueSend(text, opts = {}) {
  const job = sendChain.then(() => runSend(text, opts));
  sendChain = job.catch(() => {});
  return job;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${HOST}:${PORT}`);
  const pathname = url.pathname.replace(/\/+$/, "") || "/";

  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    });
    return res.end();
  }

  if (req.method === "GET" && (pathname === "/healthz" || pathname === "/api/agent/healthz")) {
    return json(res, 200, healthPayload());
  }

  if (req.method === "GET" && pathname === "/api/agent/providers") {
    return json(res, 200, {
      providers: listProviders(),
      cwd: runtime.cwd,
      model: runtime.model,
      activeProvider: runtime.activeProvider,
      bridgeOk: true,
    });
  }

  if (req.method === "GET" && pathname === "/api/agent/it-secrets") {
    return json(res, 200, {
      dir: path.posix.join("公司资产", "IT资产"),
      cwd: runtime.cwd,
      secrets: listItSecrets(),
    });
  }

  const putMatch = pathname.match(/^\/api\/agent\/providers\/([^/]+)$/);
  if (putMatch && (req.method === "PUT" || req.method === "PATCH")) {
    const id = decodeURIComponent(putMatch[1]);
    try {
      const body = await readBody(req);
      const cat = PROVIDER_CATALOG.find((p) => p.id === id);
      if (!cat) return json(res, 404, { error: "unknown provider" });

      if (body.clearKey) {
        clearProviderKey(id);
      } else if (body.apiKey != null && String(body.apiKey).trim()) {
        setProviderKey(id, body.apiKey);
      }

      if (body.model != null && String(body.model).trim() && id === "cursor") {
        runtime.model = String(body.model).trim();
        syncEnvKey("MODEL", runtime.model);
        saveProvidersFile();
        agentSessions.clear();
      }

      if (body.cwd != null && String(body.cwd).trim() && id === "cursor") {
        runtime.cwd = path.resolve(String(body.cwd).trim());
        syncEnvKey("WORKBENCH_CWD", runtime.cwd);
        saveProvidersFile();
        agentSessions.clear();
      }

      if (body.enabled === true) {
        runtime.activeProvider = id;
        saveProvidersFile();
      }

      return json(res, 200, {
        ok: true,
        provider: listProviders().find((p) => p.id === id),
        providers: listProviders(),
        cwd: runtime.cwd,
        model: runtime.model,
        activeProvider: runtime.activeProvider,
      });
    } catch (e) {
      const code = e?.code === "NO_PROVIDER" ? 404 : e?.code === "BAD_KEY" ? 400 : 500;
      return json(res, code, { error: e?.message || String(e), code: e?.code });
    }
  }

  if (req.method === "POST" && pathname === "/api/agent/tcp-probe") {
    try {
      const body = await readBody(req);
      const host = String(body.host || "").trim();
      const port = Number(body.port || 22);
      if (!host) return json(res, 400, { error: "host required" });
      if (!Number.isFinite(port) || port < 1 || port > 65535) {
        return json(res, 400, { error: "invalid port" });
      }
      const started = Date.now();
      const ok = await new Promise((resolve) => {
        const socket = net.connect({ host, port }, () => {
          socket.end();
          resolve(true);
        });
        socket.setTimeout(4000, () => {
          socket.destroy();
          resolve(false);
        });
        socket.on("error", () => resolve(false));
      });
      return json(res, 200, { ok, host, port, ms: Date.now() - started });
    } catch (e) {
      return json(res, 500, { error: e?.message || String(e) });
    }
  }

  if (req.method === "GET" && pathname === "/api/agent/develop-roles") {
    const roles = DEVELOP_ROLES.map((role) => {
      const file = path.join(developRoleDir(role), "genome.json");
      let present = false;
      let display_name = role;
      let title = "";
      try {
        if (fs.existsSync(file)) {
          present = true;
          const g = JSON.parse(fs.readFileSync(file, "utf8"));
          display_name = g.display_name || role;
          title = g.title || "";
        }
      } catch {
        /* ignore */
      }
      const provider = ROLE_PROVIDER[role] || "cursor";
      return {
        role,
        display_name,
        title,
        present,
        provider,
        model: provider === "kimi" ? runtime.kimiModel : runtime.model,
        path: `AgentTeam/Develop/${role}`,
        channelId:
          role === "Architect"
            ? "dm-arch"
            : role === "DevOps"
              ? "dm-devops"
              : `dm-${role.toLowerCase()}`,
      };
    });
    return json(res, 200, {
      team: "Develop",
      roles,
      defaults: { technical: "kimi", other: "cursor", kimiModel: runtime.kimiModel },
    });
  }

  if (req.method === "GET" && pathname === "/api/agent/project-channel") {
    try {
      const projectFolder = String(url.searchParams.get("projectFolder") || "").trim();
      if (!projectFolder) return json(res, 400, { error: "projectFolder required" });
      const out = getProjectChannelState(projectFolder);
      return json(res, 200, out);
    } catch (e) {
      const code = e?.code === "BAD_PROJECT" || e?.code === "NO_PROJECT" ? 400 : 500;
      return json(res, code, { error: e?.message || String(e), code: e?.code || "GET_FAILED" });
    }
  }

  if (req.method === "POST" && pathname === "/api/agent/project-channel") {
    try {
      const body = await readBody(req);
      const projectId = String(body.projectId || "").trim();
      const projectFolder = String(body.projectFolder || "").trim();
      const projectTitle = String(body.projectTitle || body.title || "").trim();
      const channelName = String(body.name || "项目频道").trim() || "项目频道";
      const importedFrom = body.importedFrom != null ? String(body.importedFrom) : null;
      const members = Array.isArray(body.members) ? body.members : [];
      if (!projectId || !projectFolder) {
        return json(res, 400, { error: "projectId and projectFolder required" });
      }
      const out = upsertProjectChannel({
        projectId,
        projectFolder,
        title: projectTitle || projectId,
        name: channelName,
        members,
        importedFrom,
      });
      return json(res, 200, { ok: true, ...out });
    } catch (e) {
      const code =
        e?.code === "BAD_PROJECT" ||
        e?.code === "NO_PROJECT" ||
        e?.code === "NO_GENOME" ||
        e?.code === "NO_MEMBERS"
          ? 400
          : 500;
      return json(res, code, { error: e?.message || String(e), code: e?.code || "UPSERT_FAILED" });
    }
  }

  if (req.method === "POST" && pathname === "/api/agent/ensure-project-team") {
    try {
      const body = await readBody(req);
      const projectId = String(body.projectId || "").trim();
      const projectFolder = String(body.projectFolder || "").trim();
      const projectTitle = String(body.projectTitle || "").trim();
      if (!projectId || !projectFolder) {
        return json(res, 400, { error: "projectId and projectFolder required" });
      }
      const out = ensureProjectDevelopTeam({
        projectId,
        projectFolder,
        title: projectTitle || projectId,
      });
      return json(res, 200, {
        ok: true,
        projectId,
        projectFolder: out.projectFolder,
        projectAbs: out.projectAbs,
        channel: out.channel,
        roles: (out.channel?.members || []).map((m) => ({
          role: m.developRole || m.name,
          path: m.path,
          provider: m.provider,
        })),
      });
    } catch (e) {
      const code =
        e?.code === "BAD_PROJECT" ||
        e?.code === "NO_PROJECT" ||
        e?.code === "NO_GENOME" ||
        e?.code === "NO_MEMBERS"
          ? 400
          : 500;
      return json(res, code, {
        error: e?.message || String(e),
        code: e?.code || "ENSURE_FAILED",
      });
    }
  }

  if (req.method === "POST" && pathname === "/api/agent/send") {
    try {
      const body = await readBody(req);
      const text = String(body.text || "").trim();
      if (!text) return json(res, 400, { error: "text required" });
      const role = body.role != null && String(body.role).trim() ? String(body.role).trim() : null;
      const teamChannel = Boolean(body.teamChannel);
      const projectId =
        body.projectId != null && String(body.projectId).trim()
          ? String(body.projectId).trim()
          : null;
      const projectFolder =
        body.projectFolder != null && String(body.projectFolder).trim()
          ? String(body.projectFolder).trim()
          : null;
      const projectTitle =
        body.projectTitle != null && String(body.projectTitle).trim()
          ? String(body.projectTitle).trim()
          : null;
      const mentions = Array.isArray(body.mentions)
        ? body.mentions.map((m) => String(m || "").trim()).filter(Boolean)
        : [];
      if (projectFolder && !projectFolder.startsWith("项目/")) {
        return json(res, 400, {
          error: "projectFolder 必须落在 项目/ 下",
          code: "BAD_PROJECT",
        });
      }
      const providerHint = resolveRoleProvider(role);
      if (!role && runtime.activeProvider !== "cursor") {
        return json(res, 503, {
          error: `当前启用 Provider「${runtime.activeProvider}」尚未接线 · 工作台频道请启用 Cursor`,
          code: "PROVIDER_NOT_WIRED",
        });
      }
      if (providerHint === "kimi" && !getProviderKey("kimi") && !projectFolder) {
        return json(res, 503, {
          error: "Kimi Key 未配置 · 见 opc/公司资产/IT资产/kimi-coding-plan.key",
          code: "NO_KEY",
        });
      }
      if (!getProviderKey("cursor") && !getProviderKey("kimi")) {
        return json(res, 503, {
          error: "Cursor / Kimi API Key 未配置 · 请到「设置 → Provider」填写",
          code: "NO_KEY",
        });
      }
      const out = await enqueueSend(text, {
        role,
        teamChannel,
        projectId,
        projectFolder,
        projectTitle,
        mentions,
      });
      return json(res, 200, out);
    } catch (e) {
      if (e instanceof CursorAgentError) {
        return json(res, 502, {
          error: e.message || "CursorAgentError",
          code: "CURSOR_AGENT",
          retryable: Boolean(e.isRetryable),
        });
      }
      if (e?.code === "KIMI_API") {
        return json(res, 502, { error: e.message || "Kimi API error", code: "KIMI_API" });
      }
      const code =
        e?.code === "NO_CHANNEL" || e?.code === "BAD_PROJECT" || e?.code === "NO_PROJECT"
          ? 400
          : e?.code === "NO_KEY" ||
              e?.code === "NO_CWD" ||
              e?.code === "NO_GENOME" ||
              e?.code === "BAD_ROLE"
            ? 503
            : 500;
      return json(res, code, {
        error: e?.message || String(e),
        code: e?.code || "SEND_FAILED",
      });
    }
  }

  json(res, 404, { error: "not found" });
});

server.listen(PORT, HOST, () => {
  console.log(`[cursor-bridge] http://${HOST}:${PORT}`);
  console.log(`[cursor-bridge] cwd=${runtime.cwd}`);
  console.log(
    `[cursor-bridge] cursorKey=${Boolean(getProviderKey("cursor"))} model=${runtime.model} active=${runtime.activeProvider}`
  );
});
