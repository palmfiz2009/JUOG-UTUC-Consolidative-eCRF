# 中嶋將仁氏向け JUOG-UTUC01 技術QA一括パッケージ

PI指定：中嶋 將仁／ITF合同会社／プログラマー・エンジニア。担当予定。受諾・開発関与・独立性・秘密保持・アクセスは未確認。連絡・共有・権限付与なし。評価・署名は未記入。医学判断はPI/医学担当者。

## 最初に評価する項目

POST-04、FUP-02を優先。原条件・既存実測・版・不足の対応は ../live_gap_readonly_20261114/QA_PRIORITY_AND_CONTRACT.md。POST-04のpCR等、FUP-02の死亡日/補助療法矛盾の網羅性を省略しない。正式PASSには中嶋氏の実評価が必要。

## 今回補完した実測証拠

../live_gap_readonly_20261114/native_export_result.json：隔離SheetsのネイティブXLSXを実取得し、独立API値と全165行の正規化後SHA一致、70sealed batch検証、旧3batch保全、971の6版の全臨床payload一致を確認。生XLSXは本人識別子を含む可能性があるため同梱・GitHub公開しない。権限者側の原本照合が必要な場合は別途許可された場所で行う。

原POST-01/02/FUP-01はアプリ内集計機能を指定していない。前回のアプリ経路必須という扱いを撤回し、新しい集計機能を正式UAT要件へ追加しない。POST-01の取得可能性は実XLSXで補完。POST-02の31日拒否/90日保存と30日イベント分離は既存実測と今回出力で照合でき、主要評価算入規則の採否はQA/医学担当者へ。FUP-01は9/12/15/18/21/24か月の実保存・読取が不足。6か月結果を流用しない。

## checkpoint原因と修正

GASはAUTH_CONNECT、フロントauth04_runtime.jsonはenabled=true/stage=AUTH04_APPROVEDのまま。entryはenabledだけでB971ハーネスを起動し、セッション状態消失時に業務request_status/read_crfを要求する。GASが拒否し、例外がcheckpoint総称に隠れる。この構成不整合が確認できた。個々の既存要求のエラー応答は今回再取得していない。

../../acl_review/auth_connect_stop_recovery/streamlit_app.py は認証専用入口の最小修正候補。既存context/署名/ui_context/ACL検証を再利用し、B971・実時間boundary・業務APIを起動しない。5回帰確認済み。未デプロイ・独立技術レビュー未完。CRFフォームへの到達まで完成したとは扱わない。反映には限定デプロイ承認が必要。

## 16項目評価票

|ID|正式状態|原合格条件|未充足条件|
|---|---|---|---|
|POST-01|BLOCKED|イベント・日付・Gradeが正確に保存され集計へ取得可能。|既存保存・監査証拠と今回出力証拠に対する正式QA評価。アプリ内集計機能の新設は要求しない。|
|POST-02|NOT RUN|術後30日以内の主要評価イベントに誤算入されない。|主要評価算入規則に対するQA/医学担当者の評価。|
|POST-03|BLOCKED|N/Aと実施記録が区別され、必須項目整合性を維持。|対象版の画面到達・条件付き必須の証拠対応|
|POST-04|BLOCKED|数値0や病理結果が失われず、データ矛盾が検出される。|独立QAによる合格条件充足・版適用範囲の評価|
|POST-06|BLOCKED|SOURCE_CRF_UPDATED等で不整合が検出される。|承認済みAPI契約による外部期待コードの正式判断。読み替え未実施|
|FUP-01|BLOCKED|訪問時期、検査、再発・進行、生存情報が正確に取得可能。|原操作が要求する9/12/15/18/21/24か月の保存・読取実測不足。追加保存は現承認外。|
|FUP-02|NOT RUN|規定の入力制御・警告が機能し、確定値を追跡可能。|独立QAの正式評価|
|AUTH-04|FAIL|氏名・MRN等は承認外で収集・露出せず、コードによる仮名化を維持。|画面/HTTP/ホスト/GASログの非露出、監査・バックアップ直接アクセス管理の実測、自由記載SOP、独立QA。正式FAIL維持|
|ENV-04|BLOCKED|現在のテスト対象版と本番版が識別可能。変更履歴が保存される。|権限者による本番の非秘密版証明とQA|
|PROD-01|NOT RUN|PRODUCTIONが正常応答し、登録件数がRegistryと一致。書込みを行わない。|PIによる読取実施者/対象/時間/個票非取得の承認|
|PROD-02|NOT RUN|サーバーエラーなく表示される。実患者情報は外部共有しない。|PROD-01と同枠の限定読取承認と正式QA|
|REG-09|BLOCKED|4週以上・原則8週以内、合理的理由で最大12週の規定を運用で逸脱なく判定。システム自動判定の範囲も記録。|医学的判断者、承認保存先、延期理由SOP承認|
|DATA-01|BLOCKED|定めた手順で復旧可能なバックアップが取得される。|バックアップ責任者/頻度/保管/アクセス権/保存期間と履行記録|
|DATA-04|BLOCKED|連絡先、代替手順、復旧後照合、データ逸失防止が文書化される。|障害連絡・代替記録・復旧照合SOPと演習記録|
|REL-02|BLOCKED|変更記録が追跡でき、未実施テストをPASSにしていない。|変更管理の正式評価、仕様変更承認、未実施の扱い|
|REL-03|BLOCKED|必要な操作手順が関係者へ伝わり、版・教育記録が保管される。|正本手順版・担当者・教育記録・署名|

## 全67項目（正式判定は変更なし）

|ID|正式状態|合格条件|
|---|---|---|
|ENV-01|PASS|SPREADSHEET_IDがPRODUCTIONと異なるTEST専用シートを指す。|
|ENV-02|PASS|TESTがPRODUCTIONデプロイID・本番台帳を参照しない。|
|ENV-03|BLOCKED|テスト時に参加施設の実メール・本番提出先へ送らない。|
|ENV-04|BLOCKED|現在のテスト対象版と本番版が識別可能。変更履歴が保存される。|
|PROD-01|NOT RUN|PRODUCTIONが正常応答し、登録件数がRegistryと一致。書込みを行わない。|
|PROD-02|NOT RUN|サーバーエラーなく表示される。実患者情報は外部共有しない。|
|SCR-01|PASS|同意要件を満たさない申請は正式受付されない。|
|SCR-02|PASS|診断時Stage IVを満たさないため適格候補にならない。|
|SCR-03|PASS|Stage IV経路として受け付け可能（最終MDTは別判定）。|
|SCR-04|PASS|Stage IV経路として受け付け可能。|
|SCR-05|BLOCKED|中央画像・臨床情報による条件確認ができる。|
|SCR-06|BLOCKED|3か月以上の条件確認ができる。|
|SCR-07|NOT RUN|条件不充足例が正式登録されない。|
|SCR-08|PASS|19歳は除外、20歳は年齢条件を通過。|
|SCR-09|PASS|ECOG 2は適格候補にならない。|
|SCR-10|PASS|プロトコルに定める例外条件を満たす場合のみ進める。|
|SCR-11|BLOCKED|診断時・最終投与後の画像と症例識別コードが照合可能。|
|SCR-12|PASS|欠損・異常は仕様どおり警告／拒否、0は0として保存される。|
|REG-01|PASS|JUOG-SCR-xxxのみ発行。正式JUOG-xxxは未発番。|
|REG-02|PASS|二重受付や重複行が作られない。|
|REG-03|PASS|同一Screening IDのreview_roundが更新され履歴が残る。|
|MDT-01|PASS|判定者ロールと日時、結果が区別され保存される。|
|MDT-02|PASS|3名未完了でJUOG番号は発番されない。|
|MDT-03|PASS|中央RECIST PD/NEでは正式登録できない。|
|MDT-04|PASS|中央RECISTが正式登録判定へ正しく使用される。|
|MDT-05|PASS|不一致の場合は合意形成記録が必要。|
|MDT-06|PASS|理由と状態が記録され、正式番号未発行。|
|MDT-07|PASS|正式番号未発行、正式登録件数は増加しない。|
|REG-04|PASS|JUOG-xxxが一つ発行されRegistryとScreening双方で追跡可。|
|REG-05|PASS|既存登録番号を保持し、新しいJUOG番号が発行されない。|
|REG-06|BLOCKED|LockServiceによりJUOG番号が重複しない。|
|REG-07|BLOCKED|SURGERY_BEFORE_MDTで拒否される。|
|REG-08|BLOCKED|SURGERY_BEFORE_REGISTRATIONで拒否される。|
|REG-09|BLOCKED|4週以上・原則8週以内、合理的理由で最大12週の規定を運用で逸脱なく判定。システム自動判定の範囲も記録。|
|CAP-01|PASS|cN1-only枠のみ+1（全体+1）。|
|CAP-02|PASS|cN1-only枠は増えず、全体のみ+1。|
|CAP-03|BLOCKED|cN1-only枠は増えず、全体のみ+1。|
|CAP-04|BLOCKED|cN1-only枠は増えない。|
|CAP-05|BLOCKED|cN1-only枠は+1。|
|CAP-06|BLOCKED|20例まで計上、21例目はCN1_CAP_REACHED。|
|CAP-07|BLOCKED|42例は許容、43例目はTOTAL_CAP_REACHED。|
|CAP-08|BLOCKED|SD12例到達後は新規SD登録を保留し、解除なしで13例目を許可しない。|
|CAP-09|BLOCKED|確定した分類が上限管理に反映、または監査可能な手作業管理手順を承認。現コードの自動修正有無は未確認。|
|CAP-10|BLOCKED|VOIDは正式登録総数・cN1-only・SDのアクティブ件数から除外。|
|POST-01|BLOCKED|イベント・日付・Gradeが正確に保存され集計へ取得可能。|
|POST-02|NOT RUN|術後30日以内の主要評価イベントに誤算入されない。|
|POST-03|BLOCKED|N/Aと実施記録が区別され、必須項目整合性を維持。|
|POST-04|BLOCKED|数値0や病理結果が失われず、データ矛盾が検出される。|
|POST-05|PASS|同一JUOG番号・施設と連携し、出典CRFを追跡できる。|
|POST-06|BLOCKED|SOURCE_CRF_UPDATED等で不整合が検出される。|
|FUP-01|BLOCKED|訪問時期、検査、再発・進行、生存情報が正確に取得可能。|
|FUP-02|NOT RUN|規定の入力制御・警告が機能し、確定値を追跡可能。|
|AUD-01|PASS|append-only記録・record_version・提出者/時刻・理由で差分が追える。|
|AUD-02|PASS|旧判定・新判定・理由・版が残り上書き消去されない。|
|AUD-03|PASS|メール不一致ではアクセスを拒否する。|
|AUTH-01|PASS|管理画面・データ・登録操作へのアクセス拒否。|
|AUTH-02|PASS|ロール外の操作を許可しない。|
|AUTH-03|PASS|UNAUTHORIZEDを返し書込みは生じない。|
|AUTH-04|FAIL|氏名・MRN等は承認外で収集・露出せず、コードによる仮名化を維持。|
|IMG-01|BLOCKED|DICOM内部メタデータ・焼込み文字・ファイル名の識別情報がない。|
|DATA-01|BLOCKED|定めた手順で復旧可能なバックアップが取得される。|
|DATA-02|BLOCKED|登録・CRF・監査履歴・添付紐付けの件数と内容が一致。|
|DATA-03|PASS|主要解析用データが欠損・重複・改変なく抽出される。|
|DATA-04|BLOCKED|連絡先、代替手順、復旧後照合、データ逸失防止が文書化される。|
|REL-01|BLOCKED|cN1-only以外の既存機能の挙動を変えていない。|
|REL-02|BLOCKED|変更記録が追跡でき、未実施テストをPASSにしていない。|
|REL-03|BLOCKED|必要な操作手順が関係者へ伝わり、版・教育記録が保管される。|

詳細の既存証拠・版・不足は同梱QA16.json/UAT67.json。正式集計PASS32/FAIL1/BLOCKED29/NOT RUN5。担当者指定は署名完了を意味しない。
