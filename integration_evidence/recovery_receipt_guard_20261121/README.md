# PR15 recovery acknowledgement fail-closed guard — 2026-11-21 JST

Scope: isolated review branch `review/pr15-authenticated-crf-integration-20261116` only; parent `cc9f12998462cf52aa71bc56e4485abee1aeefc2`.

## Finding (code-level reproduction)
Prior `isolated_recovery_ui.render` treated the aggregate `recovery.state == SAVED` and per-item `state == SAVED` as sufficient to show an audit-success message and mark a browser attempt complete. A synthetic response with `audit_verified: false` therefore released the `_recovery_blocks_new` guard. The local negative regression failed on the previous code, then passed with a fail-closed check.

## Fix
- Require exact case/CRF/visit `record_key`, nonempty unique UUIDs, strictly positive integer Version (not booleans/floats) and explicit `audit_verified is True` before showing a SAVED receipt.
- Reject empty/malformed/mixed SAVED aggregates rather than clearing the block.
- After rechecking a same-UUID retry, validate the full recovery response before announcing success.
- Mark an in-browser frozen attempt complete only when its UUID *and* case/CRF/visit/record_key match the verified response.
- Do not change the backend, signing primitives, existing formal CRF Version history or clinical validation rules.

## Evidence and limitations
- Local, isolated Python test reproduction with entirely fictional `JUOG-901/902` and intercepted adapter: prior false-success case FAILED as expected; equivalent guarded implementation passed 11 targeted unit tests in the local developer container, Python 3.13.5 (mocked transport; no network).
- Existing repository recovery tests updated for the real GAS `record_key` response contract; four additional offline test methods added.
- These results are **NOT** the historical Python 183 + GAS 40 full-suite rerun, hosted GitHub Actions, independent QA, or live browser/GAS/Sheets E2E. Do **not** increment formal UAT PASS.
- Formal baseline remains PASS 0 / FAIL 0 / BLOCKED 74 / NOT RUN 0.
- No main, production, existing TEST, Stage 1, S2-01, GAS, Sheets, Streamlit runtime, ACL, credentials or email changes.

Next: execute the full `python run_offline.py` and isolated workflow on the exact new branch SHA; then seek independent QA and individually authorized fixture setup before live UAT. Previous environment preparation approvals must not be requested again.
