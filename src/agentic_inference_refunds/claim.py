"""Build a refund claim from classified usage, and render it as JSON or Markdown."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from datetime import datetime, timezone

from . import __version__
from .rates import RateBook
from .records import SourceResult, parse_ts
from .scope import STATUSES, classify, is_refundable

UNAPPROVED = ("out_of_scope", "unrequested_change", "remediation")
SCHEMA_ID = "agentic-inference-refunds/claim@1"


def _bucket():
    return {
        "requests": 0,
        "tokens": 0,
        "input_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "cost_usd": 0.0,
        "cost_parts": {"input": 0.0, "cache_read": 0.0, "cache_write": 0.0, "output": 0.0},
        "unpriced_requests": 0,
        "provider_units": {},
    }


def _add(b, r, p):
    b["requests"] += 1
    b["tokens"] += r.total_tokens
    b["input_tokens"] += r.input_tokens
    b["cache_read_tokens"] += r.cache_read_tokens
    b["cache_write_tokens"] += r.cache_write_total
    b["output_tokens"] += r.output_tokens
    b["reasoning_tokens"] += r.reasoning_tokens
    if p["priced"]:
        b["cost_usd"] += p["total"]
        for k in b["cost_parts"]:
            b["cost_parts"][k] += p[k]
    else:
        b["unpriced_requests"] += 1
    for unit, amount in (r.provider_units or {}).items():
        b["provider_units"][unit] = b["provider_units"].get(unit, 0.0) + float(amount)


def _round(b):
    b["cost_usd"] = round(b["cost_usd"], 2)
    b["cost_parts"] = {k: round(v, 2) for k, v in b["cost_parts"].items()}
    b["provider_units"] = {k: round(v, 4) for k, v in b["provider_units"].items()}
    return b


def build_claim(scope: dict, source: SourceResult, book: RateBook) -> dict:
    labels = scope.get("labels") or {}
    segs = scope["segments"]
    priced = [(r, book.price(r)) for r in source.records]
    classified = classify(scope, [r for r, _ in priced])
    price_of = {id(r): p for r, p in priced}

    totals = OrderedDict((k, _bucket()) for k in ("all", "approved", "not_approved", "refundable", "excluded", "unclassified"))
    seg_buckets = [dict(_bucket(), groups=OrderedDict()) for _ in segs]
    by_model = OrderedDict()
    unpriced = defaultdict(lambda: {"requests": 0, "tokens": 0})
    agents_unapproved, agents_all = set(), set()
    timeline = []

    for r, idx in classified:
        p = price_of[id(r)]
        _add(totals["all"], r, p)
        timeline.append((r.timestamp, p["total"] if p["priced"] else 0.0, idx))
        if r.agent_id != "main":
            agents_all.add((r.session_id, r.agent_id))
        if not p["priced"]:
            unpriced[r.model]["requests"] += 1
            unpriced[r.model]["tokens"] += r.total_tokens
        mb = by_model.setdefault(r.model, _bucket())
        _add(mb, r, p)
        if idx is None:
            _add(totals["unclassified"], r, p)
            continue
        seg = segs[idx]
        status = seg["status"]
        sb = seg_buckets[idx]
        _add(sb, r, p)
        gkey = r.group or "main"
        gb = sb["groups"].setdefault(gkey, dict(_bucket(), agents=set()))
        _add(gb, r, p)
        if r.agent_id != "main":
            gb["agents"].add(r.agent_id)
        if status == "approved":
            _add(totals["approved"], r, p)
        elif status in UNAPPROVED:
            _add(totals["not_approved"], r, p)
            if r.agent_id != "main":
                agents_unapproved.add((r.session_id, r.agent_id))
        elif status == "excluded":
            _add(totals["excluded"], r, p)
        if is_refundable(seg):
            _add(totals["refundable"], r, p)

    segments_out = []
    for seg, sb in zip(segs, seg_buckets):
        groups = []
        for g, gb in sb.pop("groups").items():
            agents = gb.pop("agents")
            groups.append(dict(_round(gb), group=g, label=labels.get(g, ""), subagents=len(agents)))
        groups.sort(key=lambda x: -x["cost_usd"])
        segments_out.append(
            dict(
                _round(sb),
                name=seg.get("name", ""),
                status=seg["status"],
                status_meaning=STATUSES[seg["status"]],
                reason=seg.get("reason", ""),
                refundable=is_refundable(seg),
                groups=groups,
            )
        )
    for b in totals.values():
        _round(b)
    models_out = [dict(_round(b), model=m, rate=(book.lookup(m) or {}).get("model")) for m, b in by_model.items()]
    models_out.sort(key=lambda x: -x["cost_usd"])

    approved = totals["approved"]["cost_usd"]
    unapproved = totals["not_approved"]["cost_usd"]
    comparison = {
        "cost_of_approved_scope_usd": approved,
        "cost_of_unapproved_scope_usd": unapproved,
        "unapproved_share_of_classified": round(unapproved / (approved + unapproved), 4) if (approved + unapproved) else None,
        "unapproved_dollars_per_approved_dollar": round(unapproved / approved, 2) if approved else None,
    }

    behavior = _behavior(scope, source, timeline, totals, agents_all, agents_unapproved)

    unit_claims = {}
    for unit, amount in totals["refundable"]["provider_units"].items():
        price = book.unit_price(unit)
        unit_claims[unit] = {
            "refundable_units": amount,
            "approved_units": approved_units if (approved_units := totals["approved"]["provider_units"].get(unit)) is not None else 0.0,
            "usd_per_unit": price.get("usd") if price else None,
            "refundable_usd_at_unit_price": round(amount * price["usd"], 2) if price else None,
            "unit_price_verified": price.get("verified") if price else None,
        }

    used_cards = {p.get("card") for _, p in priced if p.get("priced")}
    rate_summary = [c for c in book.summary() if c["id"] in used_cards or (c.get("units") and unit_claims)]
    unverified = [c["id"] for c in rate_summary if not c["verified"]]

    warnings = list(source.warnings)
    if totals["unclassified"]["requests"]:
        warnings.append(
            f"{totals['unclassified']['requests']} requests matched no segment and are excluded from every total except 'all'. Add a segment to place them."
        )
    if unpriced:
        warnings.append("Some models have no rate card; their tokens are counted but not priced: " + ", ".join(sorted(unpriced)))
    if unverified:
        warnings.append("Prices from unverified rate cards were used (" + ", ".join(unverified) + "). Verify them against the provider's rate sheet, or pass --rates.")
    if any(r.cache_write_tokens for r in source.records):
        warnings.append("Some cache writes have no recorded TTL; they are priced at the 5-minute write rate (the lower bound).")

    ts = [r.timestamp for r in source.records if r.timestamp]
    refund = totals["refundable"]["cost_usd"]
    return {
        "schema": SCHEMA_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": {"name": "scope-refund", "version": __version__},
        "title": scope.get("title", "Refund claim"),
        "claimant": scope.get("claimant", ""),
        "addressed_to": scope.get("addressed_to", ""),
        "product": scope.get("product", ""),
        "plan": scope.get("plan", ""),
        "currency": scope.get("currency", "USD"),
        "requested": scope.get("requested", {}),
        "delivered": scope.get("delivered", {}),
        "evidence": scope.get("evidence", []),
        "remedy_request": {
            "form": scope.get("remedy", "refund"),
            "amount_usd": refund,
            "basis": "API-equivalent cost of the refundable segments: each request's recorded tokens, priced at the provider's published per-token list rates.",
            "refundable_statuses": sorted({s["status"] for s in segs if is_refundable(s)}),
        },
        "comparison": comparison,
        "totals": totals,
        "segments": segments_out,
        "by_model": models_out,
        "provider_units": unit_claims,
        "behavior": behavior,
        "unpriced_models": [{"model": m, **v} for m, v in sorted(unpriced.items())],
        "provider_reported_totals": source.provider_totals,
        "method": {
            "classification": "Each usage record is assigned to the first segment in the scope file whose match rules it satisfies; unmatched records are listed as unclassified and are never refundable.",
            "pricing": "cost = uncached input x input rate + cache reads x cache-read rate + cache writes x write rate (5-minute or 1-hour, per the recorded TTL) + output (including reasoning) x output rate.",
            "deduplication": "Claude Code: by message id. Codex: by response id. Copilot: by event id.",
            "rate_cards": rate_summary,
        },
        "integrity": {
            "files": source.files,
            "records": len(source.records),
            "first_record": min(ts) if ts else None,
            "last_record": max(ts) if ts else None,
        },
        "warnings": warnings,
    }


def _behavior(scope, source, timeline, totals, agents_all, agents_unapproved) -> dict:
    out = {
        "subagents_total": len(agents_all),
        "subagents_in_unapproved_work": len(agents_unapproved),
        "reasoning_share_of_output_tokens": round(totals["all"]["reasoning_tokens"] / totals["all"]["output_tokens"], 4)
        if totals["all"]["output_tokens"]
        else None,
        "cache_read_share_of_tokens": round(totals["all"]["cache_read_tokens"] / totals["all"]["tokens"], 4) if totals["all"]["tokens"] else None,
        "human_turns": len({(h.session_id, h.timestamp) for h in source.human_turns}),
    }
    events = sorted((parse_ts(t), c, i) for t, c, i in timeline if t)
    turns = sorted({parse_ts(h.timestamp) for h in source.human_turns if h.timestamp})
    if events and turns:
        bounds = turns + [events[-1][0]]
        best = None
        for start, end in zip(bounds, bounds[1:]):
            window = [e for e in events if start <= e[0] < end] if end != bounds[-1] else [e for e in events if start <= e[0] <= end]
            cost = sum(c for _, c, _ in window)
            if best is None or cost > best["cost_usd"]:
                best = {
                    "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "until": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "minutes": round((end - start).total_seconds() / 60, 1),
                    "requests": len(window),
                    "cost_usd": round(cost, 2),
                }
        out["largest_spend_between_human_messages"] = best
    objections = sorted(parse_ts(str(e["at"])) for e in scope.get("evidence", []) if e.get("kind") == "objection" and e.get("at"))
    if objections and events:
        first = objections[0]
        before = [e for e in events if e[0] < first]
        unapproved_before = [e for e in before if e[2] is not None and scope["segments"][e[2]]["status"] in UNAPPROVED]
        out["before_first_objection"] = {
            "objection_at": first.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "minutes_from_first_request": round((first - events[0][0]).total_seconds() / 60, 1),
            "requests": len(before),
            "cost_usd": round(sum(c for _, c, _ in before), 2),
            "unapproved_cost_usd": round(sum(c for _, c, _ in unapproved_before), 2),
        }
    return out


def _usd(x) -> str:
    return "n/a" if x is None else f"${x:,.2f}"


def _m(n) -> str:
    return f"{n / 1e6:,.1f} M" if n >= 100_000 else f"{n:,}"


def render_markdown(c: dict) -> str:
    cur = c["currency"]
    L = [f"# {c['title']}", ""]
    meta = " · ".join(x for x in (f"To: {c['addressed_to']}" if c["addressed_to"] else "", c["product"], c["plan"], f"From: {c['claimant']}" if c["claimant"] else "") if x)
    if meta:
        L += [meta, ""]
    rr = c["remedy_request"]
    L += [f"**Requested remedy: {_usd(rr['amount_usd'])} {cur}, as {rr['form']}.** {rr['basis']}", ""]
    req = c.get("requested") or {}
    L += ["## What was requested", "", req.get("summary", "")]
    if req.get("quote"):
        L += ["", "> " + req["quote"].strip().replace("\n", "\n> ")]
    if req.get("source"):
        L += ["", f"Recorded: {req['source']}"]
    dlv = c.get("delivered") or {}
    if dlv.get("summary"):
        L += ["", "## What was delivered", "", dlv["summary"]]
    cmp = c["comparison"]
    t = c["totals"]
    L += [
        "",
        "## The cost",
        "",
        "| | Requests | Tokens processed | Output tokens | API-equivalent cost |",
        "|---|---:|---:|---:|---:|",
        f"| Approved scope | {t['approved']['requests']:,} | {_m(t['approved']['tokens'])} | {t['approved']['output_tokens']:,} | {_usd(t['approved']['cost_usd'])} |",
        f"| Not approved (out of scope, unrequested changes, remediation) | {t['not_approved']['requests']:,} | {_m(t['not_approved']['tokens'])} | {t['not_approved']['output_tokens']:,} | {_usd(t['not_approved']['cost_usd'])} |",
    ]
    if t["excluded"]["requests"]:
        L.append(f"| Excluded by claimant | {t['excluded']['requests']:,} | {_m(t['excluded']['tokens'])} | {t['excluded']['output_tokens']:,} | {_usd(t['excluded']['cost_usd'])} |")
    if t["unclassified"]["requests"]:
        L.append(f"| Unclassified | {t['unclassified']['requests']:,} | {_m(t['unclassified']['tokens'])} | {t['unclassified']['output_tokens']:,} | {_usd(t['unclassified']['cost_usd'])} |")
    L.append(f"| **Refundable** | **{t['refundable']['requests']:,}** | **{_m(t['refundable']['tokens'])}** | **{t['refundable']['output_tokens']:,}** | **{_usd(t['refundable']['cost_usd'])}** |")
    if cmp["unapproved_dollars_per_approved_dollar"] is not None:
        L += ["", f"For every dollar spent on the approved scope, {_usd(cmp['unapproved_dollars_per_approved_dollar'])} went to work that was not approved."]
    L += ["", "### By segment", "", "| Segment | Status | Refundable | Requests | Tokens | Cost |", "|---|---|---|---:|---:|---:|"]
    for s in c["segments"]:
        L.append(f"| {s['name']} | {s['status']}{' (' + s['reason'] + ')' if s['reason'] else ''} | {'yes' if s['refundable'] else 'no'} | {s['requests']:,} | {_m(s['tokens'])} | {_usd(s['cost_usd'])} |")
        for g in s["groups"]:
            label = g["label"] or g["group"]
            extra = f", {g['subagents']} subagents" if g["subagents"] else ""
            L.append(f"| &nbsp;&nbsp;{label}{extra} | | | {g['requests']:,} | {_m(g['tokens'])} | {_usd(g['cost_usd'])} |")
    rp = t["refundable"]["cost_parts"]
    L += [
        "",
        f"Refundable cost by token type: output {_usd(rp['output'])}, cache reads {_usd(rp['cache_read'])}, cache writes {_usd(rp['cache_write'])}, uncached input {_usd(rp['input'])}.",
    ]
    if c["provider_units"]:
        L += ["", "### Provider billing units", ""]
        for unit, u in c["provider_units"].items():
            L.append(
                f"- {unit}: {u['refundable_units']:,} refundable units (approved scope used {u['approved_units']:,})"
                + (f"; at {_usd(u['usd_per_unit'])} per unit = {_usd(u['refundable_usd_at_unit_price'])}" if u["usd_per_unit"] is not None else "")
                + ("" if u.get("unit_price_verified") else " (unit price unverified)")
            )
    b = c["behavior"]
    L += ["", "## Behavior observed", ""]
    L.append(f"- Subagents spawned: {b['subagents_total']} ({b['subagents_in_unapproved_work']} in work that was not approved).")
    if b.get("reasoning_share_of_output_tokens") is not None:
        L.append(f"- Reasoning share of output tokens: {b['reasoning_share_of_output_tokens']:.0%}.")
    if b.get("largest_spend_between_human_messages"):
        x = b["largest_spend_between_human_messages"]
        L.append(f"- Largest spend between two human messages: {_usd(x['cost_usd'])} over {x['minutes']} minutes ({x['requests']:,} requests, {x['from']} to {x['until']}).")
    if b.get("before_first_objection"):
        x = b["before_first_objection"]
        L.append(f"- Before the first objection ({x['objection_at']}, {x['minutes_from_first_request']} minutes in): {_usd(x['cost_usd'])} spent, {_usd(x['unapproved_cost_usd'])} of it on work that was not approved.")
    if c.get("evidence"):
        L += ["", "## Evidence", ""]
        for e in c["evidence"]:
            when = f" ({e['at']})" if e.get("at") else ""
            ref = f" — {e['ref']}" if e.get("ref") else ""
            L.append(f"- **{e.get('kind', 'note')}**{when}: {e.get('text', '')}{ref}")
    L += ["", "## How this was measured", "", c["method"]["classification"], "", c["method"]["pricing"], "", c["method"]["deduplication"], ""]
    L += ["| Rate card | As of | Verified | Source |", "|---|---|---|---|"]
    for rc in c["method"]["rate_cards"]:
        L.append(f"| {rc['id']} | {rc['as_of']} | {'yes' if rc['verified'] else 'no'} | {'; '.join(rc['sources'])[:300]} |")
    integ = c["integrity"]
    L += ["", f"{integ['records']:,} usage records from {len(integ['files'])} files, {integ['first_record']} to {integ['last_record']}. SHA-256 of each source file is in the JSON claim, so the figures can be recomputed."]
    if c["unpriced_models"]:
        L += ["", "Unpriced models (tokens counted, no rate card): " + ", ".join(f"{u['model']} ({u['requests']} requests)" for u in c["unpriced_models"]) + "."]
    if c["warnings"]:
        L += ["", "## Warnings", ""] + [f"- {w}" for w in c["warnings"]]
    L += ["", f"_Generated by scope-refund {c['tool']['version']} at {c['generated_at']}._", ""]
    return "\n".join(L)
