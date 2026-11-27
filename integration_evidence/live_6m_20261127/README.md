# Live isolated 6-month CRF, 2026-11-27

Fully fictional JUOG-901 / TEST01 only. Existing fixture Streamlit, GAS Version 5, existing isolated Sheets; external notifications remain disabled. No production/main/other TEST changes.

All seven sections were automatically saved, independently read from R1_DraftEvents, then restored after a page reload/new Streamlit session. UI showed seven saved sections and complete input validation. Only changed sections 2 and 7 received subsequent revisions. The UI and saved payload referenced 30-day Version 4, UUID 803f0242-d57e-4c1b-801f-15fdf482d60e and operation date 2026-01-10.

Initial submission UUID ba70265d-15a6-4df6-a68a-816f150b7ed4 returned AUTH_EXPIRED with INTENT only. First manual canonical retry created the Version 1 CRF and audit but returned AUTH_EXPIRED without COMMIT. Reauthentication and a second authorized same-UUID retry produced COMMIT at 2026-11-27T12:48:34.310Z. Subsequent UI independently displayed Version 1 / same UUID / audit match. Direct Sheets reads confirmed one CRF row, one audit row, exact canonical payload and matching INTENT/COMMIT digest. No invented UUID or direct insertion of CRF/audit rows was used.

## Unresolved

Initial save and automatic recovery are not reliable: assertion expiry remains a major issue. The successful manual recovery does not resolve it. Sequential autosave/network processing delayed UI updates. Other visits, negative ownership/ACL cases, notification tests and independent QA adjudication are not established by this evidence. Formal UAT PASS delta is zero.

## Review-branch performance change (not deployed)

`isolated_recovery.gs` now uses one fresh CRF scan for rows and versions within the same read-only reconciliation under the single-writer lock. Previously a pending UUID caused a second scan of all three CRF tabs. No cache survives the request; no ACL/session verdict is cached; signature TTL, revocation, replay and ownership checks are unchanged. This removes three redundant CRF reads for a pending recovery, but live latency improvement is NOT YET MEASURED.

Offline regression: Python 229 (76 fixture + 20 bridge/entry + 43 PR + 90 integration), GAS 53 groups, legacy audit 13 groups and identity 14 cases passed. Initial new test fixture incorrectly expected no audit after deliberately dropping the CRF append; corrected fault injection expires immediately after INTENT instead. This tests the intended pending-INTENT boundary without relaxing authorization or rejection assertions. The full GAS suite was then rerun successfully. Existing Python/legacy suites were already successful and unchanged.
