# Approved fixture deployment — 2026-11-25 JST

User explicitly approved the fixture-branch exception and owner-executed / Everyone GAS deployment in this conversation.

## Completed
Existing branch uat-fixture-isolated-20261109 moved with expected-HEAD lease from a2bcc6f7ff513ab30b9c8455f1b4893b465ea5ca to ce3c235959239e00bd07807c1c3fa922bcfdfd22.
18 runtime blobs copied exactly from reviewed 4cf8ea66220c06be3fc8b593464c57cff9ae8be1. Post-commit tree verification: 18/18 matches; all unrelated existing blobs preserved. requirements.txt already matched and was unchanged.
No app was created/deleted. Existing app URL and OIDC secrets unchanged.
Actual existing Streamlit UI now shows JUOG-UTUC01 隔離CRF and disabled integration message. Profile remains enabled=false; no save attempted.
Cloud update logs showed transient import errors during hot reload, followed by Updated app and the rendered disabled integration screen. This is not full runtime validation or a formal UAT PASS.

## GAS
Approved Deploy button clicked. Google then required data-access authorization. No deployment success/URL observed.
Automatic approval review rejected clicking アクセスを承認 because concrete OAuth scopes/recipients were not visible and deployment approval did not establish permission for an unknown grant.
No retry or alternate-route bypass performed. User must inspect the presented Google authorization scopes before granting.
New signing credential also remains unset; user entry is required. No key published or generated.

## Outcome
Formal UAT PASS 0 / BLOCKED 74. No business writes, no mail sends, no independent QA UAT adjudication claimed.
Rollback: restore the listed runtime paths from parent a2bcc6f via a new commit if necessary; preserve unrelated work and do not force-reset shared history. Keep runtime disabled until deployment identity, credential binding, generation and principal checks complete.

## Exact deployed paths
- streamlit_app.py — 5f2aeeaabe437cba911b28467f7248a1b506baa2
- 02_perioperative_30d_crf.py — 652b24794bc0122978011c2cc06ef4ffeb454ba1
- 03_day90_crf.py — 6dbd79ea0291d947aee47c76167be981557b4da3
- 04_followup_crf.py — 0ab03e1941f6dddb68ba061bb877073c59dce1b2
- juog_common.py — 63a71698a85b417924361bad91a4dc431ca9b97e
- juog_crf_save_ui.py — 16bd53c47775ddd18530ffa5729b54b2548d1494
- isolated_crf_adapter.py — a03fe94f992d15d4e753efd770497a31389ac794
- isolated_autosave_ui.py — 1a59b451656742856813ac5c47dec720cb733d63
- isolated_correction_ui.py — 3cd5fe923f07e17a79fb6f4dd17b57be2effe763
- isolated_recovery_ui.py — 1b8631782132c07933fa8b781bac267ddbf9d5e6
- isolated_privacy.py — 77c1a5e7ec7ac4f53664fda74f50219b364a2740
- clinical_validation.py — b6a23e487aee786ce4ca56a0038a315c4aed5c07
- clinical_contract/contract.json — 92fa1e2bd8afe91a756a5a58fe3c18350acd7191
- autosave_sections.json — 2cf76151965fd3510e9fd5933354b78a5c0aaaf3
- isolated_crf_profile.json — 9527d268c92f15a845386581ab45ba5c28d9ade9
- uat_b2_auth_bridge.py — 284cf935783c3137f4941eec8e6efc482ac02b2d
- uat_b2_session.py — 4ed2904b5b740aab77f03a9862865439f28e7789
- uat_identity_proposal.py — f69b7ea2f1e0914657ae2c6c9d280740d1971e5f
