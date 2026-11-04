import unittest
from unittest.mock import patch
import json
from f01_docker_broker import command_for, run_command, SQL_ARGS, PS_ARGS

P = 'neroxa-02a3-12345-buyer'
DB = 'supabase_db_' + P


class BrokerTests(unittest.TestCase):
    def test_accepted(self):
        good = [
            list(PS_ARGS),
            ['inspect', DB],
            ['inspect', DB, '--format', '{{.Image}}'],
            ['exec', '-i', DB, *SQL_ARGS],
        ]
        for args in good:
            with self.subTest(args=args):
                self.assertIsInstance(command_for(args, P), tuple)

    def test_reject_escape(self):
        bad = [
            ['run', '--privileged', 'alpine'],
            ['exec', '-i', 'other', 'psql'],
            ['exec', '-i', DB, 'sh'],
            ['inspect', '/etc/passwd'],
            ['cp', 'secret', DB + ':/tmp/'],
            ['exec', '-i', DB, *SQL_ARGS, '--single-transaction'],
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                command_for(args, P)

    def test_reject_project(self):
        with self.assertRaises(ValueError):
            command_for(list(PS_ARGS), 'prod')

    @patch('f01_docker_broker.subprocess.run')
    def test_ps_filter(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = (
            json.dumps({'Names': 'supabase_db_' + P}) + '\n'
            + json.dumps({'Names': 'other_container'}) + '\n'
        ).encode()
        run.return_value.stderr = b''
        result = run_command(list(PS_ARGS), P, b'')
        import base64
        output = base64.b64decode(result['stdout']).decode()
        self.assertIn(P, output)
        self.assertNotIn('other_container', output)

    @patch('f01_docker_broker.subprocess.run')
    def test_inspect_labels(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps([
            {'Name': '/' + DB, 'Config': {'Labels': {'com.supabase.cli.project': P}}}
        ]).encode()
        run.return_value.stderr = b''
        self.assertEqual(run_command(['inspect', DB], P, b'')['rc'], 0)
        run.return_value.stdout = json.dumps([
            {'Name': '/' + DB, 'Config': {'Labels': {'com.supabase.cli.project': 'other'}}}
        ]).encode()
        with self.assertRaises(ValueError):
            run_command(['inspect', DB], P, b'')


if __name__ == '__main__':
    unittest.main()
