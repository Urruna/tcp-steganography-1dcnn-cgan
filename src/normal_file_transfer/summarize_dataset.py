"""汇总 Normal 数据集日志，输出 dataset_summary.json。"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
SUMMARY_FILE = LOG_DIR / "dataset_summary.json"


def summarize_csv(path: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
    summary: dict[str, object] = {
        "file": path.name,
        "rows": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
    }
    if rows and "direction" in rows[0]:
        summary["directions"] = dict(
            Counter(row.get("direction", "") for row in rows)
        )
        summary["sessions"] = len(
            {row.get("session_id", "") for row in rows if row.get("session_id")}
        )
        summary["total_bytes"] = sum(
            int(float(row.get("byte_length", "0") or 0)) for row in rows
        )
    if rows and "path" in rows[0]:
        summary["paths"] = dict(Counter(row.get("path", "") for row in rows))
        summary["result_counts"] = dict(
            Counter(row.get("result", "") for row in rows)
        )
    return summary


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "experiment_id": "normal_v1",
        "files": [
            summarize_csv(path)
            for path in sorted(LOG_DIR.glob("*.csv"))
        ],
    }
    SUMMARY_FILE.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
