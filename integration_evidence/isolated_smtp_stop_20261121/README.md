# PR15 isolated SMTP hard-stop — 2026-11-21 JST

## Starting evidence / concurrent-state guard
- Branch `review/pr15-authenticated-crf-integration-20261116` HEAD at inspection: `97f00719ae656438b1e59bd158df2d62b67c5369`; main independently read as `c5580662be09f914cad372aa4e4df0ed62cdf2e8`.
- PR #15 remains Draft, head `73a4556b24291cb36e8800c4a99b372b5c30b759` (not changed in this isolated branch).
- Prior fix `97f0071` and evidence `integration_evidence/recovery_receipt_guard_20261121/README.md` reviewed and left untouched.
- Hosted Actions list returned no workflow runs for this isolated review commit. Last listed workflow was 2026-11-16 and was unrelated to this branch.

## New code finding
In `juog_crf_save_ui.submit_crf_with_feedback`, after an *initial* confirmed CRF save (`existing=False`), the helper still imported `juog_common.send_email` and invoked SMTP. This contravened the candidate profile's `notificationsDisabled:true` requirement and the explicit prohibition on outgoing messages. The GAS flag alone cannot stop Streamlit's independently initiated SMTP.

## Isolated review-only patch
- Remove `send_email` from the import list and the first-commit SMTP branch entirely.
- Both first commit and idempotent replay now set `mail_status="disabled"` and show that no email is dispatched during isolated UAT; they must not report `sent`, `failed` or `unconfirmed`.
- Retain the exact audited CRF receipt validation, immutable UUID/version policy, append-only saves, and the existing separately routed draft cleanup. No backend, email address, approval profile or notification setting is changed.
- Adjust the mock tests that previously expected one email and add explicit first-save and replay no-SMTP test methods to `tests/test_crf_save_ui.py`.
- The helper is part of the existing integrated Streamlit fixture. This patch is not permission to deploy it or enable the disabled profile.

## Verification status / limitations
- Code-level direct path verified: no `send_email` symbol/import remains in `juog_crf_save_ui.py`; every successful initial/replay path now uses `mail_status="disabled"`.
- Added offline tests have **not** been executed by this GitHub-connector-only run: the repository was read through GitHub, but container `git ls-remote` failed with DNS resolution and there is no authorized GitHub Actions dispatch in this connector. Static review is not a regression PASS.
- The earlier Python183/GAS40 suite values remain historical offline records, not rerun. Formal UAT remains PASS 0 / BLOCKED 74, independent QA absent.
- No actual email, GAS/Sheets, patient data, external transport, deployment, production/test, protected app, main, or PR head was accessed for mutation.

## Next
Retrieve exact commit in a testing environment with repository clone access; run `python run_offline.py` (including `tests/test_crf_save_ui.py`) and verify the isolation endpoint mail flag, then progress genuine approved standalone TEST01 browser+GAS+Sheets UAT and independent QA. Previous setup approvals are not requested again.
