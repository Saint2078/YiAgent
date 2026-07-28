# case/xsct · XSCT Bench 用例

来源：[itshen/XSCT_Bench_Dataset](https://github.com/itshen/XSCT_Bench_Dataset)（commit `93faddc`）  
许可：数据集 **CC BY-NC-SA 4.0**（详见 [PROVENANCE.md](PROVENANCE.md)）  
平台：[xsct.ai/gallery](https://xsct.ai/gallery)

## 库存

| 套件 | 文件 | 条数 |
|------|------|-----:|
| xsct-l（文字） | `xsct-l/testcases.jsonl` | 362 |
| xsct-vg（图像） | `xsct-vg/testcases.jsonl` | 343 |
| xsct-w（网页） | `xsct-w/testcases.jsonl` | 181 |
| **合计** | | **886** |

各套件另有 `dimensions.json`。每条用例含 `levels.{basic,medium,hard}` 的 `messages` / `requirements` / `criteria`（裁判标尺）。

## 与 factory

默认用本目录现成题 + 题内 criteria，经 `factory/server/judge.py` 打分；口述出题仅作从 0 补洞。
