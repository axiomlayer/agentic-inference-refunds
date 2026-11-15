"""Already-normalized usage (JSONL written by ``scope-refund usage``, or CSV with the same columns).

Use this for any tool without a built-in parser: export one row per billed request with
at least ``tool, provider, model, timestamp`` and the token columns.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ..records import HumanTurn, SourceResult, UsageRecord, file_fingerprint, iter_jsonl

_INT_FIELDS = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_5m_tokens",
    "cache_write_1h_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
)


def load(path) -> SourceResult:
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(path)
    result = SourceResult()
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                d = {k: v for k, v in row.items() if v not in (None, "")}
                for k in _INT_FIELDS:
                    if k in d:
                        d[k] = int(float(d[k]))
                if "provider_units" in d:
                    d["provider_units"] = json.loads(d["provider_units"])
                result.records.append(UsageRecord.from_dict(d))
    else:
        for obj in iter_jsonl(path):
            if obj.get("kind") == "human_turn":
                result.human_turns.append(HumanTurn(obj.get("tool", ""), obj.get("session_id", ""), obj["timestamp"]))
            else:
                result.records.append(UsageRecord.from_dict(obj))
    result.files.append(file_fingerprint(path))
    return result
