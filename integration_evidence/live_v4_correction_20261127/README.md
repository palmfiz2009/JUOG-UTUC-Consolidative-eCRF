# Live Version4, reconnection, section save, correction restart

Existing fixture ea16982eca4ae637d49b33378414dfb5a9b4a04a, review c50d4c947334be333450fa1ee329122172f7f4af, GAS Version9. Fictional JUOG-901 / TEST01 / 9m only; no external email.

- A real connection-unconfirmed stop was observed. Input-preserving reconfirmation returned to the same case, correction reason and evaluation date without logging out. The raw error code was not captured; do not attribute this observation specifically to AUTH_EXPIRED.
- Initial draft sections required explicit same-operation-ID reconfirmation after uncertain responses. Eventually all seven showed saved and all seven persisted under record_version3.
- Changing only cystoscopy detail produced exactly one SECTION_SAVE (section2 revision7); all preceding 180 draft rows unchanged. UI showed a local saving overlay, then cleared it. This is actual changed-section behavior, not just offline coverage.
- One formal submit produced Version4 UUID abe66e59-5876-4d76-ac79-27d156bf5440. Automatic canonical recovery confirmed it; no manual recovery or relogin during this formal save. Observed elapsed120.596s includes tool/observation overhead; server INTENT-to-COMMIT42.941s.
- Independent connector reads: exactly one added CRF, one audit, one INTENT/COMMIT pair; expectedVersion3; receipt existing:true/version4/audit_verified:true. Original rows unchanged. Payload/UUID/key/version and journal hashes all verified. Raw insertion-order payload digest used, matching GAS JSON.stringify (not sorted-key canonicalization).
- After clicking correction restart, fresh 30d linkage version5 appeared without pressing manual linkage fetch. JUOG-901, detail「完全架空UAT：Version 4・訂正再開の入力保持確認」and all four dates2026-10-10 were retained. Correction reason alone reset to empty; UI showed one missing required item. No Version5 submitted.

Remaining: lengthy sequential autosave/formal-save latency, intermittent unconfirmed draft replies, browser-loss resume remeasurement underway. Seven-section draft correctness does not establish different-principal/other-facility denials or all visit coverage. Full formal UAT remains PASS1/BLOCKED73; no new independent-QA decision invented.

All code regressions: Actions46030973238 PASS, Python245 (76+20+43+106), GAS60groups, existing audit/identity suites. Source-linkage prior failed run46030106168 recorded; route-specific page mocks corrected and full suite passed before deployment.
