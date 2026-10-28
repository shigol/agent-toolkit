# Selecting skills

The user's brief and the project's own requirements always take priority.
Follow [SELECTION.md](SELECTION.md) for task-based routing and bounded search. When asked to add or update a source, use [INTAKE.md](INTAKE.md) to produce the guide and checked registration; the user need not author metadata.
Read the [selection catalogue](catalog/README.md) to distinguish overlapping skills; open only relevant guides and their sources. The [working plan](WORKING-PLAN.md) tracks the automatic-selection rollout and actual test evidence.

- Impeccable is the default for product UI planning, critique, redesign and refinement. Choose its task-oriented app guidance for the Job Hub. Run the current skill's context step and inspect the rendered output.
- Taste Skill is an explicitly selected alternative for exploring a different visual direction. Use its app-screen workflow for applications. Do not mix its full workflow with Impeccable in the same design pass.
- Emil's design engineering and animation skills refine interaction behavior after a direction is selected. Use break-ui for difficult content. prototype, pick-ui-library and review-animations require explicit user invocation per their source flags. Native mobile and Swift skills apply only to projects using those platforms.

- HyperFrames supports local motion graphics and video tasks. Read required domain guides directly under `vendor/hyperframes/skills/` when they are not exposed as slash commands. Publishing, cloud render, lambda and feedback uploads require an explicit user request. Verify the CLI/render prerequisites for the actual video task; installing instructions does not install the CLI.
- Humanizer supports prose editing without overriding project tone, facts or CV rules. The five PM skills support strategy, metrics, prioritization, PRDs and market sizing when relevant.

Read the selected SKILL.md and its relevant references before applying it. Do not load every collection at once.
Animation and illustration/video production are different capabilities. This toolkit does not include Remotion. The Job Hub's recorded motion work (EVG-89) used Charlie Hills' technique and custom CSS/React. Connected projects use their recorded toolkit version; the Job Hub's older codex/design paths are compatibility links to the shared skills.

The project's `.agent-toolkit.json` controls which groups both agents discover. Keep project-specific procedures local. Backend-only work does not need design/video skills. Use `status --project PATH` to distinguish installed files from session discovery.

## Work after the chat ends

Skill selection does not keep an idle chat running. For authorized work that must continue, register a bounded committed plan through the supported repository integration and verify its actual cloud state; otherwise report paused. Read [CONTINUITY.md](CONTINUITY.md) for the handoff and host limits, and the [measured cloud evidence](docs/continuity-fixtures/RESULTS.md) for what has actually passed. A toolkit version update alone does not install new workflows into an existing project.

If Claude's review or owned work is needed within the user's authorization, author a committed brief and use the configured private `/claude-wake` gateway instead of asking Eugene to relay it. [Routine setup](docs/CLAUDE-WAKE-SETUP.md) is separate from skills: it needs a UI-created routine token and starts a fresh session. Missing configuration or ambiguous submission is a visible hold, not permission to retry or claim work started.

## Agent-specific behavior

Codex discovers `.agents/skills`; compatible Claude Code hosts discover `.claude/skills`. The installer creates relative symlinks to one shared copy of each skill. Ordinary Claude web chats do not discover these folders automatically. Live remote_projects probes on 2026-10-27 skipped repository hooks and exposed account skills, correcting the earlier claim that SessionStart would initialize those threads. In that hosted surface, Claude owns the account-level `shared-skills` bootstrap, which points into the same library and supports direct SKILL.md reading. Discovery of that adapter was reported in both projects; substantive invocation is tracked separately in EVIDENCE.md and Career SHARED.md. Do not rely on a reload or repo hook to enable hosted Skill-tool discovery. Keep one shared policy; the adapter does not duplicate all skills or grant repository access.

Hooks are not installed automatically. Skill invocation and Impeccable's engine work without edit hooks. If a project opts into Impeccable detector hooks, follow the vendored `reference/hooks.md` and the agent's trust flow, preserve existing configuration, and review the resulting files. A hook configuration for one agent is not assumed to work in another.

## Updates

An upstream commit is not a toolkit release. After reviewing updated source, scripts and licenses, refresh the vendored collection and its entries in toolkit.lock.json, run tests and runtime checks, then commit the toolkit update. Each consuming project advances its submodule commit in a separate PR. Projects with the automatic-update integration can merge small compatible nonvendor Markdown updates automatically; vendor/source, manifest, executable/setup changes and removals need review. See README.md for registration and update rules. Never fetch an unpinned latest version during routine project setup.

Some upstream skills recommend their own refresh/install commands. In this pinned shared installation, update through the toolkit maintenance process instead; do not let those commands rewrite a consuming project's shared sources or install competing global copies. Preserve upstream files and licenses.
