"""Check the host-visible states at and around the ask-mode deadline."""

from pathlib import Path
import runpy
import unittest


resolve = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'replacement_window.py'))['resolve']


class ReplacementWindowTests(unittest.TestCase):
    def test_silent_deadline_and_resume(self):
        early = resolve(100, [], 159.99)
        self.assertEqual(early['status'], 'pending')
        self.assertAlmostEqual(early['seconds_left'], 0.01)
        for now in [160, 170, 500]:
            self.assertEqual(resolve(100, [], now)['status'], 'timeout_default')

    def test_queued_input_including_deadline_is_honored(self):
        for received in [159, 160]:
            for kind, expected in [('approve', 'approved'), ('veto', 'vetoed'),
                                   ('other', 'needs_clarification')]:
                with self.subTest(received=received, kind=kind):
                    replies = [{'received_at': received, 'kind': kind}]
                    self.assertEqual(resolve(100, replies, 165)['status'], expected)

    def test_reply_can_resolve_clarification_after_deadline(self):
        replies = [{'received_at': 112, 'kind': 'other'}]
        self.assertEqual(resolve(100, replies, 135)['status'], 'needs_clarification')
        self.assertEqual(resolve(100, replies, 180)['status'], 'needs_clarification')
        replies.append({'received_at': 190, 'kind': 'approve'})
        self.assertEqual(resolve(100, replies, 190)['status'], 'approved')

    def test_veto_closes_original_proposal(self):
        replies = [{'received_at': 101, 'kind': 'veto'}, {'received_at': 102, 'kind': 'approve'}]
        self.assertEqual(resolve(100, replies, 102)['status'], 'vetoed')

    def test_rejects_invalid_events(self):
        for replies in [[{'received_at': 99, 'kind': 'approve'}],
                        [{'received_at': 161, 'kind': 'approve'}],
                        [{'received_at': 155, 'kind': 'unknown'}]]:
            with self.subTest(replies=replies), self.assertRaises(ValueError):
                resolve(100, replies, 160)
