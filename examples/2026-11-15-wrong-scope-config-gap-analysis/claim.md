# Wrong scope delivered: a governance reconciliation instead of a config gap analysis

To: Anthropic · Claude Code (Claude Opus 5.5, multi-agent workflows) · subscription plan usage · From: Jasen Carroll

**Requested remedy: $211.69 USD, as extra usage credits.** API-equivalent cost of the refundable segments: each request's recorded tokens, priced at the provider's published per-token list rates.

## What was requested

A config gap analysis of the lab: what each configuration file sets, where copies disagree, and what that breaks.

> I SAID TO AUDIT THE [...] CONFIGS
> YOU AUDITED THE AGENTS [...] METADATA

Recorded: Owner's message in the session, 2026-11-15 13:18:57 PST (profanity elided). The original prompt is private.

## What was delivered

Before the objection: a governance reconciliation package (an evidence-sampling study, a 57-row gap register, 45 'decisions' and 31 'questions only you can answer'). Most of it re-asked the owner about decisions already made, and it treated the owner's own settings, approvals and holds as security exposure. The config audit itself (111 verified findings) was produced only after the objection.

## The cost

| | Requests | Tokens processed | Output tokens | API-equivalent cost |
|---|---:|---:|---:|---:|
| Approved scope | 637 | 94.2 M | 504,811 | $37.07 |
| Not approved (out of scope, unrequested changes, remediation) | 2,469 | 465.4 M | 3,484,486 | $211.69 |
| Excluded by claimant | 61 | 39.3 M | 134,505 | $12.41 |
| **Refundable** | **2,469** | **465.4 M** | **3,484,486** | **$211.69** |

For every dollar spent on the approved scope, $5.71 went to work that was not approved.

### By segment

| Segment | Status | Refundable | Requests | Tokens | Cost |
|---|---|---|---:|---:|---:|
| Config audit (the requested scope) | approved | no | 637 | 94.2 M | $37.07 |
| &nbsp;&nbsp;Config audit: the requested scope, 9 subagents | | | 637 | 94.2 M | $37.07 |
| Reconciliation workflows nobody asked for | out_of_scope (wrong_scope) | yes | 2,339 | 427.0 M | $196.43 |
| &nbsp;&nbsp;Gap discovery, 9 subagents | | | 593 | 138.1 M | $59.84 |
| &nbsp;&nbsp;Verify register, merge decisions, 8 subagents | | | 614 | 113.2 M | $54.40 |
| &nbsp;&nbsp;Compare with an earlier reconciliation, 5 subagents | | | 504 | 108.1 M | $40.04 |
| &nbsp;&nbsp;Extract decision sets, 7 subagents | | | 267 | 34.2 M | $21.83 |
| &nbsp;&nbsp;Evidence check, 9 subagents | | | 309 | 25.0 M | $13.09 |
| &nbsp;&nbsp;Lens on a newly added spec, 1 subagents | | | 32 | 6.0 M | $4.40 |
| &nbsp;&nbsp;Compare with the design's own gap list, 1 subagents | | | 20 | 2.3 M | $2.82 |
| Main thread up to the objection | out_of_scope (wrong_scope) | yes | 130 | 38.4 M | $15.25 |
| &nbsp;&nbsp;Main thread | | | 130 | 38.4 M | $15.25 |
| Main thread after the objection (follow-up work, not part of this claim) | excluded | no | 61 | 39.3 M | $12.41 |
| &nbsp;&nbsp;Main thread | | | 61 | 39.3 M | $12.41 |

Refundable cost by token type: output $69.69, cache reads $90.38, cache writes $51.60, uncached input $0.02.

## Behavior observed

- Subagents spawned: 49 (40 in work that was not approved).
- Reasoning share of output tokens: 54%.
- Largest spend between two human messages: $132.02 over 72.5 minutes (1,338 requests, 2026-11-15T19:07:36Z to 2026-11-15T20:20:04Z).
- Before the first objection (2026-11-15T21:18:57Z, 145.2 minutes in): $211.69 spent, $211.69 of it on work that was not approved.

## Evidence

- **objection** (2026-11-15T21:18:57Z): Owner: 'I waited 2 hours for 4 million tokens so you could litigate my decisions against me? ... I said to audit the configs. You audited the agents' metadata.' (profanity elided) — session transcript, user message at 13:18:57 PST
- **acknowledgement** (2026-11-15T21:21:50Z): Model: 'What I actually audited was the evidence records (agent records, practices, ledger) against the design documents. I never ran a dedicated audit of the configuration files themselves.' — session transcript, assistant reply at 13:21:50 PST
- **artifact**: The requested config audit, run after the objection: 7 config families, 111 findings (76 confirmed and 34 corrected by a second agent, 1 refuted). — workflow wf_cfa29e1d-594
- **timeline** (2026-11-15T18:53:29Z): Session start. The deliverable and the expected spend were never restated before 40 subagents were fanned out across 7 workflows.

## How this was measured

Each usage record is assigned to the first segment in the scope file whose match rules it satisfies; unmatched records are listed as unclassified and are never refundable.

cost = uncached input x input rate + cache reads x cache-read rate + cache writes x write rate (5-minute or 1-hour, per the recorded TTL) + output (including reasoning) x output rate.

Claude Code: by message id. Codex: by response id. Copilot: by event id.

| Rate card | As of | Verified | Source |
|---|---|---|---|
| anthropic-api-list-2026-11-03 | 2026-11-03 | yes | Anthropic Claude API pricing (Claude API reference, cached 2026-11-03): https://platform.claude.com/docs/en/about-claude/pricing |

3,167 usage records from 1 files, 2026-11-15T18:53:46.623Z to 2026-11-15T21:59:49.798Z. SHA-256 of each source file is in the JSON claim, so the figures can be recomputed.

_Generated by scope-refund 0.1.0 at 2026-11-15T22:02:22Z._
