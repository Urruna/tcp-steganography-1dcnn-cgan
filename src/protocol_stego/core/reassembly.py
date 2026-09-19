"""Frame reassembly by Frame ID."""

from __future__ import annotations

from dataclasses import dataclass

from .framing import Frame


class ReassemblyError(Exception):
    """Raised when frame IDs are duplicated, missing or out of order."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ReassemblyResult:
    ciphertext: bytes
    frame_ids: list[int]
    errors: list[str]
    order_ok: bool


def reassemble_frames(
    frames: list[Frame],
    start_frame_id: int = 0,
    *,
    strict: bool = True,
) -> ReassemblyResult:
    """Concatenate frame payloads after checking Frame ID continuity."""
    errors: list[str] = []
    ids = [frame.frame_id for frame in frames]
    if len(set(ids)) != len(ids):
        errors.append("duplicate frame ids")
    order_ok = ids == sorted(ids)
    if not order_ok:
        errors.append("frame order is abnormal")

    ordered = sorted(frames, key=lambda frame: frame.frame_id)
    expected = list(range(start_frame_id, start_frame_id + len(ordered)))
    if [frame.frame_id for frame in ordered] != expected:
        missing = sorted(set(expected) - set(ids))
        unexpected = sorted(set(ids) - set(expected))
        if missing:
            errors.append(f"missing frame ids: {missing}")
        if unexpected:
            errors.append(f"unexpected frame ids: {unexpected}")

    if errors and strict:
        raise ReassemblyError(errors)

    ciphertext = b"".join(frame.payload for frame in ordered)
    return ReassemblyResult(
        ciphertext=ciphertext,
        frame_ids=[frame.frame_id for frame in ordered],
        errors=errors,
        order_ok=order_ok,
    )
