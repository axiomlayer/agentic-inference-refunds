"""The scope file: what was asked, what was delivered, and which usage belongs to which.

Every usage record is assigned to the FIRST segment whose ``match`` it satisfies.
Records no segment matches are ``unclassified`` and never refundable; the claim lists
them so nothing is silently counted either way.
"""

from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path

from .records import UsageRecord, parse_ts

STATUSES = {
    "approved": "Delivered the requested scope",
    "out_of_scope": "Work outside the requested scope",
    "unrequested_change": "Changed something the requester had not asked to change",
    "remediation": "Repairing or redoing work after a mis-delivery",
    "excluded": "Left out of the claim by the claimant",
}
REFUNDABLE_BY_DEFAULT = {"out_of_scope": True, "unrequested_change": True, "remediation": True, "approved": False, "excluded": False}

TEMPLATE = '''# scope-refund claim definition. Every usage record goes to the FIRST segment it matches.
title = "Wrong scope delivered"
claimant = "Your name or org"
addressed_to = "Anthropic"            # or OpenAI, GitHub
product = "Claude Code"               # Codex, GitHub Copilot, ...
plan = "subscription plan usage"      # where the usage was billed
remedy = "extra usage credits"        # or "refund"
currency = "USD"

[requested]
summary = "What you asked for, in one or two sentences."
quote = """Paste the request verbatim, or the part that sets the scope."""
source = "Where the request is recorded (session, message time)."

[delivered]
summary = "What was produced instead."

[[evidence]]
kind = "objection"                    # objection | acknowledgement | artifact | timeline | note
at = "2026-01-01T00:00:00Z"
text = "What you said when you noticed, or what the model admitted."
ref = "session message, file, issue link"

# Optional readable names for groups or agents (workflow IDs, thread IDs, subagent IDs).
[labels]
# wf_1234 = "Gap discovery"

[[segments]]
name = "Requested work"
status = "approved"                   # approved | out_of_scope | unrequested_change | remediation | excluded
[segments.match]
groups = ["wf_*"]                     # glob patterns on group (workflow / thread / interaction type)
# agents = ["main"]                   # glob patterns on agent_id
# tools = ["claude-code"]
# models = ["claude-opus-*"]
# from = "2026-01-01T00:00:00Z"       # inclusive
# until = "2026-01-01T02:00:00Z"      # exclusive

[[segments]]
name = "Everything before the objection"
status = "out_of_scope"
reason = "wrong_scope"                # wrong_scope | unrequested_change | relitigated_decisions | regression | rework | other
[segments.match]
until = "2026-01-01T02:00:00Z"
'''


def load_scope(path) -> dict:
    path = Path(path).expanduser()
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".toml":
        try:
            import tomllib
        except ModuleNotFoundError as exc:  # Python 3.10
            raise SystemExit("TOML scope files need Python 3.11+; use JSON on older Python") from exc
        data = tomllib.loads(text)
    else:
        data = json.loads(text)
    validate_scope(data)
    return data


def validate_scope(data: dict) -> None:
    problems = []
    if not isinstance(data.get("segments"), list) or not data["segments"]:
        problems.append("at least one [[segments]] entry is required")
    for i, seg in enumerate(data.get("segments") or []):
        if seg.get("status") not in STATUSES:
            problems.append(f"segments[{i}] ({seg.get('name')!r}): status must be one of {sorted(STATUSES)}")
        m = seg.get("match", {})
        for key in ("from", "until"):
            if key in m:
                try:
                    parse_ts(str(m[key]))
                except ValueError:
                    problems.append(f"segments[{i}].match.{key} is not an ISO-8601 timestamp: {m[key]!r}")
    if not (data.get("requested") or {}).get("summary"):
        problems.append("[requested].summary is required: state what was asked for")
    if problems:
        raise ValueError("invalid scope file:\n  - " + "\n  - ".join(problems))


def _any_glob(value: str, patterns) -> bool:
    if isinstance(patterns, str):
        patterns = [patterns]
    return any(fnmatch(value or "", p) for p in patterns)


def matches(seg: dict, r: UsageRecord) -> bool:
    m = seg.get("match") or {}
    if "tools" in m and not _any_glob(r.tool, m["tools"]):
        return False
    if "groups" in m and not _any_glob(r.group, m["groups"]):
        return False
    if "agents" in m and not _any_glob(r.agent_id, m["agents"]):
        return False
    if "models" in m and not _any_glob(r.model, m["models"]):
        return False
    if "sessions" in m and not _any_glob(r.session_id, m["sessions"]):
        return False
    if ("from" in m or "until" in m) and r.timestamp:
        ts = parse_ts(r.timestamp)
        if "from" in m and ts < parse_ts(str(m["from"])):
            return False
        if "until" in m and ts >= parse_ts(str(m["until"])):
            return False
    return True


def classify(scope: dict, records) -> list:
    """Return [(record, segment_index or None)]."""
    segs = scope["segments"]
    out = []
    for r in records:
        idx = next((i for i, s in enumerate(segs) if matches(s, r)), None)
        out.append((r, idx))
    return out


def is_refundable(seg: dict) -> bool:
    if "refundable" in seg:
        return bool(seg["refundable"])
    return REFUNDABLE_BY_DEFAULT.get(seg.get("status"), False)
