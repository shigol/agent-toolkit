# Shared skills rollout

Updated: 2026-10-27. Status: implementation in progress.

## Success

Add a skill once. The system records its purpose, scope, requirements and overlaps from source evidence. Approved additions reach connected projects; Claude and Codex select relevant skills without the user naming them. Full instructions load only when useful. Project requirements and manual-only restrictions govern execution.

Availability requires the consumer update and setup to complete. Existing chats do not acquire new context merely because GitHub changed. New projects connect once. Native discovery differs by host; direct-file selection must also work.

## Execution order

| Phase | Acceptance | Status |
| --- | --- | --- |
| 1. Current catalogue | All 28 skills have purpose, scope, requirements, overlap rules and examples; admission checks enforce completeness | Implemented on this branch; publication pending |
| 2. Bounded retrieval | Search reaches the whole library regardless of native project links; output is limited; no suitable skill is a valid result | Pending |
| 3. Assisted intake | A submitted source/link produces a draft guide and provenance; checks identify duplicates, restrictions, licensing and prerequisites; unresolved cases are flagged | Pending |
| 4. Project integration | Both projects receive reviewed updates and the same small selection policy; local procedures remain intact | Pending |
| 5. Live behavioral tests | Claude and Codex each select and apply appropriate skills in both projects from unnamed task requests | Pending |
| 6. Propagation and scale | Additions/edits reach both consumers; failures and rollback work; hundreds of entries keep bounded output | Pending |

Proceed in this session, following dependencies rather than waiting days between phases. Live host access can block behavioral proof without blocking implementation. Record results instead of promising a calendar completion date.

## Decisions

- Keep one shared library; local project procedures stay local.
- Keep native defaults small; make every registered guide searchable even when its group has no native links.
- Read candidate summaries, then the selected guide, source SKILL.md and needed references. Do not load all skills at startup.
- Match the requested action, project technology and task phase. Topic similarity alone is insufficient; no skill is valid.
- Preserve explicit-only restrictions and use one primary design workflow per pass.
- Review source instructions before admission. A submitted link does not authorize executing its install commands.
- Distribute through checked consumer PRs. Existing review rules for executable/setup changes still apply.

## Behavioral test matrix

Run every case in Claude and Codex in both connected projects. Record host/model, project/toolkit commits, exact prompt, candidates, source actually read, resulting artifact/check, and pass/fail. Repeat representative cases with paraphrases and in fresh conversations. Prompts must not name the expected skill.

| Task | Expected behavior |
| --- | --- |
| Refine a dashboard | General UI workflow; preserve project design rules |
| Build a popover transition | Web motion workflow; no video workflow |
| Produce an animated video | Video workflow; check render prerequisites |
| Diagnose backend retry logic | No unrelated design/video skills |
| Audit motion, then implement an approved fix | Switch from audit to implementation instructions |
| Request resembling a manual-only skill | Preserve its explicit-invocation restriction |
| Request requiring an unavailable runtime | Identify prerequisite; do not claim execution |

Structural checks do not count as live behavioral runs. Keep private artifacts in their project and publish only generic results here.

## New-skill and change tests

1. Submit a legitimate new capability without hand-writing its catalogue metadata. Verify generated metadata against source and record unresolved decisions.
2. Publish accepted registration and update both consumers normally. Check fresh and existing checkout setup.
3. Ask both agents a relevant task without naming the new skill. Verify source reading and useful execution; test non-use on irrelevant work.
4. Edit the skill and repeat propagation. Test duplicate name, overlapping purpose, missing guide/dependency, incompatible host and manual-only source.
5. Roll back the toolkit commit without overwriting local skills.
6. Use at least 300 temporary synthetic entries to measure retrieval limits and candidate quality. Synthetic tests do not establish real-world selection accuracy.

## Evidence log

- Baseline: 28 registered skills; three source files set `disable-model-invocation: true`.
- Codex CLI exists in this environment; Claude CLI is absent. CLI presence alone does not prove live model access or skill selection.
- Guides are on `codex/skill-selection-guides`. All 19 Python tests pass, including catalogue inventory and rejection of missing guides or weakened manual-only restrictions. All 1,082 vendored hashes verify. Publication and live host tests are pending.

## Implementation handoff for Claude or Codex

### Repositories and starting point

- Shared implementation: https://github.com/shigol/agent-toolkit. Foundation branch: `codex/skill-selection-guides`. Read AGENTS.md, README.md, USAGE.md, then this document. Existing code is Python 3.9+ standard library; avoid adding services or dependencies without a measured need.
- Consumers: `shigol/career` and `shigol/eugene-s-job-hub`. The latter is the app repository; do not confuse its name with Career. Read each consumer's own agent rules before editing. Keep private project information out of the public toolkit.
- Existing consumers record toolkit commit `7c92ce19bb9293a1db4855755a1b8ae438d04366` as the baseline of this work. Fetch current main before changing anything; do not assume that baseline is still current.
- Existing installer: `scripts/toolkit.py`; inventory/provenance: `toolkit.lock.json`; guides: `catalog/`; tests: `tests/`. Existing consumer update policies already validate installation and restrict automatic merges of executable/setup changes. Preserve them.
- Tracking: EVG-124 in Linear. Update it with phase evidence, PRs and blockers; keep it open until actual host tests pass.

### Phase 2: retrieval and routing

1. Add a dependency-free `search` command to the existing toolkit CLI, accepting a task query and a bounded result limit. Search registered catalogue entries, not every vendored file, and search all groups even when a project installs only some native links.
2. Return short candidates with name, purpose, invocation restriction, guide path and source path. Use stable ranking/tie-breaking and a hard output limit. Begin with lexical matching against curated descriptions; do not pretend ranking proves suitability or silently choose a skill from weak matches.
3. Cover representative positive and negative queries and return an empty list for no supported match. If lexical retrieval misses paraphrases, measure those failures before adding synonyms or a more complex retrieval backend.
4. Put one concise selection policy in the shared toolkit. Before substantial work, identify the action/platform, consider native candidates, search when needed, inspect a few guides, then read the selected source and necessary references. Reassess at phase changes. Do not force a skill for trivial work.
5. Provide the same policy through small pointers in both consumers' AGENTS.md and CLAUDE.md. Hosted Claude must have an explicit direct-file/command path because its Skill tool may not discover `.claude/skills`. Verify the host reads those pointers; their existence alone is insufficient.
6. Preserve existing native selections initially. Tune a smaller default set only after evaluation; retrieval must already reach capabilities outside those selections. Do not solve catalogue growth by symlinking every skill into every native catalogue.

### Phase 3: intake

1. Define one intake request format for a repository URL/skill directory, optional pinned revision and reason for adding it. Collect source, license, revision, dependency and host requirements without executing submitted commands.
2. Have the agent inspect the source and draft the existing guide fields. Source-specific analysis belongs to the agent; a deterministic script cannot invent accurate use cases from a title. Produce an inspectable proposed diff and provenance, not unchecked guesses.
3. Compare names and purpose with existing entries. Recommend updating an existing skill for a duplicate capability; flag ambiguous overlaps instead of selecting a default arbitrarily.
4. Validate required descriptions, exact source links, hashes, license retention, invocation restrictions and paths. Add explicit host compatibility/dependency fields if needed and migrate existing guides consistently. Distinguish unknown compatibility from verified support.
5. For complete, permitted routine additions, proceed through the established checked publication path without asking the user to hand-author metadata. Request missing information only when it cannot be resolved from source. Keep executable/setup changes under the existing review rules.
6. Include a reusable intake workflow accessible to both agents so the user's normal action can be “add this skill: URL.” No promise that every social-media link contains a reusable or licensed skill.

### Phase 4: rollout

1. Merge the checked toolkit foundation and subsequent implementation PRs in dependency order. Then update each consumer gitlink, setup and concise selection pointers in its own PR.
2. Preserve local skills, settings, symlinks and project rules. Run idempotent setup twice and check fresh checkout setup. Verify every installed source resolves for both agents and the full catalogue is searchable.
3. Keep existing checked automatic updates. Document that active checkouts need their normal update/setup step and that an already-running conversation may need a refresh. Do not add competing global skill copies.

### Phases 5–6: execution and release gate

Create repeatable fixtures for the behavioral matrix, including paraphrases, phase changes and irrelevant tasks. Record actual source reads and outputs, not an agent's statement that it used a skill. Manual-only violations, overwritten local files or unintended external actions are release failures.

For each of the four host/project combinations, run every matrix category and a new-skill addition/edit scenario. Report correct selections and failures as counts; aim for at least 90% appropriate choices over a minimum of 20 prompts per combination, with zero manual-only violations. Review failures rather than tuning only the exact prompts. Structural tests must additionally cover missing metadata, duplicates, conflicting local skills, propagation, rollback and bounded retrieval over 300+ temporary entries.

If a live host is inaccessible, finish independent implementation and mark that matrix cell unverified with the precise blocker. Do not substitute a simulated model response or static filesystem check. The rollout remains incomplete until those cells pass.

## Session boundary

This document is the handoff contract. Keep completed evidence and pending work separate. Foundation changes are ready for a reviewable PR; retrieval, intake, consumer rollout and actual behavioral testing have not been implemented. The next agent should continue from the branch rather than regenerate the 28 guides.

## Next action

Validate and publish the catalogue foundation, then implement bounded retrieval. Update phase status and evidence after each step. Do not mark the rollout complete until both agents have passed actual host tests.
