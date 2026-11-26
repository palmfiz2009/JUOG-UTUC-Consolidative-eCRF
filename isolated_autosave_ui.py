"""Authenticated, debounced section drafts inside the existing CRF pages.

Timers see Streamlit-committed widget values (text commits on blur/Enter). No
browser-local patient store, background thread, legacy URL or automatic retry.
"""
from copy import deepcopy
from datetime import date, datetime
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import time
import uuid

SECTIONS = json.loads(Path(__file__).with_name('autosave_sections.json').read_text())
TYPES = {'peri': 'perioperative_30d', 'd90': 'day90', 'fu': 'followup'}
VISITS = ['6m', '9m', '12m', '15m', '18m', '21m', '24m']
WAIT = 2.0
_clock = time.monotonic


def canonical(value):
    def normalize(v):
        if type(v) is float and v.is_integer():
            return int(v)
        if isinstance(v, list):
            return [normalize(x) for x in v]
        if isinstance(v, dict):
            return {k: normalize(x) for k, x in v.items()}
        return v
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def capture(page, section, state):
    patterns = SECTIONS[page][section]['keys']
    result = {}
    for key in state:
        if not any(fnmatchcase(str(key), p) for p in patterns):
            continue
        v = state[key]
        if str(key).endswith('_registration_id'):
            v = str(v).strip().upper()
        kind = 'datetime' if isinstance(v, datetime) else 'date' if isinstance(v, date) else 'value'
        result[key] = {'type': kind, 'value': v.isoformat() if kind != 'value' else deepcopy(v)}
    canonical(result)  # Reject non-JSON/nonfinite values before any request.
    return result


def observe(slot, data, now):
    """Record a change without replacing an unresolved immutable operation."""
    if canonical(slot.get('observed')) != canonical(data):
        slot['observed'] = deepcopy(data)
        slot['changed_at'] = now
    return canonical(slot.get('saved')) != canonical(data)


def prepare(slot, query, section, version, now, force=False):
    if slot.get('pending'):
        return deepcopy(slot['pending']) if force else None
    if canonical(slot.get('saved')) == canonical(slot.get('observed')):
        return None
    if not force and now - slot['changed_at'] < WAIT:
        return None
    op = dict(query, section=section, record_version=version,
              expected_revision=slot.get('revision', 0), operation_id=str(uuid.uuid4()),
              data=deepcopy(slot['observed']))
    slot['pending'] = op
    # Persist uncertainty BEFORE I/O: a Streamlit interruption must leave a retry control.
    slot['status'] = 'error'
    return deepcopy(op)


def acknowledge(slot, op, response):
    response = response if isinstance(response, dict) else {}
    r = response.get('receipt', {})
    r = r if isinstance(r, dict) else {}
    if (response.get('ok') is not True or response.get('audit_verified') is not True
            or response.get('record_key') != '|'.join((op['registration_id'], op['crf_type'], op['visit']))
            or type(response.get('record_version')) is not int
            or response.get('record_version') != op['record_version']
            or r.get('operation_id') != op['operation_id'] or r.get('section') != op['section']
            or type(r.get('revision')) is not int
            or r.get('revision') != op['expected_revision'] + 1
            or canonical(r.get('data')) != canonical(op['data'])):
        slot['status'] = 'error'
        return False
    slot.update(saved=deepcopy(op['data']), revision=r['revision'], status='saved')
    slot.pop('pending', None)
    return True


def _identity(st):
    from isolated_crf_adapter import actor_key
    actor = actor_key(st)
    return hashlib.sha256(canonical([actor, st.user.get('auth_time'), st.user.get('iat')]).encode()).hexdigest()


def _clear(st, page, clear_resume=False):
    prefixes = (page + '_', 'widget_' + page + '_', '_autosave_' + page)
    if clear_resume:
        # Never show a previous principal's case ID on the resume widgets.
        prefixes += ('_resume_case_' + page, '_resume_visit_' + page,
                     '_resume_action_' + page, '_retry_' + page + '_')
    for key in list(st.session_state):
        if str(key).startswith(prefixes):
            del st.session_state[key]


def resume_panel(page):
    import streamlit as st
    from isolated_crf_adapter import call
    from juog_common import restore_draft_state, valid_registration_id
    try:
        identity = _identity(st)
    except Exception:
        identity = None
    prior = st.session_state.get('_autosave_identity')
    if prior and prior != identity:
        for p in TYPES:
            _clear(st, p, clear_resume=True)
        for key in ('_recovery_subject', '_recovery_visit', '_recovery_open'):
            st.session_state.pop(key, None)
        st.session_state.pop('_autosave_identity', None)
        st.error('本人認証が変更・失効しました。以前の入力を破棄しました。再認証後に下書きを再開してください。')
        st.stop()
    if identity:
        st.session_state['_autosave_identity'] = identity
    with st.expander('自動仮保存の再開・症例／報告時期の切替'):
        st.caption('入力確定後約2秒で変更セクションを保存します。文字入力はEnterまたは欄外クリックで確定してください。「保存しました」を確認してから閉じてください。')
        case = st.text_input('再開するJUOG登録番号', key='_resume_case_' + page).strip().upper()
        visit = st.selectbox('再開する報告時期', VISITS, key='_resume_visit_' + page) if page == 'fu' else ('30d' if page == 'peri' else '90d')
        if st.button('本人権限を確認して下書きを再開', key='_resume_action_' + page, disabled=not identity):
            if not valid_registration_id(case):
                st.error('正しい症例番号を入力してください。')
                return
            from juog_crf_save_ui import pending_attempt
            if pending_attempt(page, st.session_state):
                st.error('正式保存の未確定要求を先に復旧画面で照合してください。')
                return
            query = dict(registration_id=case, facility_code='TEST01', crf_type=TYPES[page], visit=visit)
            result = call(st, 'get_sections', query)
            if not _read_ok(result, query):
                st.error('下書きを照合できません。権限・通信状態を確認して再試行してください。')
                return
            _clear(st, page)
            for e in result['sections'].values():
                restore_draft_state(e['data'])
            st.session_state[page + '_registration_id'] = case
            st.session_state[page + '_reporter_email'] = 'fictional@example.invalid'
            if page == 'fu':
                st.session_state['fu_visit_month'] = visit.replace('m', 'ヶ月') + ('（終了）' if visit == '24m' else '')
            if page in ('fu', 'd90'):
                link = call(st, 'get_crf_linkage', {'registration_id': case, 'facility_code': 'TEST01'})
                if link.get('ok') and link.get('source_found'):
                    st.session_state[page + '_linkage'] = link
            st.session_state['_autosave_' + page] = _loaded(identity, query, result)
            st.success('本人の下書きを照合し、保存済みセクションを読み込みました。' if result['sections'] else 'この症例・報告時期に保存済みの下書きはありません。未保存の入力は復元できません。')


def _read_ok(r, q):
    from isolated_privacy import redact_draft_identifiers
    if not (isinstance(r, dict) and r.get('ok') is True and r.get('audit_verified') is True
            and r.get('record_key') == '|'.join((q['registration_id'], q['crf_type'], q['visit']))
            and type(r.get('record_version')) is int and r['record_version'] >= 0
            and isinstance(r.get('sections'), dict)):
        return False
    page = next((p for p, t in TYPES.items() if t == q['crf_type']), None)
    if page is None:
        return False
    for section, e in r['sections'].items():
        if (section not in SECTIONS[page] or not isinstance(e, dict)
                or not isinstance(e.get('data'), dict)
                or type(e.get('revision')) is not int or e['revision'] < 1):
            return False
        if redact_draft_identifiers(e['data']) != e['data']:
            return False
        for key, value in e['data'].items():
            if (key not in SECTIONS[page][section]['keys'] or not isinstance(value, dict)
                    or value.get('type') not in ('value', 'date', 'datetime') or 'value' not in value
                    or set(value) != {'type', 'value'}):
                return False
            v = value['value']
            if key.endswith('_registration_id') and v != q['registration_id']:
                return False
            if key == 'fu_visit_month' and v != q['visit'].replace('m', 'ヶ月') + ('（終了）' if q['visit'] == '24m' else ''):
                return False
            if key.endswith('_reporter_email') and v and v != 'fictional@example.invalid':
                return False
            try:
                canonical(v)
                if value['type'] == 'date':
                    if type(v) is not str or date.fromisoformat(v).isoformat() != v:
                        return False
                elif value['type'] == 'datetime':
                    if type(v) is not str:
                        return False
                    datetime.fromisoformat(v)
            except (ValueError, TypeError, OverflowError):
                return False
    return True


def _loaded(identity, query, result):
    return dict(identity=identity, query=query, version=result['record_version'], ready=True,
                slots={k: dict(saved=deepcopy(e['data']), observed=deepcopy(e['data']),
                               revision=e['revision'], changed_at=0, status='saved')
                       for k, e in result['sections'].items()})


def section_feedback(page, section):
    import streamlit as st
    # A queued fragment tick can outlive the CRF tree when the parent switches
    # to recovery or stops on an auth failure. Do not emit into that old path.
    # In particular, do not call the transport or start a new draft operation.
    if st.session_state.get('_show_recovery') or st.session_state.get('auth_connect_halted'):
        return
    selected = st.session_state.get('_integration_page')
    if selected is not None and {'30日': 'peri', '90日': 'd90', '6〜24か月': 'fu'}.get(selected) != page:
        return
    from isolated_crf_adapter import call
    from juog_common import valid_registration_id
    from juog_crf_save_ui import pending_attempt
    try:
        identity = _identity(st)
    except Exception:
        st.caption('自動仮保存：本人認証・接続承認の確認待ち')
        return
    case = str(st.session_state.get(page + '_registration_id', '')).strip().upper()
    visit = '30d' if page == 'peri' else '90d' if page == 'd90' else str(st.session_state.get('fu_visit_month', '')).replace('ヶ月（終了）', 'm').replace('ヶ月', 'm')
    if not valid_registration_id(case) or page == 'fu' and visit not in VISITS:
        st.caption('自動仮保存：症例番号・報告時期の入力待ち')
        return
    if pending_attempt(page, st.session_state) or st.session_state.get(page + '_sent') or st.session_state.get('_recovery_blocks_new'):
        st.caption('正式保存の照合中は自動仮保存を停止しています。')
        return
    query = dict(registration_id=case, facility_code='TEST01', crf_type=TYPES[page], visit=visit)
    name = '_autosave_' + page
    state = st.session_state.get(name)
    if state and (state['identity'] != identity or state['query'] != query):
        st.warning('症例・報告時期が変わりました。上部の再開・切替から対象を確認してください。自動保存は停止中です。')
        return
    if not state:
        r = call(st, 'get_sections', query)
        if not _read_ok(r, query):
            st.session_state[name] = dict(identity=identity, query=query, ready=False)
            st.caption('自動仮保存：サーバ照合できませんでした。上部の再開から再確認してください。')
            return
        state = _loaded(identity, query, r)
        if r['sections']:
            state['ready'] = False
        st.session_state[name] = state
    if not state['ready']:
        st.warning('下書きの照合・再開が必要です。上部の再開から読み込んでください。上書きはしていません。')
        return
    slot = state['slots'].setdefault(section, {})
    try:
        dirty = observe(slot, capture(page, section, st.session_state), _clock())
    except (ValueError, TypeError):
        st.error('保存できませんでした。入力値を確認してください。')
        return
    retry = False
    if slot.get('status') == 'error':
        st.error('保存できませんでした。保存結果は未確定です。競合時は下書きを再開し、事務局に照合を依頼してください。')
        retry = st.button('同じ操作IDで再確認', key=f'_retry_{page}_{section}')
    op = prepare(slot, query, section, state['version'], _clock(), force=retry)
    if op:
        overlay = st.empty()
        overlay.markdown(f'<style>.st-key-autosection_{page}_{section} {{position:relative}} .st-key-autosection_{page}_{section}::after {{content:"保存中";position:absolute;inset:0;background:rgba(255,255,255,.65);display:grid;place-items:center;z-index:20;pointer-events:all}}</style>', unsafe_allow_html=True)
        message = st.empty()
        message.info('保存中…')
        try:
            result = call(st, 'save_section', op)
            ok = acknowledge(slot, op, result)
        except Exception:
            slot['status'] = 'error'
            ok = False
        finally:
            overlay.empty()
        if ok:
            message.success('保存しました')
        else:
            message.error('保存できませんでした。成功とは扱いません。同じ操作IDで再確認してください。')
    elif dirty and slot.get('status') != 'error':
        st.caption('変更あり・自動仮保存待ち…')
    elif not dirty:
        st.caption('保存しました（このセクション）')


# Only this status fragment polls; other sections are not rerendered during I/O.
import streamlit as _st
section_feedback = _st.fragment(run_every="1s")(section_feedback)
