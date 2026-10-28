# Claude: communicating with Codex

Use this when Claude needs Codex to review, implement, investigate or verify work. The requesting agent owns the handoff until a checked result is delivered. Eugene does not relay messages, start the worker or chase either agent.

This protocol requires the reviewed collaboration integration from toolkit `6e7f5022` or a compatible later version. A toolkit pin alone does not copy workflows into an old project: use the project's adopted integration and its passing checks. New `init-project` integrations include it.

## Start one task

1. Read the project's rules, shared coordination record and latest inbox messages. Paginate a long inbox: GitHub's first comments page may contain only old messages. Check the durable registry and active workflow runs for this work. If someone already owns an active request, follow that request instead of launching another.
2. Commit a bounded Markdown brief under `docs/`, `codex/` or `tools/` on the repository's default branch, using its normal review rules. Include the goal, expected answer, allowed changes, required checks, owner and deadline. A brief on an unmerged feature branch is not available to the dispatcher. Keep secrets and copied transcripts out of it.
3. Post this as the first line of a comment on that repository's issue or PR:

   ```text
   /codex-run docs/agent-briefs/review-request.md
   ```

   Do not wrap the command itself in a code fence when sending it. Do not add an inline prompt, flags or another command. The exact standard Claude Code attribution footer is supported; other trailing prose is rejected. A prose comment, mention or SHARED.md edit alone does not start Codex.
4. Keep the returned **comment ID** as the immutable request ID. Check the request-handler outcome and the record on branch `codex/continuity-state`, file `state.json`. An ordinary task automatically becomes a monitored one-worker plan; it requires no separately authored plan JSON.
5. Check the actual **child run ID**, its execution step and progress. Also verify the registry's `monitor_run_id`/link and this record's `monitor_ack`: a model is held until the running monitor has acknowledged this registration, step, attempt and resume epoch. The handler's own run is a different run. The requesting Claude session must schedule and verify its own supported follow-up if it will leave the turn; save that follow-up's ID and next-fire time. A written deadline is not a scheduled check.

Re-delivery of the same immutable request ID is reconciled without dispatching another worker. Posting a new comment creates a new request; do not use that as a retry for an uncertain or active task.

## When a connector needs direct dispatch

Use a connected repository-writer identity to dispatch **`codex-continuity.yml`**, on the actual default branch, with these inputs:

```json
{
  "brief": "docs/agent-briefs/review-request.md",
  "request_issue": "17",
  "request_id": "123456789"
}
```

The issue number and stable numeric ID above are examples. Use the actual source comment ID where available, and preserve it after an uncertain API response. The same ID cannot be reassigned to another issue or brief. The controller checks writer permission and committed paths; it does not accept arbitrary prompts or refs.

Do not dispatch `codex-task.yml` directly for ordinary collaboration: that is the internal worker and bypasses registration. A workflow's `GITHUB_TOKEN` can suppress events from comments it creates; use an explicitly authenticated writer's supported dispatch route rather than assuming a comment fired another workflow. Never copy credentials or introduce a new token to work around routing.

Use `/codex-plan docs/plan.json` for an explicitly budgeted multi-step task, as described in [CONTINUITY.md](../CONTINUITY.md). Explicit native/global/value-smoke/value/replay-smoke acceptance modes bypass durable registration, the monitor gate and deadline notices. Use them only for bounded evaluation, not ordinary handoffs; do not run a large matrix by default.

## Read the state accurately

| Evidence | What Claude may say |
| --- | --- |
| Comment exists | Message posted; no launch verified |
| Handler accepted/reserved a dispatch | Request recorded; child execution not yet verified |
| Child run queued | Queued; no execution yet |
| Workflow active, execution step pending | Initializing; worker has not started |
| Actual execution step active | Worker started; answer not yet delivered |
| Worker succeeded, delivery failed | Inference finished; recover its existing result |
| Artifact/receipt delivered, state `review` | Result available; review/acceptance pending |
| Independent review and acceptance recorded | Accepted within the checked scope |
| `unconfirmed`, `blocked` or `paused` | Name the precise hold and recovery action |

A green worker, a `Skills:` line or a successful API response never proves the whole task is done. Read the answer, checks, source-read audit, held-path report and transport outcome. Preserve original failed receipts and raw test scores.

## Follow up without Eugene

Ask for acknowledgement within five minutes and an answer or blocker/ETA within fifteen minutes. These are coordination targets, not provider timing guarantees. Normal requests have a bounded one-worker plan, a 75-minute elapsed cap, an observed input budget of 1M and final review required. Usage is accounted when the completed worker receipt is reconciled; this is not a per-turn guard or a hard ceiling inside one provider call.

The explicitly dispatched, bounded cloud monitor reconciles immediately and then about every five minutes, records overdue start/response notices, and never runs another model just to poll. It exits when idle; at its bound it attempts one successor without resetting task budgets. Cron is only a fallback. It also emits ordinary progress notices about every thirty minutes. GitHub queues and cron can be delayed. Verify the monitor is observably running, its acknowledgment matches this task and the registry has a next action; don't infer monitoring from a workflow file merely existing.

When late, inspect the real run and checkpoint, narrow the question or take over accessible work. Reassign only after reconciling the existing attempt. Cancelling a handler does not cancel a child it already dispatched. A missing callback is not permission to restart inference. Unknown usage or execution remains held; never reset a budget to escape that hold.

Cloud notices are posted to the registered GitHub issue. They do not wake an arbitrary Claude Projects thread or guarantee delivery into this chat. Claude must use its own verified host follow-up when it needs to resume that thread. The configured Claude Code routine starts a fresh Code session; it does not resume a Projects session. If the host has no supported wake/check route, record that boundary and the actual supported recovery owner instead of promising an idle chat will monitor itself.

## Repair delivery without repeating inference

If execution completed but result saving, a later check or the callback failed:

1. Retain the original run ID, artifact and failed receipt. Check the actual completed run and successful execution/upload steps. An overall failed or cancelled job may still contain a completed execution and retained result.
2. Dispatch **`codex-recover.yml`** on the default branch with `source_run` set to that original run ID and `request_issue` set to the receiving issue/PR. Use the repository's existing writer identity.
3. The recovery job validates the actual same-repository/default-branch worker and its one retained bounded artifact. Trusted current code preflights permitted paths/modes before touching the candidate checkout. It executes no candidate code, runs no model, and never forces a conflicting review branch.
4. Inspect the recovery receipt and review branch, plus `answer.md`, `checkpoint.json`, `skill-audit.json` and `patch-report.json` in the original artifact. An absent `changes.patch` can mean a read-only answer; it does not mean no result. Held paths remain for independent review.
5. Record the recovered outcome separately. Recovery does not rewrite the original failed receipt, merge a branch, deploy, or mark a blocked continuity record accepted. Review and explicitly archive a resolved blocked record when appropriate. **Do not use pause/resume or rerun the whole worker to repair transport.**

If an ordinary result is already in `review`, merge any required reviewed change through its project PR before `/codex-accept REQUEST_ID`. Never accept unreviewed changes merely to release a queue.

## Return a short checked answer

Send the requesting thread: outcome, request ID, child run link, evidence/review link, remaining blocker and next owner/check. Report execution, delivery and acceptance separately. If no worker or scheduled check remains, say so explicitly. Keep SHARED.md current in your owned section and preserve other agents' work.

The [cloud acceptance record](collaboration-reliability/RESULTS.md) distinguishes actual runs from unit fixtures and lists remaining limits. Do not describe this protocol as an absolute guarantee against provider failure or unsupported-host limitations.
