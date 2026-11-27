# Live isolated 30-day V3 recovery, 2026-11-27 JST

Formal UAT: PASS 0 / BLOCKED 74; independent outcome QA pending. These are actual live observations, not offline-test substitutes.

## Deployment
Approved review source 9a9866dc2ff2217dfaf23c87dbbf4c50a0483d33 deployed to existing fixture branch as c3d91b8fcc658a9564b37f1120430c21f0c20b4c. Only streamlit_app.py and isolated_connection_state.py changed. Existing GAS Version 5 remains unchanged. No ACL, credentials, production, main, external email, or other environments changed.

## Live sequence
1. Authenticated TEST01 / fictional JUOG-901. Resumed server draft. Entered 30-day correction in actual browser. Observed section saving and saved labels.
2. AUTH_EXPIRED halted editing; logged out and reauthenticated with previously authorized account. Server draft restored saved earlier sections; unsaved later fields required entry. No claim of full restoration of unconfirmed input.
3. A later connection-unconfirmed stop occurred. The explicit reconnect action returned to the same case with entered fields retained (remaining required fields: readmission and last-alive date). This is the live input-preservation improvement observed after deployment.
4. First formal-save click was rejected by clinical validation for multiple-approach classification. The UI completeness indicator had not caught this condition. Corrected accidental multiple selection to open approach only. Full no-write proof for rejected attempt was not captured, so 30d-N is not marked PASS.
5. Corrected formal save displayed AUTH_EXPIRED, despite creation of a CRF V3 and audit row. Read-only Sheets inspection found INTENT but no COMMIT initially. This is a one-shot-save failure, not success.
6. Reauthenticated; opened in-app recovery; entered JUOG-901/30d. Screen showed V1/V2 audit consistency and canonical retry permitted.
7. Clicked same-UUID retry once. Screen displayed: 同一UUIDの正式保存と監査を再照合しました。Versionの重複追加はしていません。
8. Fresh server-record check displayed: 正式保存を照合しました：Version 3 / UUID 1412c1bb-2d61-4733-bb97-a60afe032b60 / 監査一致.
9. Separate Google Sheets connector reads confirmed exactly one V3 CRF row, one corresponding audit, one INTENT and one COMMIT; old V1/V2 preserved. See comparison.json and fictional-records.json.

## Exact result
UUID: 1412c1bb-2d61-4733-bb97-a60afe032b60
Key: JUOG-901|perioperative_30d|30d
Version: 3; expected prior version: 2
Payload digest: fdd2087ecc4288471d67bbd4876bc82357cb25295f7d3893abb12136db0efee0
INTENT: 2026-11-27T09:04:40.056Z
COMMIT after recovery: 2026-11-27T09:08:06.008Z
Fictional correction WBC 7, discharge 2026-01-20, last alive 2026-02-09.

## UAT mapping and gaps
| ID | Observed evidence | Remaining |
|---|---|---|
|30d-D|Section saves, same-person reauthentication/resume, transient-stop input preservation|Full value-by-value draft event and all alternate-actor checks; independent QA|
|30d-V2|V3 correction retains V1/V2 and matching audit|Does not replace original V2 scenario evidence or QA|
|30d-R|Same canonical UUID retry completed, no additional V4|Double click, changed-payload rejection and all other subcases not measured here|
|30d-N|Multiple-approach invalid payload rejected|UI completeness mismatch, comprehensive no-write verification and other invalid cases|
|30d-V1|Reuse prior V1 evidence|This run is V3, not a new V1 or clean one-shot-save PASS|

## Remaining defects
- Valid save can exceed the short signed assertion lifetime after partial writes, requiring canonical recovery. Do not weaken expiry/replay controls to hide this.
- UI completeness message can precede a stricter clinical validation failure (multiple approach classification).
- Frequent rerender/network delay interferes with dropdown interaction.
- Full 74-item UAT and independent measured-outcome QA remain incomplete. No new formal PASS assigned.
