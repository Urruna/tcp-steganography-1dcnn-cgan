"""Thread-safe JSON Lines logger for experiment datasets."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class JsonlLogger:
    def __init__(
        self,
        path: str | Path,
        session_id: str | None = None,
        *,
        flush_every: int = 1,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.flush_every = max(1, flush_every)
        self._pending = 0
        self._lock = threading.Lock()
        self._file = self.path.open("a", encoding="utf-8")

    def log(self, event: str, **fields: object) -> dict[str, object]:
        record: dict[str, object] = {
            "timestamp": time.time(),
            "session_id": self.session_id,
            "event": event,
        }
        record.update(fields)
        with self._lock:
            self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._pending += 1
            if self._pending >= self.flush_every:
                self._file.flush()
                self._pending = 0
        return record

    def close(self) -> None:
        with self._lock:
            self._file.flush()
            self._file.close()
