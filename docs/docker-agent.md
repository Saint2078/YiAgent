# YiAgent · CLI & Docker（对齐 Hermes 形态）

参考工作台内 hermes-agent 与 [Hermes Docker 文档](https://hermes-agent.nousresearch.com/docs/user-guide/docker)：

| Hermes | YiAgent |
|--------|---------|
| `HERMES_HOME` → `/opt/data` | `YIAGENT_HOME` → `/opt/data`（宿主机默认 `~/.yiagent`） |
| `config.yaml` + `.env` | 同左（行为 / 密钥分离） |
| `hermes setup` / `doctor` | `yiagent setup` / `doctor` |
| bare `hermes` → chat / `--tui` | bare `./yiagent` → **TUI**；`--cli` 经典 REPL |

## 用法

```bash
./yiagent build
./yiagent setup
./yiagent doctor
./yiagent              # Docker 内 TUI（需 -it）
./yiagent --tui
./yiagent --cli        # 经典 you> REPL
./yiagent run 你好
./yiagent variants
./yiagent improve              # 最近 session → ~/.yiagent/improve/*.json
./yiagent improve -r <id>
./yiagent improve --apply path/to/best_genome.json
```

## Sessions（对齐 Hermes）

```bash
yiagent --tui                         # 新 TUI 会话
yiagent --tui -c                      # 继续最近 TUI 会话（无则 fallback CLI）
yiagent --tui --continue
yiagent --tui -r 20260409_000000_aa11bb
yiagent --tui --resume "my t0p session"
yiagent sessions                      # 列出已存会话
```

会话文件：`~/.yiagent/sessions/{id}.json`。

宿主机状态目录：`~/.yiagent/`（`config.yaml` 里 `display.interface: tui`、`.env`、`workspace/`）。

筛选台在 `factory/`（`:8787`）。CLI 效果差时用 `yiagent improve` 导出包，在工厂 Step1「改进包」载入 / 一键改进；冠军用 `--apply` 装回。
