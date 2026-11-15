#!/usr/bin/env python3
"""Read-only CSV/GCP traceability validator.

This validates the integrity of the registry's *claims* and its requirement
coverage. It is NOT an independent QA approval and cannot prove a live UAT PASS.
No network, credentials, participant data, spreadsheet or runtime access.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UAT_PATH = ROOT / "quality/rtm/UAT67_BASELINE_20261116.json"
EVIDENCE_PATH = ROOT / "quality/rtm/EVIDENCE_REGISTER_20261116.json"
STATES = {"PASS", "FAIL", "BLOCKED", "NOT RUN"}
RISKS = {"Critical", "High", "Medium", "Low"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CASE_ID = re.compile(r"^[A-Z]+-[0-9]{2,3}$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> str:
    uat = json.loads(UAT_PATH.read_text(encoding="utf-8"))
    reg = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    require(uat["schema_version"] == "gcp-rtm-uatrecord-v1", "wrong UAT schema")
    require(reg["schema_version"] == "gcp-csv-evidence-register-v1", "wrong evidence schema")
    require(uat["source"]["ref"] == "review/acl-connection-20261112", "unexpected official source ref")
    require(HEX40.fullmatch(uat["source"]["source_blob_sha"]), "source blob SHA missing")
    require(len(uat["source"]["official_register_reported_sha256"]) == 64, "source digest missing")
    require(reg["linked_uat_baseline"] == "quality/rtm/UAT67_BASELINE_20261116.json",
            "evidence points to different UAT baseline")
    require(uat["status"] == "INITIAL_UNAPPROVED_READONLY_IMPORT", "unexpected UAT state")

    rows = uat["rows"]
    require(len(rows) == 67, f"UAT case count changed: {len(rows)}")
    cases = [r["test_id"] for r in rows]
    require(len(set(cases)) == 67, "duplicate UAT test ID")
    require(all(CASE_ID.fullmatch(x) for x in cases), "malformed UAT test ID")
    actual = Counter(r["official_status"] for r in rows)
    require(set(actual).issubset(STATES), "unknown UAT status")
    require(dict(actual) == {k: v for k, v in uat["counts"].items() if v},
            "stored UAT counts do not match individual statuses")
    require(uat["counts"] == {"PASS": 32, "FAIL": 1, "BLOCKED": 29, "NOT RUN": 5},
            "baseline UAT unexpectedly altered; use controlled change workflow")
    require(sum(r["test_id"] == "AUTH-04" and r["official_status"] == "FAIL" for r in rows) == 1,
            "AUTH-04 formal status must not be silently promoted")
    require(uat["interpretation"]["ready_to_release"] is False,
            "UAT baseline cannot assert release readiness")
    require(uat["interpretation"]["prior_evidence_refs_not_reverified"] is True,
            "historical evidence references may not be asserted as independently verified")

    requirements = uat["requirements_catalog"]
    covered = Counter()
    for r in rows:
        name = r["test_id"]
        require(r["baseline_status"] == r["official_status"],
                f"unauthorised official status change in {name}")
        require(r["evidence_verification"] == "SOURCE_REFERENCE_ONLY",
                f"unproven evidence promoted in {name}")
        require(r["new_formal_pass_in_this_import"] is False,
                f"import incorrectly claims new PASS in {name}")
        require(r["risk"] in RISKS, f"unknown risk type {name}")
        require(bool(r["acceptance_criterion"].strip()), f"missing acceptance criterion: {name}")
        require(bool(r["existing_evidence_reference"].strip()), f"missing evidence reference: {name}")
        require(bool(r["tested_version"].strip()), f"unknown historical tested version: {name}")
        ids = r["requirement_ids"]
        require(isinstance(ids, list) and len(ids) >= 1 and len(ids) == len(set(ids)),
                f"no/duplicate requirement mapping {name}")
        for requirement in ids:
            require(requirement in requirements, f"unknown requirement: {requirement} on {name}")
            covered[requirement] += 1
    require(set(covered) == set(requirements),
            f"unmapped requirements: {sorted(set(requirements) - set(covered))}")

    require(reg["release_readiness"] == "NOT_READY", "unapproved release readiness change")
    evidence_ids = set()
    for e in reg["evidence"]:
        eid = e["id"]
        require(eid not in evidence_ids, f"duplicate evidence ID: {eid}")
        evidence_ids.add(eid)
        require(e["qa_approved"] is False, f"evidence self-certified as QA approved: {eid}")
        require(e["official_uat_pass_added"] == 0, f"offline proof promoted to UAT: {eid}")
        require(e["real_isolated_env_executed"] is not True,
                f"unverified live execution in evidence: {eid}")
        require(e["proof_class"] in {"OFFLINE_FICTIONAL_TEST",
                                    "OFFLINE_FICTIONAL_TEST_AND_BOUNDED_TEST_READONLY",
                                    "HISTORICAL_FORMAL_STATUS_REFERENCE_ONLY"},
                f"unknown proof class {eid}")
        for ref in e["requirement_ids"]:
            require(ref in requirements, f"bad evidence mapping {eid}: {ref}")
        if "candidate_commit_sha" in e:
            require(HEX40.fullmatch(e["candidate_commit_sha"]),
                    f"candidate commit not pinned: {eid}")

    blockers = reg["unresolved_release_blockers"]
    require(len(blockers) >= 1, "no documented release blocker")
    require(len(set(b["id"] for b in blockers)) == len(blockers), "duplicate blocker IDs")
    for b in blockers:
        require(b["status"] == "OPEN", f"blocker was closed without approved change: {b['id']}")
        require(b["severity"] in {"CRITICAL", "HIGH", "MEDIUM"},
                f"invalid blocker severity: {b['id']}")
        require(set(b["mapped_tests"]).issubset(set(cases)),
                f"unknown blocked test reference: {b['id']}")
    require(all(v is False for v in reg["release_gates"].values()),
            "release gates were marked ready without independently approved validation")

    mapped = defaultdict(int)
    for item in reg["evidence"]:
        for req in item["requirement_ids"]:
            mapped[req] += 1
    # Build a useful markdown CI step summary. Evidence classes are not equal
    # to executable acceptance in the real isolated environment.
    lines = [
        "## GCP/CSV traceability gate — READ ONLY",
        "",
        f"- Baseline UAT: **{len(rows)}** cases (PASS {actual['PASS']} / FAIL {actual['FAIL']} / BLOCKED {actual['BLOCKED']} / NOT RUN {actual['NOT RUN']})",
        f"- Mapped requirements: **{len(covered)} / {len(requirements)}**",
        f"- Indexed candidate/historical evidence items: **{len(reg['evidence'])}**",
        f"- Open release blockers: **{len(blockers)}**",
        "- Technical CI result **does NOT create formal UAT PASS or independent QA approval**.",
        "- Production release status: **NOT READY**.",
        "",
        "| Requirement | UAT cases mapped | Indexed tech evidence entries |",
        "| --- | ---: | ---: |",
    ]
    for req in sorted(requirements):
        lines.append(f"| {req} | {covered[req]} | {mapped[req]} |")
    lines += ["", "### Open blockers"]
    for b in blockers:
        lines.append(f"- **{b['id']}** ({b['severity']}): {b['kind']} — {b['summary']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    try:
        report = validate()
        print(report)
        if len(sys.argv) > 1:
            Path(sys.argv[1]).write_text(report, encoding="utf-8")
    except Exception as exc:
        print("GCP evidence traceability gate FAILED: " + str(exc), file=sys.stderr)
        sys.exit(1)
