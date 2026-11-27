# Explicit target on recovery re-entry

Live navigation after dc7d833c165e3ca4bd9dcd01aa4a8e6b18ec7d6a preserved JUOG-901 / follow-up / saved 9m Version3 on return. However an old _recovery_open flag caused automatic checking of cleaned-up blank/default selectors on the next opening; its unknown result blocked subsequent draft writes. Keep the safety denial, but remove the unintended request.

Opening recovery now resets only the automatic-check flag. It does not clear _recovery_blocks_new or acknowledge a save; the user must explicitly select/check the target, and only a verified server result releases the existing safety gate. Added entry test asserts both flag reset and retention of a preexisting write block.

A fresh-process targeted run exposed preexisting test-order coupling: the non-UI input buffer imported an entire Streamlit fragment module for SECTIONS. It now reads the same canonical autosave_sections.json directly. Allowlist and security checks unchanged. Targeted entry/recovery/state suite 27 PASS.

Source-linkage fix f666046 initially failed two page-test doubles (missing route-specific linkage). ee394a91 supplied valid source metadata and asserted actual date widgets survive two renders. Full Actions46030469765 PASS. No failed build deployed.

No formal UAT PASS increment; no independent QA judgment fabricated.
