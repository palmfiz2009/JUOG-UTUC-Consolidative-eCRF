# Correction source linkage

Live finding: after successful 9m Version3 reconciliation and correction start, the form retained case/email but stopped at missing 30d linkage. Clearing the page discarded its non-widget linkage; later conditional widgets could then be cleaned up before rendering. Do not label this a completed resume.

Fix: 90d/follow-up correction now obtains fresh signed 30d linkage before clearing any form. It must match the original case/facility, positive integer source Version, UUID, reference date and surgery branch. Changed/unavailable source stops and retains the original completed attempt. Only after these checks are the saved widgets and linkage restored together. No new clinical judgment, write, UUID, or permission change.

Targeted tests: correction coordinator 5 PASS, all nine visit success cases and 18 source denial variants (two page types x nine failures). Hosted Actions runs full regression. No live correction PASS asserted before remeasurement; formal ledger unchanged.
