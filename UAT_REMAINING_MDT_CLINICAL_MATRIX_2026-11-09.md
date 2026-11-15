# JUOG-UTUC01 — Remaining eCRF/EDC UAT and clinical integrity test matrix
**Assessed:** 2026-11-09 (JST). **Status:** Internal source review, not a validated release or GCP certification.

## Change-control statement
Production `main`, deployed services and actual TEST/production Google Sheets have not been modified by this assessment. All implemented fixes remain isolated in Draft PRs #4–#9, each separately branched from main. **Do not merge them independently until dependencies and conflicts are resolved in a disposable integration branch.** Only approved synthetic cases may be used for further tests.

## Confirmed new finding — central MDT review round mismatch (PR #9)
- `submitScreening_` first increments the active `Screening.review_round` when an application is resubmitted and then appends `ScreeningCRF`. The two writes are not transactional. If the latter fails, active round 2 can point to the stored CRF snapshot of round 1.
- `getScreeningCrf_` previously returned the latest saved snapshot by record_version without comparing the snapshot's `review_round` with current `Screening.review_round`.
- Draft PR #9 adds a fail-closed check that returns `SCREENING_CRF_ROUND_MISMATCH` instead of showing an outdated CRF under a newer review-round heading. 8/8 synthetic tests passed: GitHub Actions run **42606354522**.
- **Residual risk:** No automatic recovery is yet defined for a partially saved screening resubmission or missing `ScreeningAudit`. The fail-closed error requires staff review of the underlying rows.

## Further observed risks / owner decisions
| Priority | Finding / potential failure mode | Required UAT or decision |
|---|---|---|
| P0 | Common `JUOG_API_TOKEN` permits facility-facing API actions without per-user site-verified identity. | Design site-bound authenticated identity and authorization on the server; verify a user from site F11 cannot retrieve or change F12 data even with a guessed JUOG ID. Do not assume a claimed e-mail or facility code equals authentication. |
| P0 | `getBackendInfo_` classifies TEST vs PRODUCTION from the spreadsheet **name** containing 'TEST'. | Require pinned environment configuration and a verified spreadsheet ID before a real deployment; a renamed file must not silently change environment safety gates. No implementation until production/STAGING config is decided. |
| P1 | `submitScreening_` identifies retries by `submission_id` and returns an existing submission without an equivalent full identity/content collision check to `savePayloadToSheet_`. | Inject reused ID with a changed facility, local subject code, consent date or clinical content and verify fail-closed response; review safe retry / screening-audit recovery without overwriting earlier round. |
| P1 | `submitMdtReview_` generates a new `review_id` for each call; normal retry after ambiguous network success may return `REVIEW_ALREADY_SUBMITTED` rather than identifying the prior success. | Test client timeout after committed review, correction retry, duplicate correction, and clear user-facing receipt retrieval. |
| P1 | Central RECIST independence is central to the study; radiology must review imaging directly, not merely validate the site's RECIST. | For PR/CR/SD/PD/NE, adjudication, discordance, independent image retrieval and assessor access, test actual reviewer UI + API with role separation, source image identifiers, and consensus audit. |
| P1 | Screening/MDT finalization updates Screening/Registry/ScreeningAudit via multiple non-transactional Sheet operations. | Inject failure between every write and verify a second retry does not generate a new JUOG number, reuse a conflicting ID or lose review history. Staff repair workflow and audit reconciliation required. |
| P1 | Surgical timing protocol is principle of EVP last dose followed by surgery in **4–8 weeks**; delays with adverse events may require protocol-defined exception. | Test exactly 27, 28, 56, 57 days; confirm which are warning vs hard stop, and mandatory reason / deviation tracking. Do not hard-code clinical decisions from interpretation alone. |
| P1 | cN1-only Stage IV quota 20 includes `cT3 or below, cN1, cM0`; excludes `cT4N1M0` and `cT3N1M1`. | Test 19→20, at 20, concurrent 20th submissions, voided rows, missing Screening link, 41→42 total cap, SD threshold, and mixed cT4/cM1 diagnoses in active rows. |
| P1 | Synthetic 90d / 6m existing TEST rows have dates not yet elapsed in real time. | Conduct date-valid real TEST write via approved isolated clock/fixture; never backdate actual informed consent or loosen production validation to make a test pass. |
| P1 | PR #5 follow-up visit-specific draft deletion and PR #7 new required reporter e-mail delete signature conflict on integration. | Resolve client calls in reviewed integration branch; test 6m and 9m existing legacy drafts, unrelated reporter email, formal submission, and cleanup; retain original committed versions. |
| P1 | PR #6 audit retry fix covers same submission ID; automatic recovery when UI regenerates a different ID remains unresolved. | Test interrupted HTTP after CRF append, persisted request fingerprint, reconciliation of 30d/90d/followup to audit, and safe manual intervention, never delete records. |
| P2 | Browser/phone workflow: segmented Japanese date inputs, focus after rerun, back/forward, high-latency links and double taps. | Test iPhone/Safari and Android, keyboard, mobile width, offline/online, session expiration, two open tabs, network timeouts; assert no duplicate submissions or lost drafts. |
| P2 | Full restore/backup is unverified. Google Sheets API/script lock does not prevent direct spreadsheet editor changes. | Confirm editor restrictions, point-in-time export with checksums, retention, restoration to a separate TEST sheet, recoverability of drafts and append-only audit; document RPO/RTO and approval. |
| P2 | Names / medical record numbers may be entered into free-text values even though direct-identifier **keys** are forbidden. | Privacy threat model, input restrictions/education and redaction review for emails, logs, screenshots and CSV exports. |
| P2 | Endpoint environment and deployed revisions may differ from GitHub source. | Compare deployed Streamlit/GAS commit hashes and script properties before UAT and release; lock down TEST notification endpoints. |

## Additional test scenarios needed
- Non-radiologist review: adverse event Grade≥3 unrecovered, ECOG not 0–1, medical safety negative, resectability negative. Confirm eligibility/hold/ineligible paths against signed protocol and final consensus rule; never silently override an independent role.
- New image: missing file, wrong patient/session label, updated scan after radiologist's preliminary review, direct-image RECIST calculation and raw audit of uploaded image revision.
- CRF exceptions: surgery not performed, procedure abandoned, death before 30d, death between 30/90d, delayed imaging and missing blood tests, conversion/open surgery, intraoperative complications, discharge after 30d, and corrected surgery date invalidating downstream calculations.
- Sheet schema drift: missing columns/renamed tabs, invalid JSON in one historic record, duplicate `record_version`, non-numeric dates, edited formulas, accidental deleted audit row, duplicated screening ID across distinct facilities.
- Operational: stale browser or saved draft after backend schema version bump; 100 concurrent synthetic submissions with lock contention metrics; recovery of rejected/lost notifications without resending patient clinical data.

## Release gates, in order
1. Obtain an approved site identity and access-control design from the study office and security owner (P0).
2. Decide intended clinical **warning vs hard stop** on 4–8-week surgery window, roles' eligibility requirements, correction semantics, and exceptional patient trajectories.
3. Consolidate Draft PRs **#4–#9** on an integration-only branch pinned to main; keep all independently reviewed changes and resolve overlapping `.gs` and follow-up draft delete signatures. Run Python/Node/Playwright regression on the exact combined tree.
4. Verify environment IDs and out-of-band TEST SMTP isolation with a dedicated synthetic-only TEST GAS, Sheet and Streamlit app. Conduct genuine browser→GAS→Sheet end-to-end UAT with fresh synthetic IDs, versions, exact audit matching, wrong-site rejection, broken network and recoverability.
5. Conduct clinical UAT independent of code author, data integrity and account / spreadsheet permission review, backup restore simulation, documented deviation handling, source-data verification, owner sign-off.
6. **Only then** consider production release. Until then: HOLD.

## Evidence status
- Screen submission round guard: mock-level 8/8 checks passed, PR #9; **not deployed or real TEST validated**.
- Draft PRs #4–#8: prior synthetic test evidence in respective PRs, **not production release**.
- No claim of full GCP-equivalent validation or of the absence of defects.
