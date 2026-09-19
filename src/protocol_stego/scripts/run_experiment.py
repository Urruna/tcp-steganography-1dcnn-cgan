"""Batch experiment runner for normal and stego sessions."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from scripts.session_runner import run_session


def _load_config(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _next_index(raw_root: Path, mode: str) -> int:
    """Return the next numeric index so existing sessions are preserved."""
    mode_dir = raw_root / mode
    if not mode_dir.exists():
        return 1
    pattern = re.compile(rf"^{re.escape(mode)}_(\d+)$")
    indices = [
        int(match.group(1))
        for path in mode_dir.iterdir()
        if path.is_dir() and (match := pattern.match(path.name))
    ]
    return max(indices, default=0) + 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="run normal/stego sessions")
    parser.add_argument("--mode", choices=["normal", "stego", "both"], default="both")
    parser.add_argument("--normal", type=int, default=None)
    parser.add_argument("--stego", type=int, default=None)
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "dataset" / "experiment_config.json"),
    )
    parser.add_argument(
        "--raw-dir",
        default=str(Path(__file__).resolve().parents[1] / "dataset" / "raw"),
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--secret-size", type=int, default=None)
    parser.add_argument("--block-gap-ms", type=int, default=None)
    parser.add_argument("--session-duration", type=int, default=None)
    parser.add_argument("--normal-chunk-size", type=int, default=None)
    parser.add_argument("--window-size", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = _load_config(Path(args.config))
    if args.seed is not None:
        config["random_seed"] = args.seed
        config["split_seed"] = args.seed
    if args.secret_size is not None:
        config["secret_size"] = args.secret_size
    if args.block_gap_ms is not None:
        config["block_gap_ms"] = args.block_gap_ms
    if args.session_duration is not None:
        config["session_duration"] = args.session_duration
    if args.normal_chunk_size is not None:
        config["normal_chunk_size"] = args.normal_chunk_size
    if args.window_size is not None:
        config["window_size"] = args.window_size

    normal_count = int(config.get("num_normal_sessions", 0))
    stego_count = int(config.get("num_stego_sessions", 0))
    if args.mode == "normal":
        stego_count = 0
    elif args.mode == "stego":
        normal_count = 0
    if args.normal is not None:
        normal_count = args.normal
    if args.stego is not None:
        stego_count = args.stego

    raw_root = Path(args.raw_dir)
    (raw_root / "normal").mkdir(parents=True, exist_ok=True)
    (raw_root / "stego").mkdir(parents=True, exist_ok=True)

    started = time.time()
    sessions: list[dict[str, object]] = []
    for mode, count in (("normal", normal_count), ("stego", stego_count)):
        start_index = _next_index(raw_root, mode)
        for index in range(start_index, start_index + count):
            session_id = f"{mode}_{index:06d}"
            print(f"[run_experiment] {session_id} ...", flush=True)
            metadata = run_session(
                session_id=session_id,
                mode=mode,
                config=config,
                raw_root=raw_root,
            )
            sessions.append(metadata)
            print(
                f"[run_experiment] {session_id} success={metadata['success']}",
                flush=True,
            )

    summary = {
        "started": started,
        "finished": time.time(),
        "mode": args.mode,
        "config": config,
        "requested": {"normal": normal_count, "stego": stego_count},
        "completed": {
            "normal": sum(1 for item in sessions if item["mode"] == "normal"),
            "stego": sum(1 for item in sessions if item["mode"] == "stego"),
        },
        "success": {
            "normal": sum(
                1 for item in sessions if item["mode"] == "normal" and item["success"]
            ),
            "stego": sum(
                1 for item in sessions if item["mode"] == "stego" and item["success"]
            ),
        },
        "sessions": sessions,
    }
    (raw_root / "run_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: summary[k] for k in ("requested", "completed", "success")}, indent=2))


if __name__ == "__main__":
    main()
