### Bug and requested remedy

I am reporting repeated behavioral misalignment in a multi-agent Codex lab-remediation session and requesting restoration of the plan/extra-usage credits spent on wrong-scope work and the resulting repair. The intended work was a remediated lab with an agreed execution sequence and one clean compilation of the improved product deliverables. Multiple agents instead lost the deliverable scope, duplicated assembly ownership, and repeatedly substituted their own next steps. A coordinator brought in to stop that behavior repeated it.

This is a separate refund/misalignment report from the narrower disabled-browser report, [#61735](https://github.com/openai/codex/issues/61735).

### Evidence package and measured scope

An eight-hour local JSONL review covers **2026-11-15T19:40:23Z to 2026-11-16T03:40:23Z**, end exclusive. The public report follows the worked-example structure in [axiomlayer/agentic-inference-refunds](https://github.com/axiomlayer/agentic-inference-refunds), informed by [the earlier Claude report](https://github.com/anthropics/claude-code/issues/110273), with that report's corrected accounting rather than its original underestimated token count.

- **Full report:** [Full eight-hour report](https://github.com/axiomlayer/agentic-inference-refunds/blob/b037e4da013c01856f9fd22a2df3cd975ef7e08b/examples/2026-11-15-codex-lab-remediation-drift/full-report.md)
- **Reproducible claim:** [Computed claim and limits](https://github.com/axiomlayer/agentic-inference-refunds/blob/b037e4da013c01856f9fd22a2df3cd975ef7e08b/examples/2026-11-15-codex-lab-remediation-drift/claim.md)
- **Source-linked, redacted evidence:** [Evidence ledger](https://github.com/axiomlayer/agentic-inference-refunds/blob/b037e4da013c01856f9fd22a2df3cd975ef7e08b/examples/2026-11-15-codex-lab-remediation-drift/evidence.md)
- **All-file coverage manifest:** [4,133-file inventory](https://github.com/axiomlayer/agentic-inference-refunds/blob/b037e4da013c01856f9fd22a2df3cd975ef7e08b/examples/2026-11-15-codex-lab-remediation-drift/coverage.csv)

The inventory screened **4,133 local JSONL paths**. Native records contain **14,777 unique OpenAI responses and 2,618,064,476 processed tokens** across the interval, including repeatedly processed cached input. These are the full observed totals, not a claim that all activity was unauthorized.

The bounded claim selects **328 responses, 76,580,662 processed tokens and 120,449 output tokens**, with a **$19.70 standard API-equivalent benchmark** using [OpenAI's published prices](https://developers.openai.com/api/docs/pricing). This is an evidenced subset, not the actual credit deduction or a ceiling on reimbursement. Please reconcile it to your request-level billing records and investigate the larger documented pattern where local attribution is insufficient.

I reported approximately **75,000 credits and three quota resets** during the broader session. The local snapshots do not independently verify that exact total or number of resets. They show an observed first-minus-last credit difference of 67,520.9760395, but are interleaved and stale in places; the report does not present that difference as a debit ledger.

### What happened

1. **Scope correction became an unrelated audit.** An ownership/offline-delivery correction triggered an exposure investigation that I had not requested and had to stop. A dedicated child's own usage is isolated in the claim.
2. **Requested visual status required avoidable repair.** The dashboard retained rejected history and later became a text-heavy summary; identifiable correction turns removed the unwanted material and restored the requested visual status view.
3. **Agents repeatedly answered the combined-ZIP request with a known subset.** They later acknowledged the mismatch and rebuilt. A 1.66 GB compilation was itself later rejected for stale or missing product contents. The issue is loss of the established requirement; small file size alone is not proof of a fake ZIP.
4. **The agreed sequence was displaced.** Agents chose downstream code/deployment-review work before the agreed prerequisites. One changed a readiness reporter, reverted it when challenged, and restored it after I objected to deleting useful work. Another changed a release verifier and reverted the off-sequence edits. The report distinguishes actual edits from read-only inspection; it does not claim that the verifier deployed anything.
5. **Multiple agents assumed assembly ownership.** One later admitted its compilation preparation duplicated the designated owner. The evidence supports duplicate preparation and ownership claims, not a fabricated claim that a second compiler was successfully written.
6. **The coordinator made unsupported contents decisions.** It presented a roughly 904 MB package before reconciling coverage, responded to a size objection by adding historical archives, and delivered 1.667 GB. I rejected the extra material. It then rebuilt a roughly 217 MB package, added `START_HERE.html` and sixteen `OPEN_PRODUCT.html` pages without my request, and had to remove all seventeen. It subsequently found the small extractor distribution contained the same engine as the newest archived version; the earlier size-based conclusion had not been established.
7. **The support attempt used the disabled built-in browser.** The browser-control setting was off throughout. The tool still accepted two tab-creation requests and returned page content. I stopped that route. The model then prematurely claimed no submission route was available before checking GitHub/CLI, which did work. No internal explanation for the preference-enforcement failure is claimed; the exact sequence is in #61735.

### Expected behavior

Preserve the owner's accepted deliverable, content boundaries, execution sequence and explicit corrections across agents. Establish one assembly owner and let other agents finish bounded contributions. Use communications to complete the work rather than repeatedly reconstructing the same status. Check actual contents before asserting delivery; do not replace an uncertain contents decision with archive bulk or unsolicited interface pages. Enforce a disabled browser-control preference at the tool boundary.

### Accounting integrity and counterevidence

- Global response/message identity deduplication removed 1,470 duplicate observations and excluded two identities whose original observations preceded the review window. Forked histories can rewrite outer timestamps; counting each file independently would be wrong.
- All **90 Codex threads** reconcile explicit response sums to cumulative usage counters across six raw token fields. No conflicting values or cumulative fallback were added.
- Substantial governance, independent verification, communications and inspection were expressly authorized. Those are not all labeled wasted. Later Governance repository/runner setup was also expressly requested and is not claimed as nonexistent.
- All Anthropic usage is excluded from this OpenAI claim; the prior Claude example is not charged twice.
- The six internal `codex-auto-review` responses remain excluded and unpriced. No guessed service-tier multiplier or subscription-credit conversion is used.
- The public package contains redacted counts, evidence references and file fingerprints. Raw transcripts, account identifiers, private product contents and billing snapshots remain local.
- Coverage limits are explicit: local inventory only, an unreadable macOS container enumeration branch, undated historical transcripts, and opaque collaboration payloads. The semantic review does not claim independent re-execution of every tool result or product test.

### Environment

macOS 27.0 (26A428), arm64. Desktop app 26.1111.21308 (27194); native transcript originator `Codex Desktop`, CLI version `0.169.0-alpha.11.1`; installed CLI `0.169.0`. Observed model labels: `gpt-6-astra`, `gpt-6.1-terra`, `gpt-6.1-sol`, plus the internal auto-review label. This is an incident trace, not a claim of a newly reproduced deterministic failure.

### Specific request to OpenAI

1. Investigate these repeated scope/coordination failures and the separate preference-enforcement defect.
2. Match the documented intervals to actual account billing and **restore the plan/extra-usage credits attributable to the wrong-scope work and its repair**, including any larger loss your billing evidence establishes.
3. Provide a usable refund path for agentic work that materially departs from a clear, repeatedly corrected scope. A technically running model is not sufficient delivery when it substitutes the work being purchased.

The $19.70 figure is a standard API benchmark for the conservatively selected subset, not a statement that my total loss was $19.70. No refund has yet been approved or processed.
