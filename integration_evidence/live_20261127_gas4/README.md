# Isolated GAS v4 / live 90-day recovery — 2026-11-27 JST

Formal UAT remains PASS 0 / BLOCKED 74. These are developer-observed live results, not independent QA outcome approval.

## Authorized deployment
The user answered the specific pending bb81840 deployment approval request with 「すすめてよ」. Updated the existing isolated deployment, not a new app. Apps Script confirmed Version 4 (2026/11/27 07:01).
- Script: 1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR
- Deployment: AKfycbxrn_U2A4PXxyaNcf2eGpIdGrcaeYJ7tpV5O8WukUqunQSczMJ6tAmA8VvJaMKZBg3z
- Same /exec URL, execution identity and access setting retained.
- Candidate B2 file SHA256 verified from editor before deployment: ddf30321934a967223bd2998fd8f5c34a23cfd289e1af738641eedaf25cddac0
- Candidate source: bb81840a6fc5a49728be738cc889fbcdbc7b209d. Only the previously staged B2 prefix verification change was deployed.
- Rollback target: Version 3 of this same deployment. No data rollback performed.
- No ACL, keys, notification settings, production or main edits.

## Observed live sequence
Used existing Streamlit fixture and authorized OIDC account. Expired native login correctly stopped access; logout and Google account selection restored TEST01 access.
Selected JUOG-901 / 90日 in recovery UI. Server canonical request retained:
UUID e68de6b2-f6de-45a5-b117-24a04ce6bfd6
digest 0b0782a83487d400d717fd115e2d4578012f039e127deee8fa2f19e0929aefb5
key JUOG-901|day90|90d, expected version 0.
No new submission UUID/payload generated.

Independent connector reads:
1. before: CRF data rows 0, audit rows 2 (old 30-day), operations 5 (90-day INTENT only).
2. after: CRF data rows 1 / Version 1; audit still 2; operations still 5. UI correctly displayed unconfirmed.
3. final (intermediate): same CRF row, audit rows 3 including matching 90-day Version 1; operations still 5. UI still unconfirmed.
4. committed: same CRF row, same audit rows 3, operations 6 including exact UUID/digest COMMIT at 2026-11-26T22:08:14.957Z (=07:08 JST).
A retry from the first page was halted by auth/ACL state. A fresh page revalidated rights; subsequent retries used only the original UUID. No bypass or direct Sheet write.

Final browser response:
> 同一UUIDの正式保存と監査を再照合しました。Versionの重複追加はしていません。

checks.json records eight checks executed against independently retrieved values: one CRF Version 1, original payload unchanged, one matching audit, one INTENT, one COMMIT, verified receipt, old operation history and old audits preserved. All true. Sheet A:Z includes complete payload_json but not all flattened columns.

## Remaining defect and status
The full write did not complete in one attempt even after B2 optimization: multiple same-UUID recoveries were required to progress row -> audit -> COMMIT. This is NOT a clean first-submit PASS. Exact per-request server error was not exposed by the recovery UI; attribution to expiry remains a hypothesis until correlated execution evidence is available.
Recovery successfully completed without duplicates, but latency / partial-write interruption remains unresolved. Do not advance later formal submissions merely to conceal this failure.

No independent QA verdict for these measured outcomes was received during this run. Start-before QA approval is not outcome approval. Formal UAT PASS unchanged.
Existing offline evidence reused: Python 217 / GAS 50 groups and existing regression success; Actions 45851415041 at 52b774. No code changes or redundant rerun in this evidence-only commit.
