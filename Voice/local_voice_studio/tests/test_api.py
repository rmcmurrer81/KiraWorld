from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from .support import generic_voice
from kira_local_voice.api import assert_loopback_bind, make_handler
from kira_local_voice.errors import ValidationError
from kira_local_voice.service import LocalVoiceService


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = LocalVoiceService(Path(self.temp.name))
        self.service.register_voice(generic_voice())
        self.api_token = "a" * 64
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service, self.api_token))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.temp.cleanup()

    def request(self, method: str, path: str, payload=None, *, host="127.0.0.1", authenticated=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        body = None if payload is None else json.dumps(payload)
        headers = {"Host": host}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.api_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body.encode("utf-8")))
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        connection.close()
        return response.status, data, dict(response.getheaders())

    def test_loopback_bind_refuses_wildcard_and_hostname(self):
        for host in ("0.0.0.0", "example.com"):
            with self.subTest(host=host):
                with self.assertRaises(ValidationError):
                    assert_loopback_bind(host)
        assert_loopback_bind("127.0.0.1")
        with self.assertRaises(ValidationError):
            assert_loopback_bind("::1")

    def test_health_capabilities_and_voices(self):
        status, health, headers = self.request("GET", "/v1/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["local_only"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.request("GET", "/v1/capabilities")[0], 200)
        voices=self.request("GET", "/v1/voices")[1]["voices"]
        self.assertEqual(voices[0]["voice_id"], "calm-fallback")
        serialized=json.dumps(voices)
        for private in ("subject_id","authority","scope","evidence_sha256","reference_hashes"):
            self.assertNotIn(private,serialized)

    def test_every_route_requires_the_local_capability_token(self):
        for method,path,payload in (
            ("GET","/v1/health",None),
            ("GET","/v1/capabilities",None),
            ("GET","/v1/voices",None),
            ("POST","/v1/synthesis-jobs",{"text":"private","voice_id":"calm-fallback"}),
        ):
            with self.subTest(path=path):
                status,body,_=self.request(method,path,payload,authenticated=False)
                self.assertEqual(status,401)
                self.assertEqual(body["error"]["code"],"authentication_required")

    def test_create_and_poll_job(self):
        status, submitted, _ = self.request(
            "POST",
            "/v1/synthesis-jobs",
            {"text": "Local hello", "voice_id": "calm-fallback", "output_name": "api-test"},
        )
        self.assertEqual(status, 202)
        done = self.service.jobs.wait(submitted["job_id"])
        status, fetched, _ = self.request("GET", f"/v1/jobs/{done.job_id}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["state"], "succeeded")
        serialized=json.dumps(fetched)
        self.assertNotIn("Local hello",serialized)
        self.assertNotIn(str(self.service.data_root),serialized)
        self.assertNotIn("sha256",serialized)
        self.assertNotIn("metadata_keys",serialized)

    def test_host_header_rejects_dns_rebinding_shape(self):
        status, payload, _ = self.request("GET", "/v1/health", host="evil.example")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "validation_error")

    def test_bad_content_type_and_unknown_route_are_structured(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(
            "POST",
            "/v1/synthesis-jobs",
            body="{}",
            headers={"Host": "127.0.0.1", "Authorization":f"Bearer {self.api_token}",
                     "Content-Type": "text/plain", "Content-Length": "2"},
        )
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.read())["error"]["code"], "validation_error")
        connection.close()
        self.assertEqual(self.request("GET", "/missing")[0], 404)

    def test_unknown_fields_and_wrong_json_types_are_rejected(self):
        status,payload,_=self.request("POST","/v1/synthesis-jobs",
            {"text":"hello","voice_id":"calm-fallback","unknown":True})
        self.assertEqual(status,400); self.assertEqual(payload["error"]["code"],"validation_error")

    def test_duplicate_keys_and_nonfinite_json_numbers_are_rejected(self):
        for body in (
            '{"text":"one","text":"two","voice_id":"calm-fallback"}',
            '{"text":"hello","voice_id":"calm-fallback","speed":NaN}',
        ):
            connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=3)
            connection.request("POST","/v1/synthesis-jobs",body=body,headers={
                "Host":"127.0.0.1","Authorization":f"Bearer {self.api_token}",
                "Content-Type":"application/json","Content-Length":str(len(body.encode()))})
            response=connection.getresponse(); self.assertEqual(response.status,400)
            self.assertEqual(json.loads(response.read())["error"]["code"],"validation_error")
            connection.close()
        status,payload,_=self.request("POST","/v1/synthesis-jobs",
            {"text":"hello","voice_id":"calm-fallback","speed":"fast"})
        self.assertEqual(status,400); self.assertEqual(payload["error"]["code"],"validation_error")


if __name__ == "__main__":
    unittest.main()
