# Work that continues after a chat

A submitted cloud job can run with the workstation closed. A finished chat turn is not a running worker, a scheduler or a promise that someone will pick up the next task.

Before ending a turn with authorised work unfinished, retain either:

- A verified queued/running cloud job, its run link, a committed brief/checkpoint, the remaining steps, owner and next check; or
- An explicit paused/not-running status with the reason and the next action. An estimate is active work time unless unattended execution is actually established.

Do not call a task running from an accepted request alone. Check the actual job state and recent progress. A completed/failed bounded run does not imply that a coordinator started the next step. Save partial work before a time limit, and keep review/merge/deployment separate from worker success.

## Coverage

New projects initialized by this toolkit and Codex global profiles receive a compact instruction pointing here. Existing projects need the reviewed pin and regenerated setup; existing chats do not refresh themselves. Claude's account adapter and canonical working rules are maintained by Claude. Repository hooks are not an enforcement mechanism on hosts that skip them.

Ordinary chats use the same reporting rule. If that chat cannot submit and inspect a cloud job, it must say that work stops when the turn ends. Account instructions can carry this rule, but this toolkit cannot inject it into every account, product or unsupported chat surface.

## Register a bounded cloud plan

The continuity integration adds a deterministic controller around the existing committed-brief worker. It requires a reviewed installation in the consuming repository; a toolkit pin alone does not copy new workflow files into an existing project. New `init-project` integrations include the files. Keep existing project authentication and dependency preparation when merging worker changes.

Commit a plan under docs/, codex/ or tools/, with one to eight steps and explicit limits:

```json
{
  "schema": 1,
  "title": "Check and document the requested change",
  "limits": {"max_runs": 3, "max_minutes": 120, "max_input_tokens": 1000000},
  "steps": [
    {"id": "check", "brief": "docs/check-request.md", "attempts": 2, "review": "none"},
    {"id": "report", "brief": "docs/report-request.md", "attempts": 1, "review": "required"}
  ]
}
```

A repository writer starts it by commenting `/codex-plan docs/plan.json` on an issue or PR. The agent authors and submits that brief under the user's original authorisation; the user does not need to relay it. The controller checks paths and hashes, saves state in the separate `codex/continuity-state` branch, reserves a unique attempt before dispatch and then verifies the actual Actions run. An uncertain dispatch is reconciled rather than blindly repeated.

Each normal worker gets a25-minute execution deadline and a15-minute trace-silence limit. It retains read-only partial patches, trace progress and a checkpoint before the model deadline, leaving time for the trusted result job to save its review branch. Input usage is measured after each completed model turn; that guard stops subsequent calls and is not a hard token cap within a call. Unknown usage blocks further automatic calls. Plan runs, attempts and elapsed time have hard controller limits; no loop renews its own budget.

Successful unchanged steps marked `review: none` can start the next committed step. Changed/held files always stop for review, even after a failure. Green execution is not project acceptance. A writer can use `/codex-accept REQUEST_ID` after reviewing the saved evidence; changed code must first be merged through its reviewed PR before dependent steps run. `/codex-pause REQUEST_ID` requests cancellation. `/codex-resume REQUEST_ID` preserves the original budgets and refuses an unconfirmed/still-active attempt. A changed plan or brief needs a newly reviewed submission.

The next worker receives the predecessor's same-repository answer/checkpoint/patch artifacts as data, without checking out candidate configuration or copying credentials. Reviewed default-branch code and the committed next brief remain authoritative. If that checkpoint has expired or cannot be restored, the worker does not invent the missing progress.

Completion events normally wake the controller immediately. A separate no-model watchdog runs about every30minutes only while there is active/unconfirmed work. It disables its own scheduled workflow when idle; a new plan enables it. A fresh installation may need one idle tick to disable the initial schedule. GitHub cron and queues can be delayed, so this is not an exact30-minute delivery guarantee. Progress and blocked/review notices go to the registered GitHub issue, not automatically into every chat product.

The implementation never merges or deploys candidate code. A human or the other agent reviews results through existing project permissions. Unknown authentication, missing callbacks or exhausted budgets become visible paused/blocked states. No credentials are copied between projects. No model runs merely to poll state. The hot registry is bounded to20 records and ten unfinished plans; accepted records move to separate versioned archive files when space is needed. Unresolved work is never silently dropped. Artifacts expire after14days; review branches and the versioned state remain in Git.

After reviewing a stopped blocked/paused plan, a writer may use `/codex-archive REQUEST_ID` to retain its outcome and evidence outside the hot registry. Archival is not acceptance and cannot hide an active/unconfirmed worker. Redelivery of an archived request never starts it again.

This does not detect promises made in unregistered chats, create account-level instructions, or make a finished chat turn an always-running coordinator. Ordinary chats need a supported cloud handoff before background execution can be claimed. The public toolkit's fixed harmless acceptance worker uses no model or credential and is separate from production project work.

## Acceptance before claiming unattended reliability

Submit a harmless task, disconnect the workstation and inspect a cloud-side result. Then test a worker timeout, stale heartbeat, failed authentication, a retried task and partial-work recovery. Confirm that the next eligible step starts once, saves its checkpoint and respects its budget. A status must distinguish actual execution, completed work and an unresolved gap. No system can guarantee no failure; the goal is to prevent a silent stop and make recovery observable.
