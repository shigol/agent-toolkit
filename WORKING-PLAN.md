# Shared skills: mission, architecture and delivery plan

Updated: 2026-10-27. Status: core implementation and initial consumer rollout merged; one substantive Career Codex source-use probe PASS. Claude owns hosted bootstrap and real-work/intake proofs; Codex owns toolkit scripts/policy and runner proofs. See [EVIDENCE.md](EVIDENCE.md) and the live coordination in Career SHARED.md; a passing pilot is not the full matrix.

## 1. Mission and freedom to adapt

Eugene discovers skills in posts and repositories and wants to say “add this” once. The system should understand the skill, describe its purpose and boundaries, resolve overlaps, publish an approved addition, and make it available in relevant connected projects. Claude and Codex should then select and use it for suitable tasks without Eugene remembering skill names, managing separate copies or repeatedly configuring machines.

The experience must keep working with hundreds of skills and conversations that move between research, development, design, writing and video. Success means better work with low maintenance and bounded context, not maximum skill invocation.

The implementing agent owns the technical approach. Change phase order, metadata, retrieval, intake mechanics and default selections when evidence supports a simpler or better solution. Record material changes here with their reason and test implications, then proceed without asking Eugene to make routine technical decisions. Proposed CLI shapes, budgets and evaluation targets below are starting points, not a fixed architecture. Preserve the mission, project requirements, source invocation restrictions, existing authorization and publication controls. Surface only decisions that genuinely change those requirements or require new authorization.

## 2. Architectural assessment

The initial plan correctly chose one durable source, progressive disclosure and real-host testing. It needed four corrections:

1. A catalogue is not an integration. An agent must demonstrably load a small bootstrap policy before retrieval can help.
2. Finding the expected skill is not proof of useful execution. Evaluate retrieval, selection and final task quality separately against a baseline.
3. “Automatic” needs an execution trigger, an owner and observable delivery states. A GitHub file or social-media link does not process itself.
4. Distribution, runtime compatibility and permissions are separate concerns. An installed instruction cannot provision unavailable capabilities or authorize an external action.

Prove one complete path early. Do not build a large routing platform before showing that a new skill improves a real task in the actual hosts.

## 3. User journey and boundaries

The normal intake is an authorized request to either connected agent: “Add this skill: URL.” That agent runs the shared intake workflow and uses its existing model to analyze the source; no separate background AI service or API key is required for the first release. A manually added folder is a draft until it passes admission. If folder-drop or GitHub-event intake is later required, implement and document its actual worker, model credentials and trigger rather than implying they already exist.

Routine complete additions should proceed through the existing checked publication process. The user should not hand-write metadata or choose skills for ordinary work. If a submission cannot be admitted, return a specific reason and keep the current library usable.

| Event | Expected result |
| --- | --- |
| Submit a source link | Inspect source and license; draft metadata; assess overlaps and compatibility |
| Admit a routine addition | Publish a checked revision and initiate or await the configured consumer-update mechanism |
| Start a project task | Load the bootstrap policy; select relevant instructions with native discovery or bounded retrieval |
| Move from audit to implementation | Reassess the action and replace incompatible workflow instructions |
| Update an existing skill | Revalidate metadata and dependencies; deliver through the same checked process |
| No suitable skill | Continue normal work; do not force a loosely related skill |

New projects opt in once. Existing projects and new machines use their documented setup. An already-running chat does not silently receive new context. Ordinary Claude web chat without repository/tool access is outside the initial supported surface; do not claim account-wide availability.

## 4. Proposed minimal architecture

Use one Git repository as the durable source. Retain vendored source bytes, licenses, pinned upstream revisions and hashes. Build on the existing Python standard-library installer and consumer workflows. Add a service, embedding database, hook framework or second agent only when measured evidence justifies it.

| Component | Responsibility | Does not establish |
| --- | --- | --- |
| Source manifest | Stable skill identity, source revision, files and integrity | Usefulness or trustworthy instructions |
| Selection catalogue | Task fit, exclusions, overlaps, restrictions and prerequisites | Runtime availability |
| Intake workflow | Agent-assisted analysis plus deterministic validation and inspectable diff | Automatic approval of unknown requirements |
| Bounded retrieval | Return a few relevant eligible candidates from the whole registered library | Final skill choice |
| Shared selection policy | Guide the agent's choice, source reading and task-phase changes | Guaranteed compliance in every host |
| Host integration | Get policy and tools into the actual session | Support in another host with a similar name |
| Consumer delivery | Advance a checked toolkit revision and run setup | Refresh of every active chat |
| Evaluation evidence | Record selection, source reads, task result and failures | Universal accuracy from a small sample |

### Source of truth and metadata

Keep the current human-readable guides. Define a machine-readable contract or parse a tightly validated guide format; avoid two independently maintained descriptions. Any generated index must be reproducible from the source and checked for drift.

Every admitted skill needs stable identity, source/revision/license, purpose, task actions, positive and negative scope/examples, expected output, invocation mode, platform/runtime requirements and overlap guidance. Host compatibility has evidence and a status: unknown, supported with evidence, or unsupported with reason. “Text is readable in both agents” does not prove the workflow can run in both.

Separate identity, upstream revision, toolkit revision and consumer revision. Record what was actually tested. Recheck the guide when its source changes. Never silently remove an upstream manual-only restriction. New metadata fields should migrate existing entries consistently rather than be silently guessed.

### Lifecycle and delivery

Track intake as submitted → analyzed → validated → published, or blocked with a reason. Track each consumer separately as update pending → checked revision merged → checkout/setup ready. Track host verification separately; a skill can be published without its runtime having passed in every environment.

Use existing PRs, commits and status output for these states before adding a database. Status must explain where an addition stopped and the next action. Repeated intake of the same source/revision is idempotent; a changed revision is an update, not a duplicate skill. An incomplete intake must not partially change installed skills.

Existing consumer Dependabot updates are daily, not immediate. The first implementation must choose and document the delivery mechanism: retain that cadence, or add a narrow event-triggered update request for registered consumers using existing authorized automation. Measure the chosen path end to end; do not promise instant propagation. Preserve checked merge policy and retry safely after a failed update.

Keep a simple list of connected consumers and setup instructions. Never publish private project contents, credentials or task transcripts in the public toolkit. Roll back through a previous reviewed toolkit revision and rerun setup, preserving local skills and settings.

### Bootstrap and host boundary

Treat “Codex” and “Claude” as product families, not single runtimes. Identify the actual Codex host/model and actual Claude host/model Eugene uses. Record repository access, instruction loading, native skill discovery, shell/tool access and runtime support. Claude Code and hosted Claude project threads require separate evidence if both are claimed.

Use genuinely new host sessions to test installation and policy loading. Do not reuse a thread initialized manually. The first PR #3 review incorrectly inferred that repo SessionStart hooks executed in hosted Claude. Claude's later event-traced remote_projects probes corrected this: only platform hooks ran; repo hooks and settings env were not applied in those tests. Keep this dated correction explicit rather than relying on the original hypothesis.

Consumer hooks and skills-only scripts are implemented for compatible Claude Code hosts and manual/environment setup. They initialize only the pinned submodule and install/verify instruction links, preserving existing hooks/settings. They do not provision engines or browsers. In hosted Claude, use the native account-level shared-skills adapter owned by Claude; it points into the same shared policy/library. Its discovery was observed in both projects after installation. Do not claim that discovery, a configured repo hook or a correct plain-text answer proves substantive policy/source use.

Existing Career SessionStart hooks have a 10-second timeout. Measure cold and warm skills-only setup; a cold network fetch is not guaranteed to fit. Set a bounded timeout supported by the actual host based on measurements, and provide a visible readiness failure plus one bounded task-time retry if installation times out or the network is unavailable. Do not silently report success, spawn an untracked background install, fetch latest, or block unrelated work indefinitely. Test an empty submodule, repeated startup, fetch failure and preservation of local skills. Reconcile any outdated consumer documentation claiming these hooks never run with the new host evidence when implementing the change.

In this Claude project host the Skill tool reports Unknown skill for repo skills. Read the selected SKILL.md directly; native skill invocation is not the fallback being tested. If the host cannot load the policy or access files, fix the connection first or label it unsupported. Do not ask Eugene to paste a router instruction into every new conversation as the completed solution.

The always-loaded consumer instruction is one short actionable pointer, for example: “Before substantial work, read .agent-toolkit/SELECTION.md; if missing, run the repo's skills-only setup.” The target shared file must exist before rollout. Career's CLAUDE.md has a 3.5 KB cap and is already near it; replace or compress an existing toolkit pointer rather than appending a policy. Run `python3 tools/context_budget.py` and keep the file within its existing cap. Put detailed policy on demand in the toolkit. Test that a fresh Claude thread actually follows the pointer for an unnamed task, instead of only checking its text or byte count.

Never load this working plan or the full catalogue in ordinary startup. Preserve current native selections during the pilot and use an optional native_limit to stop future catalogue growth; the entire admitted library remains searchable. This bounds count, not tokens. Claude's account adapter is now installed and discovered, rather than deferred; substantive activation remains a separate proof. Do not duplicate the shared policy into it or assume account storage grants access to every repository.

Host feasibility also requires evidence that a Claude project thread can create the toolkit intake branch/PR using its authorized connection. A repository attachment or permission list is not a successful write. Use the first useful intake PR as the test, avoid throwaway writes, and do not silently assume another host will publish it. If writing is unavailable, report that intake can draft but cannot complete publication until the host integration is fixed.

### Retrieval and selection

Search all admitted registered guides, regardless of native-link groups. Distinguish an unlinked skill from a project-forbidden or host-incompatible skill. Discovery must not bypass explicit exclusions or project policy. If current configuration mixes native exposure and execution eligibility, clarify those semantics before changing behavior.

Start with lexical retrieval over purpose, supported actions and positive scope. Exclusions and negative examples are eligibility evidence, not positive keyword bait. Use stable ranking, bounded results and transparent reasons; do not interpret a lexical score as confidence or always return a best match.

The agent decides using the requested action, output, platform and task phase. Apply hard restrictions first. Prefer a specific applicable workflow, use one primary design workflow, and add supporting skills only for distinct work. Use no skill for trivial or unmatched work. Search again when the task changes materially; do not repeat searches on every message.

Initial budgets: at most five candidate summaries totaling 4,000 characters; read at most two candidate guides before choosing; one additional search when ambiguous. Always-loaded bootstrap remains one pointer line within each consumer's existing byte budget; the on-demand policy may be about 600 words. Measure actual tokens where the host exposes them; character caps are not token guarantees. Bound retrieval output and reference expansion, and record exceptions when a real task requires more context. Do not truncate source instructions in a way that removes restrictions.

Only read the selected SKILL.md and needed references. Candidate results include identity, concise purpose, invocation/compatibility flags and exact guide/source paths. Missing dependencies are a readiness issue: explain them and use a compatible fallback where appropriate. Never bypass manual-only flags via direct-file reading. Update through toolkit maintenance rather than upstream self-refresh commands.

## 5. Delivery sequence and checkpoints

Milestones may be reordered when evidence supports it. Each checkpoint ends with a demonstrable artifact or test.

| Milestone | Deliverable and acceptance | Current status |
| --- | --- | --- |
| A. Foundation | All current guides, admission validation and documented restrictions | 30 guides after Claude's systematic-debugging intake in #7 |
| B. Host feasibility and evaluation fixtures | Skills-only startup, within-budget pointer and direct source reads in new threads; prove Claude publication access; estimate/cap evaluation cost | Career maintained-auth Codex runner works; app seed auth rejected; hosted Claude account adapter discovered; Claude published #7 |
| C. First vertical slice | One new capability goes through intake, selection and useful execution in a disposable consumer; then both real consumers | verification-before-completion intake → consumer delivery → unnamed search/source use → fresh checks PASS in Career run40543821429; other cells pending |
| D. Reusable workflow | Shared intake, bounded retrieval, idempotent lifecycle and concise host adapters | Merged intake/search #4, recovery #5, adapters Career #100/app #235 |
| E. Delivery integration | Tested add/edit propagation, fresh/existing setup, compatible automatic path and rollback | Both consumer pins merged; fresh/repeated setup and local edit/reversion/failure fixtures pass; live agent use after changes pending |
| F. Release verification | Host/project matrix, quality comparison, failure cases and scale evidence | 320-entry test passes; one substantive Codex case passes; no full matrix or quality baseline claimed |

Start the vertical slice with a dependency-light, useful skill that adds a distinct capability. Do not choose a fake skill designed merely to echo a marker. Use disposable branches/checkouts to avoid test artifacts entering production. Review the actual source and license before admission.

For intake, the agent produces an evidence-backed guide and proposed source/manifest changes; deterministic tools validate structure, paths, hashes, restrictions and consistency. Check duplicate identity and overlapping purpose. Require no invented capabilities. Flag unresolved licensing, dependencies or dangerous instructions rather than automatically executing supplied install commands. Preserve existing authorization: routine complete work proceeds; genuinely new external actions follow the applicable user authorization.

Publish in reviewable PRs. Update both consumer gitlinks, setup and small instruction pointers, preserving local skills and settings. Run existing checks and idempotent setup. Executable/setup changes remain under current review controls; adding a skill does not grant it credentials or broader permissions.

## 6. Evaluation that proves the mission

### Separate the questions

1. Retrieval: Was an acceptable candidate present in the bounded results? Track recall at the chosen limit and no-match behavior.
2. Selection: Did the agent choose an eligible useful workflow, abstain when appropriate and switch at task-phase changes?
3. Execution: Did it read the source and follow relevant restrictions, producing the requested artifact?
4. Value: Was the artifact correct and useful compared with the current native-only setup, without unacceptable context or latency overhead?
5. Delivery: Did an addition and an edit reach the right consumers and become usable after their supported update/setup path?

A source-read trace proves access, not full compliance. An agent's statement that it used a skill proves neither. Validate final artifacts with task-appropriate checks: code behavior, rendered interaction, factual preservation, or an actual video output when its runtime is supported.

Define acceptable workflows rather than insisting on one skill name where alternatives are valid. Evaluate artifact quality against a rubric created before running the task. Use objective checks where possible; record who judged qualitative results. Do not use the implementation agent's self-assessment as the only quality evidence.

### Live test matrix

Run in each actual supported host in both shigol/career and shigol/eugene-s-job-hub. If additional host variants are claimed, add cells. Record model/version, host, date, project/toolkit revisions, prompt, candidate/selection trace, source reads, output checks and result.

| Category | Example request without a skill name | Required observation |
| --- | --- | --- |
| UI design | Refine this dashboard using the project's design rules | Appropriate primary design approach and verified result |
| Web motion | Implement an interruptible popover transition | Web workflow, correct behavior and reduced motion |
| Research/product | Assess this opportunity using provided evidence | Appropriate analytical workflow, no invented facts |
| Writing | Revise this passage while retaining its factual claims | Facts and project voice preserved |
| Video | Create a short animated video | Correct workflow and actual output if runtime is ready |
| No relevant skill | Diagnose a backend retry bug | No unrelated design/video activation |
| Phase transition | Audit motion, then apply an approved fix | Audit restrictions preserved; implementation uses appropriate instructions |
| Explicit-only | Generic request resembling a restricted skill | No implicit invocation of manual-only workflow |
| Host/runtime limitation | Request a capability missing a prerequisite | Accurate readiness result and supported fallback |
| New addition/edit | Task needing the newly admitted capability | Automatic discovery without naming it; repeat after update |

Use independent prompts, not copies of catalogue examples, and keep a held-out set unused during tuning. Start with the capped smoke test below, not the full matrix. Compare representative tasks with the native-only baseline on the same model settings; record context/time overhead where measurable. The broader matrix is a later evidence gate, not an instruction to spend 80–160+ tasks immediately.

After budget review, the proposed broader target is at least 20 prompts and 90% eligible appropriate choices per cell, all critical workflow cases passing, zero manual-only violations or local-file clobbers, and no observed task-quality regression against baseline. This is still a small sample, not statistical proof. Do not turn the target into an unconditional task quota: expand only where justified and affordable, and explain changes using evidence. Report smoke-verified pilot support separately from broader verification; do not claim the larger matrix ran or compensate for one failing host with averages from another.

### Evaluation cost and stop rules

Claude's review cites Career rule 6 as requiring a cost estimate before work exceeding roughly 2% of the weekly plan and reports lean plan usage until 2026-11-03. Read the current consumer rule and check remaining usage before launching model-driven batches. The full matrix is a later batch, not the immediate execution schedule. Follow the actual repo rule and existing authorization; do not infer a new approval requirement beyond it.

The first batch is capped at four fresh-thread feasibility probes. Record observable input/output tokens, elapsed time, model and plan-meter change if available. Use those measurements to price the next batch before running it. Do not invent dollar costs or convert tokens into weekly-plan percentages without provider evidence.

| Stage | Maximum model-driven runs | Purpose |
| --- | ---: | --- |
| Feasibility | 4 | One new-thread bootstrap probe per host/project cell |
| Baseline | 4 | One representative native-only comparison per cell |
| Smoke | 20 | Five per cell: relevant task, abstention/restriction, phase change, newly added skill, edited skill |

The initial campaign is at most 28 runs including feasibility and baseline, not 28 plus unlimited retries. Every attempted run counts; stop and fix a systematic failure before spending the rest. Keep tasks small and bounded; a representative motion/video routing probe may test selection/readiness only, and cannot count as verified video production. Where existing legitimate task evidence is comparable, reuse it with provenance rather than rerunning work merely to fill a quota.

Illustrative planning envelope only: at 20,000 input and 2,000 output tokens per run, 28 runs would total about 560,000 input and 56,000 output tokens, excluding any unreported internal/provider usage. These assumed per-run amounts are not measurements or a promise of plan cost. After the four probes, replace them with observed numbers and a conservative estimate for artifact-producing tasks. Enforce a finite per-run output/turn/tool budget supported by the host; stop on a cap or repeated failure rather than silently extending it.

Report the smoke results and measured cost before scheduling the broad matrix. Estimate added runs explicitly, including paired baselines, repeats and retries; use a capped next batch that fits remaining allowance. If usage cannot be measured, label cost unknown and do not launch the expensive matrix. Continue deterministic local checks and useful implementation independently. Never call a smoke pass full verification.

Unsupported runtime cases can pass a readiness/abstention test, but do not count as successful execution. A video category with no actual render remains unverified for video production. Keep partial support visible rather than blocking useful text/code capabilities or declaring universal support.

### Structural, failure and scale tests

- Admission: missing/inaccurate required fields, duplicate identity, unresolved overlaps, manual-only flags, license/provenance, invalid paths and changed source hashes.
- Intake resilience: retries, repeated submissions, concurrent changes, incomplete registration and source/metadata drift leave the last working library intact.
- Consumer delivery: newly added and edited skills, fresh/existing checkout, repeated setup, exact revision consistency, update failures and rollback; preserve foreign links and local skills.
- Retrieval: unsupported/no-match requests, overlapping design skills, negative-example contamination, incompatible hosts, project exclusions and bounded candidate output.
- Scale, after the vertical slice: at least 300 temporary entries with distractors and near-duplicates. This is a deterministic local test, not hundreds of model calls. Report candidate recall, output size, search time and startup growth relative to the real catalogue. Synthetic scale tests do not prove real agent accuracy. Faster-than-daily delivery can also wait until the slice works; document the existing cadence accurately.
- Task lifecycle: new chat, existing chat after a supported refresh, phase changes and stale checkout detection.

Keep useful local diagnostics: toolkit revision, selected skill, selection reason or abstention, runtime readiness and outcome. No external telemetry service is needed. Public evidence is generic; private prompts/artifacts remain in their owning project.

## 7. Operations and definition of done

A release report lists each supported host/project cell, checks and task results, add/edit delivery evidence, measured budgets, known limitations, update trigger/cadence and rollback steps. Separate implemented, verified, unsupported and blocked. An inaccessible host remains unverified; a simulated response or filesystem check cannot fill that cell.

Complete means Eugene can submit a new skill once, have the system describe/map and deliver it, then ask ordinary tasks in both agents and both connected projects and see suitable skills used without naming them. An existing-skill edit follows the same path. Unsuitable tasks avoid those skills. Context remains bounded as the library grows.

Keep maintenance simple: source updates rerun admission and affected evaluation fixtures; do not fetch upstream latest at task startup. Retire poor skills deliberately with a migration path. No unnecessary centralized service, agent swarm, global duplicate installation or per-conversation user ritual.

## 8. Repository handoff and verified starting state

- Shared repository: https://github.com/shigol/agent-toolkit. Foundation PR #3 and implementation PR #4 are merged. Start from current main and read AGENTS.md, README.md and USAGE.md before changes. The former foundation branch is historical, not the current handoff.
- Consumers: shigol/career and shigol/eugene-s-job-hub. Read each repository's rules first. Fetch current main; the recorded baseline toolkit revision is 7c92ce19bb9293a1db4855755a1b8ae438d04366, not a promise that consumers still use it.
- Implementation: scripts/toolkit.py, toolkit.lock.json, catalog/, tests/. Preserve source/license hashes and documented portability patches. Consumer workflows already validate installation and restrict automatic merging of executable/setup changes.
- Tracking: EVG-124 in Linear. Record milestone evidence, PRs and blockers; keep it open until the declared supported host matrix passes.
- Verified locally on the foundation branch: 28 guides, 19 Python tests, four Node browser-discovery tests, 1,082 vendored hashes and git diff --check. These do not establish real agent selection.
- Three sources set disable-model-invocation: true. Preserve their restrictions. Codex CLI exists here; Claude CLI does not. Neither executable presence nor absence establishes all remote-host capabilities.
- Taste's Chromium fallback is already implemented at the recorded baseline via merged toolkit PR #2: vendor/taste/skills/scripts/lib/cdp.mjs checks /opt/pw-browsers/chromium without settings env. Four Node tests cover discovery and override precedence. Claude's review repeats the earlier missing-fallback diagnosis; do not duplicate the patch. A real browser launch in the actual Claude host remains to be verified separately.
- Automatic agent-assisted intake and bounded search are implemented. Bootstrap implementation, consumer rollout and live behavioral evidence are tracked separately above. Reuse the guides; revise inaccuracies when source evidence requires it.

## 9. Next actions and change log

1. Reread Career SHARED.md before every new phase and before shared-file edits; update only your own entry and pull/rebase before pushing. Honor Claude's 20:50 split: Claude owns hosted bootstrap, consumer trigger lines and systematic-debugging intake/delivery/probe; Codex owns scripts/policy, runner proofs, native budget guard and review. Do not duplicate work or overwrite Claude's evidence.
2. Preserve Career run40543821429 and app native-only run40558805552 as pilot evidence. App authentication now works after its credential update. Native Codex selected/read all three relevant sources without a route table; use native-first with a coverage fallback. The routed paid control was skipped. Keep Claude's host bridge. See EVIDENCE.md for exact usage and limits.
3. Claude's real intake publication is proven by #7 and both consumers now select30 skills. Read its current probes before duplicating work. Latest app proof caught an unread declaration; v6 and the nightly audit address claims. Trivial pasted-output judgments remain valid abstention controls; substantive tests require actual work and successful source output.
4. Do not impose a native cap or duplicate route table without measurements. Preserve current intentional selections; keep the complete index/search available. DraftPR9 supplies optional route generation and drift checks; consumer adoption requires a handoff, preservation of local/account rules and a header-budget check. Complete the remaining consolidated task list before the issue closes; price larger replay/value batches first.

2026-10-27 architecture revision: replaced the feature-first sequence with a mission-driven vertical slice; added explicit triggers/delivery states, host feasibility, separate eligibility/readiness, bounded context and baseline artifact evaluation. Kept existing guides, publication controls and freedom to change implementation.

2026-10-27 Claude review incorporated: [PR #3 review](https://github.com/shigol/agent-toolkit/pull/3#issuecomment-6445360498). Accepted the three must-fix requirements: fresh-thread skills-only SessionStart setup, an always-loaded one-line pointer within Career's 3.5 KB cap, and a cost-calibrated capped smoke test before the broad matrix. Deferred account-skill bootstrap, synthetic scale and accelerated delivery until the vertical slice. Corrected the stale Chromium diagnosis against code; actual host runtime and toolkit write access remain unverified. These are implementation requirements, not claims that consumer fixes have shipped.

2026-10-27 implementation: consumer fixes have now shipped in Career #100/app #235. Both fresh checkout startup commands pass at the recorded toolkit pin; new skill intake/search and recovery are merged. The deterministic 320-entry test was inexpensive and completed locally; no model-scale evaluation was implied. One nested Codex probe failed before response; actual Claude execution is unavailable in this session. Remaining work is real-host behavioral and task-quality proof, with the cost caps above.

2026-10-27 live evidence correction: actual hosted Claude skips repo hooks in the tested sessions, so Claude installed a native account adapter and owns its proof. The scoped nested-CLI filesystem fix exposed a separate auth rejection. Career's maintained-auth runner completed a substantive unnamed task with catalogue search, new skill source reads and fresh check output; the app seed-only route returned401. Simple judgment controls correctly abstained; their original forced-activation gate was invalid. Native count guard follows the demonstrated cross-group retrieval path and is coordinated with Claude's consumer updates. See EVIDENCE.md for exact scope, usage and remaining gaps.
