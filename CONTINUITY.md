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

Every immutable command comment has its own intake concurrency group. State writes use non-forced compare-and-swap recovery with bounded retries, and command IDs make redelivery idempotent. Completion/watchdog events may coalesce after the request is durable. The repository queue starts at most one registered/observed committed-brief worker at once; it also observes an installed codex-build.yml so the app's shared authentication session is preserved. Other plans stay explicitly pending. A cancelled attempt is retried only when Actions proves execution never started; an unknown executed result stays blocked.

Plan and brief hashes, plus the installed worker/controller/transport contract, are frozen. Unrelated default-branch commits do not invalidate a plan; each actual worker revision is recorded separately. Changing the task definitions or worker permissions/source pauses the plan for review. Workers still start only from the trusted current default branch, never an arbitrary candidate ref.

Each normal worker gets a25-minute execution deadline and a15-minute trace-silence limit. It retains read-only partial patches, trace progress and a checkpoint before the model deadline, leaving time for the trusted result job to save its review branch. Input usage is measured after each completed model turn; that guard stops subsequent calls and is not a hard token cap within a call. Unknown usage blocks further automatic calls. Plan runs, attempts and elapsed time have hard controller limits; no loop renews its own budget.

Plan and dispatch reservations are durable immediately in Git. Periodic model-work snapshots remain on the runner until artifact upload and review-branch transport; a hard runner loss can therefore lose edits made since the last completed upload. Graceful timeout/stall recovery is tested separately from a hard VM crash. Do not describe local snapshots as continuous remote backup.

Successful unchanged steps marked `review: none` can start the next committed step. Changed/held files always stop for review, even after a failure. Green execution is not project acceptance. A writer can use `/codex-accept REQUEST_ID` after reviewing the saved evidence; changed code must first be merged through its reviewed PR before dependent steps run. `/codex-pause REQUEST_ID` requests cancellation. `/codex-resume REQUEST_ID` preserves the original budgets and refuses an unconfirmed/still-active attempt. A changed plan or brief needs a newly reviewed submission.

The next worker receives the predecessor's same-repository answer/checkpoint/patch artifacts as data, without checking out candidate configuration or copying credentials. Reviewed default-branch code and the committed next brief remain authoritative. If that checkpoint has expired or cannot be restored, the worker does not invent the missing progress.

The trusted result job explicitly dispatches the controller after posting its receipt. The receiver polls the actual same-repository, default-branch worker until its workflow has finished, handling the result-before-parent-completion race without trusting caller assertions. The existing workflow_run event remains a fallback; the first cloud fixture did not emit that event, so it is not assumed reliable here. A separate no-model watchdog runs about every30minutes only while there is active/unconfirmed work. It disables its own scheduled workflow when idle; a new plan enables it. A fresh installation may need one idle tick to disable the initial schedule. GitHub cron and queues can be delayed, so this is not an exact30-minute delivery guarantee. Progress and blocked/review notices go to the registered GitHub issue, not automatically into every chat product.

The implementation never merges or deploys candidate code. A human or the other agent reviews results through existing project permissions. Unknown authentication, missing callbacks or exhausted budgets become visible paused/blocked states. No credentials are copied between projects. No model runs merely to poll state. The hot registry is bounded to20 records and ten unfinished plans; accepted records move to separate versioned archive files when space is needed. Unresolved work is never silently dropped. Artifacts expire after14days; review branches and the versioned state remain in Git.

After reviewing a stopped blocked/paused plan, a writer may use `/codex-archive REQUEST_ID` to retain its outcome and evidence outside the hot registry. Archival is not acceptance and cannot hide an active/unconfirmed worker. Redelivery of an archived request never starts it again.

This does not detect promises made in unregistered chats, create account-level instructions, or make a finished chat turn an always-running coordinator. Ordinary chats need a supported cloud handoff before background execution can be claimed. The public toolkit's fixed harmless acceptance worker uses no model or credential and is separate from production project work.

The legacy `/codex-run` command still submits one bounded worker and does not register a durable plan. Use `/codex-plan` for a multi-step or recovery-monitored handoff. Unregistered legacy/manual requests can still be limited by their existing runner/concurrency behaviour; this controller does not retroactively claim to own them.

## Wake Claude when its work is needed

When the user's existing authorization requires Claude's review or another owned task, resolve the nonsecret shared gateway with `python3 scripts/toolkit.py handoff-config` (or the equivalent pinned .agent-toolkit path). This reads HANDOFF.json from the shared library and honors the current working directory's .agent-handoff.json override or disabled flag by default; `--project PATH` selects a different project explicitly. New project initialization and global-only fallback use that same library profile, without copying old thread state or credentials. Resolved metadata explicitly does not check credentials or live provider access.

The agent writes a committed brief under the resolved gateway's brief directory and submits `/claude-wake docs/path.md` to its issue. Eugene does not relay between agents. This starts a fresh routine session which reads current project rules and shared coordination state; it does not resume an old thread. See the [routine setup and prompt](docs/CLAUDE-WAKE-SETUP.md).

The trusted default-branch bridge allows only repository writers, a committed regular Markdown brief and the fixed official routine-fire endpoint. It reserves the immutable comment ID on `claude/wake-state` before sending one request. It stores only dispatch metadata and a validated session link, never the brief text or token. Missing configuration sends nothing. Provider acceptance means submitted, not started or complete; wait for an actual worker acknowledgment and reviewed result links in the coordination record.

One reserved/submitted/unconfirmed wake holds the repository slot until a writer independently investigates and sends `/claude-wake-close REQUEST_ID`. Closing releases a dispatch slot; it does not certify task completion. The originating dispatch workflow must already have stopped. A lost runner, timeout, 5xx response or ambiguous success never causes a blind retry or automatic age-based reset. Initial limits are four outbound attempts per rolling 24 hours and a 15-minute cooldown, with 32 hot records and immutable archives; changing these lean defaults requires a reviewed code change. No model runs to poll another model, and this does not create an agent-to-agent recursive loop.

`init-project` copies the dormant bridge into future projects without replacing an existing integration. Existing projects need a reviewed workflow/helper adoption; a toolkit pin alone does not install it. One private gateway can serve connected projects with one routine-specific secret pair. Only the routine UI can create that token; no cookies, raw provider API key or credentials copied from another host are used. The bridge remains inactive until configured. This installation does not establish live provider access or a working routine by itself.

## Acceptance before claiming unattended reliability

Submit a harmless task, disconnect the workstation and inspect a cloud-side result. Then test a worker timeout, stale heartbeat, failed authentication, a retried task and partial-work recovery. Confirm that the next eligible step starts once, saves its checkpoint and respects its budget. A status must distinguish actual execution, completed work and an unresolved gap. No system can guarantee no failure; the goal is to prevent a silent stop and make recovery observable.
