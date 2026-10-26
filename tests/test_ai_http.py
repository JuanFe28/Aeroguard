import io
import json
import os
import secrets
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from PIL import Image
from ai_service.http_api import Handler


class MicroserviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = secrets.token_urlsafe(32)
        cls.env = patch.dict(os.environ, {"AI_SERVICE_TOKEN": cls.token})
        cls.env.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.env.stop()

    def request(self, method, path, body=None, authorized=True):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Authorization": "Bearer " + self.token} if authorized else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_health(self):
        status, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "aeroguard-ai-service")

    def test_requires_token(self):
        status, _ = self.request("POST", "/analyze", b"invalid", authorized=False)
        self.assertEqual(status, 401)

    def test_invalid_image(self):
        status, _ = self.request("POST", "/analyze", b"invalid")
        self.assertEqual(status, 400)

    def test_valid_image(self):
        buffer = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(buffer, "JPEG")
        status, body = self.request("POST", "/analyze", buffer.getvalue())
        self.assertEqual(status, 200)
        self.assertIn("confidence", body["result"])
        self.assertFalse(body["model_validated"])

    def test_unknown_endpoint(self):
        self.assertEqual(self.request("GET", "/unknown")[0], 404)
