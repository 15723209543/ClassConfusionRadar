"""
本文件的作用是：生成并校验项目使用的合成测试数据。
"""
from __future__ import annotations

import base64
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo_data" / "批量测试数据"
OUTPUT = ROOT / "frontend" / "src" / "data" / "builtinDatasets.ts"


def count_records(folder: Path) -> int:
    total = 0
    for path in folder.glob("*.csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            total += max(0, sum(1 for _ in csv.reader(handle)) - 1)
    return total


def main() -> None:
    items = []
    for folder in sorted(path for path in SOURCE.iterdir() if path.is_dir()):
        dataset_id = folder.name[:2]
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        title = manifest["session"]["title"]
        label = title.split(" ", 1)[1] if " " in title else title
        records = count_records(folder)
        items.append(
            {
                "id": dataset_id,
                "label": label.replace("_", " · "),
                "records": records,
                "description": f"包含 5 类课堂过程数据，共 {records} 条记录，适合直接导入测试完整分析流程。",
                "zipBase64": base64.b64encode((folder / "一键导入.zip").read_bytes()).decode("ascii"),
            }
        )

    content = (
        "export interface BuiltinDataset {\n"
        "  id: string;\n  label: string;\n  records: number;\n"
        "  description: string;\n  zipBase64: string;\n}\n\n"
        "export const BUILTIN_DATASETS: BuiltinDataset[] = "
        + json.dumps(items, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"generated: {OUTPUT} ({len(items)} datasets)")


if __name__ == "__main__":
    main()
