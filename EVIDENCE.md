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
| Codex GitHub runner, CLI 0.164.0 | Substantive activation PASS | Native-only activation PASS | Career40543821429; app40558805552 after the credential update |
| Codex nested CLI | Not run | Authentication blocked after filesystem fix | Scoped supported write access fixed local state initialization; provider then rejected authentication |
| Actual Claude project thread | Full source reads reported for debugging and outreach | Latest probe found an unread skill claim | Claude's recorded probes5–7; v6 tightens declarations and the nightly audit checks them |

The original nested CLI failed to create local state; a scoped filesystem grant resolved that, then the provider rejected the configured login. The app's original seed-only login failed pre-inference with401 in run40538443064. After the user renewed that app credential, its rerun produced a real response. The old pasted-log fixture still failed its source-read requirement, so it was not treated as activation proof. The substantive native experiment below passed. Career's maintained reader-auth cache was accepted separately. No credentials were transferred between repositories or routing/permission controls bypassed. CLI login status alone did not establish inference readiness.

### Substantive Codex proof

[Career run 40543821429](https://github.com/shigol/career/actions/runs/40543821429) used project bfe218551c624778b631e0435f32e05cbacdb6e9 and toolkit 92d28b7. The fictional task required independently verifying runnable code, not naming a skill. Observed successful commands read SELECTION.md, queried `skills.py search`, read the guide and vendored verification-before-completion SKILL.md, ran the fixture build (exit 0) and eight fixture checks (exit 1, two expected failures). The answer correctly identified the off-by-one retry limit and rejected completion. The chosen new development skill was absent from native links: this proves one actual use of the admitted skill through cross-group retrieval.

Result: policy read, source read, fresh checks and factual assessment all PASS. Elapsed model-task time 27.4 s; provider reported input_tokens 197,386, cached_input_tokens 157,440, output_tokens 766 and reasoning_output_tokens 10. Non-cached input is 39,946 by subtraction. These are aggregate task usage, not peak resident context, measured weekly-plan percentage, currency cost or a demonstrated saving. CLI 0.164.0 and high effort were recorded; the default model identifier was not captured. No native-only baseline or broad matrix was run.

The preceding [Career control run 40540625134](https://github.com/shigol/career/actions/runs/40540625134) correctly judged pasted evidence and read the policy without invoking a specialist. Its harness marked behavior_failed only because it incorrectly required source invocation on a trivial task. That result demonstrates why abstention must remain valid, not that all ordinary questions should invoke a skill. Reported usage: input 83,343 (46,976 cached), output 486, reasoning_output 71; 22.17 s.

### Native-first Codex proof

[App run40558805552](https://github.com/shigol/eugene-s-job-hub/actions/runs/40558805552), project b2b53fe5d7b82fd81a81de937c8c10aa997fb8ba and toolkit f33795f58864925d8f560d383c4fedd1d2239181, used CLI0.164.0 at medium effort. The isolated fixture exposed the same30 native skills as the app, with no route table or policy pointer. The prompt named no skill. It required diagnosis, fresh checks, a completion assessment and a factual stakeholder release-note rewrite.

Successful command output covered the full sources: systematic-debugging206/206 unique nonblank lines, verification-before-completion80/80 and humanizer234/234. The model ran the actual fixture checks (two tests, one intentional failure: four attempts versus three), passed the syntax-only build and correctly rejected completion. Its three declared skills matched the observed reads;27 unrelated source bodies stayed unopened. Native selection passed, so the paid routed comparison was skipped. The source-output grader and red-to-green fixture tests are in app draftPR244; its19 Python checks and PR checks passed.

Elapsed model-task time17.97s. Provider usage: input115,286; cached79,744; output512; reasoning_output0. Uncached input is35,542 by subtraction. These are aggregate task totals, not isolated discovery overhead, peak context, monetary cost or a measured percentage of the weekly plan. The exact provider model identifier was not reported. Private artifact12758152679 retains the report, answer and trace. The release note was also reviewed against the fixture failure; it accurately says the release is blocked.

Decision: Codex starts with native discovery and uses the shared routes/index/search when native coverage is absent or incomplete. Hosted Claude retains its bridge. This one compound task establishes feasibility for the tested runner; it does not prove selection across every task family, output-value improvement, global bootstrap or existing-skill edit propagation. Consumer header integration remains separate.

### Claude coordination

Claude owns the account bootstrap and its real-work probes; Codex owns runner/auth diagnosis and library mechanics. Career SHARED.md records both agents' evidence. Claude corrected its original PR #3 claim after session-event inspection: only platform hooks ran in the tested remote_projects threads; repo SessionStart, UserPromptSubmit and PreToolUse hooks were skipped. Account skills were exposed, repo skills were not. The saved `shared-skills` account adapter was then discovered in both projects. Both agents agree that short pasted-output judgments may correctly abstain; next Claude probes use real repository work. These are Claude-reported host observations, not replayed here. Discovery is not yet proof of substantive invocation.

The original four-attempt schedule was adapted after startup/auth diagnostics, under Eugene's renewed request to make it work: targeted runner probes isolated maintained auth and tested one substantive task. No unrestricted retry loop or full evaluation campaign was launched. Keep future batches capped and report current usage first; no reliable weekly-plan meter is available here.

## Remaining proof

Career policy/retrieval/source use and app native-only source use are proven for one substantive task each. Claude's real intake PR is merged and its later probes report Career source use; its app probe caught a false declaration. Remaining work includes consumer native-first integration, unattended brief submission, route adoption, fallback search, source-review controls, new-project bootstrap, live existing-skill edit propagation, and cross-agent coverage/value checks. Preserve unsupported/unverified cells. EVG-124 remains open; a successful pilot is not full release verification. Optional native_limit caps future native count while retaining index/search access; choose it from measured context needs and actual project selections.
