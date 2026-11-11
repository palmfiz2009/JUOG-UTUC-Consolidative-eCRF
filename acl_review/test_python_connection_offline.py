"""Offline only: synthetic identity, mocked transport, no Streamlit dependency."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent / "python_candidate"))
import auth_bridge
import streamlit_unified_client as client

class User(dict):
    is_logged_in = True

def fixture():
    user = User(iss="fixture-issuer", sub="fixture-sub", aud="fixture-client",
                exp=2000, auth_time=990)
    config = dict(oidc_issuer="fixture-issuer", oidc_client_id="fixture-client",
                  max_auth_age_seconds=3600, signing_key="fixture-key-not-real-" * 3,
                  bridge_issuer="fixture-bridge", audience="fixture-gas")
    return SimpleNamespace(user=user, secrets={
        "juog_identity_bridge": config,
        "unified_test": dict(enabled=False, release_approved=False,
            url="https://script.google.com/macros/s/FIXTURE_ONLY/exec",
            approved_url="https://script.google.com/macros/s/FIXTURE_ONLY/exec")
    }, session_state={})

class OfflineChecks(unittest.TestCase):
    def setUp(self):
        self.clock = patch("auth_bridge.time.time", return_value=1000)
        self.clock.start()
        self.transport = patch("streamlit_unified_client.urllib.request.urlopen",
                               side_effect=AssertionError("NETWORK_FORBIDDEN"))
        self.network = self.transport.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.transport.stop)

    def test_valid_identity_can_sign_without_network(self):
        result = auth_bridge.signed_request(fixture(), "ui_context", {})
        self.assertEqual(set(result), {"request_json", "identity_assertion"})
        self.network.assert_not_called()

    def test_unauthenticated_rejected(self):
        st = fixture()
        st.user.is_logged_in = False
        with self.assertRaises(PermissionError):
            auth_bridge.signed_request(st, "ui_context", {})

    def test_invalid_claims_rejected(self):
        for field, value in [("iss", "wrong"), ("sub", ""), ("aud", "wrong"),
                             ("exp", 999), ("auth_time", None),
                             ("auth_time", 1001), ("azp", "wrong")]:
            with self.subTest(field=field, value=value):
                st = fixture()
                st.user[field] = value
                with self.assertRaises(PermissionError):
                    auth_bridge.signed_request(st, "ui_context", {})

    def test_unapproved_configuration_never_sends(self):
        for enabled, approved in [(False, False), (True, False), (False, True)]:
            st = fixture()
            st.secrets["unified_test"].update(enabled=enabled, release_approved=approved)
            self.assertEqual(client._post(st, "ui_context", {}, 1)["error"],
                             "INTEGRATION_NOT_APPROVED")
        self.network.assert_not_called()

    def test_protected_deployment_never_sends(self):
        st = fixture()
        url = "https://script.google.com/macros/s/" + client.DENIED + "/exec"
        st.secrets["unified_test"].update(enabled=True, release_approved=True,
                                          url=url, approved_url=url)
        self.assertFalse(client._post(st, "ui_context", {}, 1)["ok"])
        self.network.assert_not_called()

    def test_missing_auth_time_never_sends(self):
        st = fixture()
        st.secrets["unified_test"].update(enabled=True, release_approved=True)
        del st.user["auth_time"]
        with self.assertRaises(PermissionError):
            client._post(st, "ui_context", {}, 1)
        self.network.assert_not_called()

    def test_endpoint_mismatch_never_sends(self):
        st = fixture()
        st.secrets["unified_test"].update(enabled=True, release_approved=True,
                                          approved_url="https://example.invalid/")
        self.assertFalse(client._post(st, "ui_context", {}, 1)["ok"])
        self.network.assert_not_called()

if __name__ == "__main__":
    unittest.main(verbosity=2)
