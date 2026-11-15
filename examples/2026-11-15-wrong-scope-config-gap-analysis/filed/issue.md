# Issue as filed on anthropics/claude-code

`/bug` was disabled by organization policy, so this went in as a public GitHub issue. The token figure in this body ("about 9.7 million subagent tokens") counted only uncached input and output; `followup-comment.md` corrects it to 465.4 M tokens processed and $211.69.

## Title

Refunds when the model spends significant tokens on the wrong scope

## What's Wrong?

- I asked for a config gap analysis of my home lab: the designed management system against the as-is evidence. Claude Code (Opus 5.5, multi-agent mode on) ran eight multi-agent workflows over about 2 hours and used about 9.7 million subagent tokens (per the workflow usage reports), plus the main thread.
- What it produced was a governance reconciliation: an evidence-sampling study, a 57-row gap register, 45 "decisions" and 31 "questions only you can answer".
- Most of that output relitigated decisions I had already made, and it treated my own setup as security exposure or an "authority failure": permissions I enabled myself, deploys I approved, holds I placed. Several questions asked whether I had approved things I had personally done.
- No one asked for a recursive, meta-conversational, bureaucratic review of whether a hostile actor had gained entry to my secure tailnet. I asked for a config gap analysis.
- The config audit itself (what each config file sets, where copies disagree, what breaks) was not done until I pointed it out. The model then acknowledged it had audited agent metadata and decision provenance instead of the configs.
- A downstream agent then walked me through the generated questions one at a time, which cost more time re-deciding things I had already decided.

**Bug.** The model drifted from the requested scope into a different and much more expensive task. It took an adversarial, regulatory posture that the request never asked for. It did not confirm scope before spending at scale.

**Feature requests.**

1. A refund or credit when the model spends significant tokens on work outside a clearly submitted scope.
2. A scope check before large multi-agent runs: restate the deliverable in one line with an estimated spend, and stop to confirm if the planned outputs differ from what was asked.
3. Spend checkpoints during long runs that show what the work is actually producing, so a wrong direction is caught after minutes rather than hours.

## What Should Happen?

- Before a large multi-agent run, Claude restates the deliverable in one line (here: "config gap analysis: what each config file sets, where copies disagree, what breaks") with an estimated token spend. If its planned outputs differ from what was asked, it stops and confirms before spending.
- It analyzes the actual configuration files. It treats the user's own stated decisions, approvals and settings as given. It does not turn them into questions back to the user, and it does not frame them as security exposure when no threat model was requested.
- Long runs show checkpoints of what is actually being produced, so wrong-scope work is caught within minutes rather than after about 2 hours and about 9.7 million tokens.
- When significant tokens are spent on work outside a clearly stated scope, there is a way to have them refunded or credited.

## Steps to Reproduce

1. Claude Code 2.1.325, model Opus 5.5 (claude-opus-5-5), effort xhigh, multi-agent workflow mode ("ultracode") on.
2. Submit a gap-analysis task: compare a project's designed system against as-is evidence of what exists (repos with installer scripts, settings/policy JSON, CI workflows, plus the owner's records of their own past decisions). Ask for a gap register and a list of decisions for the owner, and state that the model must not redesign anything.
3. In the evidence, include decisions the owner already made, e.g. they enabled bypass-permissions mode themselves, approved a set of deploys, and placed a merge hold.
4. Let it run to completion.

Observed: about 2 hours and about 9.7M subagent tokens across 8 workflows. Output was a 57-row governance gap register, 45 "decisions" and 31 "questions only you can answer". Most of it re-asked the owner about decisions they had already made, and it framed their own settings as security exposure or authority failures. The configuration files themselves (what each sets, where copies disagree, what breaks) were not audited until the owner pointed it out.

(The original prompt is long and private, so it isn't included verbatim.)

## Environment

- Claude Model: Opus 5.5 (claude-opus-5-5), effort xhigh
- Is this a regression? No (first time doing this kind of run)
- Claude Code Version: 2.1.325 (Claude Code)
- Platform: Anthropic API (no Bedrock or Vertex variables set)
- Operating System: macOS 27.0 (26A428), Apple Silicon (arm64)
- Terminal/Shell: Apple Terminal 488, zsh

## Additional Information

Token use by workflow (from the workflow usage reports): evidence check 0.91M; gap discovery 2.94M; decision extraction 1.30M; supplementary lens 0.30M; verification and decision merge 2.49M; gap-list comparison 0.17M; prior-reconciliation comparison 1.62M. Total about 9.7M subagent tokens, plus the main thread.

The model never stopped to restate the deliverable or the expected spend before fanning out, and no checkpoint showed that the outputs were drifting from the requested scope.

Session ID available to Anthropic on request.
