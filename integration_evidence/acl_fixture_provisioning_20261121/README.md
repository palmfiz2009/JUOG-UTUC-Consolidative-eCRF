# Isolated principal and fictional case provisioning — 2026-11-21 JST

Base: `b688e39cb359fd6f9e4f6f389706cce94a7d9016`.

The user authorized the designated Google account, approved TEST01 single-person ACL expiry of 2026-11-28 23:59 JST, and subsequently authorized remaining isolated work. This is PI authorization, not independent QA sign-off.

## Completed live preparation

- Verified existing issuer/subject fingerprint against the successfully authenticated fixture's principal pin. No guessed identity and no full subject or credential committed.
- Provisioned one facility-only TEST01 ACL in the PR15 candidate workbook, verified exact readback, and inspected the native saved row. The older AUTH04 workbook was read only; its expiry remains unchanged.
- Provisioned only existing fictional integration fixture JUOG-901 and its owner mapping. Registry and owner tables were header-only over their full populated schema ranges before writing. Re-read both rows after the atomic two-table update. These are setup operations, not CRF saves, clinical registration, or UAT passes.
- Target workbook: `1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs`. Exact ranges and sanitized evidence are in `provisioning.json`.

## Remaining execution gate

The running fixture app is still AUTH_CONNECT and points to the older isolated endpoint, not the PR15 candidate. The observed `AUTH_CONNECT_NOT_APPROVED` is not resolved by adding an ACL in the candidate workbook. The candidate requires a real independent review reference (`qaRef`) before enabling. No such record has been supplied; no approval flag or ref was fabricated. Clinical protocol conformity also remains unapproved. Candidate deployment, B2 generation/credentials, and Streamlit switch remain pending those prerequisites; already authorized environment actions need no repeat PI permission.

Formal UAT remains **PASS 0 / FAIL 0 / BLOCKED 74 / NOT RUN 0; new PASS 0**. No CRF, audit or Version row was directly seeded. No formal-save attempt, email, production/old TEST/Stage 1/S2-01/main modification or new app occurred.

Runtime code unchanged. Prior verified 190 Python tests, 40 GAS groups, existing GAS regression, 14 identity cases and 8,062-case clinical differential results are reused, not rerun or represented as live tests. Independent QA must be performed by an actual designated person.
