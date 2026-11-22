"""Explicit same-session correction, after fresh signed server reconciliation.

No UUID creation, business write, approval bypass or browser persistence here.
The original immutable attempt remains available until all checks succeed.
"""
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path

SECTIONS = json.loads(Path(__file__).with_name('autosave_sections.json').read_text())


def snapshot_form(page, state):
    # Only allowlisted widget values; never copy credentials or another page.
    keys = {k for section in SECTIONS[page].values() for k in section['keys']}
    out = {}
    for key in keys.intersection(state):
        value = state[key]
        if key.endswith('_registration_id'):
            value = str(value).strip().upper()
        kind = 'datetime' if isinstance(value, datetime) else 'date' if isinstance(value, date) else 'value'
        out[key] = {'type': kind, 'value': value.isoformat() if kind != 'value' else deepcopy(value)}
    return out


def start_correction(st, page):
    from isolated_crf_adapter import actor_key, call, begin_edit
    from isolated_autosave_ui import _clear, _read_ok
    from isolated_recovery_ui import _valid_recovery, _saved
    from juog_crf_save_ui import attempt_key
    from juog_common import restore_draft_state

    attempt = st.session_state.get(attempt_key(page))
    if not isinstance(attempt, dict) or attempt.get('status') != 'complete':
        return '保存済みの入力がありません。復旧画面で記録を照合してください。'
    try:
        if attempt.get('actor_key') != actor_key(st):
            return '本人認証が変更・失効しています。再認証して復旧画面で照合してください。'
    except Exception:
        return '本人認証を確認できません。訂正は開始していません。'
    p = attempt['payload']
    query = {k: p[k] for k in ('registration_id', 'facility_code', 'crf_type', 'visit')}
    key = '|'.join(query[k] for k in ('registration_id', 'crf_type', 'visit'))
    form = attempt.get('form_state')
    if not isinstance(form, dict) or not form:
        return '保存時の画面入力が残っていません。復旧画面で正式記録を確認してください。'
    sections = {s: {'revision': 1, 'data': {k: v for k, v in form.items() if k in spec['keys']}}
                for s, spec in SECTIONS[page].items()}
    restored_keys = {k for s in sections.values() for k in s['data']}
    if restored_keys != set(form) or not _read_ok(dict(ok=True, audit_verified=True,
            record_key=key, record_version=0, sections=sections), query):
        return '保存時の入力を安全に復元できません。事務局に照合を依頼してください。'
    reply = call(st, 'recovery_status', query)
    if not _valid_recovery(reply, query) or reply['recovery']['state'] != 'SAVED':
        return '正式保存・監査を確認できません。復旧画面で照合してください。'
    records = reply['recovery']['operations']
    latest = max(records, key=lambda r: r['version'])
    if (not _saved(latest) or latest['uuid'] != p['submission_id']
            or str(latest['version']) != str(attempt.get('record_version'))):
        return '別の訂正または未確定操作があります。最新Versionを復旧画面で確認してください。'
    checked = begin_edit(st, p['registration_id'])
    if checked.get('ok') is not True or checked.get('record_versions', {}).get(key) != latest['version']:
        return '症例権限または最新Versionが変わりました。入力を変更せず停止しました。'
    # Explicit reset only after authentication, ownership, audit and CAS baseline.
    _clear(st, page)
    restore_draft_state(form)
    st.session_state[page + '_submission_kind'] = '訂正報告'
    st.session_state[page + '_correction_reason'] = ''
    st.session_state[page + '_sent'] = False
    st.session_state.pop(attempt_key(page), None)
    return None


def correction_panel(page):
    import streamlit as st
    st.caption('このブラウザに残る保存時の入力を、正式記録・監査と照合して訂正に使用します。')
    if st.button('この保存を照合して訂正入力を開始', key='_correction_start_' + page):
        error = start_correction(st, page)
        if error:
            st.error(error)
        else:
            st.rerun()
