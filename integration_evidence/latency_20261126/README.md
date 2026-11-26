# Initial-save expiry: bounded I/O reduction candidate

Base: f61caa77cbbd8266d568b7a813ccd8278999d4c8, existing isolated development branch. No deployment or environment changes in this revision.

Live evidence remains in `../live_20261126_30d/`: initial AUTH_EXPIRED after CRF/audit persistence, recovered with the original UUID and Version 1 unchanged. This candidate does not establish that the live failure is fixed.

## Change

- `isolated_crf_endpoint.gs`: retain the already opened workbook handle only for the lifetime of one locked request, and clear it in finally on success or failure. Do not retain sheet data or authorization decisions. Journal append now reuses the already verified pre-append table handle instead of reading the entire table again simply to obtain its handle. Fresh post-append verification and both authorization guards remain.
- `05_registry_google_apps_script.gs`: reuse that request-local workbook handle; continue reading SPREADSHEET_ID and reject a binding change. Calls outside the isolated request retain their previous behavior.
- `integration_tests/test_endpoint.cjs`: four regression groups for one open per request, rejection cleanup/ID binding, fresh journal verification and exact live-shaped expiry after the audit append followed by same-UUID recovery.

On the same fictional first-save fixture, instrumented offline service call counts changed from 5 to 1 workbook opens and from 7 to 5 operation-table reads. ACL reads remained 12, B2 session reads 15, owner reads 9, and Registry reads 11. See `rpc_counts.json`. These are API counts, **not measured live latency**. No cell cache, relaxed assertion expiry, removed guard, weaker ACL, automatic retry or mail sending was introduced.

## Validation

`../.venv/bin/python run_offline.py`: Python 204 tests (76 + 20 + 43 + 65), GAS endpoint 46 groups, existing GAS audit-repair suite, and 14 identity cases passed. Logs and summary included. Existing Actions entry can rerun the same suite; no hosted Actions outcome is claimed here.

## Remaining live step and safety boundary

Individual approval is required to apply these **two GAS files only** to the existing isolated project and update its existing deployment to the new version (same deployment URL, project, Sheet, permissions, secrets and notifications-disabled policy). Do not create an app or deployment URL. Before mutation compare current project sources against the existing reviewed version; preserve any intervening change. Record the prior deployment version for rollback; rollback means switching the same deployment back, never reverting CRF/audit/operation rows or the B2 head.

After approved deployment, recheck backend identity and JUOG-901 Version 1 recovery status, then test a reasoned Version 2 correction with a new UI-generated UUID, preserving Version 1. Record elapsed time, UI response, CRF/audit/journal consistency and any expiry. Do not erase Version 1 to manufacture another initial-save test. A fresh first-save repetition requires a separately authorized fictional case/visit. If expiry persists, keep the recorded INTENT and reconcile the original UUID; never raise the 15-second limit to hide it.

Existing start-before-UAT QA approval is acknowledged and is not being re-requested. This new implementation delta is not represented as already independently reviewed. Formal UAT PASS delta: 0. Initial-save reliability remains unresolved until live retest; formal result decisions are not fabricated.
