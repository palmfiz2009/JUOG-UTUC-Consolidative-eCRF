"""Exercise the review screen with fake Streamlit and transport. No network."""
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

TARGET = Path(__file__).parent / "python_candidate" / "streamlit_acl_review.py"

class Stop(Exception):
    pass

def screen(response=None, logged_in=True, clicked=True):
    st = ModuleType("streamlit")
    events, calls = [], []
    st.user = SimpleNamespace(is_logged_in=logged_in)
    st.set_page_config = lambda **k: None
    st.title = lambda *a: None
    st.info = lambda *a: None
    st.button = lambda *a, **k: clicked
    st.login = lambda provider: events.append(("login", provider))
    st.error = lambda message: events.append(("error", message))
    st.success = lambda message: events.append(("success", message))
    def stop():
        raise Stop()
    st.stop = stop
    client = ModuleType("streamlit_unified_client")
    def post(*args):
        calls.append(args[1])
        if isinstance(response, Exception):
            raise response
        return response
    client._post = post
    with patch.dict("sys.modules", {"streamlit": st, "streamlit_unified_client": client}):
        try:
            runpy.run_path(str(TARGET), run_name="__main__")
        except Stop:
            pass
    return events, calls

class ScreenContract(unittest.TestCase):
    def test_case_unselected_valid_facilities(self):
        events, calls = screen(dict(ok=True, user_id="fixture", role="facility",
                                    facilities=["FIXTURE"], facility_code=None))
        self.assertTrue(any(e[0] == "success" for e in events))
        self.assertEqual(calls, ["ui_context"])

    def test_invalid_acl_response_stops(self):
        for response in [
            dict(ok=False), None, dict(ok=True, user_id="", role="admin"),
            dict(ok=True, user_id="fixture", role="unknown"),
            dict(ok=True, user_id="fixture", role="facility", facilities=[]),
            dict(ok=True, user_id="fixture", role="facility", facilities=[" "]),
            dict(ok=True, user_id="fixture", role="facility", facilities="FIXTURE"),
        ]:
            with self.subTest(response=response):
                events, calls = screen(response)
                self.assertTrue(any(e[0] == "error" for e in events))
                self.assertFalse(any(e[0] == "success" for e in events))
                self.assertEqual(calls, ["ui_context"])

    def test_unauthenticated_does_not_send(self):
        events, calls = screen(logged_in=False)
        self.assertEqual(calls, [])
        self.assertIn(("login", "google"), events)

    def test_no_click_no_request(self):
        events, calls = screen(clicked=False)
        self.assertEqual(calls, [])

    def test_auth_failure_or_uncertainty_no_retry(self):
        for error in [PermissionError("fixture"), TimeoutError("fixture")]:
            events, calls = screen(error)
            self.assertEqual(calls, ["ui_context"])
            self.assertTrue(any(e[0] == "error" for e in events))
            self.assertFalse(any(e[0] == "success" for e in events))

if __name__ == "__main__":
    unittest.main(verbosity=2)
