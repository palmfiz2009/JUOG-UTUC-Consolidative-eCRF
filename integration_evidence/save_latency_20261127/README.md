# Save latency candidate — 2026-11-27

Base 412dff41a54d86a2e5826a10e30379fe8c421cf8. Separate scratch copy; existing dirty checkout untouched. Source branch only; not deployed.

Repeated Spreadsheet.getSheetByName calls reduced by retaining object handles within a single locked request. No cell/header/ACL/session/owner verdict caching, no TTL changes, no removed guards, and no changes to UUID, payload, audit or Version semantics. Full offline save comparison: 46 sheet lookups -> 9. Fresh read counts exactly equal before/after (V3_Users 12, V3_SessionEvents 15, owner 9, Registry 11, operations 5, CRF30 4, CRF90 2, followup 2, audit 2). Missing sheet handles are not cached. New request gets new handles.

Recovery UI now displays only allowlisted failure codes (including AUTH_EXPIRED) instead of hiding the cause under a generic uncertain result. Arbitrary server text and payload are never displayed. It still blocks new submissions and never marks failed retries successful.

Regression: Python 219 (76+20+43+80), GAS 52 groups, existing audit repair and identity regressions all passed. Seven-suite runner completed; endpoint rerun after additional quantitative regression passed. These are offline results, not performance measurements on Google services. No assertion that this candidate alone resolves the live interruption. Formal UAT remains PASS 0 / BLOCKED 74.

Next live validation: deploy this exact endpoint change to existing isolated GAS same deployment, and recovery UI change to existing isolated fixture deployment branch; retain profile, keys, ACL, URL, notifications-off and B2 expiry. Then perform one explicit fictional correction (new correction UUID, expected existing Version) and independently compare CRF/audit/COMMIT. Preserve originals. Need per-deployment approval under the user's explicit restriction; no production change required. Independent QA verdict on actual measurements is separate from start-before approval.
