# Shared selection rollout evidence

Updated 2026-10-27. This is a partial implementation report, not full live-host verification.

## Implemented and checked

- Foundation PR #3 merged: 28 selection guides, source invocation restrictions and admission checks.
- Implementation PR #4 merged: bounded cross-group search, shared SELECTION.md, agent-assisted INTAKE.md and a deterministic pinned-source importer. The agent supplies evidence-backed metadata; no background AI service is implied.
- First real intake: MIT-licensed obra/superpowers verification-before-completion at 2ce8aa15d05bd57213e6f746f953aafb7ded7a8b, with source/license bytes preserved. This brought the catalogue to 29; Claude's subsequent systematic-debugging intake in PR #7 brought it to 30. Dry run, applied import and repeated unchanged intake were exercised.
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
| Codex GitHub runner, CLI 0.164.0 | Substantive activation PASS | Authentication blocked | Career run 40543821429 proves policy/search/source reads, fresh fixture checks and correct result; app seed path returned 401 |
| Codex nested CLI | Not run | Authentication blocked after filesystem fix | Scoped supported write access fixed local state initialization; provider then rejected authentication |
| Actual Claude project thread | Account adapter discovered; substantive use pending | Account adapter discovered; substantive use pending | Claude's recorded remote_projects probes, account shared-skills installed after initial hook assumption failed |

The original nested CLI failed to create local state; a scoped filesystem grant resolved that, then the provider rejected the configured login. The app's existing seed-only GitHub login also failed pre-inference with workspace routing discovery unauthorized (401), in run 40538443064. Career's existing maintained reader-auth cache was accepted. No credentials were transferred between repositories or routing/permission controls bypassed. CLI login status alone did not establish inference readiness.

### Substantive Codex proof

[Career run 40543821429](https://github.com/shigol/career/actions/runs/40543821429) used project bfe218551c624778b631e0435f32e05cbacdb6e9 and toolkit 92d28b7. The fictional task required independently verifying runnable code, not naming a skill. Observed successful commands read SELECTION.md, queried `skills.py search`, read the guide and vendored verification-before-completion SKILL.md, ran the fixture build (exit 0) and eight fixture checks (exit 1, two expected failures). The answer correctly identified the off-by-one retry limit and rejected completion. The chosen new development skill was absent from native links: this proves one actual use of the admitted skill through cross-group retrieval.

Result: policy read, source read, fresh checks and factual assessment all PASS. Elapsed model-task time 27.4 s; provider reported input_tokens 197,386, cached_input_tokens 157,440, output_tokens 766 and reasoning_output_tokens 10. Non-cached input is 39,946 by subtraction. These are aggregate task usage, not peak resident context, measured weekly-plan percentage, currency cost or a demonstrated saving. CLI 0.164.0 and high effort were recorded; the default model identifier was not captured. No native-only baseline or broad matrix was run.

The preceding [Career control run 40540625134](https://github.com/shigol/career/actions/runs/40540625134) correctly judged pasted evidence and read the policy without invoking a specialist. Its harness marked behavior_failed only because it incorrectly required source invocation on a trivial task. That result demonstrates why abstention must remain valid, not that all ordinary questions should invoke a skill. Reported usage: input 83,343 (46,976 cached), output 486, reasoning_output 71; 22.17 s.

### Claude coordination

Claude owns the account bootstrap and its real-work probes; Codex owns runner/auth diagnosis and library mechanics. Career SHARED.md records both agents' evidence. Claude corrected its original PR #3 claim after session-event inspection: only platform hooks ran in the tested remote_projects threads; repo SessionStart, UserPromptSubmit and PreToolUse hooks were skipped. Account skills were exposed, repo skills were not. The saved `shared-skills` account adapter was then discovered in both projects. Both agents agree that short pasted-output judgments may correctly abstain; next Claude probes use real repository work. These are Claude-reported host observations, not replayed here. Discovery is not yet proof of substantive invocation.

The original four-attempt schedule was adapted after startup/auth diagnostics, under Eugene's renewed request to make it work: targeted runner probes isolated maintained auth and tested one substantive task. No unrestricted retry loop or full evaluation campaign was launched. Keep future batches capped and report current usage first; no reliable weekly-plan meter is available here.

## Remaining proof

Career Codex substantive policy/retrieval/source use is proven for one task. Still obtain Claude's coordinated real-work results, its actual toolkit PR write evidence, supported app Codex authentication, live use after an existing-skill edit and task-family coverage/baselines. Preserve unsupported/unverified cells. EVG-124 remains open; a successful pilot is not full release verification. The optional native_limit guard bounds future native count while keeping all registered entries searchable; this caps count, not token usage.
