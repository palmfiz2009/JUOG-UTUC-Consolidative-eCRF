"""Recovery inside the existing fixture application. Never generate a submission UUID."""
from isolated_crf_adapter import call
PAIRS={'30日':('perioperative_30d','30d'),'90日':('day90','90d'),**{f'{m}か月':('followup',f'{m}m') for m in [6,9,12,15,18,21,24]}}

def _saved(item):
 """A server state label alone is not an audit-backed save receipt."""
 return (isinstance(item,dict) and item.get('state')=='SAVED'
         and item.get('audit_verified') is True
         and type(item.get('version')) is int and item['version']>0
         and isinstance(item.get('uuid'),str) and bool(item['uuid'].strip()))

def _valid_recovery(reply,query):
 if not isinstance(reply,dict) or reply.get('ok') is not True:return False
 recovery=reply.get('recovery')
 key='|'.join((query['registration_id'],query['crf_type'],query['visit']))
 if (not isinstance(recovery,dict) or recovery.get('record_key')!=key
         or not isinstance(recovery.get('operations'),list)
         or recovery.get('state') not in ('SAVED','RETRY_ALLOWED','NO_SERVER_RECORD','NEEDS_RECONCILIATION')):return False
 operations=recovery['operations']
 if any(not isinstance(item,dict) or not isinstance(item.get('uuid'),str)
        or not item['uuid'].strip() or item.get('state') not in
        ('SAVED','RETRY_ALLOWED','NEEDS_RECONCILIATION') for item in operations):return False
 if len(set(item['uuid'] for item in operations))!=len(operations):return False
 if any(item['state']=='SAVED' and not _saved(item) for item in operations):return False
 if recovery['state']=='SAVED' and (not operations or not all(_saved(item) for item in operations)):return False
 return True

def render(st):
 st.subheader('保存状態の照合・復旧')
 st.caption('入力や送信IDを失った場合も、新しい送信を作らず本人・症例・報告時点を照合します。')
 subject=st.text_input('照合するJUOG登録番号',key='_recovery_subject').strip().upper()
 label=st.selectbox('照合する報告時点',list(PAIRS),key='_recovery_visit')
 typ,visit=PAIRS[label];q={'registration_id':subject,'facility_code':'TEST01','crf_type':typ,'visit':visit}
 # Query again for every action/rerun; never trust a previous browser receipt.
 if not st.button('サーバの記録を照合',key='_recovery_check') and not st.session_state.get('_recovery_open'):return
 st.session_state['_recovery_open']=True
 st.session_state['_recovery_blocks_new']=True
 r=call(st,'recovery_status',q)
 if not _valid_recovery(r,q):
  st.error('保存状態を確認できません。新規送信せず事務局へ照合を依頼してください。');return
 recovery=r['recovery']
 for item in recovery.get('operations',[]):
  if _saved(item):st.success(f"正式保存を照合しました：Version {item['version']} / UUID {item['uuid']} / 監査一致")
  elif item['state']=='RETRY_ALLOWED':
   st.warning('サーバに元の送信内容が保持されています。同じUUIDで照合・再試行できます。')
   if st.button('同じUUIDで照合・再試行',key='_recover_'+item['uuid']):
    # Server selects canonical payload. No payload, digest or expected version supplied by browser.
    result=call(st,'recovery_retry',{**q,'submission_id':item['uuid']})
    check=call(st,'recovery_status',q)
    verified=_valid_recovery(check,q) and any(x['uuid']==item['uuid'] and _saved(x) for x in check['recovery']['operations'])
    if isinstance(result,dict) and result.get('ok') is True and verified:st.success('同一UUIDの正式保存と監査を再照合しました。Versionの重複追加はしていません。')
    else:st.error('結果は未確定です。新規送信せず事務局へ照合を依頼してください。')
  else:st.error('記録の整合性を確認できません。事務局による照合が必要です。')
 if recovery.get('state') in ('NO_SERVER_RECORD','NEEDS_RECONCILIATION'):
  st.error('保存結果を確定できません。新規送信は停止し、事務局へ照合を依頼してください。')
  st.session_state['_recovery_blocks_new']=True

 if recovery.get('state')=='SAVED':
  st.session_state['_recovery_blocks_new']=False
  verified={x['uuid'] for x in recovery['operations'] if _saved(x)}
  for page in ('peri','d90','fu'):
   attempt=st.session_state.get('_juog_'+page+'_save_attempt')
   payload=attempt.get('payload') if isinstance(attempt,dict) else None
   if (isinstance(payload,dict) and payload.get('submission_id') in verified
       and payload.get('record_key')==recovery['record_key']
       and payload.get('registration_id')==subject
       and payload.get('crf_type')==typ and payload.get('visit')==visit):
    attempt['status']='complete'
