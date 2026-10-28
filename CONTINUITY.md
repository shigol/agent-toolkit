# Work that continues after a chat

A submitted cloud job can run with the workstation closed. A finished chat turn is not a running worker, a scheduler or a promise that someone will pick up the next task.

Before ending a turn with authorised work unfinished, retain either:

- A verified queued/running cloud job, its run link, a committed brief/checkpoint, the remaining steps, owner and next check; or
- An explicit paused/not-running status with the reason and the next action. An estimate is active work time unless unattended execution is actually established.

Do not call a task running from an accepted request alone. Check the actual job state and recent progress. A completed/failed bounded run does not imply that a coordinator started the next step. Save partial work before a time limit, and keep review/merge/deployment separate from worker success.

## Coverage

New projects initialized by this toolkit and Codex global profiles receive a compact instruction pointing here. Existing projects need the reviewed pin and regenerated setup; existing chats do not refresh themselves. Claude's account adapter and canonical working rules are maintained by Claude. Repository hooks are not an enforcement mechanism on hosts that skip them.

Ordinary chats use the same reporting rule. If that chat cannot submit and inspect a cloud job, it must say that work stops when the turn ends. Account instructions can carry this rule, but this toolkit cannot inject it into every account, product or unsupported chat surface.

## What still requires infrastructure

Reliable continuation through a backlog needs a durable task record and an independent runner/watchdog. The record holds authorised scope, the current revision/checkpoint, queued/running/paused/done state, run ID, last measured progress, next step and retry/time/usage limits. The existing watcher should compare that record with actual runs, resume eligible stopped work and report an exhausted or blocked task. Retries must be bounded and must preserve review and permission limits.

The current committed-brief workflows execute and save one bounded task. They do not implement a universal backlog coordinator, detect promises made in unregistered chats, or provide thirty-minute chat updates after the agent stops. Do not report those features as installed merely because this contract exists.

## Acceptance before claiming unattended reliability

Submit a harmless task, disconnect the workstation and inspect a cloud-side result. Then test a worker timeout, stale heartbeat, failed authentication, a retried task and partial-work recovery. Confirm that the next eligible step starts once, saves its checkpoint and respects its budget. A status must distinguish actual execution, completed work and an unresolved gap. No system can guarantee no failure; the goal is to prevent a silent stop and make recovery observable.
