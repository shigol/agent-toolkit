# Selecting shared skills

The user's task and project rules govern the work. Use this policy in Claude and Codex; it does not grant permissions or install task runtimes.

1. Identify the requested action, deliverable, platform and current phase. Trivial tasks and work with no relevant skill can proceed normally. If the user asks to add or update a shared skill from a link, follow INTAKE.md here.
2. Consider available native skills and local project procedures. For substantial work without a clear fit, or when relevant capabilities may be outside the native list, search the entire shared catalogue:

   `python3 .agent-toolkit/scripts/skills.py search --project . --query "<action, deliverable and platform>"`

   Run from the project root. Native groups control exposure; explicit `exclude` names are also excluded from search. A result is a candidate, not a recommendation or proof of runtime readiness. No match is valid. Rephrase once if needed; do not search on every message. No need to ask the user which skill to use.
3. Read at most two relevant candidate guides and choose by supported action, exclusions, prerequisites and overlaps. Use one primary design workflow; add specialists only for distinct tasks. Default UI design uses Impeccable; Taste requires the explicitly chosen alternative direction. Do not load the catalogue index or every skill body into the conversation.
4. Read the selected source SKILL.md and only required references. Hosted Claude project threads may not expose repo skills through the Skill tool: read the exact source path directly. Preserve all invocation restrictions. `--include-restricted` can discover manual-only workflows when explicitly requested; it never authorizes implicit invocation.
5. Check the real environment before execution. Instructions being present does not establish browser, CLI, credentials, platform compatibility or permission to publish. Follow project setup for missing prerequisites and report a precise blocker if necessary. Never run upstream refresh commands against the shared pinned checkout.
6. Apply the workflow and verify the task result. Report the skill used briefly when material; do not merely claim compliance. Reassess when moving from research or audit to implementation, or when the platform changes.

If .agent-toolkit is absent, run the consuming repo's documented skills-only setup once. On timeout/network failure, report toolkit readiness accurately and continue unrelated work. Do not fetch a mutable latest revision. Shared changes are made in shigol/agent-toolkit, with local project procedures kept in their own repository. Updates reach active checkouts through their normal reviewed update/setup process; running chats do not refresh themselves.
