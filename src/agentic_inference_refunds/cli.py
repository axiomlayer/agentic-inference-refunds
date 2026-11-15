"""scope-refund: work out what an agentic coding tool should refund when it delivered the wrong scope.

Exit codes: 0 ok; 2 bad input; 3 --strict and some usage was unpriced or unclassified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .claim import build_claim, render_markdown
from .rates import RateBook
from .records import SourceResult, redact, write_jsonl
from .scope import TEMPLATE, load_scope
from .sources import LOADERS

SCHEMA_DIR = Path(__file__).parent / "data" / "schemas"


def _add_sources(p):
    g = p.add_argument_group("usage sources (repeatable; combine freely)")
    g.add_argument("--claude-code", action="append", default=[], metavar="PATH", help="Claude Code session .jsonl (subagents included) or a project directory")
    g.add_argument("--codex", action="append", default=[], metavar="PATH", help="Codex rollout .jsonl or a sessions directory")
    g.add_argument("--copilot", action="append", default=[], metavar="PATH", help="Copilot session directory, its events.jsonl, or ~/.copilot/session-state")
    g.add_argument("--usage", action="append", default=[], metavar="PATH", help="normalized usage .jsonl or .csv (from `scope-refund usage`, or your own export)")
    g.add_argument("--no-subagents", action="store_true", help="Claude Code: ignore subagent and workflow transcripts")
    p.add_argument("--redact", action="store_true", help="replace session, agent and request IDs with hashes and strip paths, for sharing")


def _load_sources(args) -> SourceResult:
    result = SourceResult()
    for path in args.claude_code:
        result.extend(LOADERS["claude-code"](path, include_subagents=not args.no_subagents))
    for kind in ("codex", "copilot", "usage"):
        for path in getattr(args, kind):
            result.extend(LOADERS[kind](path))
    if not result.records:
        raise SystemExit("no usage records found; pass at least one --claude-code, --codex, --copilot or --usage source")
    return redact(result) if args.redact else result


def cmd_usage(args) -> int:
    src = _load_sources(args)
    out = Path(args.out) if args.out else None
    if out:
        write_jsonl(src.records, out)
        if src.human_turns:
            with open(out, "a", encoding="utf-8") as fh:
                for t in src.human_turns:
                    fh.write(json.dumps({"kind": "human_turn", "tool": t.tool, "session_id": t.session_id, "timestamp": t.timestamp}) + "\n")
        print(f"wrote {len(src.records)} usage records and {len(src.human_turns)} human turns to {out}", file=sys.stderr)
    else:
        for r in src.records:
            print(json.dumps(r.to_dict(), sort_keys=True))
    for w in src.warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


def cmd_price(args) -> int:
    src = _load_sources(args)
    book = RateBook.load(args.rates)
    key = {"group": lambda r: r.group or "main", "model": lambda r: r.model, "agent": lambda r: r.agent_label or r.agent_id, "tool": lambda r: r.tool, "session": lambda r: r.session_id}[args.by]
    rows: dict = {}
    for r in src.records:
        p = book.price(r)
        row = rows.setdefault(key(r), {"requests": 0, "tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "unpriced_requests": 0})
        row["requests"] += 1
        row["tokens"] += r.total_tokens
        row["output_tokens"] += r.output_tokens
        row["cost_usd"] += p["total"]
        row["unpriced_requests"] += 0 if p["priced"] else 1
    ordered = sorted(rows.items(), key=lambda kv: -kv[1]["cost_usd"])
    if args.json:
        print(json.dumps([{"key": k, **{**v, "cost_usd": round(v["cost_usd"], 2)}} for k, v in ordered], indent=2))
        return 0
    width = max([len(str(k)) for k, _ in ordered] + [len(args.by)])
    print(f"{args.by:<{width}}  {'requests':>9}  {'tokens':>14}  {'output':>11}  {'API-equiv $':>12}")
    total = 0.0
    for k, v in ordered:
        total += v["cost_usd"]
        flag = "  (unpriced: %d)" % v["unpriced_requests"] if v["unpriced_requests"] else ""
        print(f"{str(k):<{width}}  {v['requests']:>9,}  {v['tokens']:>14,}  {v['output_tokens']:>11,}  {v['cost_usd']:>12,.2f}{flag}")
    print(f"{'total':<{width}}  {sum(v['requests'] for v in rows.values()):>9,}  {sum(v['tokens'] for v in rows.values()):>14,}  {sum(v['output_tokens'] for v in rows.values()):>11,}  {total:>12,.2f}")
    return 0


def cmd_claim(args) -> int:
    scope = load_scope(args.scope)
    src = _load_sources(args)
    book = RateBook.load(args.rates)
    claim = build_claim(scope, src, book)
    md = render_markdown(claim)
    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        if args.format in ("json", "both"):
            (out / "claim.json").write_text(json.dumps(claim, indent=2) + "\n")
        if args.format in ("md", "both"):
            (out / "claim.md").write_text(md)
        print(f"refundable: ${claim['remedy_request']['amount_usd']:,.2f} -> {out}", file=sys.stderr)
    elif args.format == "json":
        print(json.dumps(claim, indent=2))
    else:
        print(md)
    for w in claim["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    if args.strict and (claim["unpriced_models"] or claim["totals"]["unclassified"]["requests"]):
        return 3
    return 0


def cmd_rates(args) -> int:
    book = RateBook.load(args.rates)
    s = book.summary()
    if args.json:
        print(json.dumps(s, indent=2))
        return 0
    for c in s:
        print(f"{c['id']}  provider={c['provider']}  as_of={c['as_of']}  verified={'yes' if c['verified'] else 'NO'}")
        for m, r in c["models"].items():
            print(f"  {m:<20} in {r['input']:>6}  out {r['output']:>6}  cache_read {r['cache_read']:>5}  write_5m {r['cache_write_5m']:>6}  write_1h {r['cache_write_1h']:>6}")
        for u, spec in (c.get("units") or {}).items():
            print(f"  unit {u}: ${spec['usd']}  ({spec.get('label', '')})")
    print("prices: USD per million tokens. Override or add models with --rates FILE.json")
    return 0


def cmd_init(args) -> int:
    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists; pass --force to overwrite")
    out.write_text(TEMPLATE)
    print(f"wrote {out}; fill in [requested], the evidence and the segments, then run `scope-refund claim --scope {out} ...`", file=sys.stderr)
    return 0


def cmd_schema(args) -> int:
    print((SCHEMA_DIR / f"{args.which}.schema.json").read_text())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scope-refund", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"scope-refund {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("claim", help="build a refund claim (Markdown for people, JSON for agents)")
    p.add_argument("--scope", required=True, help="scope file (.toml or .json); start from `scope-refund init`")
    _add_sources(p)
    p.add_argument("--rates", action="append", default=[], metavar="FILE", help="extra or overriding rate card JSON")
    p.add_argument("--format", choices=("md", "json", "both"), default="md")
    p.add_argument("--out-dir", help="write claim.md and/or claim.json here instead of stdout")
    p.add_argument("--strict", action="store_true", help="exit 3 if any usage is unpriced or unclassified")
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("usage", help="extract normalized usage records (no message content)")
    _add_sources(p)
    p.add_argument("--out", help="write JSONL here (default: stdout)")
    p.set_defaults(func=cmd_usage)

    p = sub.add_parser("price", help="price usage at API list rates, grouped")
    _add_sources(p)
    p.add_argument("--rates", action="append", default=[], metavar="FILE")
    p.add_argument("--by", choices=("group", "model", "agent", "tool", "session"), default="group")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_price)

    p = sub.add_parser("rates", help="show the rate cards in use")
    p.add_argument("--rates", action="append", default=[], metavar="FILE")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_rates)

    p = sub.add_parser("init", help="write a scope file template")
    p.add_argument("--out", default="scope.toml")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("schema", help="print the JSON Schema for a scope file or a claim")
    p.add_argument("which", choices=("scope", "claim"))
    p.set_defaults(func=cmd_schema)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
