# Connection input loss: observed live, fix verified offline

Formal UAT remains PASS 0 / BLOCKED 74. No independent QA outcome is asserted.

## Authorized deployment and observed live result
- Review source deb978e0a6b958a1bc1f6790c647987fd6b20092; Actions 45955728629 succeeded.
- Existing fixture branch deployment commit d915d5d382111719b09befe5970690a36c1d9dd5. Only isolated_recovery_ui.py changed.
- Existing isolated GAS deployment updated to Version 5. Endpoint editor content verified as Git blob c10d70de4b4adf574200bca807c698cceb1fcea4 before deployment. Deployment ID, URL and access unchanged. B2 unchanged. Notifications disabled.
- Authenticated TEST01 user opened JUOG-901, resumed draft and entered a fictional 30-day correction. No formal submit was performed in this session.
- A transient connection warning appeared. After connection retry the form returned, but subsequent rerenders showed an empty editing subject and stopped further editing. This is an observed live input-loss failure, not a PASS.
- This record is an operator observation; no new completed CRF, audit row or one-shot-save evidence is claimed.

## Fix
Keep an actor-bound, allowlisted copy of widget input in a separate non-widget session key. Restore only after a fresh successful signed ui_context response. Do not restore cached ACL, authority, UUID, Version, or secrets. Discard backup on auth halt, actor mismatch, logged-out state or logout request. Existing server-side draft/recovery paths remain unchanged. This protects transient reruns in the same browser session; browser loss still uses server drafts and canonical UUID recovery.

## Verification
Four new tests cover widget cleanup, repeated outage, actor mismatch/auth halt, absence of actor, secret exclusion and an actual Streamlit AppTest rerun/stop/reconnect sequence. Full seven-suite offline rerun is attached. These results are not live UAT or independent QA.

## Remaining live checks
This input-preservation revision is not deployed. After authorized fixture deployment, repeat 30-day editing through connection recovery, then submit once and independently read CRF/Version/UUID/audit/operation records. Verify prior 30-day V1/V2 and 90-day V1 remain intact. Obtain independent QA on measured outcomes before changing formal UAT status.

No production, main, other TEST, Stage 1, fixed S2-01, ACL, keys or real patient data changed.
