"""Build a local review bundle only. No network, credentials or deployment.

Usage: python tools/prepare_isolated_uat.py /absolute/unused/output-directory
Deploy these nine GAS source files only after the recorded human gates pass.
Do not push the repository root (it also contains production helper scripts).
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GAS_FILES = [
    '05_registry_google_apps_script.gs', 'isolated_auth_bridge.gs',
    'isolated_session_store.gs', 'isolated_crf_endpoint.gs',
    'isolated_recovery.gs', 'clinical_contract_generated.gs',
    'clinical_validation.gs', 'autosave_sections_generated.gs',
    'isolated_autosave.gs',
]


def build(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Destination must not exist; preserve earlier bundles')
    profile = json.loads((ROOT / 'isolated_crf_profile.json').read_text())
    if profile.get('enabled') is not False or profile.get('qa_ref'):
        raise ValueError('Review source must remain disabled with no claimed QA approval')
    manifest = dict(mode='PREAPPROVAL_LOCAL_REVIEW_ONLY', formal_uat_pass_delta=0,
                    script_id=profile['script_id'], spreadsheet_id=profile['spreadsheet_id'],
                    source_files={}, independent_qa_approved=False)
    content = {name: (ROOT / name).read_bytes() for name in GAS_FILES}
    for name, data in content.items():
        manifest['source_files'][name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    destination.mkdir(parents=True)
    for name, data in content.items():
        (destination / name).write_bytes(data)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    assert set(p.name for p in destination.iterdir()) == set(GAS_FILES) | {'manifest.json'}
    for name, info in manifest['source_files'].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == info['sha256']
    return manifest


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps(build(sys.argv[1]), indent=2))
