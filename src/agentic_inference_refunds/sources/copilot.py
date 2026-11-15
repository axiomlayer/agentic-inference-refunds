"""GitHub Copilot CLI sessions (~/.copilot/session-state/<session-id>/events.jsonl).

Each billed model call writes a ``session.usage_record`` event whose ``data.usage``
gives tokens and ``cost`` (the model's premium-request multiplier). Only user-initiated
calls are billed as premium requests. Copilot counts cache reads and writes inside ``inputTokens``; they
are subtracted so token fields are disjoint. Reasoning is inside ``outputTokens``.
``session.usage_checkpoint`` / ``session.shutdown`` carry Copilot's own running
totals, kept as a cross-check.
"""

from __future__ import annotations

from pathlib import Path

from ..records import HumanTurn, SourceResult, UsageRecord, file_fingerprint, iter_jsonl, normalize_ts


def _parse_events(path: Path, session_id: str) -> SourceResult:
    result = SourceResult()
    seen = set()
    last_snapshot = None
    for entry in iter_jsonl(path):
        etype = entry.get("type")
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        ts = normalize_ts(entry.get("timestamp"))
        if etype == "session.usage_record":
            u = data.get("usage") or {}
            eid = entry.get("id") or f"{ts}:{len(seen)}"
            if eid in seen:
                continue
            seen.add(eid)
            inp = int(u.get("inputTokens") or 0)
            read = int(u.get("cacheReadTokens") or 0)
            write = int(u.get("cacheWriteTokens") or 0)
            initiator = u.get("initiator") or ""
            units = {}
            if u.get("cost") is not None:
                # Copilot charges premium requests only for user-initiated calls; agent and
                # sub-agent calls carry a cost multiplier but are not billed as premium requests
                # (this matches Copilot's own totalPremiumRequestCost in every session checked).
                units["premium_requests"] = float(u["cost"]) if initiator in ("", "user") else 0.0
            provider = ((u.get("provider") or {}).get("id") or "github-copilot")
            result.records.append(
                UsageRecord(
                    tool="copilot",
                    provider=f"github-copilot/{provider}" if provider != "github-copilot" else provider,
                    model=u.get("model") or u.get("responseModel") or "unknown",
                    timestamp=ts,
                    session_id=session_id,
                    agent_id="main" if initiator in ("", "user") else (data.get("agentId") or initiator),
                    agent_label=u.get("interactionType") or "",
                    group=u.get("interactionType") or "main",
                    request_id=str(eid),
                    input_tokens=max(0, inp - read - write),
                    cache_read_tokens=read,
                    cache_write_tokens=write,
                    output_tokens=int(u.get("outputTokens") or 0),
                    reasoning_tokens=int(u.get("reasoningTokens") or 0),
                    provider_units=units,
                    source=str(path),
                )
            )
        elif etype in ("session.usage_checkpoint", "session.shutdown"):
            snap = data.get("accountingSnapshot") or {}
            last_snapshot = {
                "tool": "copilot",
                "session_id": session_id,
                "at": ts,
                "total_premium_request_cost": snap.get("totalPremiumRequestCost"),
                "total_premium_requests": data.get("totalPremiumRequests"),
                "total_nano_aiu": snap.get("totalNanoAiu", data.get("totalNanoAiu")),
                "total_user_requests": snap.get("totalUserRequests"),
            }
        elif etype == "user.message":
            result.human_turns.append(HumanTurn("copilot", session_id, ts))
    if last_snapshot:
        result.provider_totals.append(last_snapshot)
    result.files.append(file_fingerprint(path))
    return result


def load(path) -> SourceResult:
    """Accept a session directory, an events.jsonl file, or the session-state root."""
    path = Path(path).expanduser()
    result = SourceResult()
    if path.is_file():
        return _parse_events(path, path.parent.name)
    if (path / "events.jsonl").exists():
        return _parse_events(path / "events.jsonl", path.name)
    if path.is_dir():
        found = sorted(path.glob("*/events.jsonl"))
        if not found:
            raise FileNotFoundError(f"no Copilot events.jsonl under {path}")
        for f in found:
            result.extend(_parse_events(f, f.parent.name))
        return result
    raise FileNotFoundError(path)
