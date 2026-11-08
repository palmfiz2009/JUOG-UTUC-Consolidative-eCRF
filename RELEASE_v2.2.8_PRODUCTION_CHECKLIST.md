# JUOG-UTUC01 v2.2.8 本番移行チェックリスト（要承認）

> **状態：未デプロイのリリース候補。** これだけで正式UAT合格や実患者登録の安全性を保証するものではありません。
> 本番のGoogle Sheetsへのダミー患者作成・行削除・手動変更は行わない。

## 0. 確認済み事項（2026-11-08）
- UAT専用GASで主要経路62チェック、追加56チェックがPASS。HOLD→第2ラウンド3職種→JUOG-001発番、30日・90日・追跡CRFと監査ログの保存。
- UAT専用Streamlitの事務局画面で登録済み表示を確認。30日CRFの仮保存→再開も確認。
- 本番 `JUOG_UTUC_Registry` のRegistry/Screeningに実レコードなし（閲覧時点）。
- 本番版はv2.2.7。今回の候補v2.2.8は**未デプロイ**。
- UATの118チェックは正式67ケースの全項目合格ではない。実画像を用いる中央RECIST判定も、この自動試験の対象外。

## 1. 事前保全・権限確認
- 本番GASの現在の**デプロイID・バージョンと現在の実装の控え**を残す（ロールバック用）。
- 本番Streamlitの現行コミットとSecretsのバックアップを、権限管理された安全な場所に保存する。**SecretsをGitHubやChatGPTに貼らない。**
- 施設用の認証、患者識別情報の扱い、アカウント共有の可否、操作ログの不足、利用者教育を試験のGCP/個人情報保護要件に照らして承認する。
- メール送信先のリストと通知内容（特に施設内識別コードの記載）を研究事務局が確認。

## 2. GAS Script Properties（本番プロジェクトのみ）
以下のプロパティ名について存在・接続先を確認。**値は表示・共有しない**。

```text
SPREADSHEET_ID
JUOG_EXPECTED_PRODUCTION_SHEET_ID
JUOG_API_TOKEN
DRAFT_CODE_PEPPER
JUOG_ADMIN_ACTION_TOKEN
JUOG_REVIEWER_RADIOLOGY_ACTION_TOKEN
JUOG_REVIEWER_MEDICAL_ONCOLOGY_ACTION_TOKEN
JUOG_REVIEWER_UROLOGY_ACTION_TOKEN
```

- `SPREADSHEET_ID` と `JUOG_EXPECTED_PRODUCTION_SHEET_ID` は別途Google Driveから確認した同一の本番台帳IDを設定。TEST台帳IDは使用しない。
- 4種のロールトークンは**新規の本番専用**にし、UAT用・会話に貼られた鍵を再利用しない。
- `JUOG_API_TOKEN` を不用意にローテーションしない。切替時はStreamlit側と整合させる。
- 確認用スクリプト `JUOG_Production_Preflight_v228.gs` は読み取り専用。コードを本番GASに追加し、`juogProductionPreflight_v228` を実行するとトークン内容をログに出さず照合する。正常系は `JUOG_PRODUCTION_PREFLIGHT PASS_READ_ONLY`、障害は `NOT_READY`。これは本番URL・SMTP・実際の画面ログインの検証にはならない。

## 3. Streamlit Secrets（本番アプリのみ）
- `[registry]` の `url` が**本番GAS Webアプリの /exec** を指すこと、`token` が本番GASの `JUOG_API_TOKEN` と一致することを画面外で確認。
- `[registry_role_tokens]` の `admin`, `radiology`, `medical_oncology`, `urology` と本番GASのロールキー4つを対応づける。
- 既存の `[admin]`, `[reviewer_passwords]`, `[email]`, `[office]` 等を意図せず消さない。UAT Secrets全体を本番にコピーしない。
- 検証環境に使ったメールの送信停止実装を本番に含めないことを確認。

## 4. リリースと動作確認（承認後）
1. 本番GASの編集画面にv2.2.8のコードを反映。**Webアプリは新バージョンとしてデプロイし、既存の本番 /exec IDを維持する**ことを優先。実際の対象台帳・実装バージョン・ロールトークンを直前再確認。
2. ロール権限制御は3職種・事務局のアクセス拒否/許可をHTTP経由で検証。テストで本番患者データを作らない。
3. Streamlitの本番デプロイを v2.2.8 に切替。事務局画面の表示が `Backend v2.2.8`、`PRODUCTION`、本番台帳名であることを確認。単なるSheet名で環境判定しているため、必ず実IDと照合。
4. メール機能は**患者情報のないテスト文面**で承認済みの専用メール宛に実送信して到達を確認する。誤宛先・本文中の不要な識別子がないことを確認。
5. 登録フォーム・事務局画面・3職種のレビュー画面・CRFの表示と仮保存を点検する。真の患者登録では中央放射線診断医が**実画像をRECIST v1.1で独立に確認**。
6. 正式UATの未実施ケース、運用マニュアル、障害時の代替手順と責任者の署名・判断を記録してから実運用可否を判定。

## 5. 失敗時
- 本番の動作異常があれば、新規患者登録は一時停止。
- 本番GAS Webアプリの直前の正常なデプロイ版へ戻し、本番Streamlitも直前コミットへ戻す（実施者と時刻を記録）。
- スプレッドシートの患者レコードを消してロールバックしない。

## 未確認の本番リリース阻害条件
- **本番GAS Script Propertiesへのアクセス権が現在このチャットにはない**ため、値の一致や実際のデプロイ先は未確認。
- **本番Streamlit Secretsとデプロイ管理**もこのチャットから直接操作・確認できない。
- 実SMTP送信・本番HTTPロール分離・登録フォーム全ケースの実機UATは未検証。
- 施設側は個別のアカウント認証ではなく番号・施設情報等に依存する操作があるため、利用者認証・データ取扱いの妥当性を最終承認する必要がある。
