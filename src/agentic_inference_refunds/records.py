"""Normalized usage records shared by every source parser."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


@dataclass
class UsageRecord:
    """One billed model request, in provider-neutral form.

    Token fields are disjoint, so their sum is the number of tokens processed:
    ``input_tokens`` is uncached input only; cache reads and writes are counted
    separately; ``output_tokens`` includes reasoning/thinking tokens, which every
    supported provider bills as output (``reasoning_tokens`` is the breakdown).
    """

    tool: str
    provider: str
    model: str
    timestamp: str
    session_id: str = ""
    agent_id: str = "main"
    agent_label: str = ""
    group: str = ""
    request_id: str = ""
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    provider_units: dict = field(default_factory=dict)
    source: str = ""

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_read_tokens
            + self.cache_write_5m_tokens
            + self.cache_write_1h_tokens
            + self.cache_write_tokens
            + self.output_tokens
        )

    @property
    def cache_write_total(self) -> int:
        return self.cache_write_5m_tokens + self.cache_write_1h_tokens + self.cache_write_tokens

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UsageRecord":
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in d.items() if k in known}
        for k in ("tool", "provider", "model", "timestamp"):
            if k not in clean:
                raise ValueError(f"usage record is missing required field {k!r}: {d}")
        clean["timestamp"] = normalize_ts(clean["timestamp"])
        return cls(**clean)


@dataclass
class HumanTurn:
    """A message the human typed, used to measure unattended spend."""

    tool: str
    session_id: str
    timestamp: str


@dataclass
class SourceResult:
    records: list = field(default_factory=list)
    human_turns: list = field(default_factory=list)
    files: list = field(default_factory=list)  # [{"path", "sha256", "bytes"}]
    provider_totals: list = field(default_factory=list)  # provider-reported cross-check totals
    warnings: list = field(default_factory=list)

    def extend(self, other: "SourceResult") -> None:
        self.records.extend(other.records)
        self.human_turns.extend(other.human_turns)
        self.files.extend(other.files)
        self.provider_totals.extend(other.provider_totals)
        self.warnings.extend(other.warnings)


def normalize_ts(value) -> str:
    """Return an ISO-8601 UTC timestamp ending in Z."""
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    dt = parse_ts(str(value))
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_ts(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def file_fingerprint(path: Path) -> dict:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
    return {"path": str(path), "sha256": h.hexdigest(), "bytes": size}


def iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def write_jsonl(records: Iterable[UsageRecord], path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")


def redact(result: SourceResult, salt: str = "scope-refund") -> SourceResult:
    """Replace identifying IDs and paths with stable short hashes, for sharing a claim publicly."""

    def h(value: str, prefix: str) -> str:
        if not value or value == "main":
            return value
        return prefix + hashlib.sha256((salt + value).encode()).hexdigest()[:10]

    out = SourceResult(warnings=list(result.warnings))
    for r in result.records:
        d = r.to_dict()
        d["session_id"] = h(r.session_id, "s-")
        d["agent_id"] = h(r.agent_id, "a-")
        d["request_id"] = h(r.request_id, "r-")
        d["source"] = h(Path(r.source).name, "f-") if r.source else ""
        out.records.append(UsageRecord.from_dict(d))
    for t in result.human_turns:
        out.human_turns.append(HumanTurn(t.tool, h(t.session_id, "s-"), t.timestamp))
    for f in result.files:
        out.files.append({**f, "path": h(Path(f["path"]).name, "f-")})
    for p in result.provider_totals:
        out.provider_totals.append({**p, "session_id": h(p.get("session_id", ""), "s-")})
    return out
