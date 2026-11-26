# Fresh-signature read-only save reconciliation

Candidate handles AUTH_EXPIRED / lost transport response only for save_crf. It never retransmits a write. recovery_status must authenticate again and match exact UUID, payload digest, record key, expected Version+1 and audit. request_status then authenticates independently and returns the original COMMIT receipt, checked for the same fields and pinned workbook. Any mismatch remains uncertain and blocks new submission; revoked/denied sessions do not trigger reconciliation. The 15-second assertion and B2/ACL/owner guards are unchanged.

Python 210 tests, GAS integration 47 groups and existing GAS suites: all 7 offline suites exit 0. Formal UAT PASS delta 0. Live verification pending.

The existing isolated fixture deployment may receive exactly streamlit_app.py, isolated_autosave_ui.py and isolated_crf_adapter.py from the review candidate. No profile, secrets, ACL, main, production, clinical rules or new app changes. Prior fixture HEAD 185001376644d48f6c6dee4a7843082cc7597248 is the rollback source. The user explicitly requested reflection into the existing isolated Streamlit and live verification; this deployment artifact is not a separate development line.
