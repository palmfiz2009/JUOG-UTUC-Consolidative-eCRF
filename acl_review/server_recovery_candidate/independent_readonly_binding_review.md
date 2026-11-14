# Independent technical review: read-only request/record binding

Disposition: no blocking defect found in the targeted binding and diagnostic changes. This is independent technical review plus offline verification, not formal QA, authorization to activate/deploy, or proof of live data reconciliation. No live environment, credentials, raw clinical data or identity values were accessed. All verification used local source and synthetic fixtures.

## Reviewed behavior

readonly_probe.py requires expected_record_version to be an actual nonnegative Python int, excluding booleans, floats and strings. Request operation IDs and submission IDs must have the approved bounded syntax and be unique within the listed requests. Records must have unique submission IDs and an exact contiguous positive integer version sequence, which also rejects duplicate versions. Each SAVED/COMMITTED request must bind to a record with the same submission ID and version equal to expected_record_version + 1. A FAILED or UNFINISHED request sharing a saved record submission ID rejects instead of reporting successful reconciliation. These changes fail closed for the stated structural binding requirement.

The existing request_status confirmation remains required for each listed operation and checks operation ID, save_crf action, state and phase. The probe emits metadata and hashes, excluding raw operation/submission IDs and clinical payload. It makes only list_requests, request_status and read_crf business-read calls; it does not prepare, execute or save business operations. Normal authenticated read calls can still append session bookkeeping events, so business_writes=0 must not be represented as no server-side writes of any kind.

The pinned SHA matches the local, undeployed runtime-snapshot recovery candidate exactly:

`5b7c086bee4afe98efc8c140204110765f9f8b534422e4ebe273bd85c2a89fbe`

The configuration SHA comparison is a local activation allowlist, not remote source attestation. It does not prove which version a remote endpoint is running. No deployment or activation was performed here.

The auth_diagnostics.py addition recognizes only the literal CONFIGURATION_CHANGED error code. It neither returns the raw server message nor exposes unknown error text. It grants no permissions and causes no automatic retry. Existing response/transport error sanitation remains intact.

## Limits that remain explicit

- This is submission/version structural binding, not clinical-content equality or audit-chain reconciliation. content_sha256 is validated as digest-shaped and reported; it is not recomputed against the returned clinical record by this probe. The explicit manual_submission_content_audit_reconciliation_required=true remains necessary.
- Legacy records without corresponding listed requests remain permitted for manual reconciliation. The listing is not proven complete by this client alone.
- Separate signed reads are not a single atomic snapshot across listing, per-request status and record retrieval. Drift can reject or leave incomplete evidence; the client does not retry or repair it. A full reconciliation still requires controlled access and the existing human review.
- v3_correction_candidate means only that the latest contiguous record version is two. It does not constitute approval to write, certify that all requests are terminal, or replace the separate recovery execution gates.
- Some malformed deeply nested/unhashable metadata can raise a generic Python exception rather than a named PermissionError. The reviewed Streamlit wrapper catches all such exceptions, shows only its fixed failure message, and sets the halt flag; it does not reveal raw payload. No changed path bypasses that fail-closed boundary.

## Verification performed

- `python -m unittest test_readonly_probe test_readonly_binding`: 14 tests passed.
- `python -m unittest test_diagnostics`: 4 tests passed.
- Local SHA-256 verification matched the pinned recovery candidate above.

The 18 passing tests cover activation bounds, read-only call selection, output redaction, scope and nested failures, expected-version type checks, duplicate request/record submission IDs, SAVED record binding, noncommitted-record conflict, legacy records and fixed-vocabulary diagnostic behavior. They are synthetic unit checks, not live OIDC validation, endpoint version verification, old-key rejection evidence or whole-system QA.

Additional exact-source comparison: local `git show b33e:auth_diagnostics.py` differs from the candidate solely by insertion of CONFIGURATION_CHANGED into CODES. No other bytes changed. This verifies source comparison to that commit, not independent observation of its live deployment.
