"""Recovery inside the existing fixture application. Never generate a submission UUID."""
from isolated_crf_adapter import call
PAIRS={'30日':('perioperative_30d','30d'),'90日':('day90','90d'),**{f'{m}か月':('followup',f'{m}m') for m in [6,9,12,15,18,21,24]}}
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
 if r.get('ok') is not True:
  st.error('保存状態を確認できません。新規送信せず事務局へ照合を依頼してください。');return
 recovery=r.get('recovery',{})
 for item in recovery.get('operations',[]):
  if item['state']=='SAVED':st.success(f"正式保存を照合しました：Version {item['version']} / UUID {item['uuid']} / 監査一致")
  elif item['state']=='RETRY_ALLOWED':
   st.warning('サーバに元の送信内容が保持されています。同じUUIDで照合・再試行できます。')
   if st.button('同じUUIDで照合・再試行',key='_recover_'+item['uuid']):
    # Server selects canonical payload. No payload, digest or expected version supplied by browser.
    result=call(st,'recovery_retry',{**q,'submission_id':item['uuid']})
    check=call(st,'recovery_status',q)
    verified=check.get('ok') is True and any(x.get('uuid')==item['uuid'] and x.get('state')=='SAVED' and x.get('audit_verified') is True for x in check.get('recovery',{}).get('operations',[]))
    if result.get('ok') is True and verified:st.success('同一UUIDの正式保存と監査を再照合しました。Versionの重複追加はしていません。')
    else:st.error('結果は未確定です。新規送信せず事務局へ照合を依頼してください。')
  else:st.error('記録の整合性を確認できません。事務局による照合が必要です。')
 if recovery.get('state') in ('NO_SERVER_RECORD','NEEDS_RECONCILIATION'):
  st.error('保存結果を確定できません。新規送信は停止し、事務局へ照合を依頼してください。')
  st.session_state['_recovery_blocks_new']=True

 if recovery.get('state')=='SAVED':
  st.session_state['_recovery_blocks_new']=False
  verified={x['uuid'] for x in recovery['operations'] if x.get('state')=='SAVED'}
  for page in ('peri','d90','fu'):
   attempt=st.session_state.get('_juog_'+page+'_save_attempt')
   if isinstance(attempt,dict) and attempt.get('payload',{}).get('submission_id') in verified:
    attempt['status']='complete'
