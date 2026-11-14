# Canonical 30-day CRF live input evidence (2026-11-14 UTC)

Formal UAT remains PASS32 / FAIL1 / BLOCKED29 / NOT RUN5. No business transmission or deployment performed.

## Newly observed
- User completed Google login. Signed ui_context visibly confirmed TEST01 / facility / AUTH_CONNECT / business writes prohibited.
- Canonical CRF, surgery-not-performed branch: fictional JUOG-971, fictional@example.invalid, EVP 2026-03-16, planned surgery 2026-04-13, visit/lab/alive date 2026-05-13, CRP=0, patient-preference reason, observation, alive.
- UI reported required-input/basic-consistency completion and 0 missing / 0 input errors.
- Clicking the explicitly non-sending preview generated a Version 9 signed request. UI explicitly states no transmission, save or ledger verification.
- Draft/save buttons disabled. Preview's default initial-report selection is NOT an authorized initial save: JUOG-971 already has v1/v2. No business request was sent.
- Surgery-performed branch remained incomplete. While entering discharge/pathology fields the next authentication check stopped the screen with AUTH_EXPIRED. No automatic resend or repeated login was attempted.
- AUTH_EXPIRED is evidence of a live safe stop, NOT sufficient proof of the fixed 60-minute boundary: start/expiry and same-session boundary observations are not established here.

## Integrity readback
D3_Journal A1:F1000: 165 returned rows, six-column normalized JSON SHA256 1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797, identical to prior baseline. Includes preserved business journal/audit records; authentication event ledger is separate. No raw journal, subject, keys or tokens included.

## Versions
Frontend previously pinned: 7d7859682654e31cd0cde95823e84209f37820a8; entry SHA256 5f4774443b1168daf45889735ade5de31339bcf685f4680907c8788f2b435dec. No redeploy this run. Runtime source hash not re-exported during this screen test.
GAS baseline Version 9 source SHA256 6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6; no deployment changes.
Recovery candidate reviewed at bb55180 remains undeployed. Existing offline integration evidence reused, not counted again.

## Remaining
Surgery-performed branch live 0/0 evidence; signed recovery candidate deployment/limited-read approval; exact live record version/status reconciliation before any correction. Initial save requires separately verified unused registered fictional case. Real save/correction remains prohibited pending PI's operation-specific approval. AUTH-04 historical marker/backup/log coverage and formal QA remain incomplete. No formal PASS added.

Evidence: no_surgery_ax.txt and no_surgery.jpg; expired_ax.txt and expired.jpg. These are fictional-input UI observations only, not saved clinical records.
