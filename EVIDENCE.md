# Shared selection rollout evidence

Updated 2026-10-27. This is a partial implementation report, not full live-host verification.

## Implemented and checked

- Foundation PR #3 merged: 28 selection guides, source invocation restrictions and admission checks.
- Implementation PR #4 merged: bounded cross-group search, shared SELECTION.md, agent-assisted INTAKE.md and a deterministic pinned-source importer. The agent supplies evidence-backed metadata; no background AI service is implied.
- First real intake: MIT-licensed obra/superpowers verification-before-completion at 2ce8aa15d05bd57213e6f746f953aafb7ded7a8b, with source/license bytes preserved. Catalogue now has 29 skills. Dry run, applied import and repeated unchanged intake were exercised.
- Local tests: 30 Python tests, including admitted-skill edits/reversion, rejection of weakened manual-only restrictions, source symlinks/path escapes, idempotency and write-failure restoration. Four Node browser-discovery tests pass. All 1,084 vendored hashes verify.
- Retrieval fixtures cover UI, web motion, writing, market sizing, an unsupported database query, explicit exclusions, restricted workflows and 320 synthetic entries. Output is capped to five candidates/4,000 characters. These are deterministic tests, not measured agent selection accuracy.
- Consumer integrations merged: [Career #100](https://github.com/shigol/career/pull/100) and [app #235](https://github.com/shigol/eugene-s-job-hub/pull/235). Both pin toolkit 92d28b7929ff68570be06d4de4afa97138d32d41. Career keeps 28 native shared links plus its local procedures; the app keeps 22. Cross-group discovery finds the new development skill without adding native links.
- Both consumers pass 30 shared Python tests, 13 consumer Python tests (including three startup cases), four browser-discovery tests and four merge-guard tests. Their GitHub Shared toolkit checks pass; app PR evidence also passes. Career's required prepush gate ran 43 checks in 189 seconds and exited successfully after reproducing two existing main failures. No new failure was reported. The local Python 3.11 executable is absent; the other baseline failure is the CV truth check. These are not presented as 43 passing checks.
- Career CLAUDE.md is 3,576 bytes and AGENTS.md is 3,106 bytes, both within the existing 3.5 KB limits. Two unrelated pre-existing context overruns remain in decisions.md and the whole RUNBOOK. Permission/env values and existing hooks were compared against the prior settings and preserved.

## Fresh checkout startup

Each test began without an initialized submodule, invoked the exact new SessionStart command from settings with CLAUDE_PROJECT_DIR set, checked the exact committed toolkit revision, repeated startup, verified both agents' links, and retrieved the new skill through an unnamed task query. This tests the configured command, not invocation by a live Claude session.

| Consumer | Cold startup | Warm startup | Pin/files/retrieval |
| --- | ---: | ---: | --- |
| App | 2.82 s | 0.67 s | PASS |
| Career | 3.06 s | 0.70 s | PASS |

The app used a fresh local consumer clone with normal remote toolkit initialization; Career used a fresh GitHub branch clone. Earlier attempts to clone Career's local partial repository failed because its promisor objects were unavailable to Git packing; the successful remote clone replaced that invalid test route. No mutable latest fetch was used. Times describe these runs, not a network latency guarantee.

## Live model testing

| Host | Career | App | Evidence |
| --- | --- | --- | --- |
| Codex nested CLI | Not run | Blocked before a model response | One capped probe failed to initialize the in-process app-server client: read-only filesystem |
| Actual Claude project thread | Unverified | Unverified | No Claude execution connector or CLI available in this session |

The attempted Codex probe asked whether a deliberately failing test-results fixture justified completion. It did not produce a response or skill-read trace. CLI login status alone is not runtime readiness. No broader model batch, baseline quality comparison or actual video production was run. No reliable weekly-plan usage meter was available; do not report a measured percentage or token saving.

Claude's separate review on PR #3 reports SessionStart execution, unset settings env, missing initialized submodule in a fresh thread and Unknown skill for repo skills. These observations justify the startup implementation but do not verify its new behavior.

## Remaining proof

Consumer integrations and fresh-checkout startup are complete. Still run the capped fresh-thread probes inside actual Claude/Codex hosts, including policy/source reads from unnamed requests and actual toolkit PR write access from Claude. Then measure cost before the remaining smoke matrix, actual model use after add/edit propagation, task artifacts and baseline comparisons. Preserve explicit unsupported/unverified results where a runtime is unavailable. EVG-124 remains open for this proof; installation readiness is not full release verification.
