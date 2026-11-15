"""OpenAI Codex rollout transcripts (~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl).

Preferred record: ``token_usage_record`` (one per model response, keyed by
``response_id``). Older rollouts only have cumulative ``event_msg``/``token_count``
events; for those, per-request usage is the increase in ``total_token_usage``.

OpenAI usage counts cached tokens inside ``input_tokens`` and reasoning inside
``output_tokens``. Normalization subtracts cache reads and writes from input so
token fields are disjoint; reasoning stays inside output (billed as output).
"""

from __future__ import annotations

from pathlib import Path

from ..records import HumanTurn, SourceResult, UsageRecord, file_fingerprint, iter_jsonl, normalize_ts

_USAGE_KEYS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")


def _norm(u: dict) -> dict:
    inp = int(u.get("input_tokens") or 0)
    cached = int(u.get("cached_input_tokens") or 0)
    write = int(u.get("cache_write_input_tokens") or 0)
    return {
        "input_tokens": max(0, inp - cached - write),
        "cache_read_tokens": cached,
        "cache_write_tokens": write,
        "output_tokens": int(u.get("output_tokens") or 0),
        "reasoning_tokens": int(u.get("reasoning_output_tokens") or 0),
    }


def _human_from_item(payload: dict):
    if payload.get("type") != "message" or payload.get("role") != "user":
        return None
    content = payload.get("content")
    texts = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                texts.append(block["text"])
    elif isinstance(content, str):
        texts.append(content)
    text = "\n".join(texts).strip()
    if not text or text.startswith("<"):
        return None  # environment context, AGENTS.md instructions and other injected text
    return text


def _parse_file(path: Path):
    result = SourceResult()
    session_id = ""
    provider = "openai"
    model_by_turn: dict = {}
    current_model = "unknown"
    records: dict = {}
    order: list = []
    fallback: list = []
    last_total = None
    turns_event, turns_item = [], []
    for entry in iter_jsonl(path):
        etype = entry.get("type")
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        ts = normalize_ts(entry.get("timestamp"))
        if etype == "session_meta":
            session_id = payload.get("id") or payload.get("session_id") or session_id
            provider = payload.get("model_provider") or provider
        elif etype == "turn_context":
            current_model = payload.get("model") or current_model
            if payload.get("turn_id"):
                model_by_turn[payload["turn_id"]] = current_model
        elif etype == "token_usage_record":
            u = payload.get("usage") or {}
            rid = payload.get("response_id") or f"{payload.get('turn_id')}:{len(order)}"
            if rid not in records:
                order.append(rid)
            thread = payload.get("thread_id") or ""
            sid = payload.get("session_id") or session_id
            records[rid] = UsageRecord(
                tool="codex",
                provider=provider,
                model=model_by_turn.get(payload.get("turn_id"), current_model),
                timestamp=ts,
                session_id=sid,
                agent_id="main" if (not thread or thread == sid) else thread,
                group=thread or "main",
                request_id=str(rid),
                source=str(path),
                **_norm(u),
            )
        elif etype == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info") or {}
            total = info.get("total_token_usage")
            if isinstance(total, dict):
                tot = int(total.get("total_tokens") or 0)
                if last_total is None or tot > last_total.get("total_tokens", 0):
                    prev = last_total or {}
                    delta = {k: int(total.get(k) or 0) - int(prev.get(k) or 0) for k in _USAGE_KEYS}
                    fallback.append((ts, current_model, delta))
                    last_total = {**{k: int(total.get(k) or 0) for k in _USAGE_KEYS}, "total_tokens": tot}
        elif etype == "event_msg" and payload.get("type") == "user_message":
            turns_event.append(ts)
        elif etype == "response_item":
            if _human_from_item(payload):
                turns_item.append(ts)
    if order:
        result.records.extend(records[k] for k in order)
    else:
        for i, (ts, model, delta) in enumerate(fallback):
            result.records.append(
                UsageRecord(
                    tool="codex",
                    provider=provider,
                    model=model,
                    timestamp=ts,
                    session_id=session_id,
                    request_id=f"token_count:{i}",
                    source=str(path),
                    **_norm(delta),
                )
            )
        if fallback:
            result.warnings.append(f"{path.name}: no token_usage_record events; used cumulative token_count deltas")
    for ts in (turns_event or turns_item):
        result.human_turns.append(HumanTurn("codex", session_id or path.stem, ts))
    for r in result.records:
        if not r.session_id:
            r.session_id = session_id or path.stem
    result.files.append(file_fingerprint(path))
    return result


def load(path) -> SourceResult:
    path = Path(path).expanduser()
    result = SourceResult()
    if path.is_dir():
        files = sorted(path.rglob("*.jsonl"))
        if not files:
            raise FileNotFoundError(f"no Codex rollout .jsonl files under {path}")
        for f in files:
            result.extend(_parse_file(f))
        return result
    if not path.exists():
        raise FileNotFoundError(path)
    return _parse_file(path)
