"""Exercise actual HTTP boundaries on an ephemeral loopback port; no browser or saved keys."""
import http.client
import importlib.util
import json
import threading
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).resolve().parents[1] / 'tools/live_server.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class SessionRecoveryTests(unittest.TestCase):
    def test_restart_preserves_separate_private_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'session.json'
            first=bridge.load_session(path,8766)
            self.assertNotEqual(first['token'],first['page_token'])
            self.assertEqual(bridge.load_session(path,8766),first)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertNotEqual(bridge.load_session(path,8767)['page_token'],first['page_token'])

    def test_legacy_session_migrates_without_rotating_control_token(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'session.json'
            old={'url':'http://127.0.0.1:8766','token':bridge.TOKEN}
            path.write_text(json.dumps(old))
            migrated=bridge.load_session(path,8766)
            self.assertEqual(migrated['token'],old['token'])
            self.assertEqual(bridge.load_session(path,8766),migrated)

    def test_bad_credentials_fail_closed_without_rewriting_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'session.json'
            for value in ('short',7,bridge.PAGE_TOKEN):
                original=json.dumps({'url':'http://127.0.0.1:8766','token':value,'page_token':bridge.PAGE_TOKEN})
                path.write_text(original)
                with self.assertRaises(ValueError):bridge.load_session(path,8766)
                self.assertEqual(path.read_text(),original)


class BridgeHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = bridge.ThreadingHTTPServer(('127.0.0.1', 0), bridge.Handler)
        bridge.PORT = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def request(self, path='/call', body=None, headers=None, method='POST'):
        conn = http.client.HTTPConnection('127.0.0.1', bridge.PORT, timeout=2)
        auth = {'Authorization': 'Bearer ' + bridge.TOKEN, 'Content-Type': 'application/json'}
        auth.update(headers or {})
        try:
            conn.request(method, path, json.dumps({} if body is None else body), auth)
            response = conn.getresponse()
            raw = response.read().decode()
            return response.status, json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw
        finally:
            conn.close()

    def test_only_expected_host_and_origin(self):
        for headers in ({'Origin': 'https://unrelated.example'}, {'Host': 'unrelated.example'}):
            self.assertEqual(self.request(headers=headers), (403, {'error': 'ORIGIN'}))

    def test_page_and_control_credentials_are_separate(self):
        self.assertEqual(self.request(headers={'Authorization': 'Bearer ' + bridge.PAGE_TOKEN}), (403, {'error': 'AUTH'}))
        self.assertEqual(self.request(path='/poll', body={'session': 'test'}), (403, {'error': 'AUTH'}))

    def test_malformed_shapes_return_bounded_errors(self):
        for body in ([], 4, 'text'):
            self.assertEqual(self.request(body=body), (400, {'error': 'INVALID_JSON'}))
        self.assertEqual(self.request(body={'name': []}), (400, {'error': 'UNKNOWN_TOOL'}))
        self.assertEqual(self.request(body={'name': 'nr_observe', 'args': []}), (400, {'error': 'INVALID_ARGS'}))
        self.assertEqual(len(bridge.PENDING), 0)

    def test_commands_require_observation_and_global_tools_are_absent(self):
        self.assertEqual(self.request(body={'name': 'nr_command', 'args': {}}), (400, {'error': 'OBSERVATION_REQUIRED'}))
        self.assertEqual(self.request(body={'name': 'set_health'}), (400, {'error': 'UNKNOWN_TOOL'}))

    def test_home_serves_game_but_never_control_credential(self):
        code, html = self.request(path='/', method='GET')
        self.assertEqual(code, 200)
        self.assertIn('NRCircuits', html)
        self.assertIn(bridge.PAGE_TOKEN, html)
        self.assertNotIn(bridge.TOKEN, html)
        self.assertEqual(self.request(path='/tools/.live-session.json', method='GET'), (404, {'error': 'NOT_FOUND'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
