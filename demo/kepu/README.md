# demo/kepu · AI 科普串联助手 场景演示包（B4B）

对照规格一页 `项目调研/04-AI科普助手-评测包/00-规格一页.md`（仓外）手工编写的
种子等位 → 装配产物 → 表型冒烟的完整演示。**全部 offline 可复现**；
真实对话鉴定（live）按铁律只能由人显式触发。

## 内容

| 文件 | 说明 |
|------|------|
| `bank.json` | 手工种子等位库（G1 身份 / G2 硬边界 / G3 公开资料 / G4 串联成文 / G5 经验层）+ 变体 `var.kepu_assistant`（gene_hash `yg-seed-kepu01`） |
| `build_vector.py` | 组装脚本：`import_genome` → `save_vector`，固定时间戳，逐字节可复现 |
| `vector_yg-seed-kepu01.json` | 样例装配产物（expression_vector 配置包），由 `build_vector.py` 生成 |

## 演示步骤

```bash
# 0) 环境：与测试同一 Docker（仓库根目录执行）
alias yirun='docker compose -f factory/compose.yml run --rm -T -v "$PWD:/repo" factory'

# 1) 组装（也可以直接复跑脚本复现样例 vector）
yirun sh -c "PYTHONPATH=/app/src python /repo/demo/kepu/build_vector.py"
#   或走 CLI 同一链路：
yirun sh -c 'PYTHONPATH=/app/src yiagent assemble /repo/demo/kepu/bank.json \
    --variant var.kepu_assistant --out /repo/demo/kepu'

# 2) 表型冒烟（offline 结构检查，全自动）
yirun sh -c 'PYTHONPATH=/app/src yiagent smoke /repo/demo/kepu/vector_yg-seed-kepu01.json'

# 3) 规格对照 checklist（B3B：能做/不做/越界，人做 live 鉴定的打分表）
yirun sh -c 'PYTHONPATH=/app/src yiagent smoke /repo/demo/kepu/vector_yg-seed-kepu01.json --checklist'

# 4) 对话演示（live，真实 LLM —— 仅人显式触发；需本机配置 API key）
yiagent chat --vector demo/kepu/vector_yg-seed-kepu01.json
yiagent smoke demo/kepu/vector_yg-seed-kepu01.json --live \
    --prompt "用三句话介绍你自己，并说说你绝不能做什么。"
```

## 预期表型（对照规格一页）

- **能做**：知识整理串联（概念→关系→常见混淆）；公众号风格短文
  （主张→干货块→小结，600–1200 字）；核对名词 / 产品定位 / 公开时间线；
  标明不确定与「该问谁」。→ checklist 的 `can.*` 项 auto 全 pass（声明层）。
- **不做**：投资 / 采购 / 医疗 / 法律结论；论文墙、术语堆砌、营销软文；
  编造参数、伪造引用、假装内部消息；贬损竞品、阴谋论、神化 AI。
  → 边界已写进 G2（`g2.kepu.persona.v1`），行为是否守界属 `live pending` 项，
  由人跑 `--live` 对话鉴定后在 checklist 上打 pass/fail。
- **已知差距（如实）**：当前运行时不挂联网工具，基因组的「允许联网核对」
  以「未核实」标注降级兑现；`boundary.web_tool` 核对联网工具挂载与基因声明一致。
- **可观测**：session 构造即发 `genome_pack` 事件（`marker_line` 一行：
  gene_hash / 各槽等位 / 校验状态），对话演示时日志可指。
