import json, hashlib, html
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[1]
p=root/'UAT67_formal_reconciliation.json'
x=json.loads(p.read_text())
official=Path('uat/integrated_core/final_uat_review/UAT67_current.json')
assert hashlib.sha256(official.read_bytes()).hexdigest()==x['official_register_sha256']
baseline=json.loads(official.read_text())
assert {r['test_id']:r['status'] for r in baseline['rows']}=={r['test_id']:r['status'] for r in x['rows']}
readback=json.loads((root.parent/'boundary_readback_20261113.json').read_text())
x['boundary']={'result':'NOT ESTABLISHED — missing post-deadline live observation','deadline_jst':'2026-11-13T09:41:05+09:00','same_session_ledger_open_count':1,'ledger_deadline_unchanged':True,'evidence':'uat_evidence/boundary_readback_20261113.json','missing':['timestamped post-expiry new-signature refusal','post-expiry access refusal for the same session','reload/Cookie non-extension live outcome','probe DONE/FAILED record'],'cause':'Original browser tabs and in-memory probe state unavailable after runtime inactivity/reset. No durable probe result recovered. Ledger has no per-USE observation timestamps.','formal_pass_delta':0}
x['current_turn_browser_observation']='Original app tab unavailable; only about:blank remains. No new login or request substituted for original session.'
x['current_turn_mutations']='Read-only live Sheets checks; local assessment/report updates only. No live request replay, business write, ACL edit or mode change.'
x['latest_live_evidence_commit']='4e25df7e556c96618137375d3d50c485e37b0239'
x['latest_readback']=readback
x['remaining_negative_tests']=[]
x['negative_test_assessment']={'stale_version':'Confirmed STALE_VERSION refusal; no business changes.','missing_reason':'Functional refusal confirmed. Current deployed v5 validation rejects only REQUIRED:correction_reason as VALIDATION_FAILED. Reviewed UAT criteria require reason/traceability, not the dedicated CORRECTION_REASON_REQUIRED public code. Treat observed discrepancy as harness expectation mismatch against v5; formal API-contract/QA acceptance remains outstanding.','requirements_review_scope':['UAT67_current.json AUD-01 / AUTH-04 criteria','review-branch Markdown/JSON dedicated-code references','v5 diagnostic six-case independent technical review'],'limitation':'This bounded review is not proof that no other approved API contract exists. No production API requirement changed.','live_rerun':False,'formal_pass_delta':0}
qa={'ENV-04','PROD-01','PROD-02','REG-09','DATA-01','DATA-04','REL-02','REL-03'}
for r in x['rows']:
 if r['status']=='PASS':
  r['gap_categories']=[];r['primary_gap']='既済PASS（対象版への適用範囲を維持）'
 else:
  r['gap_categories']=['独立QA・承認不足'] if r['test_id'] in qa else ['実機証拠不足','独立QA・承認不足']
  r['primary_gap']=r['gap_categories'][0]
 r['technical_defect_assessment']='本照合で未解決実装不具合は新規確定せず。未測定条件の正常性を保証しない。'
 if r['test_id']=='AUD-01':
  r['unmet_formal_pass_requirements']='既済PASS維持。新隔離版の古い版・理由欠落拒否は実測済み。VALIDATION_FAILEDの期待値差は診断証拠と併せ正式QAで評価。再送不要。'
 if r['test_id']=='AUTH-04':
  r['unfinished_reason']=r['unmet_formal_pass_requirements']
  r['required_fix_or_action']='既存の16条件拒否・下書き・所有権・CRF・監査の証拠を正式要求へ追跡し、ログ/画面/臨床値保持の残る範囲を評価。独立正式QAの判定までFAILを維持。'
  r['technical_defect_assessment']='元の識別情報不具合に対する修正と限定実測あり。正式FAILの解除条件未充足。全入力への完全自動検出は保証しない。'
 if r['test_id']=='DATA-04':
  r['unfinished_reason']='隔離90日/6月CRFの同一operation復旧と重複なしは実測済み。正式な連絡・代替記録・全体復旧照合SOPおよび承認は未充足。'
 r['evidence_files']=list(dict.fromkeys(r['evidence_files']))
x['unfinished_primary_gap_counts']=dict(Counter(r['primary_gap'] for r in x['rows'] if r['status']!='PASS'))
x['classification_note']='主阻害要因の分類。技術的不具合0は本照合で新規確定した未解決実装不具合が0という意味であり、正式FAIL0や重大問題不存在の保証ではない。複数条件を要する項目はgap_categoriesで併記。'
assert len(x['rows'])==67 and Counter(r['status'] for r in x['rows'])==Counter(x['counts'])
p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
columns=[('test_id','ID'),('status','正式判定'),('primary_gap','主阻害要因'),('live_result','実機証拠'),('tested_version','元台帳の対象版'),('unmet_formal_pass_requirements','残条件'),('evidence_files','証拠参照')]
rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,'')))+'</td>' for k,_ in columns)+'</tr>' for r in x['rows'])
(root/'UAT67_formal_reconciliation.html').write_text('<!doctype html><meta charset="utf-8"><title>JUOG UAT67 formal reconciliation</title><style>body{font-family:sans-serif}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px;vertical-align:top}th{background:#def}</style><h1>JUOG-UTUC01 67項目の正式判定照合</h1><p>PASS32 / FAIL1 / BLOCKED29 / NOT RUN5。新規正式PASS0。60分境界は期限後の実測証拠不足。新規業務送信なし。</p><p>'+html.escape(str(x['unfinished_primary_gap_counts']))+'</p><table><tr>'+''.join('<th>'+v+'</th>' for _,v in columns)+'</tr>'+rows+'</table>')
print(json.dumps({'rows':len(x['rows']),'counts':x['counts'],'primary_gaps':x['unfinished_primary_gap_counts']},ensure_ascii=False))
