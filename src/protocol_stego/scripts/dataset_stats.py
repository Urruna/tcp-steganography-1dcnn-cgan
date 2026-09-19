"""Dataset statistics and sanity checks."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import numpy as np


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _session_stats(session_dir: Path, label: int, mode: str) -> dict[str, object]:
    records = [
        record
        for record in _read_jsonl(session_dir / "receiver.jsonl")
        if record.get("observed_length") is not None
    ]
    lengths = [int(record["observed_length"]) for record in records]
    timestamps = [float(record.get("timestamp", 0.0)) for record in records]
    gaps = [
        max(0.0, timestamps[index] - timestamps[index - 1])
        for index in range(1, len(timestamps))
    ]
    metadata = _read_json(session_dir / "metadata.json")
    metrics = metadata.get("metrics", {})
    return {
        "session_id": session_dir.name,
        "mode": mode,
        "label": label,
        "success": bool(metadata.get("success")),
        "event_count": len(records),
        "total_bytes": sum(lengths),
        "length_min": min(lengths) if lengths else None,
        "length_max": max(lengths) if lengths else None,
        "ber": metrics.get("ber"),
        "frame_error_rate": metrics.get("frame_error_rate"),
        "crc_failure_count": metrics.get("crc_failure_count"),
    }


def collect(raw_root: Path, processed_dir: Path) -> dict[str, object]:
    per_session: list[dict[str, object]] = []
    all_lengths: list[int] = []
    all_gaps: list[float] = []
    for mode, label in (("normal", 0), ("stego", 1)):
        mode_dir = raw_root / mode
        if not mode_dir.exists():
            continue
        for session_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
            metadata_path = session_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            stats = _session_stats(session_dir, label, mode)
            per_session.append(stats)
            records = [
                record
                for record in _read_jsonl(session_dir / "receiver.jsonl")
                if record.get("observed_length") is not None
            ]
            all_lengths.extend(int(record["observed_length"]) for record in records)
            timestamps = [float(record.get("timestamp", 0.0)) for record in records]
            all_gaps.extend(
                max(0.0, timestamps[index] - timestamps[index - 1])
                for index in range(1, len(timestamps))
            )

    window_path = processed_dir / "windows.npz"
    index_path = processed_dir / "index.jsonl"
    sample_count = 0
    class_distribution = {"normal": 0, "stego": 0}
    X_shape: list[int] = []
    y_shape: list[int] = []
    nan_inf = None
    if window_path.exists() and index_path.exists():
        data = np.load(window_path)
        X = data["X"]
        y = data["y"]
        sample_count = int(len(y))
        X_shape = list(X.shape)
        y_shape = list(y.shape)
        class_distribution = {
            "normal": int((y == 0).sum()),
            "stego": int((y == 1).sum()),
        }
        nan_inf = bool(np.isnan(X).any() or np.isinf(X).any())

    stego_sessions = [item for item in per_session if item["mode"] == "stego"]
    normal_sessions = [item for item in per_session if item["mode"] == "normal"]

    def mean_or_none(values: list[float]) -> float | None:
        return statistics.fmean(values) if values else None

    def stdev_or_none(values: list[float]) -> float | None:
        return statistics.pstdev(values) if len(values) > 1 else 0.0 if values else None

    return {
        "session_count": len(per_session),
        "normal_session_count": len(normal_sessions),
        "stego_session_count": len(stego_sessions),
        "successful_sessions": sum(1 for item in per_session if item["success"]),
        "event_count": len(all_lengths),
        "sample_count": sample_count,
        "class_distribution": class_distribution,
        "X_shape": X_shape,
        "y_shape": y_shape,
        "nan_or_inf": nan_inf,
        "length": {
            "mean": mean_or_none([float(value) for value in all_lengths]),
            "std": stdev_or_none([float(value) for value in all_lengths]),
            "min": min(all_lengths) if all_lengths else None,
            "max": max(all_lengths) if all_lengths else None,
        },
        "inter_arrival": {
            "mean": mean_or_none(all_gaps),
            "std": stdev_or_none(all_gaps),
        },
        "stego_only_metrics": {
            "ber": mean_or_none(
                [float(item["ber"]) for item in stego_sessions if item["ber"] is not None]
            ),
            "frame_error_rate": mean_or_none(
                [
                    float(item["frame_error_rate"])
                    for item in stego_sessions
                    if item["frame_error_rate"] is not None
                ]
            ),
            "crc_failure_count": sum(
                int(item["crc_failure_count"])
                for item in stego_sessions
                if item["crc_failure_count"] is not None
            ),
            "normal_metrics": "N/A (normal has no BER/CRC/frame decoding)",
        },
        "per_session": per_session,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="dataset statistics")
    base = Path(__file__).resolve().parents[1]
    parser.add_argument("--raw-dir", default=str(base / "dataset" / "raw"))
    parser.add_argument("--processed-dir", default=str(base / "dataset" / "processed"))
    parser.add_argument("--out", default=str(base / "dataset" / "processed" / "stats.json"))
    args = parser.parse_args()
    stats = collect(Path(args.raw_dir), Path(args.processed_dir))
    Path(args.out).write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
