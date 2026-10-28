# Shared skills: working plan

## Mission and decision authority

Eugene adds a useful skill once. The agent supplies its description, route, examples and overlap rules from the actual source, completes review and connected-project delivery, and Claude/Codex use it when appropriate without Eugene naming it in each task. The library lives in GitHub, outside individual projects and Macs. Installed files, discovered descriptions, actual source reading and better output are separate outcomes.

Keep this goal fixed; change the implementation when evidence supports a simpler or better path. Claude owns its actual hosted adapter and tests. Codex owns its native-host choices and shared mechanics. Coordinate through Career SHARED.md and inbox PR #1; do not make Eugene the routine relay. Preserve existing project ownership, authorization, source licenses and factual/template constraints. This plan is not startup context.

## Implemented architecture

- One pinned source copy per consuming checkout; relative `.agents/skills` and `.claude/skills` links point into it. No duplicate global source installation.
- Every registered skill has a checked catalogue guide with 12 required fields, including Route, Synonyms, invocation restrictions, examples, requirements and overlap/default choices.
- Codex starts with native descriptions. A short project block and global profile handle missing or incomplete coverage; routes, catalogue index and search are the fallback. The measured native-only case makes a second compulsory selector unnecessary.
- Hosted Claude uses generated imperative routes and direct SKILL.md reads. Actual tests did not expose repo skills or execute repo hooks there. Compatible Claude Code hosts may use native discovery/hooks; do not generalize between surfaces.
- Selected sources are read in full, with needed references. Humanizer's 26 numbered headings are permitted only for short replies/PR prose, not documents or outreach. Use one primary UI workflow; Impeccable is the default, Taste needs an explicit alternative direction, and upstream manual-only flags stay enforced.
- Project/account procedures remain outside generated markers. Source fields come from reviewed metadata; setup regenerates existing blocks and CI checks the committed result for drift, missing markers and unresolved names.
- Search is last, with a minimum score, guide synonyms, explicit exclusions and bounded output. Forty-two authored retrieval cases pass top-three recall; seven trivial cases abstain. These are not held-out agent accuracy measurements.
- `init-project` initializes a fresh Git consumer; `bootstrap-global` writes only its own Codex instruction block, preserving credentials and other rules. Existing project pins take priority.
- Writer-only committed-brief comments start Codex unattended. The default branch and regular Markdown path are checked; arbitrary refs/prompts/modes are rejected. The worker has no repository write token. A separate trusted job validates and transports regular source changes to a review branch without executing them or merging/deploying.

## Intake, updates and removal

1. Inspect the proposed pinned source, license, tools/platform requirements and overlaps. Explain when it should and should not be used. Do not invent capabilities or weaken manual invocation flags.
2. Use the deterministic importer for path/hash/registration changes; author the checked guide and index entry. Run source, admission, retrieval, lifecycle and relevant runtime checks.
3. Obtain the other agent's actual source diff review. Changed-source category scans support this review; they do not certify safety. Do not execute supplied installation commands merely because an unreviewed skill recommends them.
4. Publish the reviewed toolkit change, then advance each relevant connected project through its checked update process. Regenerate routes, preserve local skills/settings, run setup and report which project/host states were actually verified. The agent should complete this under the original add request; Eugene should not author metadata or choose skills per task.
5. Daily Dependabot follows the reviewed shared repository. Only small compatible nonvendor Markdown changes may merge unattended. Vendor, manifest, executable/setup, removal, divergence, incomplete comparison or failed checks stay held. A shared commit alone does not instantly update every project or running chat.
6. For removal/exclusion, update the catalogue/project selection and owned links deliberately; rerun lifecycle checks and affected task probes. Revert to a prior reviewed pin for rollback. Never delete local procedures or unrelated settings.

## Context and scale contract

Load only native metadata or the compact hosted routes at startup. Read relevant guides and sources on demand. Do not preload all skill bodies, this plan or an entire growing catalogue in every task. Reconsider coverage when the task phase changes, not on every message.

`native_limit` can bound linked/native count while leaving the admitted catalogue available to fallback, respecting explicit exclusions. It is not a token budget. Current consumers expose all 30 skills with no cap. The generated hosted block is about 2.2 KiB; Career CLAUDE.md has only 13 bytes spare under its current 5.5 KiB budget. Keep project instructions as concise indices to canonical rules and test any bounded hosted/domain adapter on fresh threads before adopting it. Raising a cap or truncating source restrictions is not a scale solution.

The 320-entry retrieval fixture is structural evidence only. Before claiming hundreds-skill usability, measure metadata/context and relevant selection in the actual hosts with a bounded profile. Keep all admitted skills discoverable for missing task coverage; do not confuse unlinked, excluded and incompatible skills. Unsupported tools/dependencies are readiness limits, not reasons to claim success.

## Acceptance status

| Area | Evidence/status | Remaining owner/action |
| --- | --- | --- |
| Descriptions and routing | 30 checked guides; generator, drift checks and source flags merged | Maintain on every intake |
| Fallback retrieval | 42/42 authored top-three cases and seven abstentions; three reported misses fixed | Cross-authored live replay remains separate |
| Codex selection | App pure native case; Career integrated-native case; three full sources and real checks | Broader held-out task coverage, not a duplicate router |
| Unconnected project | Real global-only fixture passed without project toolkit/native links | Server provisioning stays with its environment owner |
| New-project setup | Fresh remote CI plus repeat/rollback/conflict tests pass | Re-run when setup changes |
| Review controls | Green-validation vendor fixture remained held; trusted-controller actor tests pass | No source auto-merge; retain review evidence |
| Unattended handoff | Real comment-to-result requests passed in both repos; actual claims matched full reads | Full selected reads and review-branch transport proved; app cache reused in40677743925; UI render timeout remains |
| Source-read audit | Successful command output, whole-source coverage, partial/unknown states and false-claim tests | Other host formats need real output evidence; declarations alone never pass |
| Claude host | Account bootstrap exists; prior source successes and a latest app read failure are recorded | Five fresh tasks correct;11/14 required reads; fix reporting-prose trigger and rerun affected cases: Codex + Claude |
| Replay | Codex delivered 38 labelled requests for Claude, including four trivial cases | Claude delivers Codex's set; smoke first, then decide expansion from usage/failures |
| Output value | Codex recorded 18 valid samples/nine blind pairs and all 12 UI renders | Both blind judgements committed; Codex map revealed (7 preferences/2ties); await Claude map; small-sample limits retained |
| Final status | Shared source bytes and scripts verified; exact runs in EVIDENCE.md and private SHARED.md | Keep EVG-124 open until peer/host gaps are actually closed |

## Evaluation protocol

Separate retrieval, selection, execution and value. A correct answer without a source read is not activation proof; a source read is not proof of better output. Source grading needs observed successful output, not command inputs, catalogue-guide reads, installed links or claimed skill names. Unknown account invocations need their own evidence. Name only sources actually read in commits/PRs; transport bots can state their limited role.

The independent replay author labels realistic requests but the executor sees only the brief and repository. Grade full reads, hard restrictions, task correctness, unrelated context and useful abstention. Start with a small smoke and record actual usage before expanding; do not launch a large repeated matrix by default.

Value uses identical factual fixtures/configuration in both arms, three independent samples per arm for prose, verification and static UI, with swapped A/B positions. Preserve all outputs, actual observations, versions and usage. Failed calls, missing source evidence or blinding leaks are invalid measurements; correctness failures remain candidate failures. UI needs actual viewport renders. Claude judges Codex outputs; Codex judges Claude outputs. Commit judgements before revealing maps, and report ties/invalids and each task's three-pair result. No outcome is predetermined.

The current Codex value batch used about 1.10M aggregate input tokens, including 0.96M cached, and 23,320 output. These sample totals are not isolated discovery overhead, prices or weekly-plan percentages. Exact provider model identity was not exposed. No API-key billing or recurring evaluation schedule was added.

## Next concrete work

1. Record the proved app cache reuse and selected-source/review-branch transport. Close the isolated transport PR unmerged. Complete rendered execution separately; a saved report and source read do not prove visual QA.
2. Deliver the explicit work-reporting prose trigger to both consumers, within their existing context budgets. Claude reruns the three affected hosted cases; Codex runs the independently authored replay smoke when supplied, grading actual reads.
3. Both agents have committed blind judgements. The Codex map is revealed; obtain Claude's precommitted-hash map and record both outcomes, including ties and marginal preferences. Do not extrapolate a large benefit from these three task families.
4. Reconcile the remaining host/scale/server limits and current evidence. Mark only achieved criteria complete; keep an unavailable peer/host result open rather than simulating it.

For ongoing work, send Eugene an update every 30 minutes while actively executing: done, remaining and estimate. Do not imply an idle-chat scheduler exists. If external peer results are unavailable, complete independent work, record the exact gap and keep the issue open.

A workstation may be closed while a submitted Actions job runs. It does not make this chat a persistent worker. Before claiming unattended continuation, retain an actual run ID and the committed brief/checkpoint; distinguish a bounded job from a coordinator that starts subsequent tasks. No automatic idle-chat updates or end-to-end overnight continuation are currently configured.
