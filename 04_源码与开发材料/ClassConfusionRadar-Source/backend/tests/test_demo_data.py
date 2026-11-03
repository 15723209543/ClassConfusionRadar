"""
本文件的作用是：验证演示数据相关功能在典型与异常场景下的行为。
"""
import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "demo_data" / "批量测试数据"
DATASETS = sorted(path for path in ROOT.iterdir() if path.is_dir())


@pytest.mark.parametrize("dataset_dir", DATASETS, ids=lambda path: path.name)
def test_bulk_demo_dataset_is_complete_and_large(dataset_dir: Path):
    required = ["quiz.csv", "submission.csv", "interaction.csv", "transcript.csv", "ppt_timeline.csv", "manifest.json"]
    for filename in required:
        assert (dataset_dir / filename).exists(), filename

    row_total = 0
    for filename in required[:5]:
        with (dataset_dir / filename).open("r", encoding="utf-8-sig", newline="") as handle:
            row_total += max(0, sum(1 for _ in csv.reader(handle)) - 1)
    assert row_total >= 600

    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["knowledge_points"]) >= 5
    assert manifest["expected_focus"]


def test_exactly_ten_bulk_datasets_are_kept():
    assert len(DATASETS) == 20
