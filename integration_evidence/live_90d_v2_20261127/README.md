# Live 90-day Version 2 — fictional isolated UAT

Review code: 8472b536a75aa3a34eb3798eaedbf681cc43b7ae; fixture branch commit: 14b30ce119c166c8e5605c1d9ac516c6e2e86a8d; existing GAS Version 9. No production/main/TEST/Stage1/S2-01 changes, no ACL/Secrets changes, external notifications disabled.

The real Streamlit form for JUOG-901/TEST01/day90/90d used current 30-day Version 5 linkage (surgery 2026-01-10), evaluation/imaging/cystoscopy/last-alive dates 2026-04-10, Negative cytology, no PD/tumour, labs not performed, no new surgical complication or recurrence, observation-only treatment and alive. Correction reason is recorded in evidence.json.

Six input sections were server-drafted. Sections 2 and 6 initially reported an uncertain result; explicit same-operation-ID reconciliation succeeded. The form passed required/basic consistency validation. One formal-save click was performed, with no manual formal resend and no re-login during saving. The UI eventually displayed “保存しました：術後90日CRF／JUOG-901／Version 2” and canonical same-UUID recovery notice. At approximately 102.6 seconds after the click, draft cleanup was still in progress; this is an observation interval, not server-only timing.

Independent Google Sheets connector reads: CRF_90d 2→3 rows; CRFSubmissionAudit 12→13; R1_Operations 23→25 (counts include headers). UUID 624e77cf-72f7-464f-b43d-40842502e0f7. Exactly one new CRF and one audit row, expected Version 1→Version 2, original rows unchanged. INTENT 2026-11-27T16:46:03.778Z; COMMIT 16:46:44.048Z; delete_draft audit 16:47:14.635Z. Payload and operation hashes, owner/facility, source linkage and receipt agree: all 14 evidence checks true. Digest uses original JSON insertion order, matching GAS.

During preparation, the Apps Script executions UI showed a Version 9 doPost at 2026/11/28 01:35:27 JST lasting 207.097 seconds, completed; surrounding calls lasted roughly 2–14 seconds. DoPost status alone does not establish business-save success or identify the action. Intermittent latency/uncertain responses remain a defect, not a clean performance PASS. A safe allowlisted connection-code caption was deployed after review CI success to help separate lock/transport/assertion outcomes without disclosing raw errors or secrets.

Regression on 8472b53: GitHub Actions 46035491692 succeeded (Python 245; GAS 60 groups; legacy audit 13 and identity 14). This is offline evidence only.

Formal ledger remains PASS 1/BLOCKED 73. This adds measured evidence for 90d-D, 90d-V2, 90d-R and later draft cleanup, without inventing independent QA adjudication of this new result or claiming unperformed abnormal-input/different-owner/double-click tests. Prior user-reported QA approval remains preserved.
