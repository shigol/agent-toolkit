# Cloud continuation evidence

Measured on GitHub Actions on 28 October 2026. These fixed fictional workers use no model, account login, user data or external service. GitHub Actions carries execution and callbacks; no workstation process performs the work. This is an infrastructure acceptance record, not proof that every ordinary chat keeps running.

## Actual cloud outcomes

The corrected worker/controller contract was released at `e8cd74b8a98722cdab6aef1e61e04d9640651340`; its merged-main [CI run 40693411297](https://github.com/shigol/agent-toolkit/actions/runs/40693411297) passed.

| Registered request | Actual worker runs | Observed result |
|---|---|---|
| [Retry plan 6469782853](https://github.com/shigol/agent-toolkit/pull/22#issuecomment-6469782853) | [40693638130](https://github.com/shigol/agent-toolkit/actions/runs/40693638130), [40693713758](https://github.com/shigol/agent-toolkit/actions/runs/40693713758), [40693794642](https://github.com/shigol/agent-toolkit/actions/runs/40693794642) | First attempt failed, second succeeded, then the next committed step ran automatically. Exactly three runs; final state required review. |
| [Exhaustion plan 6469784686](https://github.com/shigol/agent-toolkit/pull/22#issuecomment-6469784686) | [40693876998](https://github.com/shigol/agent-toolkit/actions/runs/40693876998), [40693956457](https://github.com/shigol/agent-toolkit/actions/runs/40693956457) | Both allowed attempts failed. State became blocked; no third attempt was dispatched. |
| [Partial plan 6469828891](https://github.com/shigol/agent-toolkit/pull/22#issuecomment-6469828891) | [40694068831](https://github.com/shigol/agent-toolkit/actions/runs/40694068831) | Deadline stopped the process. The uploaded checkpoint reported timeout; its actual partial.patch retained the fictional text. Review branch codex/task-40694068831 remained unmerged. |

The first two requests were submitted concurrently, and both registrations survived overlapping controller activity. The durable queue ran one worker at a time. No duplicate reserved attempt was observed. The retry plan's second attempt and next step came from trusted result callbacks, without another writer command. Final states and receipts live on `codex/continuity-state`; archival preserves the outcome rather than marking failed or reviewed work complete.

The partial artifact was downloaded and inspected: artifact `12818860786`, checkpoint status timeout, exit code -15, partial patch containing the expected fictional line. Its usage was explicitly unknown, so no later model call could be justified from that checkpoint. The fixture wrapper's expected failures are encoded in its typed receipt; the surrounding workflow can still finish successfully to deliver results.

## Failures found before the passing run

- The initial PR inbox status write returned 403: issues permission alone did not authorize PR comments on this path. Reviewed PR20 added the scoped pull-requests permission; no credential or broader PAT change was used.
- After that fix, worker 40691336981 completed and posted its receipt, but no workflow_run callback appeared in the observed run listing. Its durable plan remained waiting. This is a measured callback gap on this installation, not a general claim about GitHub. Reviewed PR22 added an explicit trusted-result workflow_dispatch, with bounded verification of the actual predecessor's completion before reconciliation. Old frozen-contract fixtures were stopped and archived before fresh registration.
- A separate read-only consumer probe found trusted Python imports creating bytecode under .github/scripts. The held-path gate stopped the plan. Reviewed PR24 prevents that side effect before the import; its fresh installed-wrapper regression checks no bytecode, project diff or held path. Review rules were not weakened. Consumer-specific answers and traces stay in their private repository.

## Checks and limits

The combined code plus bytecode fix passed 86 Python tests, 32 controller tests and 1,096 vendored source hashes. Deterministic tests cover coalesced intake, CAS conflict recovery, run-state validation, uncertain dispatch, deadlines, unknown usage, review holds, idempotency and bounded retry/exhaustion. These checks complement the actual cloud runs above; they are not all separate live failure injections.

Public fixtures disable the recurring watchdog so this acceptance creates no standing public timer. A separate consuming-repository probe observed its real watchdog API state become active during work and disabled after its final review stop. It executed exactly two task model calls (separate small authentication health checks are maintenance model calls, excluded from that task count) and included a reviewer-approved cache-only hold, so it is not presented as an uninterrupted automatic consumer chain. No extra task model call was used to retest the deterministic bytecode fix.

Registered plans have durable state and graceful checkpoint recovery. A hard VM loss can still lose the latest unuploaded edits. Observed usage stops subsequent calls, not a single call midway through a provider token allowance. GitHub cron scheduling can be delayed. Legacy unregistered requests, unsupported account/chat surfaces and idle chats are outside this controller; see [CONTINUITY.md](../../CONTINUITY.md) before promising unattended work.
