import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('continuation_receipt', Path(__file__).resolve().parents[1] / 'scripts/continuation_receipt.py')
RECEIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECEIPT)


class ContinuationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.now = '2026-10-29T10:00:00Z'
        self.record = {'continuation': {'id': 'schedule-example', 'target_thread': 'thread-example', 'scheduled_for': '2026-10-29T09:46:56Z'}}
        self.automation = {'id': 'schedule-example', 'thread_id': 'thread-example', 'is_enabled': False,
                           'schedule': 'BEGIN:VEVENT\nDTSTART:20261029T094656Z\nEND:VEVENT',
                           'last_run_time': '2026-10-29T09:46:28Z', 'run_details': {'last_run': None, 'latest_result': None, 'delivery_status': 'unknown'}}

    def check(self):
        return RECEIPT.assess(self.record, {'observed_at': self.now, 'automation': self.automation}, self.now)

    def completed(self):
        details = self.automation['run_details']
        details['last_run'] = {'id': 'run-example', 'recorded_status': 'completed', 'scheduled_for': '2026-10-29T09:46:56Z',
                               'started_at': '2026-10-29T09:47:00Z', 'completed_at': '2026-10-29T09:49:00Z',
                               'chat_ref': {'id': 'thread-example', 'type': 'codex'}}
        details['latest_result'] = {'run_id': 'run-example', 'created_at': '2026-10-29T09:49:00Z',
                                   'content_text': 'A checked bounded result', 'content_truncated': False,
                                   'is_failure_message': False, 'requires_user_action': False}

    def test_consumed_schedule_and_timestamp_do_not_prove_an_invocation(self):
        self.assertEqual(self.check()['state'], 'unconfirmed_run')
        self.assertFalse(self.check()['mission_complete'])

    def test_enabled_future_followup_is_scheduled_not_started(self):
        self.record['continuation']['scheduled_for'] = '2026-10-29T10:10:00Z'
        self.automation['is_enabled'] = True
        self.automation['schedule'] = 'BEGIN:VEVENT\nDTSTART:20261029T101000Z\nEND:VEVENT'
        self.assertEqual(self.check()['state'], 'scheduled')
        self.assertIsNone(self.check()['run_id'])

    def test_overdue_enabled_followup_is_not_running(self):
        self.automation['is_enabled'] = True
        self.assertEqual(self.check()['state'], 'unconfirmed_run')

    def test_recorded_in_progress_run_does_not_claim_live_worker(self):
        self.completed(); self.automation['run_details']['last_run']['recorded_status'] = 'in_progress'
        self.assertEqual(self.check()['state'], 'invocation_recorded')
        self.assertFalse(self.check()['worker_liveness_verified'])

    def test_completed_receipt_is_not_mission_completion_or_delivery_proof(self):
        self.completed()
        result = self.check()
        self.assertEqual(result['state'], 'result_available')
        self.assertEqual(result['run_id'], 'run-example')
        self.assertFalse(result['mission_complete'])
        self.assertEqual(result['delivery_status'], 'unknown')

    def test_old_result_from_another_run_does_not_pass(self):
        self.completed(); self.automation['run_details']['latest_result']['run_id'] = 'old-run'
        self.assertEqual(self.check()['state'], 'stale_result')

    def test_retry_with_same_id_but_old_result_does_not_pass(self):
        self.completed(); self.automation['run_details']['latest_result']['created_at'] = '2026-10-29T09:46:00Z'
        self.assertEqual(self.check()['state'], 'stale_result')

    def test_failure_after_output_remains_failed(self):
        self.completed(); self.automation['run_details']['last_run']['recorded_status'] = 'failed'
        self.assertEqual(self.check()['state'], 'failed')

    def test_unknown_failure_state_does_not_pass(self):
        self.completed(); del self.automation['run_details']['latest_result']['is_failure_message']
        self.assertEqual(self.check()['state'], 'invalid_observation')

    def test_rescheduled_or_recurring_provider_task_is_not_this_one_time_check(self):
        for schedule in ('BEGIN:VEVENT\nDTSTART:20261029T101000Z\nEND:VEVENT',
                         'BEGIN:VEVENT\nDTSTART:20261029T094656Z\nRRULE:FREQ=HOURLY\nEND:VEVENT'):
            changed = copy.deepcopy(self.automation); changed['schedule'] = schedule
            result = RECEIPT.assess(self.record, {'observed_at': self.now, 'automation': changed}, self.now)
            self.assertIn(result['state'], ('mismatched_task', 'invalid_observation'))

    def test_truncated_result_remains_partial(self):
        self.completed(); self.automation['run_details']['latest_result']['content_truncated'] = True
        self.assertEqual(self.check()['state'], 'partial_result')

    def test_different_chat_or_schedule_is_rejected(self):
        for key in ('id', 'thread_id'):
            changed = copy.deepcopy(self.automation); changed[key] = 'different'
            result = RECEIPT.assess(self.record, {'observed_at': self.now, 'automation': changed}, self.now)
            self.assertEqual(result['state'], 'mismatched_task')

    def test_another_invocation_schedule_is_rejected(self):
        self.completed(); self.automation['run_details']['last_run']['scheduled_for'] = '2026-10-29T08:00:00Z'
        self.assertEqual(self.check()['state'], 'mismatched_run')

    def test_stale_or_future_observation_cannot_certify_state(self):
        for observed in ('2026-10-29T09:00:00Z', '2026-10-29T11:00:00Z'):
            result = RECEIPT.assess(self.record, {'observed_at': observed, 'automation': self.automation}, self.now)
            self.assertEqual(result['state'], 'stale_observation')

    def test_invalid_and_naive_timestamps_are_unconfirmed(self):
        for observed in ('bad', '2026-10-29T10:00:00'):
            result = RECEIPT.assess(self.record, {'observed_at': observed, 'automation': self.automation}, self.now)
            self.assertEqual(result['state'], 'invalid_observation')
