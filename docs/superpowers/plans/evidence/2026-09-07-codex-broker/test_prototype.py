"""Portable behavior tests; no model, network, or host sandbox required."""
import os
from pathlib import Path
import tempfile
import unittest

from prototype import Broker, Commands, Denied, MAX_CONTENT, digest


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='broker-unit-')
        self.root = Path(self.temp.name)
        (self.root / 'src').mkdir()
        (self.root / 'src/app.py').write_text('old')
        (self.root / 'AGENTS.md').write_text('protected')
        self.broker = Broker(self.root, 'IMPLEMENT')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.broker.close)

    def put(self, path, content='new', expected=None):
        return self.broker.request(dict(op='put', path=path, content=content,
                                        expected=expected))

    def test_edit_create_delete_and_stale_rejection(self):
        result = self.broker.request(dict(op='read', path='src/app.py'))
        self.assertEqual(result['content'], 'old')
        self.put('src/app.py', expected=result['sha256'])
        with self.assertRaises(Denied):
            self.put('src/app.py', expected=result['sha256'])
        self.assertEqual((self.root / 'src/app.py').read_text(), 'new')
        self.broker.request(dict(op='mkdir', path='new dir'))
        self.put('new dir/code.py')
        self.broker.request(dict(op='delete', path='new dir/code.py', expected=digest(b'new')))
        self.assertFalse((self.root / 'new dir/code.py').exists())

    def test_protected_paths_at_arbitrary_new_depth(self):
        self.broker.request(dict(op='mkdir', path='new'))
        self.broker.request(dict(op='mkdir', path='new/deeper'))
        for name in ['AGENTS.md', 'AGENTS.override.md', 'CLAUDE.md', 'CLAUDE.local.md',
                     '.agents', '.codex', '.claude', '.git', '.github', '.env',
                     '.env.local', 'config.env', '.agent-data', '.npmrc']:
            for prefix in ['', 'src/', 'new/deeper/']:
                with self.subTest(path=prefix + name), self.assertRaises(Denied):
                    self.put(prefix + name)
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'protected')

    def test_noncanonical_paths_and_case_aliases(self):
        for path in ['', '/tmp/escape', '../escape', 'src/../AGENTS.md', 'src//x',
                     './x', 'src/./x', 'src\\AGENTS.md', 'src/agents.MD', 'a\x00b']:
            with self.subTest(path=path), self.assertRaises(Denied):
                self.put(path)

    def test_symlink_parent_and_leaf(self):
        (self.root / 'alias').symlink_to('AGENTS.md')
        (self.root / 'linked').symlink_to('src', target_is_directory=True)
        for path in ['alias', 'linked/new.py']:
            with self.subTest(path=path), self.assertRaises(Denied):
                self.put(path)
        self.assertFalse((self.root / 'src/new.py').exists())

    def test_preexisting_hardlink_alias(self):
        os.link(self.root / 'AGENTS.md', self.root / 'alias')
        with self.assertRaises(Denied):
            self.put('alias', expected=digest(b'protected'))
        with self.assertRaises(Denied):
            self.broker.request(dict(op='delete', path='alias', expected=digest(b'protected')))
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'protected')

    def test_parent_replacement_and_other_operations_denied(self):
        (self.root / 'src/AGENTS.md').write_text('nested')
        for op in ['rename', 'symlink', 'hardlink', 'chmod', 'shell', 'exec', 'apply_patch']:
            with self.subTest(op=op), self.assertRaises(Denied):
                self.broker.request(dict(op=op, path='src', target='moved'))
        with self.assertRaises(Denied):
            self.broker.request(dict(op='delete', path='src', expected=None))
        self.assertEqual((self.root / 'src/AGENTS.md').read_text(), 'nested')

    def test_read_only_phases_cannot_mutate(self):
        for phase in ['TRIAGE', 'REPLY', 'VALIDATE', 'ADVERSARIAL_PLAN',
                      'POST_IMPL_REVIEW', 'CLEANUP']:
            broker = Broker(self.root, phase)
            try:
                self.assertEqual(broker.request(dict(op='read', path='src/app.py'))['content'], 'old')
                for request in [dict(op='mkdir', path='created'),
                                dict(op='delete', path='src/app.py', expected=digest(b'old')),
                                dict(op='put', path='created', content='x', expected=None)]:
                    with self.subTest(phase=phase, op=request['op']), self.assertRaises(Denied):
                        broker.request(request)
            finally:
                broker.close()

    def test_unknown_phase_and_extra_fields_denied(self):
        with self.assertRaises(Denied):
            Broker(self.root, 'TYPO')
        with self.assertRaises(Denied):
            self.broker.request(dict(op='read', path='src/app.py', cwd='/'))
        for value in [None, [], 'shell']:
            with self.assertRaises(Denied):
                self.broker.request(value)

    def test_special_files_size_and_executable_mode(self):
        os.mkfifo(self.root / 'fifo')
        with self.assertRaises(Denied):
            self.broker.request(dict(op='read', path='fifo'))
        with self.assertRaises(Denied):
            self.put('huge', content='x' * (MAX_CONTENT + 1))
        self.assertFalse((self.root / 'huge').exists())
        os.chmod(self.root / 'src/app.py', 0o755)
        self.put('src/app.py', expected=digest(b'old'))
        self.assertEqual((self.root / 'src/app.py').stat().st_mode & 0o7777, 0o755)
        self.assertFalse(list(self.root.glob('**/.broker-*')))

    def test_command_requests_cannot_supply_shell_argv_env_or_config(self):
        commands = Commands(self.root, self.root)
        for request in [dict(op='shell', command='id'), dict(op='test', argv=['sh']),
                        dict(op='test', env={'AGENT_PAT': 'x'}),
                        dict(op='test', cwd='/'), dict(op='test', timeout=0),
                        dict(op='test; id'), dict(op='test', rules='Bash(*)')]:
            with self.subTest(request=request), self.assertRaises(Denied):
                commands.request(request)


if __name__ == '__main__':
    unittest.main(verbosity=2)
