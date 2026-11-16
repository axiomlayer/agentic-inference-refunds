# Worked example: Codex lab-remediation drift and repeated ZIP misdelivery

This case reviews the locally available JSONL evidence for an eight-hour lab-remediation session on November 15, 2026. Agents repeatedly lost the requested product handoff, execution order and assembly ownership; the eventual coordinator added unwanted archives and HTML pages and then spent further inference repairing those decisions.

The inventory covers **4,133 local JSONL paths**. Globally deduplicated records contain **14,777 OpenAI responses / 2,618,064,476 processed tokens**, including cached input. Those are the full observed totals, **not the claimed refundable total**. Bounded failures and repair work are selected separately in the claim. Substantial authorized governance and inspection work, mixed work without reliable attribution, and all Anthropic usage are excluded from the OpenAI request.

The selected claim covers **328 responses, 76,580,662 processed tokens and a $19.70 standard API-equivalent benchmark**. This measured subset is not a ceiling on credit restoration determined from OpenAI's billing records. The broader report asks OpenAI to investigate the owner's reported 75,000-credit loss; local snapshots cannot establish a request-level credit refund.

- [Full report](full-report.md): findings, timeline, accounting, counterevidence, coverage limits and requested remedy.
- [Computed claim](claim.md) and [machine-readable claim](claim.json): selected response counts, token totals and standard API-equivalent value.
- [Evidence ledger](evidence.md) and [structured evidence](evidence.json): original file identifiers, line numbers and timestamps, with privacy redactions.
- [Every-file inventory](coverage.csv) and [conversation review dispositions](review-coverage.csv): coverage including exclusions.
- [Scope](scope.toml), [redacted usage](usage.jsonl), [verified pricing](rates-openai.json) and [expected totals](expected.json): reproducible inputs/results.
- [Counter reconciliation](counter-reconciliation.json): the 90 thread-level usage cross-checks, with redacted identifiers.
- `filed/`: exact issue text and verified submission receipt after filing.

Original transcripts and account/billing identifiers remain local. The dollar benchmark does not establish actual subscription-credit deductions. The owner requested a refund; only OpenAI can adjudicate or process it.

From the repository root, reproduce the claim with the installed CLI:

```sh
scope-refund claim --scope examples/2026-11-15-codex-lab-remediation-drift/scope.toml --usage examples/2026-11-15-codex-lab-remediation-drift/usage.jsonl --rates examples/2026-11-15-codex-lab-remediation-drift/rates-openai.json --format both --out-dir build/reproduced-codex-claim
```

The internal `codex-auto-review` model has no verified public price and is explicitly excluded. Strict mode is expected to flag those six unpriced records; it must not be presented as a fully priced dataset.
