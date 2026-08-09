from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
from urllib.request import Request, urlopen

from .contract import validate_batch


class Publisher(Protocol):
    def publish(self, batch: dict) -> None: ...


class JsonlPublisher:
    """Writes public-only contract batches for ingestion fixtures or replay."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, batch: dict) -> None:
        validate_batch(batch)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(batch, sort_keys=True) + "\n")


class ApiPublisher:
    """Posts public observations only; it has no private-truth input."""
    def __init__(self, api_url: str):
        self.url = f"{api_url.rstrip('/')}/api/v1/ingestion/observations"

    def publish(self, batch: dict) -> None:
        validate_batch(batch)
        request = Request(self.url, data=json.dumps(batch).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise RuntimeError(f"ingestion returned HTTP {response.status}")
