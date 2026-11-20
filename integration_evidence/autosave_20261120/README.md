# Section autosave implementation — offline only

Base: `c23e4edc99efd6e397c9728a5d80452a21f73b7c`, isolated integration branch. Remote HEAD was verified; local files were checked against its Git blobs (only known terminal-newline/CRLF transport differences). No unexplained edits were present. No live deployment, connection, ACL, Sheets or mail changes in this work.

## Implemented behavior

- Existing 30d / 90d / follow-up pages have 4 / 6 / 7 input-section containers. A nested one-second status fragment observes committed widget state; it waits two seconds after the last change before sending only the changed section. Other sections are not rerendered for that section's network request. Text widgets commit on Enter or blur: unsent keystrokes and changes made immediately before closing the tab cannot be promised durable. The UI explicitly tells the user to check the saved status before closing.
- Saving adds a translucent CSS overlay to the one section, displays 保存中, then removes the overlay in `finally`. Only a matching verified response displays 保存しました. Failure displays 保存できませんでした and retains an immutable operation ID/data/expected revision. No automatic retry loop; the explicit retry signs a fresh assertion for the same operation.
- No artificial case registration or official Version is created by autosave. A draft section is one append-only `SECTION_SAVE` event in existing `R1_DraftEvents`: data and audit are the same verified record. CAS revision is per case/type/visit/section/official-version epoch. Same operation replay is idempotent; different payload/actor, stale tab or competing same-revision operation is rejected. Older official-version draft history is retained but not restored over a newer official CRF.
- The existing signed endpoint dispatches `get_sections`/`save_section` only after OIDC-derived signature, B2 expiry/revocation, facility ACL and case ownership checks under ScriptLock. It checks owner again at the append boundary. Pending official-save intent blocks draft operations for that visit. No legacy token fallback is added.
- Server reconstruction after browser loss returns the latest audited sections for the authenticated owner, exact case and visit. The existing app has a resume/switch panel. It rechecks server authorization before clearing/loading form state, preserves dates/null/0/false/empty values and refreshes 30d linkage for subsequent pages. A change of identity/auth epoch clears prior form and pending section state. Server data cannot restore arbitrary auth/session keys: both server and UI use an exact generated allowlist.
- Existing manual whole-draft controls were removed from these three pages to avoid two competing save mechanisms. Legacy draft APIs/rows remain intact for backward compatibility; no historical data migration or deletion was attempted. The preflight fixture's legacy CRF_Drafts was header-only. Existing official save/recovery/Version paths are retained.

## Evidence and limitations

Final regression: **180 Python tests PASS** (165 existing + 15 new), **40 GAS integration groups PASS** (31 existing + 9 new), existing GAS repair regression PASS and 14 identity cases PASS. Clinical differential: **8,062 cases, zero differences**, 254 conditions reached. Both generators reproduce unchanged output. See results.json and the existing suite logs. Auth/signature/session primitives are byte-identical to c23e4ed. Hosted Actions were not dispatched; the workflow is ready for a manual run on this branch.


`test_autosave.py` covers debounce boundaries, frozen retries, receipt mismatch/audit denial, typed values, hidden-field removal, unchanged sections, malformed replies and restore-key isolation. `test_autosave_ui.py` runs all three real page files through Streamlit AppTest, checks only-changed-section requests, fresh-session resume, failed-save feedback/overlay cleanup and identity-change purge. These are offline component tests with explicit fictional transport doubles, not real browser or GAS UAT.

The GAS suite executes actual auth/session/endpoint source with in-memory Google services. New section groups cover append/replay, lost response, silent write failure, all nine visits, ownership/session rejection, stale revisions, official-version transitions and corrupted journal refusal. Existing official v1/v2, UUID, audit, auth and clinical suites remain in the runner. CI checks both generated clinical validators and section allowlists for drift before running all offline suites.

Clinical validation functions for all three pages are identical to the baseline (254 conditions); only source locations/widget inventory changed after the UI controls/layout changed. Generated artifacts were refreshed. The 2026-09-16 first-edition source document was located in existing user-uploaded material; `protocol_source.json` records its identity and SHA-256. A cover/date match is not an independent approval or full clinical-condition review. No clinical rule was inferred or changed.

Real overlay appearance/timing, actual browser closure during network I/O, authenticated runtime restore, notification success/failure, and all formal UAT remain unverified until coordinated candidate deployment and existing fixture switch. The profile remains disabled. A complete datastore rollback/truncation detection scheme is not claimed by per-row draft hashes; database permissions and independent audit/backup review remain required.

## UAT dependency order

All 74 existing IDs are retained; no new formal PASS is claimed. `UAT_MAPPING.csv` now assigns each ID prerequisites and an execution order:

| Order | Items | Execution prerequisites |
|---|---:|---|
| 1 | 4 | Reuse c23e4ed backups/writer-stop evidence; authorized runtime configuration and identity/schema verification; restore rehearsal |
| 2 | 5 | Verified TEST01 principal, renewed PI-specified ACL expiry, B2 initialization; authentication/denial tests |
| 3 | 9 | Owned fictional cases and signed endpoint; autosave/resume for each visit (later pages need saved 30d linkage) |
| 4 | 18 | Clinical original/254-condition conformity review; negative inputs and 30d linkage |
| 5 | 9 | Validated first formal saves; 30d first, then 90d and seven later visits |
| 6 | 26 | Corresponding v1; correction/replay/communication faults, concurrent requests, audit and privacy evidence |
| 7 | 2 | Specifically designated test mailbox and scoped mail authorization |
| 8 | 1 | Independent QA reviews complete mandatory evidence |

This is a dependency graph, not a requirement to finish every order-3/4 visit before 30d-V1: execute 30d input/negative checks, then 30d-V1 to unlock later visits, and proceed per-case/visit prerequisites. Development/offline regression is not blocked on naming a QA reviewer. Deployment gates/ACL renewal are not bypassed.

Completed backup and old-writer-stop actions were not repeated. Required human decisions remain the real TEST01 principal and new ACL expiry, clinical conformity review, independent QA designation/decision, and mail recipient/sending scope. Coordinated runtime changes need their applicable approval prerequisites; this commit does not perform them.
