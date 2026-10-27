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

## Agent-specific behavior

Codex discovers `.agents/skills`; Claude Code discovers `.claude/skills`. The installer creates relative symlinks to one shared copy of each skill. Ordinary Claude web chats do not discover these folders automatically. Managed Claude project threads may also report Unknown skill despite installed files; read the selected SKILL.md directly in that host. Do not rely on a reload to enable its Skill tool.

Hooks are not installed automatically. Skill invocation and Impeccable's engine work without edit hooks. If a project opts into Impeccable detector hooks, follow the vendored `reference/hooks.md` and the agent's trust flow, preserve existing configuration, and review the resulting files. A hook configuration for one agent is not assumed to work in another.

## Updates

An upstream commit is not a toolkit release. After reviewing updated source, scripts and licenses, refresh the vendored collection and its entries in toolkit.lock.json, run tests and runtime checks, then commit the toolkit update. Each consuming project advances its submodule commit in a separate PR. Projects with the automatic-update integration can merge compatible checked text updates automatically; executable/setup changes and removals need review. See README.md for registration and update rules. Never fetch an unpinned latest version during routine project setup.

Some upstream skills recommend their own refresh/install commands. In this pinned shared installation, update through the toolkit maintenance process instead; do not let those commands rewrite a consuming project's shared sources or install competing global copies. Preserve upstream files and licenses.
