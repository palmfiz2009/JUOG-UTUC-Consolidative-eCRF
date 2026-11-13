import json, hashlib
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parent
matrix=json.loads((root.parent/'uat67_execution_20261113/UAT67_formal_reconciliation.json').read_text())
groups={
 'A':['SCR-05','SCR-06','SCR-07','SCR-11','REG-06','REG-07','REG-08']+[f'CAP-{i:02}' for i in range(3,11)],
 'B':['POST-01','POST-02','POST-03','POST-04','POST-06','FUP-01','FUP-02'],
 'C':['ENV-03','IMG-01','DATA-02','REL-01'], 'D':['AUTH-04'],
 'QA':['ENV-04','PROD-01','PROD-02','REG-09','DATA-01','DATA-04','REL-02','REL-03']}
details={
 'SCR-05':'架空の中央画像・臨床判定を役割別に提出し、各担当・一致/不一致・監査を確認。医師の判定そのものをAIで代替しない。',
 'SCR-06':'cNED等の原条件を満たす対照/満たさない対照を3か月境界で作成。正式日数定義は原仕様照合後に固定。',
 'SCR-07':'cM1条件不充足→保留/拒否→適格対照。原台帳のcM1期間定義を確認し、正式登録不可とrevision不変を確認。',
 'SCR-11':'IMG-01と同じ架空DICOMで診断時/最終投与後の症例コード照合。逆対応は拒否。外部アップロードなし。',
 'REG-06':'独立した正規認証要求2本で同時finalize_mdt。返却JUOG番号の一意性とRegistry/監査の件数を照合。',
 'REG-07':'手術日がMDT前の対照をSURGERY_BEFORE_MDTで拒否。適格日付へ戻して登録し版/監査を照合。',
 'REG-08':'手術日が登録前の対照をSURGERY_BEFORE_REGISTRATIONで拒否。登録日と同日の境界も確認。',
 'CAP-03':'原台帳の非cN1-only分類で全体のみ+1、cN1-only不変。CAP-04/05と同一集計読取を共有。',
 'CAP-04':'cT4等のcN1-only非該当例を原台帳に従い対照化しcN1-only非加算を確認。登録適格性と枠算入を混同しない。',
 'CAP-05':'cT3以下/cN1/cM0の適格対照で全体+1、cN1-only+1。',
 'CAP-06':'架空スナップショット19→20許可→21拒否CN1_CAP_REACHED。他の枠は上限未満に固定。',
 'CAP-07':'架空スナップショット41→42許可→43拒否TOTAL_CAP_REACHED。他の枠は上限未満に固定。',
 'CAP-08':'SD11→12許可→13保留/拒否。上限解除なし。全体/cN1枠は非拘束状態。',
 'CAP-09':'中央分類訂正前後で枠と監査を照合。自動訂正APIがない場合、承認済み手順の実測へ切替し実装を迂回しない。',
 'CAP-10':'void_registrationを理由・approval_ref付きで実施。ACTIVEのみの全体/cN1/SD計上から除外、旧記録保持。',
 'POST-01':'JUOG-971手術あり候補でGrade IIIaの術後30日イベント→保存/読取/集計/監査。',
 'POST-02':'同症例の31日イベントを30日CRFで拒否。90日CRFの31–90日領域へ正常保存し主要評価誤算入なしを確認。',
 'POST-03':'既済970非手術N/Aを再利用し971手術あり対照の必須項目と表示・保存の差を確認。',
 'POST-04':'病理評価不能理由/その他詳細の欠落拒否→復元→保存。CRP0、出血量0、病理径0の保持と不正値拒否。',
 'POST-06':'971の30日v1→v2後、90日/追跡の旧参照拒否→実際に返却された最新版/提出IDへ再結合。',
 'FUP-01':'再発/PD/死亡の完全架空分岐を6月以降の正当な訪問で保存/読取/集計。検査省略理由も原条件に照合。',
 'FUP-02':'PD日が評価日後、死亡原因欠落、再発詳細欠落を拒否→同一フォーム復元→正当保存。旧版不変。',
 'ENV-03':'現行隔離版の通知/アップロード全入口の禁止と非到達を確認。旧TESTへの適用範囲は別判定。外部送信で検証しない。',
 'IMG-01':'ローカル生成DICOMのメタデータ/ファイル名/画素に架空マーカーを埋め込み、除去/拒否を検査。焼込み文字は目視評価を併用。実患者画像・外部Dropbox禁止。',
 'DATA-02':'匿名化済み隔離スナップショットを別の新規隔離復元先へ復元しRegistry/全CRF/全版/監査/添付対応を全件比較。元台帳へ復元しない。',
 'REL-01':'差分影響マップで必要回帰だけを選び、原32PASSの対象版との差を追跡。A/B/C/D完了証拠を再利用。',
 'AUTH-04':'16条件拒否と保存/復元/訂正/監査を再利用。正常臨床値・画面/応答/ログの非露出範囲、自由記載リスクの証拠と正式QA判断を補う。'}
qa={
 'ENV-04':('隔離GAS v5、フロント69030ab9、既存TEST版保全記録','本番稼働版とソースの対応証明。権限者から非秘密の版証明を受領。'),
 'PROD-01':('未実施。原合格条件を保持','PIが読取実施者・時間・画面/総件数のみの範囲を指定。Registry一致は担当者側で確認し個票を取得しない。'),
 'PROD-02':('未実施。原合格条件を保持','PROD-01と同一枠で画面遷移/サーバー異常の有無のみ確認。患者情報の画面撮影/外部持出しなし。'),
 'REG-09':('既存4–12週等8条件の画面証拠','延期理由の医学的判断者と判断・承認保存先を指定しSOP承認。期間例外を新設しない。'),
 'DATA-01':('原保存期間の確認、既存バックアップ部分証拠','バックアップ頻度/責任者/保存先/アクセス権/保持期限/復元演習頻度を承認し履行記録を提出。'),
 'DATA-04':('90日/6月の同一operation復旧・重複なしの実測','障害連絡先、代替記録、復旧後照合の責任分担を承認し机上演習と実演記録を提出。'),
 'REL-02':('レビューコミット・隔離v5のSHA対応','旧GAS v6を含む変更履歴との対応、仕様変更の承認番号、欠測/未実施の区別を正式確認。'),
 'REL-03':('既存説明資料・手順参照','正本マニュアル版、MDT全手順、対象者/受講日/教育内容/理解確認/教育者署名の実記録を提出。')}
rows=[]
for group,ids in groups.items():
 for id in ids:
  old=next(r for r in matrix['rows'] if r['test_id']==id)
  rows.append(dict(test_id=id,group=group,formal_status=old['status'],criterion=old['pass_criterion'],existing_evidence=old['evidence_files'],scenario=details.get(id,qa.get(id,('',''))[1]),evidence_resolved_this_turn=False,formal_pass_delta=0,approval_required=True if group in ['A','B','C','QA'] else False,remaining=old['unmet_formal_pass_requirements']))
assert len(rows)==35 and len({r['test_id'] for r in rows})==35
assert set(r['test_id'] for r in rows)==set(r['test_id'] for r in matrix['rows'] if r['status']!='PASS')
out={'baseline_commit':'241d9f9094c83b701340059b1ae98cdc56fa258a','counts':matrix['counts'],'group_counts':dict(Counter(r['group'] for r in rows)),'live_evidence_resolved':0,'new_formal_pass':0,'rows':rows}
(root/'UAT35_batch_plan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
lines=['# 27項目の依存関係別・限定実機試験計画','', '計画書。現行AUTH_CONNECT維持。承認前の業務送信・役割付与・外部アップロードは行わない。', '', '|ID|正式判定|原合格条件|試験シナリオ|','|---|---|---|---|']
for r in rows:
 if r['group']!='QA':lines.append('|'+ '|'.join([r['test_id'],r['formal_status'],r['criterion'],r['scenario']])+'|')
lines+=['','## 実施順と共通評価','', '1. 版/SHA・AUTH_CONNECT・業務台帳66行の基準を再確認。別の隔離fixture領域を予約し、fixtureハッシュとAPI allowlistを承認時に固定。既存970とその監査は保持する。','2. A群の正規役割認証・割当が成立したら中央判定/登録/上限を実行。B群はA群とは独立した登録済み971候補を使用できるが初期化は別途承認対象。','3. B群の正常保存と拒否を交互に行い、C群の復元・回帰、D群の臨床値保持へ同じ証拠を再利用。','4. 各操作のbefore/afterで旧CRF版/最新版/業務revision/業務監査/requestEventを比較。拒否でrequestEventが追加されても業務書込みと混同しない。','5. 実測は正規署名とGAS本人ACLを通す。operation_idを固定し、遅延時はstatus照会で確認してから同じIDで許可された回復だけを行う。新IDで再送しない。','6. 対象外更新、予期しない許可、秘密値露出があれば停止しAUTH_CONNECTへ戻す。既存業務履歴を削除して復元しない。','','## fixture と権限の具体的境界','','- A群：TEST01内の新規架空スクリーニングfixture A-SCR01〜08、上限用A-CN1/A-TOTAL/A-SDの分離スナップショット。名称は未予約。実JUOG番号はサーバー返却値を記録し推測で固定しない。19/41/11件の初期状態を設定するバッチは一覧・hash・件数を固定してから1回実行。','- B群：JUOG-971は既存の手術例候補、未作成/未allowlist。登録2026-04-01、手術2026-04-13、30日2026-05-13、31日2026-05-14、90日2026-07-12、6月2026-10-13。正当性は原仕様に照合し、初期化監査には実際の操作時刻を記録する。','- A群のfacility/radiology/medical_oncology/urology/adminは役割名であり、本人登録の承認ではない。PIが実担当者を指定し、正規OIDCで照合した者だけを割り当てる。全施設権限、本人ロールの無断変更、架空subject登録は禁止。','- B群は現在のfacility本人を再利用。既存970の新規保存は不要。C群の復元先ID/権限は未指定なので復元を実行しない。','','## 読取・書込APIの限定候補','','- A facility：submit_screening / get_screening_draft。MDT：list_review_cases / get_screening_crf / get_own_review / submit_mdt_review / get_mdt_reviews。admin：list_screenings / get_screening / finalize_mdt / stats / void_registration。分類訂正は既存ルート/SOPに対応するか未確定であり、未知APIを許可しない。','- B/D：save_draft / get_draft / get_crf_linkage / save_crf / read_crf。実際のprepare/execute/status封筒は承認済みoperation manifestへ束縛する。削除APIは含めない。','- C：隔離バックアップ取得・新規別領域復元・ローカル画像検査。外部Dropbox/メール/画像アップロードAPIは含めない。','','現在のv5限定ガードは970と限られたAUTH-04操作に束縛されている。A/Bを単にフラグ変更で通さない。拡張ガード候補・ソースSHA・fixture一覧・役割割当のレビューが完了するまで、この計画の承認だけで送信可能にはならない。']
(root/'BATCH_EXECUTION_PLAN.md').write_text('\n'.join(lines)+'\n')
lines=['# 正式QA 8項目の一括評価票','', '8/8の評価票を作成。QA承認・実記録が揃ったという意味ではない。AI技術レビューは正式第三者QAを代替しない。','', '|ID|既存証拠・状態|必要な判断/提出記録|QA判定|','|---|---|---|---|']
for id,(evidence,gap) in qa.items():lines.append(f'|{id}|{evidence}|{gap}|未評価・未署名|')
lines+=['','正式QA記入欄：担当者（独立性確認）、評価日、対象版、証拠参照、承認/差戻し、残リスク、署名。全欄未記入。中本先生への依頼は行わない。','','各票の原合格条件と既存証拠ファイル名はUAT35_batch_plan.jsonに保持。元の全添付が現物再取得済みとは主張しない。']
(root/'QA8_REVIEW_PACKET.md').write_text('\n'.join(lines)+'\n')
manifest={}
for folder in [root,root.parents[1]/'acl_review/boundary_durable_candidate']:
 for file in folder.iterdir():
  if file.is_file() and file.name!='SHA256_manifest.json':manifest[str(file.relative_to(root.parents[1]))]=hashlib.sha256(file.read_bytes()).hexdigest()
(root/'SHA256_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'groups':out['group_counts'],'rows':len(rows),'live_resolved':0}))
if __name__=='__main__':pass
