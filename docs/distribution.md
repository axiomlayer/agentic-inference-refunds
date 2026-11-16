# Distribution: what ships, and what stays local

## The source distribution

The source distribution of `agentic-inference-refunds` is the tracked contents of this repository. That's what you get from a clone, from `git archive`, or from GitHub's source download. It consists of:

| Contents | Where |
|---|---|
| Code | `src/agentic_inference_refunds/`, including the bundled rate cards and JSON schemas under `data/`; `tests/` and its fixtures; repository configuration (`.github/`, `.gitignore`) |
| Package metadata | `pyproject.toml` |
| License | `LICENSE` |
| Documentation | `README.md`, `docs/` |
| Neutral examples | `examples/`: curated worked examples whose usage, scope and claim files were reviewed and committed on purpose |

`examples/` is part of the source distribution. Everything in it is deliberately published reference material, so don't put new private data there.

## What stays outside it

These never belong in the source distribution:

- **Private usage exports:** Claude Code, Codex or Copilot session files, and anything `scope-refund usage` writes from them.
- **Operator-specific scope settings:** the scope file describing your own dispute, with your name, the verbatim request and your evidence.
- **Generated claims:** `claim.md` and `claim.json` from your own runs. They repeat the scope file's contents and record your source file paths (see [the operator procedure](operator.md#what-a-claim-contains-and-who-should-see-it)).

When you work inside a checkout, keep these in the root-local paths that `.gitignore` excludes:

```gitignore
/local-usage/
/local-claims/
/scope.private.toml
```

The entries are anchored to the repository root, so they never match anything under `examples/`. Already-tracked example files stay tracked.

Two things `.gitignore` can't do:

- **It doesn't remove a file that is already tracked.** If private data was committed before, removing it is a separate change that only deletes that file. It doesn't rewrite history or touch any other file.
- **It doesn't stop a forced add (`git add -f`).** Don't force-add anything from these paths.

Private data kept somewhere outside the checkout is outside the source distribution by definition. These exclusions just give a safe default to people who work inside one.

## Built packages

Running `pip install .`, `pipx install` or a package build produces artifacts that are a **subset** of the source distribution. They are assembled from the package declaration in `pyproject.toml`, not from `.gitignore`. Checked against the current `pyproject.toml` with setuptools:

- **Wheel:** the `agentic_inference_refunds` package with its bundled rate cards and schemas, plus metadata and `LICENSE`.
- **sdist:** the same package, `pyproject.toml`, a generated `setup.cfg` and `PKG-INFO`, `README.md`, `LICENSE`, and `tests/test_scope_refund.py`. It doesn't include `docs/`, `examples/` or `tests/fixtures/`.

Neither artifact picks up root-local files. A build run with `local-usage/`, `local-claims/` and `scope.private.toml` present at the checkout root left all three out. This protection comes from where the files sit, not from the ignore rules: anything placed inside `src/agentic_inference_refunds/` that matches its package data would ship. So private data never goes under `src/`.

## Not covered here

This document defines contents. It doesn't publish anything: no package upload, no release and no installation is part of it.
