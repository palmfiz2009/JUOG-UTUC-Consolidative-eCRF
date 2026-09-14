# v2.2.2 移行手順

## 1. GitHub
以下を同じrepositoryへ上書き/追加する。
- 01_registration_crf.py
- 02_perioperative_30d_crf.py
- 03_day90_crf.py
- 04_followup_crf.py
- 05_admin_mdt_registration.py
- 06_mdt_reviewer.py（新規）
- juog_common.py
- streamlit_app.py
- requirements.txt

## 2. Google Apps Script
1. 現在のCode.gsをローカルにバックアップ。
2. `05_registry_google_apps_script.gs` の全内容へ置換して保存。
3. `setupRegistry()` を実行。
   - 既存Registryは削除しない。
   - v2.1の既存Screening行にはreview_round=1を補完する。
   - MDTReviews / ScreeningCRF / CRF_30d / CRF_90d / CRF_Followup / CRFSubmissionAuditを作成する。
4. 「デプロイを管理」→既存Webアプリを編集→「新バージョン」→デプロイ。
5. WebアプリURLは既存deploymentを更新する限り原則同じ。

## 3. Streamlit Secrets
既存 `[email]`, `[registry]`, `[admin]` を保持し、以下を追加する。

```toml
[reviewer_passwords]
radiology = "LONG_RANDOM_PASSWORD"
medical_oncology = "LONG_RANDOM_PASSWORD"
urology = "LONG_RANDOM_PASSWORD"
```

実際のパスワードをGitHubへ保存しない。

## 4. Reboot
Streamlitの Manage app → Reboot app。
サイドバーに6ページが表示されることを確認する。

## 5. UAT
実患者ではなくTEST症例を使用する。
1. 中央MDT申請 → JUOG-SCR番号発行
2. 放射線診断役で判定
3. 腫瘍内科役で判定
4. 泌尿器科役で判定
5. 事務局画面で3/3表示
6. 全員合意を確認 → JUOG正式番号発行
7. CRF_30dへ初回報告保存
8. 同じ時点を「訂正報告」で再提出しversion 2になることを確認
9. 90日、Follow-upも各Sheetへ保存されることを確認
10. 別TEST症例を不適格にし、Screeningには残るがRegistryへ入らないことを確認
11. 保留→追加情報再提出でreview_roundが増え、旧判定が新ラウンドに流用されないことを確認

## 6. 本番前
- このチャット等に露出したRegistry tokenを `rotateApiToken()` で更新しStreamlit Secretsも更新。
- 露出済みGmail App Passwordを失効し、新規発行してSecretsを更新。
- TESTデータを本番集積から明確に分離する（推奨：UAT専用Sheet）。
- MDT判定者/事務局への自動メール通知先を最終設定する。


## v2.2 → v2.2.1 の追加手順
Apps Scriptをv2.2.1へ差し替えて `setupRegistry()` を1回実行してください。既存行は削除されません。`Registry` / `Screening` / `ScreeningAudit` に不足するRECIST関連列が追記され、既存登録例は `screening_id` を用いて可能な範囲で `site_recist` と `recist_concordance` が補完されます。


## v2.2.1 → v2.2.2 の追加手順
GitHub側は `01_registration_crf.py`, `02_perioperative_30d_crf.py`, `juog_common.py` を含むv2.2.2一式へ更新します。Apps Scriptも `05_registry_google_apps_script.gs` をv2.2.2へ差し替え、既存Webアプリを新バージョンとして再デプロイしてください。`setupRegistry()` は既存データを削除しないため、列/シート整合確認目的で1回実行して構いません。

この版では画面側だけでなくApps Script側でも、明らかな桁違いおよび重要な日付矛盾をhard stopします。したがってStreamlitだけ更新してApps Scriptを旧版のままにしないでください。
