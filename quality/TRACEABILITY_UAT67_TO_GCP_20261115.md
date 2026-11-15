# GCP/CSV 要求―UAT67項目トレーサビリティ（初版・未承認）

作成: 2026-11-15 JST。ソースは `review/acl-connection-20261112/uat_evidence/uat67_execution_20261113/UAT67_formal_reconciliation.json`。GCP領域は今回の初期分類であり、正式QAによる適合性評価ではない。

**67件: PASS32 / FAIL1 (AUTH-04) / BLOCKED29 / NOT RUN5。** 本表の作成は正式PASS件数を増減させない。試験証拠は元台帳・元証拠を確認し、承認前に原本性を照合すること。既存PASSは試験した版・環境に限る。

## 優先順と必要な工程
1. **AUTH-04 FAIL / GCP-01,08**：個人情報・完全生年月日・カルテ番号の禁止と正当な年齢等の保持、入力・応答・ログの非漏洩範囲を確定。コード修正・限定隔離実機結果はあるが、全経路の正常入力と不正入力の証拠、自由記載の残存リスク、独立QAが足りない。正式FAILを勝手に解除しない。
2. **POST-01, POST-02, POST-03, FUP-01, FUP-02 / GCP-02,03**：CRF保存→監査→読取→同一UUID再送→訂正履歴を同一版・同一隔離Sheetで検証。v2.2.10候補の保存成功応答とSheet独立読取が不一致のため、保存成功とみなさない。
3. **AUTH・GASセッション/権限境界 / GCP-01**：本人識別・施設ACL・役割ACL・60分失効・再読込・署名要求の拒否を偽装なしの限定実機で再確認する。
4. **DATA-01,02,04 / GCP-07,10**：障害・リストア・監査証跡・全件照合の試験証拠を用意。
5. **ENV/REL/PROD / GCP-04,06,09**：構成/リリース版の同定、変更影響評価、SOP、教育記録、独立QAレビューの順に完了する。

## 初期マッピング一覧（受入基準は元台帳を要参照）

| UAT ID | 正式判定 | リスク | 初期GCPギャップID | 元台帳の受入基準（抜粋） |
| --- | --- | --- | --- | --- |
| ENV-01 | PASS | Critical | GCP-03,GCP-06 | SPREADSHEET_IDがPRODUCTIONと異なるTEST専用シートを指す。 |
| ENV-02 | PASS | Critical | GCP-03,GCP-06 | TESTがPRODUCTIONデプロイID・本番台帳を参照しない。 |
| ENV-03 | BLOCKED | High | GCP-03,GCP-06 | テスト時に参加施設の実メール・本番提出先へ送らない。 |
| ENV-04 | BLOCKED | High | GCP-03,GCP-06 | 現在のテスト対象版と本番版が識別可能。変更履歴が保存される。 |
| PROD-01 | NOT RUN | High | GCP-06,GCP-09 | PRODUCTIONが正常応答し、登録件数がRegistryと一致。書込みを行わない。 |
| PROD-02 | NOT RUN | Medium | GCP-06,GCP-09 | サーバーエラーなく表示される。実患者情報は外部共有しない。 |
| SCR-01 | PASS | Critical | GCP-01,GCP-05 | 同意要件を満たさない申請は正式受付されない。 |
| SCR-02 | PASS | Critical | GCP-01,GCP-05 | 診断時Stage IVを満たさないため適格候補にならない。 |
| SCR-03 | PASS | Critical | GCP-01,GCP-05 | Stage IV経路として受け付け可能（最終MDTは別判定）。 |
| SCR-04 | PASS | Critical | GCP-01,GCP-05 | Stage IV経路として受け付け可能。 |
| SCR-05 | BLOCKED | Critical | GCP-01,GCP-05 | 中央画像・臨床情報による条件確認ができる。 |
| SCR-06 | BLOCKED | Critical | GCP-01,GCP-05 | 3か月以上の条件確認ができる。 |
| SCR-07 | NOT RUN | Critical | GCP-01,GCP-05 | 条件不充足例が正式登録されない。 |
| SCR-08 | PASS | High | GCP-01,GCP-05 | 19歳は除外、20歳は年齢条件を通過。 |
| SCR-09 | PASS | High | GCP-01,GCP-05 | ECOG 2は適格候補にならない。 |
| SCR-10 | PASS | Critical | GCP-01,GCP-05 | プロトコルに定める例外条件を満たす場合のみ進める。 |
| SCR-11 | BLOCKED | High | GCP-01,GCP-05 | 診断時・最終投与後の画像と症例識別コードが照合可能。 |
| SCR-12 | PASS | High | GCP-01,GCP-05 | 欠損・異常は仕様どおり警告／拒否、0は0として保存される。 |
| REG-01 | PASS | Critical | GCP-05,GCP-08 | JUOG-SCR-xxxのみ発行。正式JUOG-xxxは未発番。 |
| REG-02 | PASS | High | GCP-05,GCP-08 | 二重受付や重複行が作られない。 |
| REG-03 | PASS | High | GCP-05,GCP-08 | 同一Screening IDのreview_roundが更新され履歴が残る。 |
| MDT-01 | PASS | Critical | GCP-04 | 判定者ロールと日時、結果が区別され保存される。 |
| MDT-02 | PASS | Critical | GCP-04 | 3名未完了でJUOG番号は発番されない。 |
| MDT-03 | PASS | Critical | GCP-04 | 中央RECIST PD/NEでは正式登録できない。 |
| MDT-04 | PASS | Critical | GCP-04 | 中央RECISTが正式登録判定へ正しく使用される。 |
| MDT-05 | PASS | High | GCP-04 | 不一致の場合は合意形成記録が必要。 |
| MDT-06 | PASS | Critical | GCP-04 | 理由と状態が記録され、正式番号未発行。 |
| MDT-07 | PASS | Critical | GCP-04 | 正式番号未発行、正式登録件数は増加しない。 |
| REG-04 | PASS | Critical | GCP-05,GCP-08 | JUOG-xxxが一つ発行されRegistryとScreening双方で追跡可。 |
| REG-05 | PASS | Critical | GCP-05,GCP-08 | 既存登録番号を保持し、新しいJUOG番号が発行されない。 |
| REG-06 | BLOCKED | Critical | GCP-05,GCP-08 | LockServiceによりJUOG番号が重複しない。 |
| REG-07 | BLOCKED | High | GCP-05,GCP-08 | SURGERY_BEFORE_MDTで拒否される。 |
| REG-08 | BLOCKED | High | GCP-05,GCP-08 | SURGERY_BEFORE_REGISTRATIONで拒否される。 |
| REG-09 | BLOCKED | High | GCP-05,GCP-08 | 4週以上・原則8週以内、合理的理由で最大12週の規定を運用で逸脱なく判定。システム自動判定の範囲も記録。 |
| CAP-01 | PASS | Critical | GCP-05,GCP-06 | cN1-only枠のみ+1（全体+1）。 |
| CAP-02 | PASS | Critical | GCP-05,GCP-06 | cN1-only枠は増えず、全体のみ+1。 |
| CAP-03 | BLOCKED | Critical | GCP-05,GCP-06 | cN1-only枠は増えず、全体のみ+1。 |
| CAP-04 | BLOCKED | Critical | GCP-05,GCP-06 | cN1-only枠は増えない。 |
| CAP-05 | BLOCKED | Critical | GCP-05,GCP-06 | cN1-only枠は+1。 |
| CAP-06 | BLOCKED | Critical | GCP-05,GCP-06 | 20例まで計上、21例目はCN1_CAP_REACHED。 |
| CAP-07 | BLOCKED | Critical | GCP-05,GCP-06 | 42例は許容、43例目はTOTAL_CAP_REACHED。 |
| CAP-08 | BLOCKED | Critical | GCP-05,GCP-06 | SD12例到達後は新規SD登録を保留し、解除なしで13例目を許可しない。 |
| CAP-09 | BLOCKED | High | GCP-05,GCP-06 | 確定した分類が上限管理に反映、または監査可能な手作業管理手順を承認。現コードの自動修正有無は未確認。 |
| CAP-10 | BLOCKED | High | GCP-05,GCP-06 | VOIDは正式登録総数・cN1-only・SDのアクティブ件数から除外。 |
| POST-01 | BLOCKED | Critical | GCP-02,GCP-03,GCP-05 | イベント・日付・Gradeが正確に保存され集計へ取得可能。 |
| POST-02 | NOT RUN | Critical | GCP-02,GCP-03,GCP-05 | 術後30日以内の主要評価イベントに誤算入されない。 |
| POST-03 | BLOCKED | High | GCP-02,GCP-03,GCP-05 | N/Aと実施記録が区別され、必須項目整合性を維持。 |
| POST-04 | BLOCKED | High | GCP-02,GCP-03,GCP-05 | 数値0や病理結果が失われず、データ矛盾が検出される。 |
| POST-05 | PASS | High | GCP-02,GCP-03,GCP-05 | 同一JUOG番号・施設と連携し、出典CRFを追跡できる。 |
| POST-06 | BLOCKED | High | GCP-02,GCP-03,GCP-05 | SOURCE_CRF_UPDATED等で不整合が検出される。 |
| FUP-01 | BLOCKED | High | GCP-02,GCP-03,GCP-05 | 訪問時期、検査、再発・進行、生存情報が正確に取得可能。 |
| FUP-02 | NOT RUN | High | GCP-02,GCP-03,GCP-05 | 規定の入力制御・警告が機能し、確定値を追跡可能。 |
| AUD-01 | PASS | Critical | GCP-02,GCP-08 | append-only記録・record_version・提出者/時刻・理由で差分が追える。 |
| AUD-02 | PASS | High | GCP-02,GCP-08 | 旧判定・新判定・理由・版が残り上書き消去されない。 |
| AUD-03 | PASS | High | GCP-02,GCP-08 | メール不一致ではアクセスを拒否する。 |
| AUTH-01 | PASS | Critical | GCP-01,GCP-08 | 管理画面・データ・登録操作へのアクセス拒否。 |
| AUTH-02 | PASS | High | GCP-01,GCP-08 | ロール外の操作を許可しない。 |
| AUTH-03 | PASS | Critical | GCP-01,GCP-08 | UNAUTHORIZEDを返し書込みは生じない。 |
| AUTH-04 | FAIL | Critical | GCP-01,GCP-08 | 氏名・MRN等は承認外で収集・露出せず、コードによる仮名化を維持。 |
| IMG-01 | BLOCKED | High | GCP-09,GCP-10 | DICOM内部メタデータ・焼込み文字・ファイル名の識別情報がない。 |
| DATA-01 | BLOCKED | Critical | GCP-07,GCP-10 | 定めた手順で復旧可能なバックアップが取得される。 |
| DATA-02 | BLOCKED | Critical | GCP-07,GCP-10 | 登録・CRF・監査履歴・添付紐付けの件数と内容が一致。 |
| DATA-03 | PASS | High | GCP-07,GCP-10 | 主要解析用データが欠損・重複・改変なく抽出される。 |
| DATA-04 | BLOCKED | High | GCP-07,GCP-10 | 連絡先、代替手順、復旧後照合、データ逸失防止が文書化される。 |
| REL-01 | BLOCKED | High | GCP-04,GCP-06 | cN1-only以外の既存機能の挙動を変えていない。 |
| REL-02 | BLOCKED | High | GCP-04,GCP-06 | 変更記録が追跡でき、未実施テストをPASSにしていない。 |
| REL-03 | BLOCKED | Medium | GCP-04,GCP-06 | 必要な操作手順が関係者へ伝わり、版・教育記録が保管される。 |

## 判定・保全の原則
- この表のPASSは**既存正式判定の転記**であり、新版や製品全体のGCP適合性を証明しない。
- ローカル/CIの成功は「技術的確認」と記録し、正式UATの合格とは別に集計する。
- 要求仕様（URS/FS）、リスク評価、試験スクリプト、実測出力、監査ログ、レビュアー、承認日時、対象Git SHA/GAS deployment ID/Spreadsheet IDをRTM行に関連づける。
- 認証情報・患者データをGitHubのログ/報告書へ記録しない。実患者や本番シートへの書込は本計画から除外。
- 通知・患者情報の取扱い・試験の進行について本番/既存TEST/固定隔離環境を変更する場合は、別途承認と保全を要する。
- 状態変更は正式なテストケースの原本台帳と検証証拠が一致した場合だけ行う。

関連: `quality/GCP_READINESS_GAP_REGISTER_20261115.md`、ドラフト PR #18。
