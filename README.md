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

Read [USAGE.md](USAGE.md) for selection guidance. Project-specific UX and brand rules belong in each app's own PRODUCT.md, DESIGN.md and agent instructions.
Every registered skill has a [selection guide](catalog/README.md). New skills require the same description and examples; catalogue admission checks run in CI. Track ongoing implementation and host verification in [WORKING-PLAN.md](WORKING-PLAN.md).
Agents follow [SELECTION.md](SELECTION.md): routes first, then the catalogue index, then search if still unsure. Use [INTAKE.md](INTAKE.md) when asked to add a source. Intake is triggered by the request to the agent; no background model service is installed. Search validates the whole registered catalogue and reaches unlinked groups while honoring explicit exclusions. Publication and live readiness remain separate states.

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

Commit `.gitmodules`, the `.agent-toolkit` gitlink, and the generated `.agents/skills` and `.claude/skills` symlinks. The gitlink pins an exact toolkit commit. There is one skill copy inside the submodule, with relative links for both agents. An existing unrelated skill is never overwritten; conflicts stop the entire installation before links are created.

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

Compatible additions and edits to Markdown skill instructions and references can merge automatically with their manifest updates. Installer/runtime changes, executable files, deleted files, moved or removed skills, conflicts with project-specific skills, and failed checks need review. Project branch protections and requested changes remain in force. Publication here does not silently alter an active checkout or chat: pull the consuming project, rerun its setup, and reload the agent when needed.

To add a skill, preserve its source and license under `vendor/`, register its unique name, directory and package in `toolkit.lock.json`, and include every vendored file's SHA-256 hash. The registered directory must contain `SKILL.md`. Installation creates links for every registered skill in both agents' folders, including skills added after a project first connected. An existing project-specific skill with the same name stops installation rather than being overwritten. Update the collection table and selection guidance when adding a collection.

Automatic consumer updates follow commits published in this repository. Updating from each original author's repository remains a deliberate maintenance task. Adding a new project still requires opting it into the submodule, setup command and update workflows; existing unrelated projects are unaffected.

### Managed Claude project containers

Taste browser discovery includes `/opt/pw-browsers/chromium` as a fallback when it exists. Explicit browser overrides retain precedence. This documented compatibility patch applies to actual Taste browser launches as well as runtime verification; its upstream and patched hashes are recorded in the manifest and its diff is in `patches/`.

Claude project threads may not expose filesystem skills through their Skill tool even when every file is installed. In that host, read the selected `SKILL.md` directly; a reload is not claimed to enable discovery. `status` reports file installation only.
