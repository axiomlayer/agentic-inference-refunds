"""Claude Code session transcripts (~/.claude/projects/<project>/<session>.jsonl).

Each assistant message carries ``message.usage``. Streaming writes the same message
several times, so records are de-duplicated by ``message.id`` (last write wins).
Subagent and workflow transcripts live beside the session in
``<session>/subagents/**/agent-*.jsonl``; their ``agent-*.meta.json`` gives a label.
In Anthropic usage, ``input_tokens`` already excludes cache reads and writes.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..records import HumanTurn, SourceResult, UsageRecord, file_fingerprint, iter_jsonl, normalize_ts

_NOT_HUMAN_PREFIXES = (
    "<local-command",
    "<command-name",
    "<command-message",
    "<task-notification",
    "<system-reminder",
    "[Request interrupted",
    "Caveat:",
)


def _human_text(message: dict):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                return None
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
        return "\n".join(texts) if texts else None
    return None


def _is_human(entry: dict) -> bool:
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return False
    text = _human_text(entry.get("message") or {})
    if not text or not text.strip():
        return False
    stripped = text.lstrip()
    return not any(stripped.startswith(p) for p in _NOT_HUMAN_PREFIXES)


def _parse_file(path: Path, session_id: str, agent_id: str, agent_label: str, group: str, collect_turns: bool):
    msgs: dict = {}
    order: list = []
    turns = []
    for entry in iter_jsonl(path):
        if collect_turns and _is_human(entry):
            turns.append(HumanTurn("claude-code", session_id, normalize_ts(entry.get("timestamp"))))
        if entry.get("type") != "assistant":
            continue
        msg = entry.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
            continue
        mid = msg.get("id") or entry.get("requestId") or entry.get("uuid")
        if mid not in msgs:
            order.append(mid)
        msgs[mid] = (msg, entry)
    records = []
    for mid in order:
        msg, entry = msgs[mid]
        u = msg["usage"]
        cc = u.get("cache_creation") or {}
        write_total = int(u.get("cache_creation_input_tokens") or 0)
        w5 = int(cc.get("ephemeral_5m_input_tokens") or 0)
        w1h = int(cc.get("ephemeral_1h_input_tokens") or 0)
        unknown = max(0, write_total - w5 - w1h)
        details = u.get("output_tokens_details") or {}
        model = msg.get("model") or "unknown"
        if model == "<synthetic>":
            continue
        records.append(
            UsageRecord(
                tool="claude-code",
                provider="anthropic",
                model=model,
                timestamp=normalize_ts(entry.get("timestamp")),
                session_id=session_id,
                agent_id=agent_id,
                agent_label=agent_label,
                group=group,
                request_id=str(mid or ""),
                input_tokens=int(u.get("input_tokens") or 0),
                cache_read_tokens=int(u.get("cache_read_input_tokens") or 0),
                cache_write_5m_tokens=w5,
                cache_write_1h_tokens=w1h,
                cache_write_tokens=unknown,
                output_tokens=int(u.get("output_tokens") or 0),
                reasoning_tokens=int(details.get("thinking_tokens") or 0),
                source=str(path),
            )
        )
    return records, turns


def load(path, include_subagents: bool = True) -> SourceResult:
    """Load a Claude Code session file (and, by default, its subagent transcripts)."""
    path = Path(path).expanduser()
    result = SourceResult()
    if path.is_dir():
        sessions = sorted(p for p in path.glob("*.jsonl"))
        if not sessions:
            raise FileNotFoundError(f"no Claude Code session .jsonl files in {path}")
        for p in sessions:
            result.extend(load(p, include_subagents))
        return result
    if not path.exists():
        raise FileNotFoundError(path)
    session_id = path.stem
    recs, turns = _parse_file(path, session_id, "main", "main thread", "main", collect_turns=True)
    result.records.extend(recs)
    result.human_turns.extend(turns)
    result.files.append(file_fingerprint(path))
    sub_root = path.with_suffix("") / "subagents"
    if include_subagents and sub_root.is_dir():
        for f in sorted(sub_root.rglob("agent-*.jsonl")):
            agent_id = f.stem.replace("agent-", "", 1)
            label = ""
            meta = f.with_name(f.stem + ".meta.json")
            if meta.exists():
                try:
                    label = json.loads(meta.read_text()).get("description") or ""
                except (OSError, json.JSONDecodeError):
                    label = ""
            rel = f.relative_to(sub_root).parts
            group = rel[1] if len(rel) >= 3 and rel[0] == "workflows" else (rel[0] if len(rel) > 1 else "subagents")
            recs, _ = _parse_file(f, session_id, agent_id, label, group, collect_turns=False)
            result.records.extend(recs)
            result.files.append(file_fingerprint(f))
    return result
