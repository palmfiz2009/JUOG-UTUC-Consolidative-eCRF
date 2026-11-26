# Isolated live UAT continuation — 2026-11-26 JST

Formal UAT PASS delta: 0. Existing ledger baseline remains PASS 0 / BLOCKED 74; this report explicitly records a live UI failure, not a successful UAT.

## Executed
- Confirmed isolated development HEAD d0ffbb6feb328b2b305249c267987814642fbb31 (leased update, no local reset).
- Compared existing isolated GAS registry with deployed Version 2 hash eb9c5fd1cf3b52391878d5d470f2c538ed93863bd1e9c7ec2699b3af3a409667.
- Saved tested registry with hash 792006803fa31216cf38a97d1a0a81b1196c8277c7518056406a830908c8007a; editor copy-back matched exactly.
- Updated the same existing isolated deployment to Version 3 at 23:07 JST. See juog_deploy3.txt. Deployment URL, execution identity and access settings unchanged. No setupRegistry execution, secret changes, ACL changes, production writes or notification enablement.
- Expired app identity stopped access. Logged out and used the previously authorized Google account; signed-in TEST01 UI returned.
- Selected fictional JUOG-901. The 30d draft resume reported no saved draft; subsequent blank form section saves displayed saved. No formal CRF submission occurred in this run.
- Switched to 90d, read existing surgery information: 30d Version 2, surgery performed, operation date 2026-01-10, permitted assessment dates 2026-03-27 through 2026-04-24.
- Entered fictional 90d assessment date 2026-04-10. The page became blank and console reported disconnected rerun messages. This is FAIL for uninterrupted navigation/input. No 90d formal save was clicked.
- One reload restored authenticated app entry. Collected app server logs; installed Streamlit 1.67.0, prior missing-fragment and WebSocket exceptions are visible. These logs do not by themselves establish the cause of this blank screen.

## Candidate UI change
The report selector now has an explicit session key. A retired section timer returns without output or transport when the selected report belongs to a different page, in addition to the existing recovery/auth-halt guards. Added offline tests across all three report switches. This candidate is committed on the isolated review branch only; it has NOT been deployed to Streamlit, and the live blank-screen defect is NOT marked fixed.

## Remaining blockers
- GAS Version 3 normal formal-save response latency has NOT been remeasured; AUTH_EXPIRED-after-commit remains unresolved until a fresh live save verifies it.
- Repeated Streamlit blank screen remains unresolved in the live deployment. A safe deployment of the UI candidate and a live rerun are still required; source/deployment differences must be preserved.
- Existing Version 1/2 evidence is in ../live_20261126_30d and ../live_20261126_v2. No duplicate formal rows were intentionally created here; no new independent Sheets read was completed in this run.
- Start-review approval is not substituted for independent QA acceptance of these measured outcomes. No formal PASS added.
