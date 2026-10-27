# Selecting skills

The user's brief and the project's own requirements always take priority.

- Impeccable is the default for product UI planning, critique, redesign and refinement. Choose its task-oriented app guidance for the Job Hub. Run the current skill's context step and inspect the rendered output.
- Taste Skill is an explicitly selected alternative for exploring a different visual direction. Use its app-screen workflow for applications. Do not mix its full workflow with Impeccable in the same design pass.
- Emil's design engineering and animation skills refine interaction behavior after a direction is selected. Use prototype for variants and break-ui for difficult content. Native mobile and Swift skills apply only to projects using those platforms.

Read the selected SKILL.md and its relevant references before applying it. Do not load every collection at once.
Animation and illustration/video production are different capabilities. This initial toolkit does not include Remotion. The Job Hub's recorded motion work (EVG-89) used Charlie Hills' technique and custom CSS/React. The current app already vendors Impeccable 4.6.0 and emil-design-eng under codex/design; migrate those references deliberately when connecting this newer toolkit.

## Agent-specific behavior

Codex discovers `.agents/skills`; Claude Code discovers `.claude/skills`. The installer creates relative symlinks to one shared copy of each skill. Ordinary Claude web chats do not discover these folders automatically.

Hooks are not installed automatically. Skill invocation and Impeccable's engine work without edit hooks. If a project opts into Impeccable detector hooks, follow the vendored `reference/hooks.md` and the agent's trust flow, preserve existing configuration, and review the resulting files. A hook configuration for one agent is not assumed to work in another.

## Updates

An upstream commit is not a toolkit release. After reviewing updated source, scripts and licenses, refresh the vendored collection and its entries in toolkit.lock.json, run tests and runtime checks, then commit the toolkit update. Each consuming project advances its submodule commit in a separate reviewed change. Never fetch an unpinned latest version during routine project setup.
