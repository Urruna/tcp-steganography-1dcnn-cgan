"""Build fixed-window samples from raw session JSONL data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

FEATURES = ["direction", "length", "inter_arrival_time", "cumulative_bytes"]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _direction_value(direction: object) -> int:
    if direction == "forward":
        return 1
    if direction == "reverse":
        return -1
    raise ValueError(f"invalid direction: {direction!r}")


def _session_events(session_dir: Path) -> list[dict[str, object]]:
    """Use receiver-side observed_length as the event source.

    We deliberately do not substitute sender-side actual_write_length here:
    the dataset must preserve the observed application-layer receive behavior.
    """
    records = _read_jsonl(session_dir / "receiver.jsonl")
    events: list[dict[str, object]] = []
    for record in records:
        if record.get("observed_length") is None:
            continue
        events.append(
            {
                "timestamp": float(record.get("timestamp", 0.0)),
                "direction": _direction_value(record.get("direction", "forward")),
                "length": int(record["observed_length"]),
            }
        )
    events.sort(key=lambda item: item["timestamp"])
    cumulative = {1: 0, -1: 0}
    previous_ts: float | None = None
    for event in events:
        timestamp = float(event["timestamp"])
        event["inter_arrival_time"] = (
            0.0 if previous_ts is None else max(0.0, timestamp - previous_ts)
        )
        previous_ts = timestamp
        direction = int(event["direction"])
        cumulative[direction] += int(event["length"])
        event["cumulative_bytes"] = cumulative[direction]
    return events


def _windows_for_session(
    events: list[dict[str, object]],
    *,
    session_id: str,
    label: int,
    window_size: int,
) -> tuple[list[np.ndarray], list[dict[str, object]]]:
    samples: list[np.ndarray] = []
    index: list[dict[str, object]] = []
    for window_id, start in enumerate(range(0, len(events) - window_size + 1, window_size)):
        window = events[start : start + window_size]
        matrix = np.asarray(
            [
                [event["direction"] for event in window],
                [event["length"] for event in window],
                [event["inter_arrival_time"] for event in window],
                [event["cumulative_bytes"] for event in window],
            ],
            dtype=np.float64,
        )
        samples.append(matrix)
        index.append(
            {
                "session_id": session_id,
                "window_id": window_id,
                "label": label,
                "start_event": start,
                "end_event": start + window_size,
            }
        )
    return samples, index


def build_dataset(raw_root: Path, out_dir: Path, window_size: int) -> dict[str, object]:
    if window_size <= 0:
        raise ValueError("window_size must be > 0")
    all_samples: list[np.ndarray] = []
    all_labels: list[int] = []
    all_index: list[dict[str, object]] = []
    sessions_seen = 0
    sessions_used = 0
    skipped: list[dict[str, object]] = []

    for mode, label in (("normal", 0), ("stego", 1)):
        mode_dir = raw_root / mode
        if not mode_dir.exists():
            continue
        for session_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
            metadata_path = session_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            sessions_seen += 1
            metadata = _read_json(metadata_path)
            session_id = str(metadata.get("session_id", session_dir.name))
            events = _session_events(session_dir)
            if len(events) < window_size:
                skipped.append(
                    {
                        "session_id": session_id,
                        "event_count": len(events),
                        "reason": "fewer events than window_size",
                    }
                )
                continue
            samples, index = _windows_for_session(
                events,
                session_id=session_id,
                label=label,
                window_size=window_size,
            )
            all_samples.extend(samples)
            all_labels.extend([label] * len(samples))
            all_index.extend(index)
            sessions_used += 1

    if not all_samples:
        raise RuntimeError("no windows were produced; check raw sessions and window_size")
    X = np.stack(all_samples).astype(np.float32)
    y = np.asarray(all_labels, dtype=np.int64)
    if X.shape[1:] != (len(FEATURES), window_size):
        raise RuntimeError(f"unexpected X shape: {X.shape}")
    if np.isnan(X).any() or np.isinf(X).any():
        raise RuntimeError("dataset contains NaN/Inf")

    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "windows.npz", X=X, y=y)
    (out_dir / "index.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in all_index) + "\n",
        encoding="utf-8",
    )
    summary = {
        "window_size": window_size,
        "features": FEATURES,
        "X_shape": list(X.shape),
        "y_shape": list(y.shape),
        "sessions_seen": sessions_seen,
        "sessions_used": sessions_used,
        "skipped_sessions": skipped,
        "class_distribution": {
            "normal": int((y == 0).sum()),
            "stego": int((y == 1).sum()),
        },
    }
    (out_dir / "build_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="build fixed-window dataset")
    parser.add_argument(
        "--raw-dir",
        default=str(Path(__file__).resolve().parents[1] / "dataset" / "raw"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[1] / "dataset" / "processed"),
    )
    parser.add_argument("--window-size", type=int, default=128)
    args = parser.parse_args()
    summary = build_dataset(Path(args.raw_dir), Path(args.out_dir), args.window_size)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
