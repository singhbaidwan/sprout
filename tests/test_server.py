import http.client
import json
import threading
import unittest

from farm.engine import new_state
from farm.server import create_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        defaults = {'Content-Type': 'application/json'}
        defaults.update(headers or {})
        body = json.dumps(data) if data is not None else None
        connection.request(method, path, body, defaults)
        response = connection.getresponse()
        content = response.read()
        result = response.status, dict(response.getheaders()), content
        connection.close()
        return result

    def test_bootstrap_and_assets(self):
        status, _, body = self.request('GET', '/api/bootstrap')
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data['state'], new_state())
        self.assertEqual(len(data['examples']), 4)
        for asset in ['/', '/app.js', '/farm.js', '/style.css', '/favicon.svg']:
            status, headers, body = self.request('GET', asset)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 100)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])

    def test_run_and_validation(self):
        status, _, body = self.request('POST', '/api/run', {'state': new_state(), 'code': 'harvest()'})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertIsNone(result['error'])
        self.assertEqual(result['frames'][0]['state']['coins'], 25)
        status, _, _ = self.request('POST', '/api/validate', {'state': {'invalid': True}})
        self.assertEqual(status, 400)

    def test_unlock_endpoint(self):
        state = new_state(); state['coins'] = 80
        status, _, body = self.request('POST', '/api/unlock', {'state': state, 'item': 'carrot'})
        self.assertEqual(status, 200)
        self.assertIn('carrot', json.loads(body)['state']['unlocked'])

    def test_portable_save_endpoint(self):
        legacy = {'version': 1, 'state': new_state(), 'code': 'harvest()', 'speed': '2'}
        status, _, body = self.request('POST', '/api/save/validate', {'save': legacy})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['save']['games']['classic']['state'], new_state())
        status, _, _ = self.request('POST', '/api/save/validate', {'save': {'version': 99}})
        self.assertEqual(status, 400)

    def test_rejects_cross_origin_and_unknown_hosts(self):
        for headers in [{'Origin': 'https://example.org'}, {'Host': 'evil.example:8000'}]:
            status, _, _ = self.request('POST', '/api/run', {'state': new_state(), 'code': 'harvest()'}, headers)
            self.assertEqual(status, 403)

    def test_only_public_assets_are_served(self):
        for path in ['/run.py', '/farm/engine.py', '/docs/REQUIREMENTS.md', '/../README.md', '/api/nope']:
            status, _, _ = self.request('GET', path)
            self.assertEqual(status, 404)

    def test_request_limits_and_wrong_content_type(self):
        status, _, _ = self.request('POST', '/api/run', {'code': 'x' * 100001})
        self.assertEqual(status, 413)
        status, _, _ = self.request('POST', '/api/run', {}, {'Content-Type': 'text/plain'})
        self.assertEqual(status, 415)
        status, _, _ = self.request('POST', '/api/run', [])
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
