"""Run a full data-quality audit and generate docs/DATA_QUALITY_REPORT.md."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

FEATURES = ["direction", "length", "inter_arrival_time", "cumulative_bytes"]


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


def _stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
        }
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def _inter_arrivals(records: list[dict[str, object]]) -> list[float]:
    timestamps = [float(record.get("timestamp", 0.0)) for record in records]
    return [
        max(0.0, timestamps[index] - timestamps[index - 1])
        for index in range(1, len(timestamps))
    ]


def _collect_sessions(raw_root: Path) -> list[dict[str, object]]:
    sessions: list[dict[str, object]] = []
    for mode, label in (("normal", 0), ("stego", 1)):
        mode_dir = raw_root / mode
        if not mode_dir.exists():
            continue
        for session_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
            metadata_path = session_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = _read_json(metadata_path)
            sender_events = _read_jsonl(session_dir / "sender.jsonl")
            receiver_events = _read_jsonl(session_dir / "receiver.jsonl")
            observed_records = [
                record
                for record in receiver_events
                if record.get("observed_length") is not None
            ]
            lengths = [int(record["observed_length"]) for record in observed_records]
            gaps = _inter_arrivals(observed_records)
            metrics = metadata.get("metrics", {})
            duration_ms = (
                float(metrics.get("duration_ms"))
                if isinstance(metrics, dict) and metrics.get("duration_ms") is not None
                else None
            )
            timestamps = [float(record.get("timestamp", 0.0)) for record in observed_records]
            if duration_ms is None and len(timestamps) > 1:
                duration_ms = (max(timestamps) - min(timestamps)) * 1000.0
            sessions.append(
                {
                    "session_id": str(metadata.get("session_id", session_dir.name)),
                    "label": int(metadata.get("label", label)),
                    "mode": str(metadata.get("mode", mode)),
                    "timestamp": metadata.get("timestamp"),
                    "success": bool(metadata.get("success")),
                    "metadata": metadata,
                    "sender_events": sender_events,
                    "receiver_events": receiver_events,
                    "observed_records": observed_records,
                    "event_count": len(observed_records),
                    "total_bytes": sum(lengths),
                    "lengths": lengths,
                    "inter_arrivals": gaps,
                    "inter_arrival_mean": statistics.fmean(gaps) if gaps else None,
                    "inter_arrival_std": statistics.pstdev(gaps) if len(gaps) > 1 else (0.0 if gaps else None),
                    "duration_s": duration_ms / 1000.0 if duration_ms is not None else None,
                    "avg_event_length": statistics.fmean(lengths) if lengths else None,
                    "sender_log_lines": len(sender_events),
                    "receiver_log_lines": len(receiver_events),
                    "sender_result": _read_json(session_dir / "sender_result.json"),
                    "receiver_result": _read_json(session_dir / "receiver_result.json"),
                    "session_dir": str(session_dir),
                }
            )
    return sessions


def _class_metric_stats(
    sessions: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for mode in ("normal", "stego"):
        values = [
            float(session[field])
            for session in sessions
            if session["mode"] == mode and session.get(field) is not None
        ]
        result[mode] = _stats(values)
    return result


def _modulation_audit(sessions: list[dict[str, object]]) -> dict[str, object]:
    target_counts: Counter = Counter()
    bit_counts: Counter = Counter()
    actual_counts: Counter = Counter()
    observed_counts: Counter = Counter()
    actual_matches_target = 0
    actual_total = 0
    actual_equals_observed = 0
    compared_total = 0
    crosstab: Counter = Counter()
    bit_errors = 0
    bit_total = 0
    frame_errors = 0
    frame_total = 0
    crc_failures = 0
    per_session: list[dict[str, object]] = []

    for session in sessions:
        if session["mode"] != "stego":
            continue
        sender_writes = [
            record
            for record in session["sender_events"]
            if record.get("event") == "write"
        ]
        receiver_reads = [
            record
            for record in session["observed_records"]
            if record.get("observed_length") is not None
        ]
        session_targets = Counter()
        session_bits = Counter()
        session_actuals = Counter()
        session_observed = Counter()
        for record in sender_writes:
            if record.get("target_length") is not None:
                session_targets[int(record["target_length"])] += 1
                target_counts[int(record["target_length"])] += 1
            if record.get("bit") is not None:
                session_bits[int(record["bit"])] += 1
                bit_counts[int(record["bit"])] += 1
            if record.get("actual_write_length") is not None:
                actual = int(record["actual_write_length"])
                session_actuals[actual] += 1
                actual_counts[actual] += 1
                actual_total += 1
                if record.get("target_length") is not None and actual == int(record["target_length"]):
                    actual_matches_target += 1
        for record in receiver_reads:
            observed = int(record["observed_length"])
            session_observed[observed] += 1
            observed_counts[observed] += 1

        actual_seq = [
            int(record["actual_write_length"])
            for record in sender_writes
            if record.get("actual_write_length") is not None
        ]
        observed_seq = [
            int(record["observed_length"]) for record in receiver_reads
        ]
        for actual, observed in zip(actual_seq, observed_seq):
            compared_total += 1
            crosstab[(actual, observed)] += 1
            if actual == observed:
                actual_equals_observed += 1

        sender_result = session["sender_result"]
        receiver_result = session["receiver_result"]
        sent_bits = list(sender_result.get("sender_bits", []))
        recovered_bits = list(receiver_result.get("recovered_bits", []))
        session_bit_errors = abs(len(sent_bits) - len(recovered_bits)) + sum(
            1 for left, right in zip(sent_bits, recovered_bits) if left != right
        )
        bit_errors += session_bit_errors
        bit_total += len(sent_bits)
        frame_count = int(sender_result.get("frame_count", 0))
        received_frames = len(receiver_result.get("frames", []))
        session_frame_errors = max(0, frame_count - received_frames)
        frame_errors += session_frame_errors
        frame_total += frame_count
        session_crc = int(receiver_result.get("crc_failures", 0))
        crc_failures += session_crc
        per_session.append(
            {
                "session_id": session["session_id"],
                "success": session["success"],
                "targets": dict(session_targets),
                "bits": dict(session_bits),
                "actual_lengths": dict(session_actuals),
                "observed_lengths": dict(session_observed),
                "bit_errors": session_bit_errors,
                "bit_total": len(sent_bits),
                "frame_errors": session_frame_errors,
                "frame_total": frame_count,
                "crc_failures": session_crc,
                "ber": session_bit_errors / len(sent_bits) if sent_bits else None,
                "frame_error_rate": session_frame_errors / frame_count if frame_count else None,
            }
        )

    observed_other = sum(
        count for length, count in observed_counts.items() if length not in (800, 1200)
    )
    return {
        "target_counts": dict(target_counts),
        "bit_counts": dict(bit_counts),
        "actual_counts": dict(actual_counts),
        "observed_counts": dict(observed_counts),
        "observed_other": observed_other,
        "actual_matches_target": actual_matches_target,
        "actual_total": actual_total,
        "actual_target_ratio": actual_matches_target / actual_total if actual_total else None,
        "actual_equals_observed": actual_equals_observed,
        "compared_total": compared_total,
        "actual_observed_ratio": actual_equals_observed / compared_total if compared_total else None,
        "crosstab": [
            {"actual": actual, "observed": observed, "count": count}
            for (actual, observed), count in sorted(crosstab.items())
        ],
        "bit_errors": bit_errors,
        "bit_total": bit_total,
        "ber": bit_errors / bit_total if bit_total else None,
        "frame_errors": frame_errors,
        "frame_total": frame_total,
        "frame_error_rate": frame_errors / frame_total if frame_total else None,
        "crc_failures": crc_failures,
        "crc_failure_rate": crc_failures / frame_total if frame_total else None,
        "per_session": per_session,
    }


def _normal_audit(sessions: list[dict[str, object]]) -> dict[str, object]:
    lengths: list[int] = []
    sender_events = 0
    sender_has_modulation_fields = 0
    exact_800 = 0
    exact_1200 = 0
    for session in sessions:
        if session["mode"] != "normal":
            continue
        lengths.extend(int(value) for value in session["lengths"])
        for record in session["sender_events"]:
            sender_events += 1
            if "target_length" in record or "bit" in record:
                sender_has_modulation_fields += 1
        exact_800 += sum(1 for value in session["lengths"] if value == 800)
        exact_1200 += sum(1 for value in session["lengths"] if value == 1200)
    return {
        "sender_events": sender_events,
        "sender_has_modulation_fields": sender_has_modulation_fields,
        "exact_800": exact_800,
        "exact_1200": exact_1200,
        "length_stats": _stats([float(value) for value in lengths]),
    }


def _leakage_audit(splits_dir: Path, processed_dir: Path) -> dict[str, object]:
    split_sessions: dict[str, set[str]] = {}
    split_windows: dict[str, list[dict[str, object]]] = {}
    for split_name in ("train", "val", "test"):
        index_path = splits_dir / f"{split_name}_index.jsonl"
        if not index_path.exists():
            split_sessions[split_name] = set()
            split_windows[split_name] = []
            continue
        windows = _read_jsonl(index_path)
        split_windows[split_name] = windows
        split_sessions[split_name] = {str(item["session_id"]) for item in windows}

    overlaps = {}
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlaps[f"{left}_{right}"] = sorted(
            split_sessions[left] & split_sessions[right]
        )

    session_split_count: Counter = Counter()
    for split_name, sessions in split_sessions.items():
        for session_id in sessions:
            session_split_count[session_id] += 1
    multi_split_sessions = [
        session_id for session_id, count in session_split_count.items() if count > 1
    ]

    data = np.load(processed_dir / "windows.npz")
    X = data["X"]
    hashes: dict[str, list[int]] = defaultdict(list)
    for index in range(len(X)):
        digest = hashlib.sha256(X[index].tobytes()).hexdigest()
        hashes[digest].append(index)
    duplicates = [indices for indices in hashes.values() if len(indices) > 1]
    return {
        "split_sessions": {key: sorted(value) for key, value in split_sessions.items()},
        "overlaps": overlaps,
        "multi_split_sessions": multi_split_sessions,
        "duplicate_sample_groups": duplicates[:20],
        "duplicate_sample_count": sum(len(group) - 1 for group in duplicates),
    }


def _xy_audit(processed_dir: Path) -> dict[str, object]:
    data = np.load(processed_dir / "windows.npz")
    X = data["X"]
    y = data["y"]
    feature_stats = {}
    class_feature_stats = {}
    for index, feature in enumerate(FEATURES):
        values = X[:, index, :].reshape(-1).astype(float)
        feature_stats[feature] = _stats(values.tolist())
        class_feature_stats[feature] = {
            "normal": _stats(
                X[y == 0, index, :].reshape(-1).astype(float).tolist()
            ),
            "stego": _stats(
                X[y == 1, index, :].reshape(-1).astype(float).tolist()
            ),
        }
    return {
        "X_shape": list(X.shape),
        "y_shape": list(y.shape),
        "X_dtype": str(X.dtype),
        "y_dtype": str(y.dtype),
        "window_size": int(X.shape[2]) if X.ndim == 3 else None,
        "feature_count": int(X.shape[1]) if X.ndim == 3 else None,
        "features": FEATURES,
        "nan_count": int(np.isnan(X).sum()),
        "inf_count": int(np.isinf(X).sum()),
        "feature_stats": feature_stats,
        "class_feature_stats": class_feature_stats,
        "class_distribution": {
            "normal": int((y == 0).sum()),
            "stego": int((y == 1).sum()),
        },
    }


def _svg_grouped_bar(
    path: Path,
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
) -> None:
    width, height = 960, 420
    margin_left, margin_bottom, margin_top = 70, 90, 50
    plot_width = width - margin_left - 40
    plot_height = height - margin_top - margin_bottom
    max_value = max((max(values) for _, values, _ in series if values), default=1.0)
    max_value = max(max_value, 1.0)
    group_width = plot_width / max(1, len(labels))
    bar_width = group_width / (len(series) + 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-size="18">{title}</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height-margin_bottom}" stroke="black"/>',
        f'<line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-40}" y2="{height-margin_bottom}" stroke="black"/>',
    ]
    for group_index, label in enumerate(labels):
        x0 = margin_left + group_index * group_width
        for series_index, (name, values, color) in enumerate(series):
            value = values[group_index] if group_index < len(values) else 0.0
            bar_height = value / max_value * plot_height
            x = x0 + (series_index + 0.5) * bar_width
            y = height - margin_bottom - bar_height
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" fill="{color}"/>'
            )
        parts.append(
            f'<text x="{x0 + group_width/2:.1f}" y="{height-margin_bottom+18}" '
            f'text-anchor="middle" font-size="11">{label}</text>'
        )
    legend_x = margin_left
    for name, _, color in series:
        parts.append(
            f'<rect x="{legend_x}" y="{height-40}" width="14" height="14" fill="{color}"/>'
            f'<text x="{legend_x+20}" y="{height-28}" font-size="12">{name}</text>'
        )
        legend_x += 110
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def _binned(values: list[float], edges: list[float]) -> list[float]:
    counts = [0] * (len(edges) - 1)
    for value in values:
        for index in range(len(edges) - 1):
            if edges[index] <= value < edges[index + 1]:
                counts[index] += 1
                break
        else:
            if values and value >= edges[-1]:
                counts[-1] += 1
    return [float(value) for value in counts]


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def build_report(raw_root: Path, processed_dir: Path, splits_dir: Path, docs_dir: Path) -> dict[str, object]:
    sessions = _collect_sessions(raw_root)
    modulation = _modulation_audit(sessions)
    normal_audit = _normal_audit(sessions)
    leakage = _leakage_audit(splits_dir, processed_dir)
    xy = _xy_audit(processed_dir)

    session_rows = [
        [
            session["session_id"],
            session["mode"],
            session["label"],
            session["success"],
            session["event_count"],
            session["total_bytes"],
            _fmt(session["duration_s"]),
            session["sender_log_lines"],
            session["receiver_log_lines"],
        ]
        for session in sessions
    ]

    comparison = {}
    for field, label in (
        ("duration_s", "duration_s"),
        ("event_count", "event_count"),
        ("total_bytes", "total_bytes"),
        ("avg_event_length", "avg_event_length"),
        ("inter_arrival_mean", "inter_arrival_mean_s"),
    ):
        comparison[field] = _class_metric_stats(sessions, field)

    normal_sessions = [s for s in sessions if s["mode"] == "normal"]
    stego_sessions = [s for s in sessions if s["mode"] == "stego"]
    anomalies: list[str] = []
    if len(normal_sessions) < 50:
        anomalies.append(
            "preferred normal session count >=50 not reached "
            f"(current {len(normal_sessions)})"
        )
    if len(stego_sessions) < 50:
        anomalies.append(
            "preferred stego session count >=50 not reached "
            f"(current {len(stego_sessions)})"
        )
    if xy["nan_count"] or xy["inf_count"]:
        anomalies.append("X contains NaN or Inf")
    if any(leakage["overlaps"].values()):
        anomalies.append("train/val/test session overlap detected")
    if leakage["multi_split_sessions"]:
        anomalies.append("a session appears in multiple splits")
    if leakage["duplicate_sample_count"]:
        anomalies.append("duplicate window samples detected")
    if normal_audit["sender_has_modulation_fields"]:
        anomalies.append("normal sender log contains modulation fields")
    if modulation["observed_other"]:
        anomalies.append("stego observed_length contains values outside 800/1200")
    if modulation["ber"] not in (None, 0.0):
        anomalies.append("stego BER is non-zero")
    if modulation["frame_error_rate"] not in (None, 0.0):
        anomalies.append("stego frame error rate is non-zero")

    # Comparability: mean duration / event count / total bytes must be close.
    comparability = {}
    for field in ("duration_s", "event_count", "total_bytes"):
        normal_mean = statistics.fmean(
            [float(s[field]) for s in normal_sessions if s[field] is not None]
        ) if normal_sessions else 0.0
        stego_mean = statistics.fmean(
            [float(s[field]) for s in stego_sessions if s[field] is not None]
        ) if stego_sessions else 0.0
        ratio = (
            max(normal_mean, stego_mean) / max(1e-9, min(normal_mean, stego_mean))
            if normal_mean and stego_mean
            else float("inf")
        )
        comparability[field] = {
            "normal_mean": normal_mean,
            "stego_mean": stego_mean,
            "ratio": ratio,
        }
    comparable = all(
        item["ratio"] <= 2.0 for item in comparability.values()
    )

    if any(
        item
        for item in (
            leakage["overlaps"]["train_val"],
            leakage["overlaps"]["train_test"],
            leakage["overlaps"]["val_test"],
            leakage["multi_split_sessions"],
            xy["nan_count"],
            xy["inf_count"],
            normal_audit["sender_has_modulation_fields"],
        )
    ):
        conclusion = "NEEDS FIX"
    elif (
        len(normal_sessions) >= 20
        and len(stego_sessions) >= 20
        and xy["X_shape"][0] >= 100
        and comparable
        and modulation["ber"] in (None, 0.0)
        and modulation["frame_error_rate"] in (None, 0.0)
        and modulation["crc_failure_rate"] in (None, 0.0)
    ):
        conclusion = "READY_FOR_CNN"
    else:
        conclusion = "NEEDS MORE DATA"

    plots_dir = docs_dir / "plots"
    normal_lengths = [
        float(value)
        for session in sessions
        if session["mode"] == "normal"
        for value in session["lengths"]
    ]
    stego_lengths = [
        float(value)
        for session in sessions
        if session["mode"] == "stego"
        for value in session["lengths"]
    ]
    length_edges = [0, 400, 700, 900, 1100, 1300, 3000]
    length_labels = ["0-399", "400-699", "700-899", "900-1099", "1100-1299", "1300+"]
    _svg_grouped_bar(
        plots_dir / "length_distribution.svg",
        "Normal vs Stego event length distribution",
        length_labels,
        [
            ("normal", _binned(normal_lengths, length_edges), "#4c78a8"),
            ("stego", _binned(stego_lengths, length_edges), "#f58518"),
        ],
    )
    normal_gaps = [
        gap
        for session in sessions
        if session["mode"] == "normal"
        for gap in session["inter_arrivals"]
    ]
    stego_gaps = [
        gap
        for session in sessions
        if session["mode"] == "stego"
        for gap in session["inter_arrivals"]
    ]
    gap_edges = [0, 0.005, 0.015, 0.025, 0.05, 1.0]
    gap_labels = ["<5ms", "5-15ms", "15-25ms", "25-50ms", "50ms+"]
    _svg_grouped_bar(
        plots_dir / "inter_arrival_distribution.svg",
        "Normal vs Stego inter-arrival distribution",
        gap_labels,
        [
            ("normal", _binned(normal_gaps, gap_edges), "#4c78a8"),
            ("stego", _binned(stego_gaps, gap_edges), "#f58518"),
        ],
    )
    _svg_grouped_bar(
        plots_dir / "events_per_session.svg",
        "Events per session",
        [session["session_id"] for session in sessions],
        [
            (
                "event_count",
                [float(session["event_count"]) for session in sessions],
                "#54a24b",
            )
        ],
    )

    report = {
        "sessions": sessions,
        "modulation": modulation,
        "normal_audit": normal_audit,
        "leakage": leakage,
        "xy": xy,
        "comparison": comparison,
        "anomalies": anomalies,
        "conclusion": conclusion,
        "comparability": comparability,
    }
    (processed_dir / "data_quality_report.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    _write_markdown(docs_dir / "DATA_QUALITY_REPORT.md", report)
    return report


def _write_markdown(path: Path, report: dict[str, object]) -> None:
    sessions = report["sessions"]  # type: ignore[assignment]
    modulation = report["modulation"]  # type: ignore[assignment]
    normal_audit = report["normal_audit"]  # type: ignore[assignment]
    leakage = report["leakage"]  # type: ignore[assignment]
    xy = report["xy"]  # type: ignore[assignment]
    comparison = report["comparison"]  # type: ignore[assignment]
    anomalies = report["anomalies"]  # type: ignore[assignment]
    conclusion = report["conclusion"]

    lines: list[str] = [
        "# DATA QUALITY REPORT",
        "",
        f"Conclusion: **{conclusion}**",
        "",
        "## 1 数据集概况",
        "",
    ]
    lines.append(
        _markdown_table(
            ["session_id", "mode", "label", "success", "events", "bytes", "duration_s", "sender_lines", "receiver_lines"],
            [
                [
                    session["session_id"],
                    session["mode"],
                    session["label"],
                    session["success"],
                    session["event_count"],
                    session["total_bytes"],
                    _fmt(session["duration_s"]),
                    session["sender_log_lines"],
                    session["receiver_log_lines"],
                ]
                for session in sessions
            ],
        )
    )
    lines.extend(["", "## 2 Session 统计", ""])
    modes = Counter(session["mode"] for session in sessions)
    success = Counter(
        session["mode"] for session in sessions if session["success"]
    )
    lines.append(
        _markdown_table(
            ["mode", "sessions", "success", "failed"],
            [
                [mode, modes.get(mode, 0), success.get(mode, 0), modes.get(mode, 0) - success.get(mode, 0)]
                for mode in ("normal", "stego")
            ],
        )
    )
    lines.extend(["", "## 3 Normal / Stego 对比", ""])
    for field in (
        "duration_s",
        "event_count",
        "total_bytes",
        "avg_event_length",
        "inter_arrival_mean",
    ):
        lines.append(f"### {field}")
        lines.append("")
        lines.append(
            _markdown_table(
                ["mode", "min", "max", "mean", "median", "std"],
                [
                    [
                        mode,
                        _fmt(comparison[field][mode]["min"]),
                        _fmt(comparison[field][mode]["max"]),
                        _fmt(comparison[field][mode]["mean"]),
                        _fmt(comparison[field][mode]["median"]),
                        _fmt(comparison[field][mode]["std"]),
                    ]
                    for mode in ("normal", "stego")
                ],
            )
        )
        lines.append("")
    lines.append("### Comparability ratios")
    lines.append("")
    lines.append(
        _markdown_table(
            ["metric", "normal_mean", "stego_mean", "max/min ratio"],
            [
                [
                    field,
                    _fmt(item["normal_mean"]),
                    _fmt(item["stego_mean"]),
                    _fmt(item["ratio"]),
                ]
                for field, item in report["comparability"].items()
            ],
        )
    )
    lines.append("")

    lines.extend(["## 4 Stego 调制验证", ""])
    lines.append(
        _markdown_table(
            ["item", "value"],
            [
                ["target counts", modulation["target_counts"]],
                ["bit counts", modulation["bit_counts"]],
                ["actual_write_length counts", modulation["actual_counts"]],
                ["observed_length counts", modulation["observed_counts"]],
                ["observed outside 800/1200", modulation["observed_other"]],
                ["actual == target ratio", _fmt(modulation["actual_target_ratio"])],
                ["actual == observed ratio", _fmt(modulation["actual_observed_ratio"])],
                ["BER", _fmt(modulation["ber"])],
                ["frame error rate", _fmt(modulation["frame_error_rate"])],
                ["CRC failure rate", _fmt(modulation["crc_failure_rate"])],
            ],
        )
    )
    lines.extend(["", "## 5 数据泄漏检查", ""])
    lines.append(
        _markdown_table(
            ["check", "result"],
            [
                ["train ∩ val", leakage["overlaps"]["train_val"]],
                ["train ∩ test", leakage["overlaps"]["train_test"]],
                ["val ∩ test", leakage["overlaps"]["val_test"]],
                ["sessions in multiple splits", leakage["multi_split_sessions"]],
                ["duplicate sample count", leakage["duplicate_sample_count"]],
            ],
        )
    )
    lines.extend(["", "## 6 X / y 检查", ""])
    lines.append(
        _markdown_table(
            ["item", "value"],
            [
                ["X.shape", xy["X_shape"]],
                ["y.shape", xy["y_shape"]],
                ["X.dtype", xy["X_dtype"]],
                ["y.dtype", xy["y_dtype"]],
                ["features", xy["features"]],
                ["window_size", xy["window_size"]],
                ["NaN count", xy["nan_count"]],
                ["Inf count", xy["inf_count"]],
                ["class distribution", xy["class_distribution"]],
            ],
        )
    )
    lines.extend(["", "## 7 特征统计", ""])
    for feature in FEATURES:
        lines.append(f"### {feature}")
        lines.append("")
        lines.append(
            _markdown_table(
                ["mode", "min", "max", "mean", "median", "std"],
                [
                    [
                        mode,
                        _fmt(xy["class_feature_stats"][feature][mode]["min"]),
                        _fmt(xy["class_feature_stats"][feature][mode]["max"]),
                        _fmt(xy["class_feature_stats"][feature][mode]["mean"]),
                        _fmt(xy["class_feature_stats"][feature][mode]["median"]),
                        _fmt(xy["class_feature_stats"][feature][mode]["std"]),
                    ]
                    for mode in ("normal", "stego")
                ],
            )
        )
        lines.append("")
    lines.extend(["## 8 异常数据与观察", ""])
    lines.extend([f"- {item}" for item in anomalies] or ["- none"])
    lines.extend(
        [
            "",
            "## 9 数据质量问题",
            "",
            "Normal length stats: "
            f"{normal_audit['length_stats']}",
            "",
            "- normal sender contains modulation fields: "
            f"{normal_audit['sender_has_modulation_fields']}",
            f"- normal exact 800 events: {normal_audit['exact_800']}",
            f"- normal exact 1200 events: {normal_audit['exact_1200']}",
            "",
            "## 10 是否可以进入 1D-CNN",
            "",
            f"结论：**{conclusion}**",
            "",
        ]
    )
    if conclusion == "READY_FOR_CNN":
        lines.extend(
            [
                "## 11 下一步建议",
                "",
                "- 当前规模与可比性满足首轮 1D-CNN 基线实验。",
                "- CNN 结果应解释为对 800/1200 modulation 的检测，"
                "不能直接推广为一般隐写可检测性。",
                "- 建议继续增加 Normal 业务多样性（不同文件大小、双向 HTTP 业务）。",
                "- 训练 CNN 时同时报告 rule-based 与传统 ML baseline。",
                "- 生成的多份统计图见 docs/plots/。",
                "",
            ]
        )
    elif conclusion == "NEEDS MORE DATA":
        lines.extend(
            [
                "## 11 下一步建议",
                "",
                "- 按同一配置扩大 normal/stego session 数。",
                "- 保持 session 级 train/val/test 划分，不跨 session 切窗口。",
                "- 保持 actual_write_length 与 observed_length 分开记录。",
                "- 生成的多份统计图见 docs/plots/。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## 11 下一步建议",
                "",
                "- 先修复 P0 数据/实验问题，再重新采集与评估。",
                "- 修复后重新运行 dataset_builder / split / stats / quality report。",
                "- 生成的多份统计图见 docs/plots/。",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="data quality report")
    base = Path(__file__).resolve().parents[1]
    parser.add_argument("--raw-dir", default=str(base / "dataset" / "raw"))
    parser.add_argument("--processed-dir", default=str(base / "dataset" / "processed"))
    parser.add_argument("--splits-dir", default=str(base / "dataset" / "splits"))
    parser.add_argument("--docs-dir", default=str(base / "docs"))
    args = parser.parse_args()
    report = build_report(
        Path(args.raw_dir),
        Path(args.processed_dir),
        Path(args.splits_dir),
        Path(args.docs_dir),
    )
    print(json.dumps({
        "conclusion": report["conclusion"],
        "anomalies": report["anomalies"],
        "X_shape": report["xy"]["X_shape"],
        "y_shape": report["xy"]["y_shape"],
        "class_distribution": report["xy"]["class_distribution"],
        "modulation": {
            key: report["modulation"][key]
            for key in (
                "target_counts",
                "bit_counts",
                "observed_counts",
                "actual_target_ratio",
                "actual_observed_ratio",
                "ber",
                "frame_error_rate",
                "crc_failure_rate",
            )
        },
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
