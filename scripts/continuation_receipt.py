#!/usr/bin/env python3
"""Check captured native-task metadata; never dispatch or accept a mission.

The caller must obtain a fresh provider observation. JSON validation is not a
substitute for that query, and a recorded result does not establish delivery.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a timezone-aware string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp requires a timezone')
    return result


def assess(record, observation, now):
    def result(state, reason, run_id=None):
        return {'state': state, 'reason': reason, 'run_id': run_id,
                'worker_liveness_verified': False, 'delivery_status': 'unknown',
                'mission_complete': False}

    try:
        current = timestamp(now)
        observed = timestamp(observation['observed_at'])
        age = (current - observed).total_seconds()
        if age < -60 or age > 300:
            return result('stale_observation', 'Query the provider again; this observation is stale or in the future.')
        continuation = record['continuation']
        due = timestamp(continuation['scheduled_for'])
        automation = observation['automation']
        if not isinstance(continuation.get('id'), str) or not continuation['id']:
            raise ValueError('Missing continuation ID')
        if not isinstance(continuation.get('target_thread'), str) or not continuation['target_thread']:
            raise ValueError('Missing target thread')
        if automation.get('id') != continuation['id'] or automation.get('thread_id') != continuation['target_thread']:
            return result('mismatched_task', 'The provider observation belongs to another task or target thread.')
        schedule = automation.get('schedule')
        if not isinstance(schedule, str):
            return result('invalid_observation', 'This adapter requires an explicit one-time provider schedule.')
        # Validate the whole supported layout, not just a DTSTART extracted from
        # an otherwise unrestricted calendar. EXDATE/RDATE can change its meaning.
        start = re.fullmatch(r'BEGIN:VEVENT\r?\nDTSTART:(\d{8}T\d{6}Z)\r?\nEND:VEVENT\r?\n?', schedule)
        if not start or datetime.strptime(start.group(1), '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc) != due:
            return result('mismatched_task', 'The provider schedule no longer matches the registered check.')
        details = automation.get('run_details') or {}
        run = details.get('last_run')
        if not run:
            if automation.get('is_enabled') is True and due > current:
                return result('scheduled', 'An enabled future schedule exists; execution has not been established.')
            return result('unconfirmed_run', 'No invocation ID is exposed. A consumed schedule or last-run timestamp alone is insufficient.')
        run_id = run.get('id')
        if not isinstance(run_id, str) or not run_id:
            return result('unconfirmed_run', 'The provider did not expose an invocation ID.')
        if timestamp(run.get('scheduled_for')) != due:
            return result('mismatched_run', 'The invocation belongs to a different scheduled check.', run_id)
        target = run.get('chat_ref')
        if not isinstance(target, dict) or target.get('id') != continuation['target_thread']:
            return result('mismatched_run', 'The invocation does not establish the requested target chat.', run_id)
        started = timestamp(run.get('started_at'))
        if started > observed or (due - started).total_seconds() > 60:
            return result('mismatched_run', 'The invocation start does not match this check and observation.', run_id)
        state = run.get('recorded_status')
        if state == 'failed':
            return result('failed', 'The recorded attempt failed; retain any partial result before recovery.', run_id)
        if state == 'in_progress':
            return result('invocation_recorded', 'A started invocation is recorded; current worker liveness still requires direct progress evidence.', run_id)
        if state not in ('completed', 'no_update'):
            return result('unconfirmed_run', 'Unknown provider invocation state.', run_id)
        completed = timestamp(run.get('completed_at'))
        if completed < started or completed > observed:
            return result('invalid_observation', 'The invocation completion time is inconsistent.', run_id)
        if state == 'no_update':
            return result('no_update', 'The provider recorded completion with suppressed output; no delivered result is established.', run_id)
        latest = details.get('latest_result')
        if not latest:
            return result('awaiting_result', 'The invocation ended but its result is not exposed.', run_id)
        if latest.get('run_id') != run_id or timestamp(latest.get('created_at')) < started:
            return result('stale_result', 'The exposed result belongs to another run or an earlier retry.', run_id)
        if timestamp(latest['created_at']) > observed:
            return result('invalid_observation', 'The result is newer than its captured observation.', run_id)
        if latest.get('is_failure_message') is True:
            return result('failed', 'The current result reports failure.', run_id)
        if latest.get('is_failure_message') is not False:
            return result('invalid_observation', 'The provider does not establish the current result failure state.', run_id)
        if latest.get('content_truncated') is not False:
            return result('partial_result', 'The full result is unavailable; inspect its original source.', run_id)
        if latest.get('requires_user_action') is not False:
            return result('result_requires_action', 'The current result requires action or does not establish that it can proceed.', run_id)
        if not isinstance(latest.get('content_text'), str) or not latest['content_text'].strip():
            return result('awaiting_result', 'The provider exposes no readable result.', run_id)
        return result('result_available', 'A matching result is recorded. Inspect its evidence; delivery and mission acceptance are separate.', run_id)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return result('invalid_observation', 'Missing, malformed or inconsistent continuation metadata; query the provider rather than guessing.')


def read_json(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 1_000_000:
        raise ValueError('Expected a regular JSON file under1MB')
    return json.loads(source.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True)
    parser.add_argument('--observation', required=True)
    args = parser.parse_args()
    try:
        report = assess(read_json(args.record), read_json(args.observation), datetime.now(timezone.utc).isoformat())
    except (OSError, ValueError, RecursionError):
        report = {'state': 'invalid_observation', 'reason': 'Cannot read bounded JSON inputs.', 'mission_complete': False}
    print(json.dumps(report, indent=2))
    return 0 if report['state'] in ('scheduled', 'invocation_recorded', 'result_available') else 2


if __name__ == '__main__':
    raise SystemExit(main())
