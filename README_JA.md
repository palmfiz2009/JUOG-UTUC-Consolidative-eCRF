# JUOG UTUC_Consolidative eCRF 完成版（試験開始前 v1.0）

このフォルダは、研究計画書 第2版（2026/08/15）を基準として、登録判定、周術期・30日、90日、6〜24か月定期経過を共通仕様で統一した eCRF 一式です。

## ファイル
- `01_registration_crf.py`：スクリーニング、適格性、中央MDT、中央症例登録
- `02_perioperative_30d_crf.py`：手術、術中情報、病理、術後30日安全性
- `03_day90_crf.py`：90日（90±14日）安全性・再発/進行評価
- `04_followup_crf.py`：6/9/12/15/18/21/24か月定期経過
- `juog_common.py`：全CRF共通の施設名、検査項目、バリデーション、RECIST補助、メール、JSON、中央登録照合
- `05_registry_google_apps_script.gs`：JUOG-001, JUOG-002... の中央連番発番・重複防止
- `secrets.toml.example`：Streamlit Secrets 設定例
- `requirements.txt`：実行環境
- `PROTOCOL_ALIGNMENT.md`：研究計画書との対応表
- `UAT_CHECKLIST.md`：実患者登録前の受入試験
- `TEST_REPORT.md`：実施済み自動テスト

## 登録番号の考え方
研究計画書上の2種類のコードを分けています。

1. **施設内研究対象者識別コード**
   - 各施設が氏名等との対応表を施設内で管理する仮名コード
   - 登録判定/MDT時に使用
   - 氏名、カルテ番号そのものは入力しない

2. **JUOG登録番号**
   - 中央登録確定時に `JUOG-001`, `JUOG-002`... と自動発番
   - 以後の全CRFの共通キー
   - 同時登録でも重複しないよう Google Apps Script `LockService` を使用

## 中央登録台帳の設定
1. 研究事務局専用の Google Sheet を新規作成する。
2. 拡張機能 → Apps Script を開く。
3. `05_registry_google_apps_script.gs` を貼り付ける。
4. `setupRegistry()` を1回実行する。
5. 実行ログに表示される `JUOG_API_TOKEN` を控える。
6. Apps Script を Web app としてデプロイする。
7. Web app URL と token を Streamlit Secrets の `[registry]` に設定する。

中央台帳は、
- 同一施設＋同一施設内識別コードの二重登録を防止
- 目標登録数42例で自動停止（Settingsで事務局のみ解除可能）
- cN1 20例到達後を自動停止
- SD 12例到達後を一時保留
- 後続CRFで JUOG番号と施設の組み合わせを照合
します。

## Streamlit の配置
4本を同じ GitHub repository に置き、`juog_common.py` も同じ階層に置いてください。

同じ repository から4つの Streamlit app を作成し、それぞれ main file を以下に指定する方法がシンプルです。

- Registration：`01_registration_crf.py`
- Perioperative/30d：`02_perioperative_30d_crf.py`
- Day90：`03_day90_crf.py`
- Follow-up：`04_followup_crf.py`

4 app 全てに同じ Secrets を設定します。

## Secrets
`secrets.toml.example` を参照してください。

Gmail のアプリパスワード、Registry API token は GitHub に置かず、Streamlit Secrets のみに保存してください。

## 日付窓
- 30日評価：30日 ±14日。範囲外でも入力を禁止せず、逸脱理由を保存。
- 90日評価：90日 ±14日＝術後76〜104日。術後84日は正常な許容範囲。
- 6〜24か月：計画書は「術後3か月毎」で日単位の許容幅を規定していないため、カレンダー月で目安日を表示し、30日超のずれは警告するが入力を禁止しない。
- 手術関連合併症の主要/副次評価は訪問日とは別に、実際の手術後30日以内、90日以内で判定する。

## RECIST 1.1
登録CRF内の標的病変計算は入力整合性確認の**補助**です。最終的なRECIST判定は中央/放射線診断医の総合判定を使用します。

補助計算では、
- 標的病変 最大5病変、1臓器最大2病変
- 非リンパ節：長径
- リンパ節：短径、標的病変として15 mm以上を目安
- PR：baselineから30%以上減少
- PD：治療中の最小SLD（nadir）から20%以上かつ絶対5 mm以上増加
- 新病変、非標的病変の明らかな増悪：PD
を扱います。

## CTCAE
有害事象は CTCAE v6.0（JCOG日本語訳最新版を参照）で記録する前提です。Grade、発現日、処置、転帰などは詳細欄に記録してください。

## メール → Excel 自動取込
全CRFメール末尾に以下を付加します。

```
--- MACHINE_READABLE_JSON_START ---
{...}
--- MACHINE_READABLE_JSON_END ---
```

共通キー：
- `registration_id`
- `crf_type`
- `visit`
- `record_key`
- `submission_id`
- `submitted_at`
- `submission_kind`
- `correction_reason`

Excel/データベース側では `record_key` ごとに最新版を採用しつつ、`submission_id` は監査履歴として全件保持する設計を推奨します。

## 本番開始前に必ず行うこと
`UAT_CHECKLIST.md` をダミー症例で一巡させてください。特に、実環境の Gmail、Streamlit Secrets、Google Apps Script、Google Sheet 権限はローカルのコードテストだけでは検証できません。

本パッケージはデータ品質チェックを自動化しますが、RECIST、適格性、因果関係、Clavien-Dindo/CTCAE Grade の最終臨床判断は、研究計画書に従い担当医・中央MDT・研究事務局が行います。
