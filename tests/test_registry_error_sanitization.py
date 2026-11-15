"""No raw network exception may be exposed by the registry client.

Entirely offline: fake Streamlit secrets and fake urlopen; no user data or network.
"""
from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from juog_common import registry_call


class RegistryExceptionBoundaryTests(unittest.TestCase):
    def fake_streamlit(self):
        return types.SimpleNamespace(
            secrets={"registry":{
                "url":"https://test-endpoint.invalid/exec",
                "token":"FICTIONAL-TOKEN",
            }},
            session_state={},
        )

    def test_transport_exception_never_contains_internal_information(self):
        value = "PRIVATE_FAKE_QUERY_TOKEN_OR_PATIENT_ID"
        with patch.dict(sys.modules, {"streamlit":self.fake_streamlit()}), \
             patch("urllib.request.urlopen", side_effect=RuntimeError(value)), \
             patch("time.sleep", return_value=None) as sleep:
            result = registry_call("save_crf", {"payload":{"data":{"fake":True}}}, timeout=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"],"REGISTRY_CONNECTION_FAILED")
        self.assertNotIn(value,str(result))
        self.assertEqual(sleep.call_count,2)

    def test_invalid_server_json_must_not_echo_response(self):
        fake_body = "FAKE_SENSITIVE_RESPONSE_BODY: not json"
        fake_reply = MagicMock()
        fake_reply.read.return_value = fake_body.encode("utf-8")
        fake_context=MagicMock()
        fake_context.__enter__.return_value=fake_reply
        with patch.dict(sys.modules, {"streamlit":self.fake_streamlit()}), \
             patch("urllib.request.urlopen", return_value=fake_context), \
             patch("time.sleep", return_value=None):
            result=registry_call("save_crf", {"payload":{}}, timeout=1)
        self.assertEqual(result["error"],"REGISTRY_CONNECTION_FAILED")
        self.assertNotIn(fake_body,str(result))

    def test_http_errors_return_only_status_code(self):
        fake_url = "https://test-endpoint.invalid/exec"
        err=urllib.error.HTTPError(fake_url,503,"FAKE_PRIVATE_ERROR_BODY",None,None)
        with patch.dict(sys.modules, {"streamlit":self.fake_streamlit()}), \
             patch("urllib.request.urlopen", side_effect=err), \
             patch("time.sleep", return_value=None):
            result=registry_call("save_crf", {"payload":{}}, timeout=1)
        self.assertEqual(result["error"],"HTTP_503")
        self.assertNotIn("FAKE_PRIVATE_ERROR_BODY",str(result))

    def test_missing_credentials_error_does_not_mention_secrets(self):
        fake=types.SimpleNamespace(secrets={},session_state={})
        with patch.dict(sys.modules, {"streamlit":fake}), \
             patch("urllib.request.urlopen") as urlopen:
            result=registry_call("save_crf", {"payload":{}}, timeout=1)
        self.assertEqual(result["error"],"REGISTRY_NOT_CONFIGURED")
        urlopen.assert_not_called()


if __name__=="__main__":
    unittest.main()
