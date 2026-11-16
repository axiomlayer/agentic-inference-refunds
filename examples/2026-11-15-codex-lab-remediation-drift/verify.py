#!/usr/bin/env python3
"""Verify public accounting, original selectors, redaction, and strict CLI output.

Run with Python 3.11+ from any directory. No private transcripts are required.
This verifier reads existing artifacts without changing them.
"""
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agentic_inference_refunds.claim import render_markdown
from agentic_inference_refunds.cli import main as cli_main
from agentic_inference_refunds.records import parse_ts
from agentic_inference_refunds.scope import load_scope, matches
from agentic_inference_refunds.sources.generic import load

START = '2026-11-15T19:40:23.000Z'
END = '2026-11-16T03:40:23.000Z'
FIELDS = ('input_tokens', 'cache_read_tokens', 'cache_write_5m_tokens',
          'cache_write_1h_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens')


def thread(row):
    return row['session_id'] if row['agent_id'] == 'main' else row['agent_id']


def selected(segment, row):
    """Reconstruct the original hashed identity/time selector, ignoring group."""
    if row['tool'] != 'codex' or row['model'] == 'codex-auto-review':
        return False
    sel = segment['selection']
    identity = row['session_id'] if sel['kind'] == 'session' else thread(row)
    return identity == sel['identity'] and parse_ts(sel['from']) <= parse_ts(row['timestamp']) < parse_ts(sel['until'])


def verify():
    expected = json.loads((HERE / 'expected.json').read_text())
    scope = load_scope(HERE / 'historical-scope.toml')
    source = load(HERE / 'usage.jsonl')
    rows = [r.to_dict() for r in source.records]
    assert len(rows) == expected['records'] == 16405
    assert len({(r['tool'], r['request_id']) for r in rows}) == len(rows)
    assert all(parse_ts(START) <= parse_ts(r['timestamp']) < parse_ts(END) for r in rows)
    assert hashlib.sha256((HERE / 'usage.jsonl').read_bytes()).hexdigest() == expected['usage_sha256']
    assert {f: sum(r[f] for r in rows) for f in FIELDS} == expected['token_totals']
    assert sum(r.total_tokens for r in source.records) == expected['processed_tokens'] == 2979029529
    candidates = [s for s in scope['segments'] if s['status'] != 'excluded']
    candidate_rows = []
    for row, record in zip(rows, source.records):
        found = [s for s in candidates if selected(s, row)]
        assert len(found) <= 1
        if found:
            candidate_rows.append(row)
        group = found[0]['match']['groups'][0] if found else (
            'excluded-other-provider-previous-claim' if row['tool'] == 'claude-code' else
            'excluded-internal-auto-review-unpriced' if row['model'] == 'codex-auto-review' else
            'excluded-authorized-or-not-individually-attributable')
        assert row['group'] == group
        assert sum(matches(s, record) for s in scope['segments']) == 1
        assert re.fullmatch(r'id-[0-9a-f]{20}', row['session_id'])
        assert row['agent_id'] == 'main' or re.fullmatch(r'id-[0-9a-f]{20}', row['agent_id'])
        assert re.fullmatch(r'request-[0-9a-f]{20}', row['request_id'])
        assert re.fullmatch(r'f-[0-9a-f]{12}', row['source'])
        assert all(row[f] >= 0 for f in FIELDS)
        assert row['reasoning_tokens'] <= row['output_tokens']
        if row['tool'] == 'codex':
            assert sum(row[f] for f in ('cache_write_5m_tokens', 'cache_write_1h_tokens', 'cache_write_tokens')) == 0

    # Exercise the actual strict CLI. Capture output without rewriting artifacts.
    stdout, stderr = io.StringIO(), io.StringIO()
    old_cwd = Path.cwd()
    os.chdir(HERE)
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(['claim', '--scope', 'historical-scope.toml', '--usage', 'usage.jsonl',
                                  '--rates', 'rates-openai.json', '--format', 'json', '--strict'])
    finally:
        os.chdir(old_cwd)
    assert exit_code == expected['strict_exit_code'] == 3
    assert 'codex-auto-review' in stderr.getvalue()
    rebuilt = json.loads(stdout.getvalue())
    stored = json.loads((HERE / 'historical-selected-subtotal.json').read_text())
    rebuilt['generated_at'] = stored['generated_at']
    assert rebuilt == stored
    assert render_markdown(stored) == (HERE / 'historical-selected-subtotal.md').read_text()
    assert stored['totals']['refundable']['requests'] == expected['refundable_requests'] == len(candidate_rows)
    assert stored['totals']['refundable']['tokens'] == expected['refundable_tokens']
    assert stored['totals']['refundable']['cost_usd'] == expected['refundable_usd']
    assert stored['totals']['unclassified']['requests'] == expected['unclassified_requests'] == 0
    assert stored['unpriced_models'] == expected['unpriced_models']
    keys = ('name', 'status', 'requests', 'tokens', 'cost_usd')
    assert [{k: s[k] for k in keys} for s in stored['segments']] == expected['per_segment']
    assert all(s['requests'] > 0 for s in stored['segments'])

    # Independent decimal arithmetic using the three standard benchmark rates.
    fixed_rates = {'gpt-6-astra': ('10', '1', '50'),
                   'gpt-6.1-sol': ('2', '.1', '10'),
                   'gpt-6.1-terra': ('1', '.05', '5')}
    price = Decimal(0)
    for row in candidate_rows:
        ir, cr, outr = map(Decimal, fixed_rates[row['model']])
        price += (row['input_tokens'] * ir + row['cache_read_tokens'] * cr + row['output_tokens'] * outr) / Decimal(1000000)
    assert price.quantize(Decimal('.01'), rounding=ROUND_HALF_UP) == Decimal(str(expected['refundable_usd']))

    counters = json.loads((HERE / 'counter-reconciliation.json').read_text())
    assert len(counters) == len({r['thread_id'] for r in counters}) == 90
    assert hashlib.sha256((HERE / 'counter-reconciliation.json').read_bytes()).hexdigest() == expected['counter_reconciliation_sha256']
    for counter in counters:
        own = [r for r in rows if r['tool'] == 'codex' and thread(r) == counter['thread_id']]
        assert counter['matches'] is True and len(own) == counter['requests']
        raw = dict(
            input_tokens=sum(r['input_tokens'] + r['cache_read_tokens'] + r['cache_write_tokens'] for r in own),
            cached_input_tokens=sum(r['cache_read_tokens'] for r in own),
            cache_write_input_tokens=sum(r['cache_write_tokens'] for r in own),
            output_tokens=sum(r['output_tokens'] for r in own),
            reasoning_output_tokens=sum(r['reasoning_tokens'] for r in own),
            total_tokens=sum(sum(r[f] for f in FIELDS if f != 'reasoning_tokens') for r in own))
        assert raw == counter['sum_explicit_usage'] == counter['cumulative_endpoint_span']
        assert all(value == 0 for value in counter['difference'].values())
    for name in ('historical-scope.toml', 'usage.jsonl', 'claim.json', 'claim.md', 'expected.json', 'rates-openai.json', 'counter-reconciliation.json'):
        text = (HERE / name).read_text()
        assert '/Users/' not in text and '/var/folders/' not in text
        assert not re.search(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', text)
    print(json.dumps(dict(verified=True, records=len(rows),
                         candidate_requests=expected['refundable_requests'],
                         candidate_tokens=expected['refundable_tokens'],
                         standard_api_benchmark_usd=expected['refundable_usd'],
                         unclassified_requests=0, unpriced_responses=6,
                         strict_cli_exit=exit_code, reconciled_codex_threads=len(counters)), indent=2))


if __name__ == '__main__':
    verify()
