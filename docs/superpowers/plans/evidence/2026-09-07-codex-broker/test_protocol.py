"""Behavior tests for hostile wire requests; no worker/model invocation."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import broker_protocol as protocol
from prototype import Broker


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='broker-protocol-')
        self.root = Path(self.temp.name)
        (self.root / 'AGENTS.md').write_text('protected')
        self.broker = Broker(self.root, 'IMPLEMENT')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.broker.close)

    def frame(self, identifier=1, path='source.py', **extra):
        return (json.dumps(dict(id=identifier, request=dict(op='put', path=path,
                    content='allowed', expected=None), **extra)) + '\n').encode()

    def run_wire(self, wire, broker=None):
        output = io.BytesIO()
        reason = protocol.serve(io.BytesIO(wire), output, broker or self.broker)
        return reason, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_allowed_write_and_read_only_phase_over_wire(self):
        reason, replies = self.run_wire(self.frame())
        self.assertEqual(reason, 'eof')
        self.assertTrue(replies[0]['ok'])
        self.assertEqual((self.root / 'source.py').read_text(), 'allowed')
        review = Broker(self.root, 'POST_IMPL_REVIEW')
        try:
            _, replies = self.run_wire(self.frame(path='review.py'), review)
            self.assertFalse(replies[0]['ok'])
            self.assertFalse((self.root / 'review.py').exists())
        finally:
            review.close()

    def test_duplicate_keys_invalid_numbers_types_and_utf8(self):
        frames = [b'{"id":1,"id":2,"request":{}}\n',
                  b'{"id":1,"request":{"op":"read","op":"put"}}\n',
                  b'{"id":NaN,"request":{}}\n', b'{"id":true,"request":{}}\n',
                  b'{"id":1,"request":{"op":[]}}\n',
                  b'{"id":1,"request":{"op":{}}}\n',
                  b'{"id":1,"request":null}\n', b'\xff\n', b'[]\n',
                  self.frame(2**31), self.frame(-1), self.frame(root='/tmp')]
        for frame in frames:
            with self.subTest(frame=frame):
                _, replies = self.run_wire(frame)
                self.assertFalse(replies[0]['ok'])
        self.assertEqual(list(self.root.iterdir()), [self.root / 'AGENTS.md'])

    def test_oversized_and_truncated_frame_closes_before_following_mutation(self):
        for wire in [b'x' * (protocol.MAX_FRAME + 1) + b'\n' + self.frame(),
                     self.frame().rstrip(b'\n')]:
            reason, replies = self.run_wire(wire)
            self.assertEqual(reason, 'frame_limit')
            self.assertFalse(replies[0]['ok'])
            self.assertFalse((self.root / 'source.py').exists())

    def test_replayed_id_cannot_authorize_second_mutation(self):
        _, replies = self.run_wire(self.frame() + self.frame(path='second.py'))
        self.assertTrue(replies[0]['ok'])
        self.assertFalse(replies[1]['ok'])
        self.assertFalse((self.root / 'second.py').exists())

    def test_protected_path_and_forged_phase_rejected(self):
        _, replies = self.run_wire(self.frame(path='AGENTS.md') + self.frame(2, phase='IMPLEMENT'))
        self.assertTrue(all(not reply['ok'] for reply in replies))
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'protected')

    def test_request_and_input_budgets_stop_before_next_mutation(self):
        with patch.object(protocol, 'MAX_REQUESTS', 1):
            reason, _ = self.run_wire(self.frame() + self.frame(2, 'second.py'))
        self.assertEqual(reason, 'request_limit')
        self.assertFalse((self.root / 'second.py').exists())
        with patch.object(protocol, 'MAX_SESSION_INPUT', 10):
            reason, _ = self.run_wire(self.frame(3, 'third.py'))
        self.assertEqual(reason, 'input_limit')
        self.assertFalse((self.root / 'third.py').exists())

    def test_output_budget_reserved_before_mutation(self):
        with patch.object(protocol, 'MAX_SESSION_OUTPUT', protocol.MAX_FRAME + protocol.CONTROL_RESERVE):
            reason, replies = self.run_wire(self.frame() + self.frame(2, 'second.py'))
        self.assertEqual(reason, 'output_limit')
        self.assertTrue(replies[0]['ok'])
        self.assertFalse((self.root / 'second.py').exists())

    def test_json_depth_limit_rejects_without_mutation(self):
        reason, replies = self.run_wire(b'[' * 1500 + b'0' + b']' * 1500 + b'\n')
        self.assertEqual(reason, 'eof')
        self.assertFalse(replies[0]['ok'])
        self.assertFalse((self.root / 'source.py').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
