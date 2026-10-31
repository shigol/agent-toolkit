# Checking a native continuation receipt

For a native one-time Codex task, capture a fresh automation observation using the supported task tool. Keep the private mission record and observation in the private project, outside this public library. The observation JSON has `observed_at` (a timezone-aware timestamp) and `automation` (the selected provider task object, including its run details).

Run:

```bash
python3 .agent-toolkit/scripts/continuation_receipt.py --record /path/to/mission.json --observation /path/to/observation.json
```

The mission record must identify `continuation.id`, `continuation.target_thread` and `continuation.scheduled_for`. This initial adapter supports exactly `BEGIN:VEVENT`, one UTC `DTSTART`, and `END:VEVENT`, with LF or CRLF line endings and an optional final newline. It rejects extra properties, exclusions, added occurrences, recurrence and changed schedules. It makes no network requests, starts no worker and changes no files. The caller must query the provider and timestamp the observation honestly; a JSON file is not independent provider evidence.

The check distinguishes an enabled future schedule, a recorded invocation and a matching result. Missing invocation history remains unconfirmed even if the provider reports a last-run timestamp or consumed the schedule. Results must match the actual invocation and be newer than its current retry start. Failed attempts, truncated output, stale observations and unknown result flags do not pass.

Exit0 means the metadata supports a scheduled check, a recorded invocation or an available result. It never means the mission is complete. A recorded in-progress status does not establish current worker liveness. Delivery remains unknown; independently check the agreed destination and review the task evidence. This helper is not yet an automatic end-of-turn hook, a watchdog or a universal task adapter.

Do not store private prompts, credentials, raw transcripts or real project task identifiers in public regression fixtures. Tests use fictional identifiers and the observed API response structure.
