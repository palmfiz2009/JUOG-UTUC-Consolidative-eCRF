# JUOG-UTUC01 MDT UI minimal replacement files (2026-11-15)

Source: main branch at creation of review/mdt-ui-minimal-replacements-20261115.
This branch is PREVIEW ONLY. No production or original TEST deployment has been altered.

## Replace exactly these 3 files

- `01_registration_crf.py` — remind applicants to describe other-cancer history and long-term lymph node follow-up in the existing past_history field. No new database column or eligibility rule.
- `06_mdt_reviewer.py` — present submitted past_history, comorbidity and other_cancer to all three central MDT reviewers (with a clear 'applicant-supplied' label); in correction mode, pre-populate previous reviewer fields; use a stable comment-label so form state is not lost after a decision change.
- `05_admin_mdt_registration.py` — render central RECIST from the current latest radiology review as plain read-only text rather than a keyed disabled widget. Fixes stale display after a v1→v2 correction.

## Intentionally NOT changed
- No GAS code, Script Properties, credentials, production Sheets or records.
- No change to RECIST, clinical eligibility, cM1 criteria, vascular consult / PET proposals, numerical limits, audit/approval workflow or recipient lists.
- No large form-wide rewrite or CSS fade suppression. Streamlit's dimmed/stale display on rerun may still occur; this patch is not claimed to remove it.

## Quick deployment checklist
1. Preserve current 3 Python files and note the deployed commit / app source branch.
2. Download this branch as ZIP or use these 3 files ONLY; do not replace GAS, secrets, settings or data.
3. Run `python -m py_compile 01_registration_crf.py 06_mdt_reviewer.py 05_admin_mdt_registration.py` with Python >= 3.10.
4. In an isolated app with fabricated data, verify: applicant history is entered/saved; all three MDT reviewers see it; radiology still does NOT see site RECIST or site invasion before the independent review; v1 submission, correction prefill, correction to v2 and comment preservation; admin displays v2 RECIST; office mail only contains the final public reason, not private consensus notes.
5. Check role authentication, GET/submit responses, and append-only review version 1→2; do not use real patients in isolation.
6. Obtain normal approval before merging/deploying; verify production app is serving the new commit. Roll back only the three Python files if the visible behavior is abnormal.

**Caution:** Replacing local files by itself does not update a hosted Streamlit Cloud app. The approved changes must be committed to the branch actually used by that deployment.
