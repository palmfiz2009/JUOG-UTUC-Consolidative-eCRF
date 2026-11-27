# Fragment return to connection gate

Follow-up to 78120619d9524105bbaec3b8f448dc8d806770a5. When section autosave sets the assertion-reconfirmation latch, preserve allowlisted input and rerun the full app so its signed ACL gate becomes visible. No retry or success is inferred inside the fragment. Other retired fragment guards remain unchanged.

Targeted regression: all 10 autosave UI tests PASS, including a new failed-section assertion -> full-page gate test, with preserved fictional registration and no success indicator. Previous whole-suite baseline 240 Python / 60 GAS groups PASS; this adds one Python case. Hosted workflow will run the full suite on this commit. No formal UAT PASS added.
