"""B4B 演示包：由种子等位手工组装样例 vector（全离线、可复现）。

用法（仓库根目录，与测试同一 Docker 环境）：

    docker compose -f factory/compose.yml run --rm -T -v "$PWD:/repo" factory \
      sh -c "PYTHONPATH=/app/src python /repo/demo/kepu/build_vector.py"

产物：`vector_yg-seed-kepu01.json`（assembled_at 固定，同一 bank 逐字节可复现）。
"""

from pathlib import Path

from yiagent.recipient import import_genome, save_vector

HERE = Path(__file__).resolve().parent

# 固定装配时间戳：演示产物可复现
ASSEMBLED_AT = "2026-08-02T00:00:00Z"

HOST = (
    "你是 AI 科普串联助手运行时：按已装载的 G1–G5 基因组行事。"
    "面向普通人写作，公众号可读；无法核对的事实时标注「未核实」。"
)


def main() -> None:
    pack = import_genome(
        HERE / "bank.json",
        host=HOST,
        variant_id="var.kepu_assistant",
        assembled_at=ASSEMBLED_AT,
    )
    out = save_vector(pack, HERE)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
