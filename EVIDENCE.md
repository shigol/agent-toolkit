# Shared selection rollout evidence

Updated 2026-10-27. This is a partial implementation report, not full live-host verification.

## Implemented and checked

- Foundation PR #3 merged: 28 selection guides, source invocation restrictions and admission checks.
- Implementation PR #4 merged: bounded cross-group search, shared SELECTION.md, agent-assisted INTAKE.md and a deterministic pinned-source importer. The agent supplies evidence-backed metadata; no background AI service is implied.
- First real intake: MIT-licensed obra/superpowers verification-before-completion at 2ce8aa15d05bd57213e6f746f953aafb7ded7a8b, with source/license bytes preserved. Catalogue now has 29 skills. Dry run, applied import and repeated unchanged intake were exercised.
- Local tests: 30 Python tests, including admitted-skill edits/reversion, rejection of weakened manual-only restrictions, source symlinks/path escapes, idempotency and write-failure restoration. Four Node browser-discovery tests pass. All 1,084 vendored hashes verify.
- Retrieval fixtures cover UI, web motion, writing, market sizing, an unsupported database query, explicit exclusions, restricted workflows and 320 synthetic entries. Output is capped to five candidates/4,000 characters. These are deterministic tests, not measured agent selection accuracy.
- Both consumer worktrees have exercised skills-only startup and cross-group discovery with 28 and 22 native shared links respectively. The new development skill is discoverable without growing those native sets. Fresh-clone and publication evidence is added when verified.

## Live model testing

| Host | Career | App | Evidence |
| --- | --- | --- | --- |
| Codex nested CLI | Not run | Blocked before a model response | One capped probe failed to initialize the in-process app-server client: read-only filesystem |
| Actual Claude project thread | Unverified | Unverified | No Claude execution connector or CLI available in this session |

The attempted Codex probe asked whether a deliberately failing test-results fixture justified completion. It did not produce a response or skill-read trace. CLI login status alone is not runtime readiness. No broader model batch, baseline quality comparison or actual video production was run. No reliable weekly-plan usage meter was available; do not report a measured percentage or token saving.

Claude's separate review on PR #3 reports SessionStart execution, unset settings env, missing initialized submodule in a fresh thread and Unknown skill for repo skills. These observations justify the startup implementation but do not verify its new behavior.

## Remaining proof

Publish consumer integrations and test fresh clones at their exact recorded pins. Run the capped fresh-thread probes in actual Claude/Codex hosts, including direct source reads from unnamed requests and actual toolkit PR write access from Claude. Then measure cost before the remaining smoke matrix, add/edit propagation, task artifacts and baseline comparisons. Preserve explicit unsupported/unverified results where a runtime is unavailable.
