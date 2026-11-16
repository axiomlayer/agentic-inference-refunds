# Operator procedure: generating a claim locally

This is the sequence for turning a local usage export into a refund claim on your own machine, and for correcting that claim later without losing the earlier version. Everything here runs locally. Nothing is uploaded, and **generating a claim does not submit it to a provider and does not guarantee a refund.** Submitting is a separate step that a person decides on and does by hand.

## Prerequisites

- **Python 3.11 or newer** already installed. The `scope-refund` runtime uses the standard library only.
- **The `scope-refund` command.** Use either of these:
  - the installed entrypoint, for example from `pipx install git+https://github.com/axiomlayer/agentic-inference-refunds`;
  - or, from a checkout without installing, `PYTHONPATH=<checkout>/src python3 -m agentic_inference_refunds`. It takes the same subcommands and flags as `scope-refund`.
- **A usage export you are authorized to use.** Only use usage records that belong to you, or that the account owner has authorized you to process. The examples below use a normalized export called `usage.jsonl`, in the format `scope-refund usage` writes. Records from a supported tool's own files can be passed directly with `--claude-code`, `--codex` or `--copilot` instead of `--usage`; see the [README](../README.md#where-each-tool-keeps-its-usage).

## Where to work

Run every command from one working directory that holds your private inputs. If you work inside a checkout of this repository, use the root-local folders that `.gitignore` already excludes:

| Path (relative to the checkout root) | Holds |
|---|---|
| `local-usage/` | Your usage exports, for example `local-usage/usage.jsonl` |
| `local-claims/` | Generated claim directories, one per version |
| `scope.private.toml` | Your scope file, if you keep it at the root |

`examples/` holds curated, neutral examples that are part of the repository. Don't put your own exports, scope files or claims there. [Distribution](distribution.md) explains why.

The commands below use the neutral filenames from the issue and assume the working directory holds `usage.jsonl`. Inside a checkout, use the root-local paths above instead, for example `--usage local-usage/usage.jsonl --scope scope.private.toml --out-dir local-claims/claim-v1/`.

## The sequence

### 1. Describe the scope

```sh
scope-refund init --out scope.toml
```

- **Reads:** nothing.
- **Creates:** `scope.toml` in the working directory, a template to fill in.
- If `scope.toml` already exists, `init` refuses and changes nothing unless you pass `--force`. Don't use `--force` on a scope file that a previous claim was generated from (see [Correcting a claim](#correcting-a-claim)).

Fill in `[requested]` (required), `[delivered]`, the `[[evidence]]` entries, and the `[[segments]]` that split the usage. `scope-refund schema scope` prints the full schema.

### 2. See where the usage went

```sh
scope-refund price --usage usage.jsonl --by group
```

- **Reads:** `usage.jsonl`, plus the bundled rate cards and any `--rates` file you add.
- **Creates:** nothing. It prints a table to the terminal.

Use this table to choose segment match rules. `--by` also accepts `model`, `agent`, `tool` and `session`. A row marked `(unpriced: N)` has a model that no rate card covers.

### 3. Generate the claim

```sh
scope-refund claim --scope scope.toml --usage usage.jsonl --format both --out-dir claim/
```

- **Reads:** `scope.toml`, `usage.jsonl` and the rate cards.
- **Creates:** the `claim/` directory (made if missing), containing `claim.md` (the letter, for people) and `claim.json` (the same claim for agents; `scope-refund schema claim` prints its schema). It prints the refundable amount and any warnings to the terminal.
- **Leaves alone:** `usage.jsonl` and `scope.toml`. The command doesn't modify its inputs.

If `claim/` already holds a `claim.md` or `claim.json`, this command **overwrites them without asking.** Give every version its own directory. See [Correcting a claim](#correcting-a-claim).

## How usage is classified and priced

**First match wins.** Every usage record goes to the **first** `[[segments]]` entry, in file order, whose `match` rules it satisfies. A record that matches no segment is **unclassified**. Unclassified usage is never refunded, appears only in the `all` total, and causes a warning naming how many requests were left out. Nothing is silently counted either way: to include unclassified usage, add or reorder segments, then generate a new version.

**Status decides refundability.** By default, `out_of_scope`, `unrequested_change` and `remediation` are refundable; `approved` and `excluded` are not. A segment can override that default with `refundable = true` or `refundable = false`.

**Unpriced and uncertain rates stay visible.** A model that no rate card covers has its tokens counted but is never priced or guessed at. It is listed under `unpriced_models` and raises a warning. The OpenAI and GitHub Copilot cards are marked unverified; claims priced from them say so in their warnings, and you should check them against the provider's rate sheet before relying on the figure. `scope-refund rates` shows every card, its date and whether it is verified. To correct or add a price, pass `--rates mycard.json`. That overrides the bundled entry for that model only, in that run.

**API-equivalent, not a bill.** The amount is an **API-equivalent** figure: the recorded tokens priced at the provider's published per-token list rates. If the usage was drawn from a subscription plan, the figure measures the plan usage consumed, in the provider's own published prices. It isn't what you were billed, and it isn't how the provider accounts for plan usage internally.

## Exit codes

These are the CLI's documented exit codes:

| Exit code | Meaning |
|---|---|
| 0 | OK |
| 2 | Bad input: a missing file, or an invalid scope file (the error lists each problem) |
| 3 | `--strict` was passed and some usage was unpriced or unclassified |

Two refusals currently print a message and exit with status 1 instead: `init` declining to overwrite an existing file, and a run whose sources contain no usage records at all. Treat any non-zero exit as "no usable output from this run".

## Correcting a claim

A correction is a new version. It never replaces the old one:

1. **Keep the original export unchanged.** Don't edit or re-export over `usage.jsonl`. `claim.json` records the SHA-256 of every source file, so a changed export no longer matches the earlier claim.
2. **Keep the earlier claim directory unchanged.** Leave `claim/`, or `local-claims/claim-v1/`, exactly as generated.
3. **Edit only the inputs that need it.** That means the scope file you choose (segments, statuses, evidence) or a local rate override file. If you want the earlier scope file preserved too, copy it first (for example `cp scope.toml scope-v2.toml`) and edit the copy.
4. **Generate into a newly named directory:**

   ```sh
   scope-refund claim --scope scope.toml --usage usage.jsonl --format both --out-dir claim-v2/
   ```

   If you changed rates, add `--rates mycard.json`. Use a directory name that doesn't exist yet: `--out-dir` overwrites an existing `claim.md` or `claim.json` without warning.

5. **Compare** `claim-v2/` with the earlier directory before you use the new figure anywhere.

Reusing the earlier output directory is not a correction path. It destroys the version you are correcting.

## What a claim contains, and who should see it

`claim.md` and `claim.json` carry what you put in the scope file: the claimant name, the verbatim request quote, the evidence text and the provider addressed. `claim.json` also records each source file's path exactly as you passed it on the command line, with its SHA-256 and size. Token counts, model names, timestamps and IDs are read from the usage; message content never is. If you pass `--redact`, session, agent and request IDs and source file names are replaced with hashes. The scope-file text is still included.

Treat generated claims as private until you decide to share one.

## Submitting

`scope-refund` stops at the claim files. It doesn't contact a provider, file anything or request a refund. Whether, where and how to submit a claim is a separate decision for a person, made after reviewing the claim and its warnings. A generated claim is a measurement. It guarantees no refund and implies no provider approval.
