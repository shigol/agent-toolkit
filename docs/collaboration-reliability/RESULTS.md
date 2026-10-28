# Collaboration reliability verification

Reviewed code release: `97df0c26a4f74264214f74f644b7ef6457e98728` ([PR36](https://github.com/shigol/agent-toolkit/pull/36)), following [PR35](https://github.com/shigol/agent-toolkit/pull/35), `89975b59`. PR36 exact-head CI [40778743744](https://github.com/shigol/agent-toolkit/actions/runs/40778743744) and main CI [40779034927](https://github.com/shigol/agent-toolkit/actions/runs/40779034927) passed.

Local checks:114 Python tests,92 Node tests,30 selection guides,1,096 vendor hashes and15 workflow lints passed. Consumer managed checks cover60 Node tests. Independent review corrected post-execution job-outcome handling, transport time allowance, frozen helper dependencies, completed-step/missing-receipt status, monitor exit races and resumed-attempt acknowledgment.

## Actual GitHub-hosted checks

All timestamps below are UTC on2026-10-28. These fixed fixtures call no model or paid API and contain no project data or credentials. They run in GitHub-hosted jobs, independently of a local Mac. A literal Mac-disconnection experiment was not performed.

| Check | Observed evidence | Result |
| --- | --- | --- |
| Exact Claude Code footer | Request6482117204 accepted; child [40779101382](https://github.com/shigol/agent-toolkit/actions/runs/40779101382) | Pass |
| Same-request replay | Handler [40779047774](https://github.com/shigol/agent-toolkit/actions/runs/40779047774), attempt2 success; registry total_runs1, same child | Pass; no duplicate execution |
| Observable monitor before worker | Monitor [40779074582](https://github.com/shigol/agent-toolkit/actions/runs/40779074582) acknowledged registration22:19:35.780; child created22:19:42 | Pass |
| Delayed start accurately reported | Fixed execution delayed11minutes; state initializing while execution pending | Pass |
| Independent start deadline notices | Target22:24:24.133; notice [6482221045](https://github.com/shigol/agent-toolkit/pull/36#issuecomment-6482221045)22:24:50. Queued second target22:24:33.772; notice22:24:53 | Pass, automatically emitted by monitor; no manual reconciliation tick |
| Durable queue | Request6482118578 initially total_runs0 behind first; later one child [40780591244](https://github.com/shigol/agent-toolkit/actions/runs/40780591244) | Pass |
| Execution versus delivery | Second child completed fixed execution and retained artifact; save deliberately failed. Original [receipt6482359344](https://github.com/shigol/agent-toolkit/pull/36#issuecomment-6482359344) preserved; registry blocked with total_runs1 | Pass; no inference retry |
| Artifact-only recovery | [Recovery40780754982](https://github.com/shigol/agent-toolkit/actions/runs/40780754982) succeeded; branch codex/task-40780591244 | Pass; independent comparison found exactly one fictional delivery-checkpoint.txt |
| Review and closure | First read-only fixture accepted by6482380543; second recovery reviewed by6482399651 and archived by6482399987 | Original failed outcome preserved; archival does not mark it accepted |

## Failed criterion retained

The first release's cron-only monitoring failed the timely-notice test: no scheduled watchdog ran during the eleven-minute delay. Earlier footer/replay/queue/recovery checks passed, including recovery [40776610759](https://github.com/shigol/agent-toolkit/actions/runs/40776610759), but that is not a monitoring pass. PR36 replaced this dependency with an explicitly dispatched bounded monitor and per-request acknowledgment. Cron remains a fallback.

## Consumer rollout

- App [PR272](https://github.com/shigol/eugene-s-job-hub/pull/272) merged `525e2152`; final head `5211211c` passed installation [40779411799](https://github.com/shigol/eugene-s-job-hub/actions/runs/40779411799) and PR evidence checks.
- Career [PR126](https://github.com/shigol/career/pull/126) merged `3a3fda95`; final head `64c64e96` passed installation [40780632831](https://github.com/shigol/career/actions/runs/40780632831). Required prepush used a disclosed code-equivalent cached-data baseline:37 pass and12 unchanged cached-baseline failures. This is not a current-data or scoring certification.
- Both pin97df0c26. Project authentication, worker setup and native skill preparation were preserved. Installing a library pin alone does not copy workflow updates into an existing project.

## Boundaries

Unit fixtures separately cover ambiguous dispatch/callbacks, timeout budgets, resume epochs, path validation and monitor handoff. Those branches are not all separately induced in live production. Normal task execution is bounded to one call by default; observed token usage is not a hard ceiling within a provider call. Provider outages and runner queues can delay checks.

Cloud notices go to the registered GitHub issue/PR. They do not automatically appear in this chat or wake arbitrary Claude Projects threads. The configured routine starts a fresh Claude Code session. No thirty-minute chat automation is claimed. Shared-skills selection quality and original Claude Projects raw-read evidence remain separate EVG-124 acceptance work.

Claude's initiating and follow-up procedure is [CLAUDE-TO-CODEX.md](../CLAUDE-TO-CODEX.md).
