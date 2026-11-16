# Accounting method and limits

This example retains **16,405 distinct response/message usage records** from the fixed UTC interval **2026-11-15 19:40:23 inclusive to 2026-11-16 03:40:23 exclusive**. The original **328-response / $19.70 subset** is now historical: the assistant had no authorization to narrow the requested refund to those selectors. The current claim concerns actual credit restoration across the full disputed OpenAI population. The accounting counts remain valid; original exclusion labels are retained only to reproduce the mistake.

The private inventory covered 4,133 JSONL paths and 4,055,353,484 bytes. Native usage appeared in 115 files during the interval. No read error affected an inventoried file; four malformed lines belonged to unrelated artifact/test data. Enumeration separately encountered an interrupted system call in an operating-system-managed container directory, so completeness beyond the enumerated local files is not asserted. An additional 383-path scan found no further in-window usage.

Codex usage is deduplicated globally by response ID, Claude by message ID, and Copilot by accounting usage/API-call identity. Forked history can rewrite outer timestamps: an identity whose earliest observed occurrence predates the interval is excluded even when copied inside it. The physical file owner comes from its first session metadata record. Duplicate observations are not new requests. The extraction removed 1,470 duplicate observations and two additional historical identities. All 90 Codex threads reconciled exactly against their cumulative thread counters; no cumulative fallback was needed. The redacted results in `counter-reconciliation.json` can be checked against the public usage totals. The interval contains no Copilot usage.

Token categories are disjoint: uncached input, cache reads, cache writes, and output. Reasoning is a subset of output. Processing billions of cached tokens does not mean billions of newly generated tokens. Public session, agent and request identities are hashed; `main` remains a role marker. Sources use inventory file IDs. Raw paths, complete prompts and private provenance remain outside this example.

`historical-scope.toml` records each original candidate interval, rationale and hashed identity selector. RR-03 covers the coordinator's session including two children. PR intervals cover their named main thread only. Other intervals cover exact threads. The verifier reconstructs those historical selections and checks the arithmetic. The original group labels do not establish accepted work or the current refund disposition.

The historical calculator excluded all remaining OpenAI work as authorized or not individually attributable. That unsupported catch-all is withdrawn. **The empty historical approved bucket does not mean that no useful authorized work occurred.** Its approved/unapproved comparison must not be interpreted as an overall waste measure. All OpenAI activity remains in the disputed review population. Anthropic usage stays outside this provider's remedy. The current [itemized calculation](remedy-calculation.md) combines owner-confirmed balance loss and a provisional, separately disclosed valuation of consumed plan capacity, including correction overage; it does not add the full token benchmark to credit loss.

The [OpenAI pricing source](https://developers.openai.com/api/docs/pricing), retrieved November 16, 2026, supplies standard USD-per-million-token rates. This is an API benchmark, without guessed service-tier multipliers. The current official cache-write columns are 30 minutes and 12 hours; the existing package's legacy 5-minute/1-hour fields hold those rates solely for schema compatibility. Every OpenAI write count is zero, so this mapping has no monetary effect. Six internal `codex-auto-review` responses are counted but unpriced, not assigned a zero rate. Credit balances and quota snapshots are not converted into attributable charges.

From the repository root, reproduce the generated claim with:

```bash
cd examples/2026-11-15-codex-lab-remediation-drift
PYTHONPATH=../../src python3 -m agentic_inference_refunds claim --scope historical-scope.toml --usage usage.jsonl --rates rates-openai.json --out-dir ../../build/reproduced-historical-subtotal --format both --strict
```

**Exit 3 is expected**, solely because the six internal responses lack a public rate. There are zero unclassified responses. Then run `python3 verify.py` to check the recorded totals, unique identities, interval membership, redaction, rate use and exact claim regeneration apart from its generation timestamp. Private extraction and semantic review cannot be independently repeated from the redacted example alone.
