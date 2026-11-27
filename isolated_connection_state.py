"""Keep allowlisted input independently of Streamlit widget cleanup during outages."""
from copy import deepcopy
from fnmatch import fnmatchcase
import json
from pathlib import Path
SECTIONS = json.loads(Path(__file__).with_name('autosave_sections.json').read_text())

BACKUP = '_connection_input_backup'
RECOVERY_BACKUP = '_recovery_input_backup'

def preserve_recovery(state):
    preserve(state)
    backup = state.pop(BACKUP, None)
    if backup is not None:
        state[RECOVERY_BACKUP] = backup

def restore_recovery(state):
    # Entry calls this only after a fresh signed server ACL confirmation.
    backup = state.pop(RECOVERY_BACKUP, None)
    if backup is not None:
        state[BACKUP] = backup
        restore(state)

def _allowed(key):
    patterns = [p for sections in SECTIONS.values() for section in sections.values() for p in section['keys']]
    patterns += ['_integration_subject', '_integration_page', '_resume_case_*', '_resume_visit_*']
    return isinstance(key, str) and any(fnmatchcase(key, p) for p in patterns)

def preserve(state):
    actor = state.get('_integration_actor')
    if not isinstance(actor, str) or not actor:
        state.pop(BACKUP, None)
        return
    prior = state.get(BACKUP)
    values = deepcopy(prior['values']) if isinstance(prior, dict) and prior.get('actor') == actor else {}
    values.update({k: deepcopy(state[k]) for k in list(state) if _allowed(k)})
    state[BACKUP] = {'actor': actor, 'values': values}

def restore(state):
    # Caller must first obtain a fresh successful signed ui_context response.
    backup = state.pop(BACKUP, None)
    if not isinstance(backup, dict) or backup.get('actor') != state.get('_integration_actor') or state.get('auth_connect_halted'):
        return
    for key, value in backup.get('values', {}).items():
        if _allowed(key):
            state[key] = deepcopy(value)
