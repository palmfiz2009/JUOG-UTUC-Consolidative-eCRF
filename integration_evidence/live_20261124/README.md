# Isolated live preparation — 2026-11-24
Formal UAT remains PASS 0 / FAIL 0 / BLOCKED 74. New formal PASS: 0.
This is preparation evidence, not a live CRF save or independent QA UAT outcome.

## Approval provenance
Reviewed runtime: 4cf8ea66220c06be3fc8b593464c57cff9ae8be1.
Signed independent start-review received from user, reviewer 中本喬大, dated 2026-11-24. Private signature photographs are not published.
QA receipt: PR #15 comment 7135183051. PI confirmation for P01–P08 current implementation: comment 7135220940.
These authorize the recorded limited start scope; they do not certify future live UAT results.
Review-branch HEAD checked: a69c0cd3a1994e035c6f1b250a2e6faf240c8f86.
PR #15 has a different draft branch and was not changed.

## Observed and performed
- Existing isolated workbook 1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs copied natively to private owner-only backup 1T39Xuki4k0ifqMnKBxSJ3ItSnP9ZM5jzM1JD66Nc5y4.
- 19/19 tab FORMULA-value comparisons matched in bounded ranges A1:Z100 (Screening through AA100; Registry A1:Z20). Native copy is full workbook; bounded comparison is not a complete restore rehearsal.
- Source modifiedTime remained 2026-11-21T09:10:32.124Z before/after backup.
- JUOG-901 registry and TEST01 ACL/owner mapping matched. ACL expiry 2026-11-28T23:59:00+09:00. Private identity subject is intentionally omitted.
- Clinical CRFs, submission audit, operations and B2 session events were header-only in inspected ranges. No synthetic CRF/version/audit rows inserted.
- Old fixture GAS active deployments: zero, previous version retained archived. Current-account triggers: zero for old and candidate projects. This is not a global proof concerning other-account triggers or unknown projects.
- Existing candidate project 1_oVuL1i6Kmyu5egp-iDHIku-nN5JxoQ1ySPSluAsNc2gCFXGvBSJGDAR now contains exactly the nine reviewed GAS files. All nine were reloaded and copied back from the editor and matched reviewed source bytes/hash.
- Original candidate code was preserved; SHA256 9ae2408249cbe34e7da492962be3b698c14f9b733a8f87fb0c27f8ff320e602d. Existing private backup retained.
- SPREADSHEET_ID, disabled JUOG_PR15_CONFIG, and initial B2 head were saved and reloaded. Generation 6f661f85-6aab-463f-a801-383a87dfb208. Initial head 0:5af3a7d657ad09bc1537f6ab03b8e936b0cbece3a2c145cf9db32e3d88f04ea8.
- Candidate enabled=false, notificationsDisabled=true. No signingKey generated or entered. No candidate deployment or business function executed.
- Existing Streamlit app was awakened. Runtime logs show uat-fixture-isolated-20261109 / streamlit_app.py. Its current GitHub branch HEAD is a2bcc6f7ff513ab30b9c8455f1b4893b465ea5ca; this is not proof of the exact running commit.
- App settings General exposes URL/Python version, not source branch switching. Secrets were not modified.

## Remaining concrete gates
1. Existing app source is uat-fixture-isolated-20261109. User's later review-branch-only code restriction prevents updating this deployed branch without an explicit exception. Proposal: deploy reviewed runtime files to this existing fixture branch, preserve its unrelated files/history and existing OIDC secrets, retain existing app URL. Do not replace whole tree, force push, create or delete an app. Recheck HEAD and exact direct-tree delta before applying.
2. Candidate web-app deployment dialog prepared with owner execution and access Everyone, description binding reviewed SHA/TEST01/JUOG-901/notifications disabled. No Deploy click. Browser policy requires action-time confirmation for this new public execution endpoint; application signature/ACL gates remain mandatory.
3. New signing credential entry must be completed by user under browser credential-change handoff policy. Never record it in GitHub, evidence, logs or chat. Same key is required at the two authorized isolated endpoints; maintain disabled state until coherent configuration verified.
4. Then verify deployment identity, OIDC, B2/ACL/owner, and perform existing UAT_30D_FIRST_PASS.md sequence. Capture actual draft/reopen/Version1 response UUID and independently read Sheets/audit. Human QA adjudicates formal PASS.
5. External mail remains disabled; no mail-success claim.

No production/main/old TEST/Stage1/fixed S2-01 or patient data changed. No new offline test claimed. Prior 198 Python / 42 GAS groups and hosted run 45001482081 are historical reused evidence.

## Sources and backup comparisons
- PR #15 live-prep record: https://github.com/palmfiz2009/JUOG-UTUC-Consolidative-eCRF/pull/15#issuecomment-7135667495
- Streamlit official source-coordinate change procedure: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/rename-your-app
- Streamlit existing source updates: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
```json
[
  {
    "title": "シート1",
    "matched": true,
    "sourceRows": 0,
    "backupRows": 0
  },
  {
    "title": "Registry",
    "matched": true,
    "sourceRows": 2,
    "backupRows": 2
  },
  {
    "title": "Screening",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "ScreeningAudit",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "MDTReviews",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "ScreeningCRF",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "CRF_30d",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "CRF_90d",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "CRF_Followup",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "CRFSubmissionAudit",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "CRF_Drafts",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "Settings",
    "matched": true,
    "sourceRows": 7,
    "backupRows": 7
  },
  {
    "title": "UAT_Provenance",
    "matched": true,
    "sourceRows": 11,
    "backupRows": 11
  },
  {
    "title": "V3_Users",
    "matched": true,
    "sourceRows": 2,
    "backupRows": 2
  },
  {
    "title": "V3_SessionEvents",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "R1_CaseOwners",
    "matched": true,
    "sourceRows": 2,
    "backupRows": 2
  },
  {
    "title": "R1_Operations",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "R1_DraftOwners",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  },
  {
    "title": "R1_DraftEvents",
    "matched": true,
    "sourceRows": 1,
    "backupRows": 1
  }
]
```
