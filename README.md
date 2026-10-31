# Agent toolkit

Shared, versioned design, video, writing and product skills for Eugene's projects, usable by Codex and Claude Code on macOS and Linux/cloud environments. GitHub is the durable source; a cloud machine's filesystem is not the only copy.

## Included

| Collection | Skills | Purpose |
| --- | ---: | --- |
| [Impeccable](https://github.com/pbakaus/impeccable) | 1 | Product UI design, critique, refinement and checks |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill) | 1 | Alternative visual directions and rendered checks |
| [Emil Kowalski](https://github.com/emilkowalski/skills) | 15 | Interaction design, animation, prototyping and mobile details |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | 5 | Local motion graphics and video creation |
| [Humanizer](https://github.com/blader/humanizer) | 1 | Editing prose |
| [PM Skills](https://github.com/phuryn/pm-skills) | 5 | Strategy, metrics, prioritization, PRDs and market sizing |
| [Superpowers](https://github.com/obra/superpowers) | 2 | Root-cause debugging and evidence before completion claims |

Exact upstream commits, all vendored file hashes, skill names and paths are in `toolkit.lock.json`. Full supporting files are included. Upstream licenses and notices are preserved beside each collection under `vendor/`; they govern those files. The POSIX Impeccable launcher has its executable bit set for direct invocation; file contents are unchanged. Toolkit-owned scripts and docs are maintained in this public repository; no license grant is implied for those files.

Read [USAGE.md](USAGE.md) for selection guidance. Claude initiating a handoff follows the [Codex communication guide](docs/CLAUDE-TO-CODEX.md), including launch verification, follow-up and result recovery. [CONTINUITY.md](CONTINUITY.md) distinguishes an active cloud job from an idle chat and defines the required handoff for unfinished work. Project-specific UX and brand rules belong in each app's own PRODUCT.md, DESIGN.md and agent instructions.
Every registered skill has a [selection guide](catalog/README.md). New skills require the same description and examples; catalogue admission checks run in CI. Track ongoing implementation and host verification in [WORKING-PLAN.md](WORKING-PLAN.md).

## New projects and global Codex fallback

From a committed toolkit checkout, initialize an existing Git repository with one command:

```bash
python3 scripts/toolkit.py init-project /absolute/path/to/project
```

This pins the exact current toolkit commit, installs relative source links for both agents, generates Claude's route block and a compact native-first Codex block, and adds setup plus daily checked-update integration. It does not download design runtimes, commit, push or deploy. Review and commit the generated files; Git's submodule command stages its own gitlink and .gitmodules entries. Existing project selections and instructions outside owned markers are preserved. A conflicting integration is reported before cloning; preserve and merge that project's configuration deliberately instead of overwriting it. Agents can complete that integration under the project's existing rules without asking the user to choose skills.

Configure Codex's fallback for repositories that have no toolkit:

```bash
python3 scripts/toolkit.py bootstrap-global
```

It writes only its owned block in CODEX_HOME/AGENTS.md (default ~/.codex/AGENTS.md), preserving other instructions and credentials. Pass `--codex-home /path` for a runner or test home. Project-native skills and project pins take priority; otherwise Codex reads the shared source from this checkout. Keep that checkout available. It creates no global skill copies and does not assert that a running chat refreshed its native catalogue. Run the same bootstrap from the pinned library when provisioning another machine or the planned server.

Connected repositories can also accept an unattended brief request. Commit a Markdown brief under codex/, docs/ or tools/, then comment `/codex-run docs/path.md` on a repository issue or PR. Only repository writers can dispatch it; normal task requests use the durable controller and the worker reads the default branch, uses that repository's existing ChatGPT login, and returns an answer, source-read trace and review branch to the same thread. The request handler never accepts arbitrary prompt text or a PR checkout. No new account credential is created. A repository without CODEX_AUTH_JSON or its maintained authentication cache must configure its own login first; initialization does not copy credentials between projects.

For work expected to continue after the chat, use the writer-only `/codex-plan docs/plan.json` handoff described in [CONTINUITY.md](CONTINUITY.md). It records a bounded plan, actual worker state and review checkpoints, and enables recovery monitoring. Ordinary tasks are held until a separately running cloud monitor has acknowledged their registration; cron is only a fallback. An ordinary single-brief command now registers a monitored one-call plan automatically; explicit acceptance modes retain their separate evaluation path.

When Claude's work is needed, the nonsecret HANDOFF.json profile locates the shared private gateway; `toolkit.py handoff-config` resolves it for existing, new and global-only projects. The dormant `/claude-wake` integration starts a fresh routine session only after separate [routine setup](docs/CLAUDE-WAKE-SETUP.md). It does not copy credentials or prove live access. Provider acceptance and task completion remain separate states.

Acceptance probes can be dispatched with mode native or global. The global fixture contains no project toolkit or native skill links. The shared grader counts complete successful source output, real fixture checks, answer correctness and aggregate usage. Normal task artifacts also compare declared names with observed source reads; unknown names remain unverified, and partial Humanizer reads count only in explicitly short-prose audits.

For the separate quality experiment, mode value-smoke records one factual outreach pair. Inspect its source-read evidence and actual usage before mode value expands to18 calls across prose, verification and static UI. A/B positions are shuffled, and outputs are separated from the private condition map and read traces. Only valid pairs belong in an independent blind judgement; the runner does not claim a value benefit.

The same writer-only comment can append native, global, value-smoke, value or replay-smoke to dispatch an acceptance mode, for example `/codex-run docs/path.md value-smoke`. Only these modes are accepted; the committed brief and default-branch rules still apply. This uses the existing connected GitHub identity and repository workflow token, so a separate terminal login is not required. The value mode explicitly requests18 calls; start with the two-call pilot. The replay-smoke mode runs only the independent recommended cases for the two current consumers (three Career, two app) from a checked docs/skills/codex-replay-v1.json. It supplies no expected labels to the executor, isolates local edits, audits actual source outputs and retains usage/patches for review. It does not expand to the full case set, publish changes or infer task correctness/rendering from source reads. The app should prepare its locked dependencies before invoking it; the harness can explicitly link those existing runner dependencies without copying credentials or profiles. When present, only the pinned checksum-verified Impeccable engine is copied into the snapshot. Career explicitly uses its established prepush archive exclusions, recording omitted file/byte counts and leaving archive-dependent findings unverified; bounds remain in force. Calls share a host and /tmp, so fresh snapshots do not imply hard filesystem isolation or statistical independence.

The worker has no repository write token. A separate trusted job transports only allowed regular source/document files to a review branch, without executing candidate code or hooks. Workflow/hidden/credential paths, symlinks and submodule changes are held for direct review; it never opens or merges a PR or deploys. Branch existence is not a passing-test claim; check the answer and trace. Existing project CI still governs eventual PR review.

The checked GitHub templates are under integrations/github. Their trusted merge controller independently holds vendor, manifest and executable changes for independent review even if candidate validation passes. Central CI reports bounded source-review category counts, not source contents or an approval verdict. Shared-source or manifest changes require the other agent's recorded diff review before merge; upstream refresh is deliberate, on request or quarterly.
Agents follow [SELECTION.md](SELECTION.md): Codex starts with native discovery; hosted Claude uses project routes. Missing coverage falls back to routes, the catalogue index, then search if still unsure. Use [INTAKE.md](INTAKE.md) when asked to add a source. Intake is triggered by the request to the agent; no background model service is installed. Search validates the whole registered catalogue and reaches unlinked groups while honoring explicit exclusions. Publication and live readiness remain separate states.

Fallback search uses reviewed guide synonyms and a minimum score; stop-word-only requests return no candidates. CI requires at least90% top-three recall on42 labelled regression requests and checks trivial-task abstention. These authored retrieval cases are not independent live selection or output-value evidence; the cross-agent replay remains separate.

## Project selections

Commit `.agent-toolkit.json` in the consuming project. Both agents use the same selection:

```json
{"schema": 1, "groups": ["design", "video"], "native_limit": 22}
```

Groups are `design` (17 skills), `video` (five HyperFrames entry skills), `writing` (Humanizer), and `product` (five PM skills). These four are the original native selections; development is described below. Optional `include` and `exclude` arrays take exact skill names. No config preserves the earlier all-skills behavior; invalid config stops setup before changes.
The `development` group contains verification-before-completion and systematic-debugging. Existing group choices control native links; the full catalogue remains searchable. Explicit `exclude` names are excluded from search as well. Include `development` only if native exposure is desired; it is not required for direct-file task selection.

Set an optional positive integer `native_limit` to bound native catalogue growth, for example `{"schema":1,"groups":["design","video"],"native_limit":22}`. The first matching registered entries remain native; later additions remain available through the index and search without new native links. Explicit `include` names take priority within the cap; exceeding it fails clearly rather than silently dropping requested names. Omitting the limit preserves older behavior. This caps skill count, not tokens; keep descriptions concise and measure actual host context separately. Choose a limit from the project's current intended selection.

Groups map to packages in `toolkit.lock.json`, so newly registered skills in a selected package join after the next checked update and setup. Unselected groups stay in the library without agent discovery links. Narrowing a selection removes only exact toolkit-owned symlinks, preserving local skills and foreign links. A selected name conflicting with a local skill stops installation. Project-specific operational skills stay in their project.

The complete upstream HyperFrames support tree is included so the five entry skills retain their relative references, including motion principles and data-in-motion guides. Read supporting domain guides directly without exposing every upstream skill in the agent catalogue. This does not install the HyperFrames CLI or certify its render runtime.

`python3 .agent-toolkit/scripts/toolkit.py status --project .` lists selected skills and installed/missing files separately for both agents. It does not claim that the current session discovered them. Run setup in the same checkout the agent uses, then reload the session or read SKILL.md directly. Pass `--project .` to runtime commands as well: text-only selections do not need Impeccable or a browser.

## Add to a project once

Requires Git, Python 3.9+ and read access to GitHub. This repository is public; cloning it requires no personal access token. From the consuming project's root:

```bash
git submodule add https://github.com/shigol/agent-toolkit.git .agent-toolkit
python3 .agent-toolkit/scripts/toolkit.py install --project .
python3 .agent-toolkit/scripts/toolkit.py setup-runtime --project .
python3 .agent-toolkit/scripts/toolkit.py verify-runtime --project .
```

Commit `.gitmodules`, the `.agent-toolkit` gitlink, and the generated `.agents/skills` and `.claude/skills` symlinks. The gitlink pins an exact toolkit commit. The pinned submodule is authoritative; both agents use relative links. Projects may also track generated readable entry copies as described below. An existing unrelated skill is never overwritten; conflicts stop the entire installation before links are created.

For a new `init-project`, `entry_cache: true` is enabled in `.agent-toolkit.json`. Existing projects can opt in by adding that boolean and running setup. Commit the generated `.agent-skill-cache/` directory together with both agents’ links and the reviewed pin. A fresh clone can then read every selected SKILL.md and its license/notice files without initializing the submodule. This does not load all skill bodies into startup context or change `native_limit`.

The cache mirrors exact pinned entry bytes; it is never another source to edit. Relative reference aliases and runtimes still require the pinned toolkit setup. Normal setup repairs missing or unchanged older generated files, refuses modified or foreign contents, and preserves project skills. After a reviewed source/selection update, run setup and commit cache and route changes in the same consumer PR. Identical entry/license bytes leave the cache manifest unchanged even when the toolkit pin advances.

CI runs `python3 .agent-toolkit/scripts/toolkit.py verify-cache --project . --check` **before** setup and again afterward. It rejects stale, missing, modified, untracked or uncommitted cache outputs and incorrect agent links; automatic local repair cannot hide published drift. Keep these generated checks when customizing consumer workflows. With `entry_cache: false` (the legacy default for existing configs), links continue to point directly into the submodule.

Generate the routing instructions after installation:

```bash
python3 .agent-toolkit/scripts/toolkit.py emit-routes --project .
python3 .agent-toolkit/scripts/toolkit.py emit-routes --project . --check
```

The command puts the same selected-skill block at the top of CLAUDE.md and AGENTS.md. Each guide's Route field supplies its task trigger; invocation restrictions are preserved. Groups, includes, exclusions and native_limit filter the block. Move project-only and account-only procedures outside the owned `skill-routes` markers before first adoption; that block is replaced on regeneration. Content outside it is preserved. Routine install regenerates existing blocks after a pin update, and verify rejects stale blocks. Existing projects without markers opt in through emit-routes. Add its `--check` invocation to consumer CI to require both blocks, including when they have been deleted. Installation does not prove native discovery or actual skill use in a running agent.

The runtime step downloads Impeccable's pinned engine for this OS/architecture and verifies it against the vendored checksum. It installs beside the launcher so the launcher selects the pinned engine ahead of any older global installation. Downloaded binaries are ignored by Git. Taste requires Node.js 22+ and Chrome, Edge or Chromium; provision these in the cloud environment image or install them on the workstation. Set `CHROME_PATH` if the browser is outside standard locations. Runtime verification checks these prerequisites without installing system packages or altering browser profiles.

## New Mac or fresh cloud checkout

Clone the consuming project with submodules, or initialize the existing checkout:

```bash
git submodule update --init -- .agent-toolkit
python3 .agent-toolkit/scripts/toolkit.py install --project .
python3 .agent-toolkit/scripts/toolkit.py setup-runtime --project .
python3 .agent-toolkit/scripts/toolkit.py verify --project .
python3 .agent-toolkit/scripts/toolkit.py verify-runtime --project .
```

Put those commands in the project's environment setup script. The toolkit is public and needs no GitHub read token. A private consuming project still needs its own GitHub access; signing in to a chat alone does not establish Git access. Launch the agent with its working directory inside the consuming project. Restart/reload the session if newly installed skills are not listed. In restricted hosted sessions, skill discovery may be controlled by the host; project instructions should point explicitly to the local skill files as a fallback.

This does not configure every future chat automatically. New projects must opt in, and cloud environments must run their setup. Ordinary Claude web chat is not Claude Code. Optional Impeccable edit hooks require per-agent setup and trust; see USAGE.md.

## Verification and updates

```bash
python3 scripts/toolkit.py verify-sources
python3 -m unittest discover -s tests -v
```

`verify --project PATH` checks all vendored hashes and both agents' links. `verify-runtime` checks the pinned engine checksum/handshake, Node version and browser executable. Those checks establish installation readiness; they do not claim the current agent loaded a skill or that a design passed visual QA.

To update a consuming project deliberately, fetch the toolkit submodule, check out the reviewed toolkit commit, rerun setup and checks, and commit the updated gitlink. Do not use `git submodule update --remote` in routine startup. Never put GitHub tokens or other secrets in a URL, script, manifest or commit.

### Automatic updates in connected projects

A consuming project can opt into daily Dependabot `gitsubmodule` update PRs for `.agent-toolkit`. Its own validation workflow checks the inventory, source hashes, repeatable installation, runtime, and new-skill propagation to both agents. A separate merge workflow can merge a checked Dependabot PR that changes only the gitlink. The project continues to record an exact version.

Changes to vendored skill instructions/references and their manifest updates require the other agent's review, including additive Markdown. Only small compatible nonvendor Markdown updates remain eligible for unattended merging. Installer/runtime changes, executable files, deleted files, moved or removed skills, conflicts with project-specific skills, and failed checks need review. Project branch protections and requested changes remain in force. Publication here does not silently alter an active checkout or chat: pull the consuming project, rerun its setup, and reload the agent when needed.

To add a skill, preserve its source and license under `vendor/`, register its unique name, directory and package in `toolkit.lock.json`, and include every vendored file's SHA-256 hash. The registered directory must contain `SKILL.md`. Installation creates links for every registered skill in both agents' folders, including skills added after a project first connected. An existing project-specific skill with the same name stops installation rather than being overwritten. Update the collection table and selection guidance when adding a collection.

Automatic consumer updates follow commits published in this repository. Updating from each original author's repository remains a deliberate maintenance task. Adding a new project still requires opting it into the submodule, setup command and update workflows; existing unrelated projects are unaffected.

### Managed Claude project containers

Taste browser discovery includes `/opt/pw-browsers/chromium` as a fallback when it exists. Explicit browser overrides retain precedence. This documented compatibility patch applies to actual Taste browser launches as well as runtime verification; its upstream and patched hashes are recorded in the manifest and its diff is in `patches/`.

Claude project threads may not expose filesystem skills through their Skill tool even when every file is installed. In that host, read the selected `SKILL.md` directly; a reload is not claimed to enable discovery. `status` reports file installation only.

## Commit skills audit

Consumer setup (`toolkit.py install` from the consumer's pinned `.agent-toolkit`)
and `init-project` install `.githooks/commit-msg` and set local `core.hooksPath`.
The hook runs `scripts/skills_audit.py` directly from the pin; consumers carry no
copy of the grader. Standalone source-link installs outside a consumer's pinned
submodule do not install Git hooks. Setup preserves other `.githooks` files and
refuses a foreign commit-msg, custom hooksPath or active default hooks before
changing skill links. Merge those project hooks deliberately, then rerun setup.
Career may keep its compatibility entry point and existing hook.

The audit preserves Career's stamp, nightly collector commands and offline
selftests. From a consumer root:

```sh
python3 .agent-toolkit/scripts/skills_audit.py selftest --pinned-sources
python3 .agent-toolkit/scripts/skills_audit.py stamp .git/COMMIT_EDITMSG
```

Claude uses `CLAUDE_CODE_SESSION_ID` and its local project transcript. Codex uses
`CODEX_THREAD_ID` and the matching rollout under `${CODEX_HOME:-~/.codex}/sessions`.
It accepts paired function/custom tool results, including code-mode output,
checks the same Tbilisi window and rejects failed or truncated evidence.
It never picks the newest session or borrows another thread's reads. These
formats were checked against a local Codex rollout; unsupported or ephemeral
hosts cannot provide the same evidence. OpenAI's [CLI reference](https://developers.openai.com/codex/cli/reference)
documents `--ephemeral`, which disables session persistence.

`UNREAD`, `PARTIAL` and `GUIDE` refuse the commit; full reads stamp `Skills-Read`
and `Skills-Window`. Existing fail-open behavior for unknown sources, missing
session/transcript and stamp errors is retained. A missing transcript prints a
skip diagnostic. This checks declared reads, not semantic application, missing
Skills lines or deliberate hook bypass. New clones must run setup: Git does not
clone local hooksPath configuration. Cache-only skill readability does not mean
the audit executable or hooks are ready. No account files are edited.
