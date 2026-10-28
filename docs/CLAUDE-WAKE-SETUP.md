# Let Codex start Claude in the cloud

The wake bridge lets an authorized agent submit a committed brief to a saved Claude Code cloud routine. It creates a **new Claude session**. It does not inject a message into an existing project thread, restore another session's private state or prove that the work has started merely because the API returned a link.

Use one private repository as the gateway for connected projects. Keep its credentials there; agents working in other repositories can submit their brief to that gateway through their connected GitHub identity. The routine must have access to the repositories needed by the task. There is no dependency on a Mac being awake.

## Future projects and fresh threads

The nonsecret [HANDOFF.json](../HANDOFF.json) in the shared library identifies the default gateway, inbox and brief directory. It contains no account token or old thread ID. Fresh project setup inherits this profile from its reviewed toolkit version; the configured global Codex fallback can resolve it outside a connected project too. A project can explicitly override or disable the profile with `.agent-handoff.json`.

An agent resolves the target before posting:

```bash
python3 .agent-toolkit/scripts/toolkit.py handoff-config --project .
```

That command reports metadata, not credential/provider readiness. The gateway checks its secrets when it receives a request. Every agent reconstructs the task from the committed brief, current project rules and shared outcome records; this conversation is not required context. New sessions and machines still need their documented project/global bootstrap, GitHub access and the routine's repository access. Repo files cannot inject this integration into an unsupported ordinary chat.

Use the existing continuity rule when Claude's help is needed within an authorized task: prepare the brief and submit the wake without asking Eugene to relay it. Do not add all handoff documentation to every thread's startup context; the compact existing continuity pointer is sufficient.

## One-time account connection

First install the reviewed wake workflow and helpers in the gateway repository. New projects receive the integration through init-project; an existing project needs the reviewed workflow adoption. A source pin alone does not copy new workflows.

1. Open [Claude Code scheduled tasks](https://claude.ai/code/routines) and create a task named **Agent handoff worker**. Choose an **API trigger**, without a recurring schedule. Paste the saved prompt below. Select the required repositories, cloud environment and GitHub connector. Include additional connectors only when the task needs them. If the task is created from a Claude project, verify which project context and tools its run actually receives.
2. Generate the routine's API token and copy its fire URL. Anthropic shows the token once and provides no public token-management API. Use a routine-scoped token, not a Claude Platform API key, browser cookie or a copy of another agent's login.
3. In the gateway repository's **Settings → Secrets and variables → Actions**, add repository secrets named `CLAUDE_ROUTINE_FIRE_URL` and `CLAUDE_ROUTINE_FIRE_TOKEN`. Paste the two values directly into those secret fields. Do not put them in chat, issues, source files, screenshots or shell history. Do not regenerate an existing routine's token unless its other callers will also be updated; regeneration invalidates the previous token.

The agent handles the first test after this connection. It checks the actual result and Claude's acknowledgement; you do not need to relay task descriptions between agents. The gateway secrets remain on GitHub, so this connection does not need repeating on each Mac or each project that uses that gateway.

## Saved routine prompt

Copy this assignment into the routine's prompt field. It is deliberately self-contained because each fire creates a fresh cloud session.

```text
You are the Claude worker for authorized handoffs from the user's coding agents.

The API context identifies a request ID, repository, issue or PR, source commit,
committed brief path/hash and task text. Read the actual brief and project rules.
If the referenced repository or required tools are unavailable, report the
specific missing access in the request's GitHub thread. Do not guess or claim
that an unrelated host/session passed the requested checks.

Read CLAUDE.md and applicable repository instructions. In the Career repository,
read job-market/codex/SHARED.md and the latest inbox PR1 comments before edits.
Use the shared skills policy and read the selected SKILL.md files; hosted
project threads may require direct file reads instead of native invocation.
Follow source-review rules and name only skills whose sources you actually read.

First post one acknowledgement to the supplied GitHub issue or PR, naming the
wake request ID and the task you have begun. Identify the actual cloud session
when the host exposes its reference; never invent a session URL. Acknowledge
only after you are actually executing, not from a trigger-delivered status.

If the task requires an existing project owner and project-thread messaging is
available, check the owner/state before sending one focused message. Report
whether the owner was actually resumed. Otherwise do the authorized work in
this session when that satisfies the task, and explicitly retain any requirement
that depends on the original project host or its private state. Do not recreate
hidden experiment labels or substitute a different host for a required probe.

Finish the bounded assignment using standing user/project authorization.
Preserve other agents' work, avoid duplicate active work and keep code changes
in reviewed branches/PRs. Do not merge or deploy solely because a worker passed.
Do not send email/Slack or change account credentials unless explicitly covered
by the user's task. Do not bypass permission prompts or claim blocked steps ran.

Post the outcome once to the original GitHub thread: completed work, evidence
links, source/host/test limits and any next owner. Update only your owned Shared
section when the project requires it. Keep partial work and report an exact
blocked state if the host, authentication or budget prevents completion.

Do not start a repeating polling loop or bounce wake requests between agents.
Do not close the gateway's wake record yourself to permit another session; its
independent writer closes it after reviewing the actual session/outcome.
```

## How an agent uses it

Within the task's existing authorization, the agent writes a bounded Markdown brief under an allowed committed path, pushes/merges it through that repository's rules, then comments on a gateway issue or PR:

```text
/claude-wake docs/agent-briefs/review-request.md
```

The workflow validates the repository writer, default-branch brief and configuration. Its separate durable ledger reserves the immutable comment ID before one API request. Initial limits are one outstanding request per gateway, four fire reservations per24hours and a15-minute cooldown. These are conservative deployment defaults, not the provider's rate limits.

Missing credentials produce a visible not-configured result and no provider call. A successful response means submitted with a validated Claude session link. Actual running/completed claims need acknowledgement and evidence. The fire token cannot read session progress; use the returned session and GitHub outcome rather than inventing a monitoring capability.

The provider has no idempotency key. A timeout, ambiguous response or lost response must remain unconfirmed, with no automatic retry. Do not clear that hold just because time elapsed. An independent writer reviews the previous request/session before releasing the slot:

```text
/claude-wake-close REQUEST_ID
```

Closing a wake record is not a claim that the task passed. Record any failed or uncertain outcome honestly. The routine can consume the user's Claude subscription allowance; a configured token does not create an unlimited budget.

## First live check

Use one harmless read-only committed brief. Verify a single reservation and provider response, then an actual Claude acknowledgement/result in the requested thread. Re-deliver the same command event and verify no second fire. Test the real endpoint only after the account connection exists; mock/CI tests establish guards, not that Claude was started.

For the shared-skills closeout, the request should point to the current working plan and Claude-owned asks in Shared. Keep the original strict replay scores and the committed blind-verdict/map order. Any project-thread-specific check must run in that host, and a map unavailable to the new session remains missing until its owner supplies it.

## References and limits

- [Official routine fire API](https://platform.claude.com/docs/en/api/claude-code/routines-fire): routine-scoped authentication, new-session response, non-idempotent requests and subscription usage.
- [Claude cloud scheduled tasks](https://code.claude.com/docs/en/routines): repositories, connectors, API-trigger setup and execution permissions.
- [Projects and cloud threads](https://code.claude.com/docs/en/claude-projects): project-specific context and the difference between repository skills and account skills.

The API is experimental. No live readiness is claimed before a real configured fire and acknowledgement. Ordinary chats do not automatically become persistent workers, and a new routine session is not a public API for controlling arbitrary existing project threads.
