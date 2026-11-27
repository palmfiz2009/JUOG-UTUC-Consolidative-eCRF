# Unselected approach classification: live finding fixed

The live 30d correction rejected multiple approaches with no classification despite the completeness banner. Streamlit radio(index=None) returns None; the UI tested only empty string. The server normalized None to empty string and correctly rejected it. Changed the UI condition to `not text(approach_pattern)` and regenerated the same 254-condition contract. No medical rule, authorization or server acceptance was relaxed.

Regression executes the actual extracted UI validator with None and empty string (without server normalization), checks both reject; an explicitly planned hybrid remains valid. Full offline run: Python 224 tests (76+20+43+85), GAS 52 groups and legacy tests pass. Differential discrepancies: 0. See attached logs. Formal live UAT PASS delta: 0.

GAS deployment is not required for equivalent existing server rejection and was not changed. Review source includes synchronized generated contract. Live latency/assertion-expiry problem remains unresolved; canonical V3 recovery evidence is in ../live_v3_recovery_20261127.
