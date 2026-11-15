# Worked example: $211.69 spent on the wrong scope

On 2026-11-15 a Claude Code session (Claude Opus 5.5, multi-agent workflows) was asked for a **config gap analysis** of a home lab: what each configuration file sets, where copies disagree, and what that breaks. It delivered a **governance reconciliation** instead. Two hours and twenty-five minutes later the owner objected. The config audit was then run, and took 24 minutes.

This folder is the claim that came out of it, rebuilt from the session's own usage records with this tool.

## The numbers

| | Requests | Tokens processed | API-equivalent cost |
|---|---:|---:|---:|
| Approved scope: the config audit | 637 | 94.2 M | **$37.07** |
| Not approved: everything before the objection | 2,469 | 465.4 M | **$211.69** |

- **$5.71 of unapproved work for every $1 of approved work.**
- **40 subagents across 7 workflows** fanned out before anyone checked the deliverable. The approved audit used 9.
- **Largest spend between two human messages: $132.02 over 72 minutes** (1,338 requests). The last thing the owner had said before it was "word".
- **Before the first objection:** 145 minutes, all $211.69, every dollar of it on unapproved work.
- 97% of tokens were cache reads, and 54% of output tokens were reasoning.

The follow-up after the objection ($12.41 at the time of export) is excluded from the claim. It includes the bug report and building this tool.

## What was delivered instead

Before the objection, the session produced:

- An evidence-sampling study.
- A 57-row governance gap register.
- 45 "decisions" and 31 "questions only you can answer" for the owner.

Most of the questions re-asked the owner about decisions he had already made: holds he had placed, deploys he had approved, a bypass-permissions setting he had turned on himself. Several high-risk rows framed his own setup as security exposure. When the owner said he had asked for a config audit, the model replied: "What I actually audited was the evidence records (agent records, practices, ledger) against the design documents. I never ran a dedicated audit of the configuration files themselves."

The config audit that followed found 111 issues across seven config families, 110 of which held up when a second agent checked them. Examples:

- Whole-file rewrites of shell and git config on every apply.
- Agent settings forced to a different permission mode.
- Three managed policies disabling a mode the owner had enabled.
- Paused update jobs that the next apply would silently re-enable.

The raw reconciliation package and the audit stay private: they name hosts, addresses and the locations of credential files.

## Files

- `scope.toml`: what was asked, what was delivered, the evidence, and the four segments the usage is split into.
- `usage.jsonl`: one line per billed request, extracted with `scope-refund usage --redact`. It holds token counts, model, timestamp and hashed IDs only, with no message content.
- `claim.md` and `claim.json`: the claim the tool produces.
- `expected.json`: the figures the test suite holds the tool to.
- `filed/`: what was actually filed with Anthropic. That is the GitHub issue (its "9.7M tokens" figure was wrong and is corrected in the follow-up), the follow-up comment with the $211.69 measurement and the credit argument, and the cost chart.

## Reproduce

```sh
scope-refund claim --scope scope.toml --usage usage.jsonl --format md
```

Usage was extracted from the live transcripts with:

```sh
scope-refund usage --claude-code ~/.claude/projects/<project>/<session>.jsonl --redact --out usage.jsonl
```
