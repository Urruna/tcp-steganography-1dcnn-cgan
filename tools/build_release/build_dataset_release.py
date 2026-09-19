"""Build the standalone dataset_release package.

Stages:
    data      -- copy/normalize raw and processed data, extract X.npy/y.npy
    finalize  -- integrity checks, SHA256SUMS.txt, dataset_release.zip
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import shutil
import struct
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "src" / "protocol_stego"
DATASET_ROOT = PROJECT_ROOT / "dataset"
DOCS_ROOT = PROJECT_ROOT / "docs"
RELEASE_ROOT = REPO_ROOT / "releases" / "dataset_release_v1"


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _stage_historical(docker_proxy_a: Path, docker_proxy_b: Path) -> None:
    historical = RELEASE_ROOT / "historical_normal"
    raw_docker = historical / "raw" / "docker_chain_smoke"
    raw_baseline = historical / "raw" / "baseline_lenmix_v1"
    processed = historical / "processed"
    for path in (raw_docker, raw_baseline, processed):
        path.mkdir(parents=True, exist_ok=True)

    _copy_file(docker_proxy_a, raw_docker / "proxy_a_events.csv")
    _copy_file(docker_proxy_b, raw_docker / "proxy_b_events.csv")
    for name in ("client_events.csv", "proxy_a_events.csv", "proxy_b_events.csv"):
        _copy_file(REPO_ROOT / "baseline_lenmix_v1" / name, raw_baseline / name)

    # Normalized early Docker view: keep only rows that follow the documented
    # 7-column schema (the later 2026-09-17 rows used a different writer schema).
    normalized_rows: list[dict[str, object]] = []
    for proxy_name, path in (("proxy_a", docker_proxy_a), ("proxy_b", docker_proxy_b)):
        with path.open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row.get("direction") in ("forward", "reverse"):
                    normalized_rows.append(
                        {
                            "timestamp": row["timestamp"],
                            "proxy_name": proxy_name,
                            "session_id": row["session_id"],
                            "direction": row["direction"],
                            "event_index": row["event_index"],
                            "byte_length": row["byte_length"],
                            "inter_event_gap_ms": row["inter_event_gap_ms"],
                        }
                    )
    normalized_path = processed / "early_docker_normal_events.csv"
    with normalized_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "proxy_name",
                "session_id",
                "direction",
                "event_index",
                "byte_length",
                "inter_event_gap_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(normalized_rows)

    baseline_summary: dict[str, object] = {}
    for name in ("client_events.csv", "proxy_a_events.csv", "proxy_b_events.csv"):
        with (raw_baseline / name).open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        baseline_summary[name] = {
            "rows": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "sessions": len(
                {
                    row.get("session_id") or row.get("experiment_id")
                    for row in rows
                    if row.get("session_id") or row.get("experiment_id")
                }
            ),
            "directions": {
                value: sum(1 for row in rows if row.get("direction") == value)
                for value in ("forward", "reverse")
            },
            "lengths": sorted(
                {
                    int(row.get("byte_length") or row.get("expected_byte_length") or 0)
                    for row in rows
                    if row.get("byte_length") or row.get("expected_byte_length")
                }
            ),
            "statuses": {
                value: sum(1 for row in rows if row.get("status") == value)
                for value in {row.get("status") for row in rows if row.get("status")}
            },
        }
    (processed / "baseline_lenmix_v1_summary.json").write_text(
        json.dumps(baseline_summary, indent=2) + "\n",
        encoding="utf-8",
    )


def _stage_protocol() -> None:
    protocol = RELEASE_ROOT / "protocol_stego"
    shutil.copytree(DATASET_ROOT / "raw", protocol / "raw", dirs_exist_ok=True)
    processed_src = DATASET_ROOT / "processed"
    processed_dst = protocol / "processed"
    processed_dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "windows.npz",
        "index.jsonl",
        "build_summary.json",
        "stats.json",
        "data_quality_report.json",
        "baseline_analysis.json",
    ):
        _copy_file(processed_src / name, processed_dst / name)
    with zipfile.ZipFile(processed_src / "windows.npz") as archive:
        for name in ("X.npy", "y.npy"):
            (processed_dst / name).write_bytes(archive.read(name))

    shutil.copytree(DATASET_ROOT / "splits", protocol / "splits", dirs_exist_ok=True)

    metadata = protocol / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    _copy_file(DATASET_ROOT / "experiment_config.json", metadata / "experiment_config.json")
    _copy_file(PROJECT_ROOT / "config.yaml", metadata / "protocol_config.yaml")
    _copy_file(PROJECT_ROOT / "docs" / "DATASET.md", metadata / "DATASET.md")
    _copy_file(
        PROJECT_ROOT / "docs" / "DATA_QUALITY_REPORT.md",
        metadata / "DATA_QUALITY_REPORT.md",
    )
    _copy_file(
        PROJECT_ROOT / "docs" / "BASELINE_ANALYSIS.md",
        metadata / "BASELINE_ANALYSIS.md",
    )
    shutil.copytree(DOCS_ROOT / "plots", metadata / "plots", dirs_exist_ok=True)


def stage_data(args: argparse.Namespace) -> None:
    if RELEASE_ROOT.exists():
        if not args.force:
            raise SystemExit(f"{RELEASE_ROOT} exists; use --force to rebuild")
        shutil.rmtree(RELEASE_ROOT)
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    (RELEASE_ROOT / "checksums").mkdir(parents=True, exist_ok=True)
    _stage_historical(Path(args.docker_proxy_a), Path(args.docker_proxy_b))
    _stage_protocol()
    print(f"[release] data staged at {RELEASE_ROOT}")


def _npy_meta(path: Path) -> dict[str, object]:
    with path.open("rb") as file:
        magic = file.read(6)
        if magic != b"\x93NUMPY":
            raise ValueError(f"not a npy file: {path}")
        major = file.read(1)[0]
        file.read(1)
        if major == 1:
            header_size = struct.unpack("<H", file.read(2))[0]
            encoding = "latin1"
        else:
            header_size = struct.unpack("<I", file.read(4))[0]
            encoding = "utf-8"
        header = ast.literal_eval(file.read(header_size).decode(encoding).strip())
        data = file.read()
    return {"header": header, "data": data}


def _dtype_size(descr: str) -> int:
    match = "".join(ch for ch in descr if ch.isdigit())
    if not match:
        raise ValueError(f"cannot determine dtype size: {descr}")
    # numpy dtype strings such as <f4 / |i8 / |u1 express size in bytes.
    return max(1, int(match))


def _struct_format(descr: str) -> str:
    mapping = {
        "<f4": "<f",
        "|f4": "<f",
        ">f4": ">f",
        "<f8": "<d",
        ">f8": ">d",
        "<i8": "<q",
        "|i8": "<q",
        ">i8": ">q",
        "<i4": "<i",
        ">i4": ">i",
        "|u1": "B",
    }
    if descr not in mapping:
        raise ValueError(f"unsupported npy dtype for integrity check: {descr}")
    return mapping[descr]


def _integrity() -> dict[str, object]:
    protocol = RELEASE_ROOT / "protocol_stego"
    raw_root = protocol / "raw"
    session_count = {"normal": 0, "stego": 0}
    event_count = {"normal": 0, "stego": 0}
    metadata_ok = 0
    jsonl_errors: list[str] = []
    empty_files: list[str] = []
    file_count = 0
    for mode in ("normal", "stego"):
        mode_dir = raw_root / mode
        if not mode_dir.exists():
            continue
        for session_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
            session_count[mode] += 1
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                metadata = _read_json(metadata_path)
                required = {"session_id", "label", "mode", "timestamp", "config", "success"}
                if required <= set(metadata):
                    metadata_ok += 1
            for name in ("sender.jsonl", "receiver.jsonl", "errors.jsonl"):
                path = session_dir / name
                if not path.exists():
                    continue
                try:
                    rows = _read_jsonl(path)
                except Exception as exc:
                    jsonl_errors.append(f"{path}: {exc}")
                    continue
                if name == "receiver.jsonl":
                    event_count[mode] += sum(
                        1 for row in rows if row.get("observed_length") is not None
                    )
    for path in RELEASE_ROOT.rglob("*"):
        if path.is_file():
            file_count += 1
            if path.stat().st_size == 0:
                empty_files.append(str(path.relative_to(RELEASE_ROOT)))

    X = _npy_meta(protocol / "processed" / "X.npy")
    y = _npy_meta(protocol / "processed" / "y.npy")
    X_header = X["header"]
    y_header = y["header"]
    X_shape = list(X_header["shape"])
    y_shape = list(y_header["shape"])
    if X_header.get("fortran_order"):
        raise ValueError("X.npy must be C-order")
    sample_shape = X_shape[1:]
    sample_count = math.prod(sample_shape)
    sample_bytes = sample_count * _dtype_size(str(X_header["descr"]))
    X_data = X["data"]
    y_data = y["data"]
    hashes: dict[str, int] = {}
    duplicate_groups = 0
    duplicate_samples = 0
    for index in range(X_shape[0]):
        digest = hashlib.sha256(
            X_data[index * sample_bytes : (index + 1) * sample_bytes]
        ).hexdigest()
        hashes[digest] = hashes.get(digest, 0) + 1
    for count in hashes.values():
        if count > 1:
            duplicate_groups += 1
            duplicate_samples += count - 1
    nan_count = 0
    inf_count = 0
    descr = str(X_header["descr"])
    if descr in {"<f4", "|f4", ">f4", "<f8", ">f8"}:
        for value in struct.iter_unpack(_struct_format(descr), X_data):
            if math.isnan(value[0]):
                nan_count += 1
            elif math.isinf(value[0]):
                inf_count += 1
    y_values = [
        value[0]
        for value in struct.iter_unpack(
            _struct_format(str(y_header["descr"])), y_data
        )
    ]
    label_distribution = {
        "normal": int(sum(1 for value in y_values if value == 0)),
        "stego": int(sum(1 for value in y_values if value == 1)),
    }

    split_sessions: dict[str, set[str]] = {}
    for split_name in ("train", "val", "test"):
        path = protocol / "splits" / f"{split_name}_index.jsonl"
        split_sessions[split_name] = {
            str(row["session_id"]) for row in _read_jsonl(path)
        } if path.exists() else set()
    overlaps = {
        "train_val": sorted(split_sessions["train"] & split_sessions["val"]),
        "train_test": sorted(split_sessions["train"] & split_sessions["test"]),
        "val_test": sorted(split_sessions["val"] & split_sessions["test"]),
    }
    result = {
        "file_count": file_count,
        "empty_files": empty_files,
        "session_count": session_count,
        "event_count": event_count,
        "metadata_complete": metadata_ok,
        "jsonl_errors": jsonl_errors,
        "X_shape": X_shape,
        "y_shape": y_shape,
        "X_dtype": X_header["descr"],
        "y_dtype": y_header["descr"],
        "label_distribution": label_distribution,
        "split_overlaps": overlaps,
        "duplicate_sample_groups": duplicate_groups,
        "duplicate_sample_count": duplicate_samples,
        "nan_count": nan_count,
        "inf_count": inf_count,
    }
    empty_required = [
        name for name in empty_files if not name.endswith("errors.jsonl")
    ]
    result["empty_required_files"] = empty_required
    result["passed"] = not (
        empty_required
        or jsonl_errors
        or overlaps["train_val"]
        or overlaps["train_test"]
        or overlaps["val_test"]
        or duplicate_samples
        or nan_count
        or inf_count
    )
    return result


def _write_integrity(result: dict[str, object]) -> None:
    baseline_summary = _read_json(
        RELEASE_ROOT / "historical_normal" / "processed" / "baseline_lenmix_v1_summary.json"
    )
    lines = [
        "# DATASET INTEGRITY",
        "",
        f"Passed: **{result['passed']}**",
        "",
        "## protocol_stego",
        "",
        f"- sessions: {result['session_count']}",
        f"- events: {result['event_count']}",
        f"- metadata complete: {result['metadata_complete']}",
        f"- file count: {result['file_count']}",
        f"- empty files: {result['empty_files']}",
        "- note: empty `errors.jsonl` files are expected when a session had no errors",
        f"- empty non-error files: {result['empty_required_files']}",
        f"- JSONL parse errors: {result['jsonl_errors']}",
        f"- X.shape: {result['X_shape']}",
        f"- y.shape: {result['y_shape']}",
        f"- X dtype: {result['X_dtype']}",
        f"- y dtype: {result['y_dtype']}",
        f"- label distribution: {result['label_distribution']}",
        f"- split overlaps: {result['split_overlaps']}",
        f"- duplicate sample count: {result['duplicate_sample_count']}",
        f"- NaN count: {result['nan_count']}",
        f"- Inf count: {result['inf_count']}",
        "",
        "## historical_normal",
        "",
        f"- baseline_lenmix_v1 summary: {json.dumps(baseline_summary)}",
        "",
        "## checksums",
        "",
        "See `checksums/SHA256SUMS.txt`.",
        "",
    ]
    (RELEASE_ROOT / "DATASET_INTEGRITY.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_checksums() -> int:
    lines: list[str] = []
    for path in sorted(RELEASE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SHA256SUMS.txt":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(RELEASE_ROOT).as_posix()}")
    (RELEASE_ROOT / "checksums" / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return len(lines)


def _zip_release() -> Path:
    zip_path = REPO_ROOT / "releases" / "dataset_release_v1.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(RELEASE_ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(RELEASE_ROOT)
            if any(part in {".git", "__pycache__", ".venv", "venv"} for part in relative.parts):
                continue
            if path.suffix in {".pyc", ".pyo"}:
                continue
            archive.write(path, arcname=f"dataset_release/{relative.as_posix()}")
    return zip_path


def finalize() -> None:
    result = _integrity()
    _write_integrity(result)
    checksum_count = _write_checksums()
    zip_path = _zip_release()
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    summary = {
        "integrity_passed": result["passed"],
        "X_shape": result["X_shape"],
        "y_shape": result["y_shape"],
        "session_count": result["session_count"],
        "event_count": result["event_count"],
        "checksum_count": checksum_count,
        "zip_path": str(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": digest,
    }
    (RELEASE_ROOT / "metadata_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="build dataset_release")
    parser.add_argument("--stage", choices=["data", "finalize"], required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--docker-proxy-a",
        default=r"D:\temp\hist_docker_proxy_a.csv",
    )
    parser.add_argument(
        "--docker-proxy-b",
        default=r"D:\temp\hist_docker_proxy_b.csv",
    )
    args = parser.parse_args()
    if args.stage == "data":
        stage_data(args)
    else:
        finalize()


if __name__ == "__main__":
    main()
