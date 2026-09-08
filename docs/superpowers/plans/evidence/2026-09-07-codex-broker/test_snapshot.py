"""Source-export and candidate-integrity behavior tests."""
import os
from pathlib import Path
import tempfile
import unittest

from prototype import Broker, Denied
from source_snapshot import export, validate_candidate


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='broker-snapshot-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.snapshot = self.root / 'snapshot'
        (self.source / 'AGENTS.md').write_text('protected')
        (self.source / 'code.py').write_text('original')

    def test_config_and_credentials_omitted_at_every_depth(self):
        for parent in [self.source, self.source / 'nested']:
            parent.mkdir(exist_ok=True)
            for directory in ['.codex', '.agents', '.claude', '.git']:
                (parent / directory).mkdir()
                (parent / directory / 'config.toml').write_text('hostile or secret')
            for file in ['config.env', '.env.local', '.npmrc']:
                (parent / file).write_text('synthetic secret')
        baseline = export(self.source, self.snapshot)
        self.assertEqual(set(baseline), {'code.py', 'AGENTS.md'})
        self.assertEqual((self.snapshot / 'AGENTS.md').read_text(), 'protected')
        self.assertEqual(validate_candidate(self.snapshot, baseline), [])

    def test_broker_changes_validate_without_changing_original(self):
        baseline = export(self.source, self.snapshot)
        broker = Broker(self.snapshot, 'IMPLEMENT')
        try:
            broker.request(dict(op='put', path='code.py', content='changed',
                                expected=baseline['code.py']['sha256']))
        finally:
            broker.close()
        changes = validate_candidate(self.snapshot, baseline)
        self.assertEqual([c['path'] for c in changes], ['code.py'])
        self.assertEqual((self.source / 'code.py').read_text(), 'original')
        self.assertNotEqual((self.source / 'code.py').stat().st_ino,
                            (self.snapshot / 'code.py').stat().st_ino)

    def test_symlink_hardlink_and_special_file_fail_before_export(self):
        bad = self.source / 'alias'
        for kind in ['symlink', 'hardlink', 'fifo']:
            if kind == 'symlink':
                bad.symlink_to(self.root / 'outside')
            elif kind == 'hardlink':
                os.link(self.source / 'AGENTS.md', bad)
            else:
                os.mkfifo(bad)
            with self.subTest(kind=kind), self.assertRaises(Denied):
                export(self.source, self.snapshot)
            self.assertFalse(self.snapshot.exists())
            bad.unlink()

    def test_instruction_creation_replacement_deletion_and_mode_rejected(self):
        baseline = export(self.source, self.snapshot)
        instruction = self.snapshot / 'AGENTS.md'
        for change in ['write', 'delete', 'mode', 'directory', 'new']:
            instruction.write_text('protected')
            instruction.chmod(0o644)
            if change == 'write':
                instruction.write_text('attacked')
            elif change == 'delete':
                instruction.unlink()
            elif change == 'mode':
                instruction.chmod(0o755)
            elif change == 'directory':
                instruction.unlink()
                instruction.mkdir()
            else:
                (self.snapshot / 'nested').mkdir()
                (self.snapshot / 'nested/AGENTS.override.md').write_text('new instructions')
            with self.subTest(change=change), self.assertRaises(Denied):
                validate_candidate(self.snapshot, baseline)
            if change == 'directory':
                instruction.rmdir()

    def test_candidate_config_injection_is_rejected_not_silently_omitted(self):
        baseline = export(self.source, self.snapshot)
        (self.snapshot / '.codex').mkdir()
        with self.assertRaises(Denied):
            validate_candidate(self.snapshot, baseline)

    def test_export_never_overwrites_existing_destination(self):
        self.snapshot.mkdir()
        (self.snapshot / 'existing').write_text('keep')
        with self.assertRaises(FileExistsError):
            export(self.source, self.snapshot)
        self.assertEqual((self.snapshot / 'existing').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main(verbosity=2)
