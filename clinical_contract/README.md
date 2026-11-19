# Clinical validation contract — offline candidate, not clinical approval

Baseline: `2c358c4bc14af399cabd431f6adc6e31ac294fae`. Original UI rules are compiled, not replaced with a new clinical policy. All data in fixtures and evidence are fictional.

## Traceability

- `input_specification.csv`: all 191 widget calls in the three CRF source files, with visibility ancestry, payload path and widget constraints. 175 mapped, 8 read-only displays, 6 draft lookup widgets, 2 reusable laboratory helper definitions. The latter expand `LAB_FIELDS` for day-30, inpatient, day-90 and follow-up raw/parsed lab dictionaries. Shared facility and report-kind selectors are represented in the contract metadata mappings and existing `render_facility` / `render_submission_kind` helpers.
- `validation_conditions.csv`: 254 individual conditional rules in the existing `validate_all` functions, with source file/line and expression. Date, required, conditional required, pathology, recurrence, vital status, complications and warning branches are retained verbatim.
- `contract.json`: source hashes, complete variable-to-payload mapping, dates, options, ranges, laboratory definitions and the pinned Python validator source. `clinical_contract_generated.gs` compiles the same AST to GAS. Generation rejects unsupported syntax.
- `../integration_evidence/clinical_witnesses.json`: deterministic differential-corpus case indexes witnessing each true/false outcome. Recreate those inputs with `integration_tests.test_clinical.corpus()`.
- `../integration_evidence/clinical_coverage.json`: measured counts; no real UAT status is changed.

Every rule has a test witness. Rule `04-394` (unselected visit) cannot reach its true branch through the canonical payload validator because `VISIT_LABEL_MISMATCH` rejects it first. `test_unselected_visit_rejected_before_rule_04_394` tests this rejection explicitly; it is not represented as branch coverage.

## Representation rules and write barrier

Null, empty string, zero and false are not interchanged. Empty widgets are reconstructed as their existing UI defaults; numbers must be finite numbers (not booleans), checkboxes must be booleans, multi-selects must be lists of allowed strings, date strings must be valid ISO dates, and choices/ranges match the pinned widgets. Hidden defaults such as `ypNX（郭清なし）` remain permitted. Mandatory checks still depend on the original visibility/clinical branches. Display-only values are not independent editable clinical inputs.

Raw lab values are retained alongside parsed numeric values and checked for agreement. This distinguishes blank from explicit `NA` and stops forged parsed results. Both runtimes now use finite ASCII decimal/exponent numeric syntax; NaN, Infinity, hexadecimal, underscores and booleans are not clinical numeric values. This is serialization/input hardening, not a new clinical reference range. Existing laboratory negative-value and differential-count percentage rules are retained.

The save helper validates the frozen payload, and GAS validates again before appending INTENT, CRF, version or CRF audit. Invalid input does not trigger notifications or draft cleanup. Authentication session-use evidence can still be recorded: that is not a successful clinical-save audit.

The tests include both operated and non-operated positive fixtures; zero blood loss and zero pathological size remain representable. Existing warnings (for example an evaluation date outside a suggested window) have NOT silently become mandatory rejection criteria. Direct requests still undergo existing subject/linkage hard stops in addition to this contract.

## Clinical approval limitation — unresolved release gate

The repository's `PROTOCOL_ALIGNMENT.md` describes a 2026-09-14/v3 basis, while the requested approved source is the 2026-09-16 plan. `PROTOCOL_CHANGE_SUGGESTIONS.md` is a proposal, not approval. The authoritative approved protocol/CRF rule set and its sign-off were not established in this work. Therefore UI parity is tested, but **approved clinical-specification conformity is NOT VERIFIED**. Review the table against the approved original, especially warning versus hard-stop windows, non-operated paths, pathology/Grade and recurrence definitions. No unapproved clinical judgment was invented to close this gap.

## Reproduction

Run `python build_clinical_contract.py` then `python run_offline.py` from the repository root with requirements installed. The manual-only GitHub Actions workflow runs the same commands on this isolation branch and rejects generated-file drift. It has not been dispatched here; hosted execution and its available free quota are not claimed verified. No deployments, secrets or service connections are used by these tests.
