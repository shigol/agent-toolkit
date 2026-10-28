# Shared selection rollout evidence

Updated 28 October 2026. Installation, source reading, task correctness and added output value are separate results. This report does not claim universal selection accuracy or complete Claude-host acceptance.

## Current implementation

The library has 30 registered skills and 30 selection guides. Every guide requires Purpose, Invocation, Route, Synonyms, Use when, Do not use when, Overlaps and default, Requirements, Expected output, Positive example, Negative example and Source. All 1,096 vendor files match their recorded hashes; original source commits, licenses and portability patches remain recorded.

Merged toolkit PRs #9–12 and #14–15 provide generated routing, stronger fallback retrieval, new-project/global setup, unattended committed briefs, successful-output read audits and opt-in blind value sampling. At `80f512e`, 68 Python tests and five dispatcher tests pass. Four browser-discovery tests exercise explicit overrides and the managed-Claude Chromium fallback. These checks do not demonstrate that every skill improves every task.

Both connected consumers expose all 30 shared skills to both agents. Codex starts with native descriptions and a compact project rule; hosted Claude retains generated imperative routes and direct source reads. Project/account procedures remain outside generated markers. CI rejects stale or missing routing after setup, including a committed-header diff check so regeneration cannot hide drift.

Fallback search reaches the admitted catalogue while respecting exclusions and manual invocation rules. It requires a minimum score, uses guide synonyms and returns at most five candidates/4,000 characters. The authored regression set passes 42/42 top-three cases, including the three reported misses, and seven trivial abstentions. The 320-entry structural fixture tests bounded retrieval; neither result establishes live selection accuracy at hundreds of native skills.

## Observed Codex runs

| Surface and run | Observed result | Limit |
| --- | --- | --- |
| Career runner [40543821429](https://github.com/shigol/career/actions/runs/40543821429) | An unlinked, newly admitted verification skill was found through policy/index/search, read, and applied to fresh failing checks and a passing syntax build; completion correctly rejected | One substantive case, CLI 0.164.0; not native-only |
| App native-only [40558805552](https://github.com/shigol/eugene-s-job-hub/actions/runs/40558805552) | With 30 native links and no route/global pointer, the unnamed compound task fully read debugging, verification and Humanizer, ran actual checks and correctly rejected the release | One case, CLI 0.164.0; not broad accuracy or output-value evidence |
| Career integrated-native [40581479135](https://github.com/shigol/career/actions/runs/40581479135) | The same three sources were fully observed with fresh checks and a correct assessment | CLI 0.165.0; a global baseline was installed, so this is not a pure native-only control |
| App global fallback [40579914045](https://github.com/shigol/eugene-s-job-hub/actions/runs/40579914045) | A fixture with no project toolkit or native links found all three sources through the global profile and correctly checked the release | CLI 0.165.0; one dependency-light task |
| App unattended request [40579868768](https://github.com/shigol/eugene-s-job-hub/actions/runs/40579868768) | A writer comment dispatched the committed brief; actual Humanizer/verification reads matched its declarations, and fresh integration checks ran | Read-only request; no generated branch was needed |
| Career unattended request [40581679740](https://github.com/shigol/career/actions/runs/40581679740) | The same request-to-result path and two full source reads passed, using Career's maintained reader login | Read-only request; does not prove every development dependency |

Full-reading measurements compare unique nonblank source lines in successful command output: debugging 206/206, verification 80/80 and Humanizer 234/234 in the three-source probes. The initial native-only task loaded no unrelated skill bodies into its observed tool outputs. Hashing files locally during setup is not loading those bodies into model context. Claims, guides and attempted reads alone do not pass the grader.

The global proof used toolkit `9c96689`, project `e0111f7`, medium effort and 25.49 seconds. Aggregate input was 130,943, cached input 94,336 and output 860. The initial pure native run took 17.97 seconds: input 115,286, cached 79,744, output 512. These are aggregate task totals, not isolated catalogue overhead, peak context, currency cost or weekly-plan percentages. Exact provider model identity was unavailable.

## Blind value samples

The two-call pilot [40584537539](https://github.com/shigol/eugene-s-job-hub/actions/runs/40584537539) produced valid arm/read evidence and no detected condition labels. It used 55,157 aggregate input tokens (41,088 cached) and 288 output tokens. That pilot justified a fixed expansion, not a quality claim.

The full run [40587812315](https://github.com/shigol/eugene-s-job-hub/actions/runs/40587812315) recorded 18 independent samples: three tasks, two arms and three samples per arm. A/B positions were swapped. All calls completed, assigned-source evidence passed, no extra registered skill bodies appeared, and all 12 static-UI viewport renders were captured. The task/fixture code was unchanged from `5382be4`; the executing library was `80f512e`, CLI 0.165.0, medium effort. Both arms used the same CLI-default configuration and common global baseline; the provider's exact model identifier was not exposed.

Sample usage was 1,098,323 aggregate input tokens, 960,896 cached, 137,427 uncached by subtraction, and 23,320 output. This excludes the separate pilot and setup/authentication checks. No API-key billing or recurring value run was enabled.

The anonymous outputs, observations, hashes and renders were delivered to private Career PR #109. Condition mapping and raw evidence were excluded from that handoff. Claude committed its blind verdicts in730fb212 before the original map was published inb210b9be: seven with-skill preferences and two ties, with several explicitly marginal and a knowledgeable-judge bias. All outputs were correct, so this is modest, small-sample preference evidence rather than a correctness gain or general improvement rate. Codex independently reviewed Claude's18 outputs and12 renders and committed nine verdicts in054295dc before asking for Claude's map: six marginal preferences and three ties. Those preferences remain blinded until that separate map is provided. The experiment tests added source guidance under the existing baseline; it does not remove all prior model knowledge.

## Update and lifecycle controls

Source intake and setup tests cover additions, edits, unchanged retries, removals/exclusions, local skill preservation, conflicting names, failed writes and rollback. The actual Superpowers intakes introduced useful verification/debugging capabilities rather than marker-only test skills; later unnamed Codex runs used them. Fresh remote CI also initializes an empty Git repository with one `init-project` command and verifies the global profile without touching credentials.

Vendor/source changes remain held for independent review even when validation is green. Controlled, unmerged toolkit PR #13 added one harmless reference with a correct hash. Consumer app PR #247/run 40580443689 passed inventory/runtime/tests while its policy step explicitly refused source-update eligibility. The trusted controller independently compares commits; it does not trust candidate output. Its tests cover the Dependabot actor path. The live fixture was not authored by Dependabot and is not claimed as an end-to-end bot-actor test. Both fixture PRs were closed unmerged; production vendor bytes remain unchanged. Category scans support review and are not safety verdicts.

Terminal GitHub API authentication later returned 401 while the connected service and normal Git remained usable. The trusted comment route now accepts whitelisted acceptance modes and successfully dispatched the full value run without a permission change or credential substitution. This is a supported alternative connection, not a proxy/authentication bypass.

## Claude and host boundaries

Recorded hosted-Claude probes showed account skills, no repository skill discovery, and skipped repository hooks. Compatible Claude Code hosts are a different surface. The account bootstrap and direct source reads remain necessary for the hosted threads tested. Earlier one-line policy pointers did not reliably fire; the current generated imperative routes require fresh hosted verification.

Claude's reported debugging/outreach source reads passed in some prior probes. Claude subsequently acknowledged pickup and reported a five-thread hosted smoke: all five tasks correct,11 of14 required reads passed, with no unrelated skill bodies. The three missed reads were Humanizer patterns in replies reporting code work. That report was graded from session events by Claude's worker, not independently replayed by Codex. The proposed route change explicitly names work-reporting replies, retains whole-source reads for documents/outreach and preserves setup/declaration instructions. Its behavioural effect still needs affected fresh-host reruns.

The 38 author-written replay briefs and blind protocol for Claude are delivered in Career #106. They are realistic project requests, not claimed historical transcripts or measured accuracy. A small smoke precedes any larger batch. Claude owns the independently authored Codex set, its hosted execution and judging Codex's blind outputs. Codex has now committed its blind judgements of Claude's supplied pairs. Claude's independently authored42-case Codex replay set is published (private blob209e72bb); its recommended five-case execution and the affected hosted reruns remain open; the handoff is acknowledged, not inferred from a post.

## Remaining acceptance

- App run40592700554 saved only its requested temporary report on a review branch. Its audit observed full Impeccable65/65, Humanizer234/234 and verification80/80 unique lines. Render attempts timed out; visual/keyboard verification was correctly left unproven. This establishes selection and transport, not successful rendered task execution.
- App run40677743925 restored the previous run's finished encrypted cache, logged successful login from that cache and saved its own prepared/finished cache. Real forced rotation was not tested; dummy-client tests cover rotation/rekey/persistence. A valid seed remains necessary after cache expiry or account revocation.
- Complete affected hosted-Claude read-depth reruns, the independent Codex replay smoke, unblinding of Claude's samples and remaining rendered execution checks. Both judges' blind verdicts are now committed.
- Record any retained limitations rather than reporting all task families, native metadata overhead or hundreds-skill usability as proven.
- Keep startup instructions within the actual project budgets; the new route wording must be measured in each consumer before merging. Career's generated integration fit its existing 5.5 KiB limits, with only 13 bytes spare in CLAUDE.md; adding skills requires a bounded, tested adjustment rather than silently increasing that budget.
- Provision the global profile when the separately owned server environment is ready; the GitHub runner/global fixture evidence is not a server deployment claim.

One unchanged Git self-mirror setup test intermittently failed with exit 128 in app run 40590884016, then the failed job passed on a single retry. Its underlying cause was not established from the retained stderr. This is recorded as an intermittent test limitation, not presented as a repaired code defect.

## Cloud execution continuity

Submitted GitHub Actions jobs run independently of a workstation. A completed chat response does not create a persistent project coordinator or a thirty-minute scheduler. No continuing job was left assigned to the remaining project work overnight on27–28October; do not describe that interval as active implementation. The next bounded cloud check was actually dispatched and observed as40677743925. This proves that job execution, not automatic continuation through the entire backlog.

The held-out smoke harness is isolated from expected labels: fixed recommended cases, committed source snapshots, successful-output source grading, explicit label-leak/invalid states, bounded calls/artifacts and separate correctness/render review. Deterministic tests do not constitute a live replay pass. The source set was published before Codex executed it; live results must record the actual consumer/library revisions and usage.
