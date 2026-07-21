# maid-validator-csharp

C# (`.cs`) language validator **plugin** for MAID Runner, backed by
tree-sitter-c-sharp. It registers through the `maid_runner.validators`
entry point (`csharp = "maid_validator_csharp:CSharpValidator"`), adding `.cs`
support to any maid-runner install **without modifying maid-runner core**. This
follows maid-runner's plugin support boundary (`docs/validator-plugin-authoring.md`
in that repo): new languages ship as external packages.

## Layout

- `src/maid_validator_csharp/validator.py` — `CSharpValidator(BaseValidator)`, thin wrapper over tree-sitter.
- `src/maid_validator_csharp/_parse.py` — parse session + parse-error walk.
- `src/maid_validator_csharp/_implementation.py` — definition collector (public API surface only).
- `src/maid_validator_csharp/_behavioral.py` — test-reference collector.
- `tests/test_conformance.py` — the maid-runner conformance kit; **this is the acceptance bar**.
- `tests/test_implementation.py`, `tests/test_behavioral.py` — hand-written extraction cases.

## Quality gate (run before any handoff)

There is **no `make`** here; these three commands are the gate:

- `uv run pytest -q`
- `uv run ruff check src/ tests/`
- `uv run black --check src/ tests/`

When changing collectors, inspect the tree-sitter-c-sharp node/field names
against real C# **before** coding — the grammar is the source of truth
(construct → `ArtifactKind` mapping and visibility rules live in
`_implementation.py`). maid-runner is a dependency (`>=2,<3`); the venv uses the
published release, so contract changes needing unreleased maid-runner fixes
require publishing maid-runner first.

<!-- BEGIN MAID RUNNER -->
## MAID Runner

Instruction payload version: 2026.07.18.1

### MAID Codex Skills Workflow
Use the installed MAID Codex skills for manifest-driven development: `maid-planner`, `maid-plan-review`, `maid-implementer`, `maid-implementation-review`, `maid-auditor`, `maid-outcome-enrich`, `maid-run-review`.

For new features, bug fixes, and refactors, plan with `maid-planner`, review with `maid-plan-review`, implement with `maid-implementer`, and review the result with `maid-implementation-review` before handoff.

Before editing a file during an active MAID task, run `maid hook scope-check --path <file>` and treat exit code 2 as out-of-scope. This pre-edit hook check is advisory and does not replace `maid verify` changed-scope validation.

Draft manifests under `manifests/drafts/` are planning inventory, not active contracts. Child implementation drafts live at `manifests/drafts/*.manifest.yaml`; epic planning records live at `manifests/drafts/*.epic.yaml` and use split-before-promote before implementation; archived draft records are historical inventory. Before promoting the selected child draft, refresh the Outcome index when needed and run `uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet` when completed Outcome records exist. Recall is advisory planning context only: it can inform draft hardening and implementation risks, but it does not expand scope or replace red evidence, behavioral validation, plan lock, implementation validation, or review. Use `uv run maid insights` to review recurring Outcome lessons when an index is available. To intentionally include instructive failed or abandoned Outcome lessons, refresh the index with `uv run maid learn --include-status completed --include-status abandoned`, then recall from that index; the completed-only default is unchanged. When related Outcome evidence is retrieved, do not dump a raw recall or insights transcript into the task. Digest it visibly: name applicable lessons, reject stale or irrelevant lessons with a reason, and state what changed because of the evidence for the current planning, implementation, or review phase. Recalled, aggregated, and digested Outcomes remain advisory planning context only; they do not create an approval, promotion, done, or review gate. Promote one selected child draft with `uv run maid manifest promote manifests/drafts/<slug>.manifest.yaml`. Do not manually move or copy draft manifests. For metadata-only reference cleanup on locked active manifests, use `uv run maid plan revise <manifest> --reason "<text>" --preserve-red-evidence`. For review-driven behavioral contract changes after implementation exists, use `uv run maid plan revise <manifest> --reason "<text>" --stash-implementation` so MAID temporarily hides declared implementation changes while it captures fresh red evidence.

Always capture an Outcome record after implementation validation and implementation review, before final handoff. Capture Outcome after implementation review so the result records the reviewed evidence. Outcome capture is required for completed, partial, failed, superseded, archived, or abandoned MAID work. The Outcome must cite concrete validation evidence and review notes; it does not replace behavioral tests, declared artifacts, validation commands, or implementation review. After Outcome capture, run `uv run maid learn` to refresh the local `.maid/outcomes.json` advisory index for subsequent recall. `.maid/outcomes.json` is generated and ignored; do not commit it. If `maid learn` fails, report the refresh failure as advisory unless recall or insights are required for the current task. See `docs/draft-manifest-workflow.md` and `docs/manifest-outcome-records.md`.

Installed Codex skill-local agent metadata files: 7.
<!-- END MAID RUNNER -->
