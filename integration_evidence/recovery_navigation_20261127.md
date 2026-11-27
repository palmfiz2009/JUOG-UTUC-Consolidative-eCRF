# Recovery navigation: retain same-actor input

Observed in the existing fixture after 2021e887e92337536784288c351b4e1d5790c857: signed recovery successfully displayed 9m Versions 1/2/3 with UUID/audit matches. Independent connector reads found CRF_Followup (5 rows), CRFSubmissionAudit (11), R1_Operations (21) byte-for-byte equal to pre-navigation snapshots. No duplicate rows.

Defect: navigating recovery -> editor caused Streamlit widget cleanup to erase the subject and selected report page. The next edit check defaulted to 30d, requiring re-entry. This is not an ownership bypass, but blocks smooth resume.

Fix: preserve only allowlisted input in a same-actor navigation buffer before opening recovery; restore only after returning through a fresh successful signed ui_context. Never preserve authority/version/session assertions. Actor mismatch or halted identity consumes/discards backup without restoration. Logout, unauthenticated state and permanent denial clear the navigation buffer. Repeated opening while already in recovery cannot replace the buffer with empty widget state.

Targeted connection-state/entry tests: 16 PASS, including actual Streamlit widget cleanup, report-page/input retention, changed-actor/halt rejection. Whole-suite prior baseline: Python241/GAS60 on Actions46028701494 PASS. This adds 2 Python tests; hosted CI reruns all.

Deployment note: existing fixture update at 15:53:12 UTC logged a transient KeyError importing isolated_connection_feedback. Subsequent ordinary app rerun reached authenticated recovery and successfully verified all three saved versions; no server restart, secrets change or bypass was used. Keep this transient hot-update exception visible as a deployment observation, not a clean-start PASS.

Formal ledger remains PASS1/BLOCKED73. No new QA determination or full-row PASS inferred from these new observations.
