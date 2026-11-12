# AUTH-04移行計画・独立技術レビュー

作成日: 2026-11-13。読取レビューと計画のみ。AUTH-04の実送信、業務設定変更、ACL変更、障害注入は実施していない。本書は実行承認ではない。AUTH_CONNECTの承認をAUTH04へ転用しない。

## 判定と既存証拠

AUTH-04への移行は現時点では保留。正式集計はユーザー提示のPASS32 / FAIL1 / BLOCKED29 / NOT RUN5を維持し、本レビューによる増分は0。

既存30操作は承認対象コミット・操作・役割・施設・期待値の対応を確認して再利用し、再実行を既定にしない。`acl_review/test01_e2e_steps.review.json`は複数役割を含むREVIEW ONLYの候補であり、facility一人の実機権限で全操作を再現できる証拠ではない。

`/workspace/scratch/426ea3aa0205/uat/integrated_core/final_uat_review/auth04_results.json`には12種類の架空識別入力について、旧検出漏れ、候補の拒否、状態不変、Python/GASの除去一致、捕捉・復元、生年月・年齢保持のオフライン証拠がある。実画面・実GAS・実ログの証拠には代用しない。古い`session_b2_live_connection_status.json`の未配備等は過去時点の記録であり、現在状態として引用しない。

## 移行前に解消する具体的阻害事項

1. **フロントのprivacy修正未統合**: `session-b2/juog_common.py`および`auth-connect/juog_common.py`の`capture_draft_state`と`restore_draft_state`は、識別子の除去なしに値を保存・復元する旧実装。検証済み修正は`uat/integrated_core/streamlit_connection_candidate/juog_common.py`に存在する。差分を現行フロントへ適用する候補を作り、呼出元、override、入れ子JSON、型復元をレビューして対象ハッシュを固定する必要がある。AUTH_CONNECTはこの業務UIを使わないため現行の限定試験には影響しない。
2. **業務経路の承認は別**: AUTH_CONNECT専用承認では`allRoutesReviewed`、`schemaParityApproved`、`auth04ExecutionApprovalRef`を承認済みと見なせない。AUTH04モードはfacility以外のコード経路も含むため、実行対象のaction allowlistを固定した試験構成をレビューする。切替だけで広い業務経路を無条件に公開しない。
3. **正当な架空症例と下書き所有権**: TEST01、ACTIVE状態、該当CRF・来院時点、日付条件を満たす既存架空fixtureを確認する。`V3_DraftOwners`がない旧下書きは`DRAFT_OWNER_REQUIRED`で拒否される。所有権を推測登録したり、本番の旧下書きを移植してはならない。既存正規所有者が確認できない場合は、完全架空の専用fixture作成を別途承認する。
4. **業務鍵とバックアップ**: AUTH04ではresume derivation key/draft pepperを必要とする。隔離専用値の配置・保管・対象ID確認、復旧可能な開始時点スナップショットが必要。秘密値を証拠へ出さない。
5. **実測の未完**: AUTH_CONNECT残余のACL否定条件と実時間60分境界を完了し、その結果を対象ハッシュに対応付ける。15秒署名期限切れは60分アプリセッション試験の代用にならない。

## AUTH_CONNECTで先に行うACL否定試験案（別のPI承認が必要）

推測issuer/subject、他人のアカウント、架空IDの登録を使わない。同一の正規認証済み本人について、対象V3_Usersの1行を退避し、他の試験操作を止めた状態で1条件ずつ変更する。直接Sheets操作はGASのScriptLockを共有しないため、要求処理完了を待ってから変更・確認・復元する。

| 条件 | 一時操作案 | 期待結果 |
|---|---|---|
| 未登録 | 本人行を管理下で一時的に対象表から外す。issuer/subの捏造は禁止 | 新しい署名のui_contextを拒否 |
| 他施設 | 本人行のfacility_ids_jsonをPI承認済みの非TEST01架空コードに変更 | 拒否。これは他施設への権限付与ではなく、厳密TEST01ゲートの否定試験 |
| 不正ロール | roleを未定義の試験値に一時変更 | 拒否 |
| 期限切れ | valid_untilを過去に変更 | 拒否 |
| 権限失効 | enabledをFALSEへ変更 | 拒否 |

各回、正規値へ復元し、行数・7列値・本人のfingerprint・TEST01・facility・期限2026-11-19 23:59 JSTを照合する。新しい署名で再許可を確認する。未登録行の復元も事前承認に含める。復元不能・不一致・応答不確定なら実行を停止し、管理者が接続設定を無効化する。これらのACL変更は本書だけでは許可されない。

## 60分境界の実測

正規OIDCのiatを起点にdeadline=min(iat+3600, exp)をサーバー内で計算し、証拠には時刻と判定だけ記録する。token/nonce/subjectは出さない。同じトークンを保持し、自動再ログインや新たなOIDC発行を挟まない。期限前に新しい署名のui_contextが許可されること、実時間で期限に到達した後に同じトークンから新規署名を作れず拒否されることを確認する。期限まで待つ間のページ再表示・新タブによる期限延長がないことも確認する。

expがiat+3600より短ければ、それは短いトークン期限の証拠であり、60分境界PASSにしない。境界後は署名自体を作れないのが正常である。GAS側上限はオフライン証拠と区別し、期限前に発行した15秒署名を1時間放置する試験で代用しない。時刻を改ざんした本番トークン、サーバー時計変更、業務日付設定を認証時計に流用しない。

## AUTH-04の実施順序（すべて今後の個別承認後）

各段階前後にD3_Journalの全体ハッシュ/行数とmaterialized業務状態、revision、requests/intents/audits/commits/requestEvents、CRF旧版のハッシュを取得する。B2のOPEN/USE/REVOKEは認証記録として別計数する。認証のUSE追記があることを「業務監査不変違反」と誤判定しない。業務台帳が変更されたことを認証ログの例外で隠さない。

| 順番 | 実操作 | 合格証拠 |
|---|---|---|
| 0 | 対象コード・配備・設定・ACL・架空fixture・業務鍵配置・通知停止・開始snapshot確認 | ID/版/hash一致。AUTH04個別承認、独立レビュー記録 |
| 1 | 実画面に架空の氏名ラベル/MRN/DOB/全角キー/入れ子JSONを順に入力し、捕捉・復元を確認 | 除去対象がdraft payload・復元widgetへ残らず、生年月（YYYY-MM）・年齢・臨床日付は保持 |
| 2 | 同じ完全架空識別入力を署名済みprepare_requestで直接検証 | DIRECT_IDENTIFIER_NOT_ALLOWED。operation_idなし。D3のrequests/intents/audits/commits/業務revision/旧版は不変。画面で除去された結果のみの試験ではGAS拒否を証明できない |
| 3 | 正常な架空下書きをprepare→execute→statusの順に保存 | SAVEDだけでなく唯一のintent/audit/commitと所有権を照合。通信不確定なら新規prepare禁止、元operation_idのstatusで照合 |
| 4 | get_draftで読み、画面を一旦空にして復元 | 正常値・型の一致。読取によるD3/版不変。認証情報や識別値を画面・応答に露出しない |
| 5 | 承認された完全架空legacy下書きの読取・復元 | 返却/復元で識別情報を除去。旧fixture自体は不変。新たにサニタイズ済み下書きを保存するなら別の明示操作と監査。過去journalの消去とは扱わない |
| 6 | 正常CRF v1を正規prepare→execute→status→read_crf | record_key、submission_id、actor、版、業務revision、intent/audit/commitおよび投影の一致。保存成功表示と実保存・監査の一致 |
| 7 | 訂正理由付きv2を正常保存後に読取 | v1のバイト/意味不変、v2だけ追加、正しいaudit。旧expected_record_versionでの要求は拒否しCRF/業務audit不変を確認 |
| 8 | 同じoperation_idの再実行/状態確認、実ログ・通知確認 | 新たな重複版・業務auditなし。ログ、応答、画面、通知に架空識別マーカー/tokenなし。通知実送信なし |

段階2はprepare時の識別拒否なので完全なD3不変を要求できる。一方、意味的検証がexecute時に拒否する場合は、既存PREPAREDとFAILED requestEventが存在し得る。CRF/intent/audit/commit不変とrequestEventの期待差分を分けて判定する。すべての拒否を「全シート不変」と定義しない。

legacy旧下書きはサニタイズされた読取結果と元データの不変を確認する試験であり、保存済み識別情報を遡及削除する実装ではない。Append-only journalに架空legacy fixtureを入れる場合にも承認と明示された保管・後処理方針が必要。実患者情報は禁止。

## 終了・停止基準

不明な応答、意図しない行増加、監査不一致、秘密値/識別マーカー露出、所有権不一致で停止する。自動再送、再ログインでの継続、旧版や監査の手修正は禁止。管理者が接続を無効化し、証拠を保全する。データ復旧や障害注入は別承認。

無ラベル自由文中の人名等を正規表現で完全検出できるとは宣言しない。施設内原資料と中央収集の区別、生年月の許容範囲、入力SOPをPI/DMが確認する。実画面・実GAS・実ログ・通知停止・独立QAの対応証拠が揃うまでAUTH-04 FAILをPASSへ変更しない。本番・既存TEST・Stage1・固定S2-01・mainへの変更および中本先生への依頼は対象外。
