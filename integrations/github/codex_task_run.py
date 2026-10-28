"""Bounded model execution with truthful trace-progress and partial-work checkpoints."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from codex_task_patch import snapshot


def usage(trace):
    total, known = 0, False
    if trace.is_file():
        with trace.open(errors='replace') as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('type') == 'turn.completed':
                    value = event.get('usage', {}).get('input_tokens')
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                        total += value
                        known = True
    return total, known


def run(command, output, seconds=1500, stale_seconds=900, interval=30):
    output.mkdir(parents=True, exist_ok=True)
    trace = output / 'trace.jsonl'
    started = time.monotonic()
    changed, last_size, last_snapshot = started, 0, started - interval
    stop = []
    previous = {}
    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, lambda number, frame: stop.append('interrupted'))
    status, checkpoint_error = 'running', ''
    process = None
    try:
        with trace.open('wb') as stdout, (output / 'error.log').open('wb') as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            while process.poll() is None:
                now = time.monotonic()
                size = trace.stat().st_size
                if size != last_size:
                    changed, last_size = now, size
                if now - started >= seconds:
                    stop.append('timeout')
                elif now - changed >= stale_seconds:
                    stop.append('stalled')
                if stop:
                    status = stop[0]
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                if now - last_snapshot >= interval or stop:
                    try:
                        snapshot(output)
                        checkpoint_error = ''
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        checkpoint_error = type(error).__name__
                    count, known = usage(trace)
                    data = {'schema': 1, 'status': status, 'observed_at': datetime.now(timezone.utc).isoformat(),
                            'elapsed_seconds': round(now - started), 'trace_bytes': size,
                            'seconds_since_trace_progress': round(now - changed),
                            'input_tokens': count, 'usage_known': known, 'checkpoint_error': checkpoint_error}
                    temporary = output / 'checkpoint.json.tmp'
                    temporary.write_text(json.dumps(data) + '\n')
                    temporary.replace(output / 'checkpoint.json')
                    print(f"codex-progress: state={status} trace_bytes={size} seconds_since_trace_progress={data['seconds_since_trace_progress']}", flush=True)
                    last_snapshot = now
                time.sleep(min(0.2, interval))
            if status == 'running':
                status = 'execution_complete' if process.returncode == 0 else 'failed'
        try:
            snapshot(output)
            checkpoint_error = ''
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            checkpoint_error = type(error).__name__
        count, known = usage(trace)
        (output / 'checkpoint.json').write_text(json.dumps({'schema': 1, 'status': status,
            'observed_at': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': round(time.monotonic() - started),
            'trace_bytes': trace.stat().st_size, 'exit_code': process.returncode,
            'input_tokens': count, 'usage_known': known, 'checkpoint_error': checkpoint_error}) + '\n')
        return process.returncode if status in ('execution_complete', 'failed') else 124
    finally:
        if process and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=1500)
    parser.add_argument('--stale-seconds', type=int, default=900)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1800 or not 1 <= args.stale_seconds <= 1500:
        parser.error('Execution bounds exceed the supported limits')
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A command is required')
    raise SystemExit(run(command, args.output, args.seconds, args.stale_seconds))
