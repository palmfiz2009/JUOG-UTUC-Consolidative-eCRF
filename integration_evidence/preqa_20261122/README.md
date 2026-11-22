# 承認前の技術修正・検証 — 2026-11-22 JST

開始HEAD `78b4f127ffdbc55a86119a090f663fb1a0875bd6`。PR #15は別HEADのDraft。GitHubの全151ファイルをGit blob SHAで一致確認した新規作業コピーを使用し、以前のローカル差分を上書きしていない。

## 修正と検証

| 問題 | 修正 | 証拠 |
|---|---|---|
| 保存後に画面再読込しか案内されず、同じブラウザで訂正入力へ戻れない | 保存時の許可済みフォーム値を凍結。保存済み画面に訂正開始を追加。新しい本人認証・サーバのUUID/Version/監査・最新Version照合が成立したときだけ入力を復元。競合・失効・不明結果は状態を保持して拒否。新UUIDは次の正式送信時だけ作成 | test_correction.py、test_autosave_ui.pyの3画面、GASの全9visit v1/v2/CAS |
| 臨床入力エラーを未確定要求として固定してしまう | 最初の臨床検証をネットワーク/要求固定より前に移動。未送信の入力エラーは修正可能。送信済み/不明結果のUUIDは従来通り固定 | test_crf_save_ui.py：不正→通信0・attemptなし→修正後正常保存 |
| 完了済み要求の結果を別症例/別visit/別payloadへ返す可能性 | 完了応答の再利用にも同一要求の照合を追加。不一致は成功を返さない | test_crf_save_ui.py：別症例/visit/UUID拒否、同一要求は追加保存なし |
| 下書き読出しで保存時の型/症例/連絡先/識別情報検証を再適用していない | GAS読出しと再試行に共通検証を適用。Python復元にも識別情報拒否を適用。ダイジェストを再計算しても不正データを読戻さない | GAS追加群：不正な保存済みdataの読出し/再送拒否、CRF/監査/operation/下書き追記0 |
| 「患者氏名 テスト太郎」等の空白区切りが検出対象外 | Python/GAS双方で明示ラベル＋空白区切りを拒否。任意の氏名を完全に検出できるとの主張はしない | Python訂正復元拒否、GASの氏名/カルテ/生年月日/全角空白の保存拒否 |

- 全回帰：**Python 198件 PASS**（fixture76＋bridge20＋PR43＋adapter59）。前回190件から8件追加（各ケース内の全9visitや異常系subtestを含む）。
- **GAS 42試験群 PASS**（40＋2）。既存GAS監査回帰・識別情報14ケースもPASS。
- **臨床差分8,062ケース、差異0、254条件到達、253条件両分岐**。残る1条件は先行schema拒否で到達しない分岐。未検証の分岐を合格にしていない。
- 254条件の式と3validate_allのASTは基準と同一。生成物は新しいソース行・hashへ同期。臨床判断を変更していない。
- 本物のStreamlit AppTestで3画面の訂正開始と全9visitの別セッション再開を確認。署名通信/本人情報は架空ダブル、GASはインメモリGoogleサービス。実ブラウザ・実GAS・実Sheets試験ではない。
- 実行環境Python3.12.14、Streamlit1.67.0。run_offline.pyはPython TCPを拒否。Nodeのテストは実GASソース＋インメモリ代替。通知は無送信。
- 原ログ7本、summary/clinical_coverage/checks.jsonを同フォルダーに保存。過去の原ログは上書きせず保持。

## 配備・実機準備

- `tools/prepare_isolated_uat.py`：既存候補へ配備する9本のGASを明示し、ローカル限定でコピー/hash manifestを生成・再読戻し。実際に9/9一致を確認。署名鍵・qaRefを作成せず、ネットワークも配備もしない。
- `gas_bundle_manifest.json`：今回の配備候補コードのhash一覧。
- `UAT_30D_FIRST_PASS.md`：対象環境、単一writer、バックアップ/復旧、B2、配備順序、JUOG-901の入力→仮保存→再開→Version1→保存行/監査照合、判定基準と証拠ファイル名。
- `CLINICAL_DECISIONS.md`：原本・現行実装・提案・PI判断欄を8項目で整理。P05は原本要約の12週間と表の暦3ヶ月の表現差も明記。全件未決。
- 74項目対応表の依存条件から、解消済みの本人ACL/ownerを未完了扱いする古い説明を除き、現在の証拠へ接続。状態は74件すべてBLOCKEDのまま。

## GitHub Actions

従来のworkflow_dispatchだけでは、デフォルトブランチにないworkflowを起動できない。mainを変更せず、既存隔離ブランチのコードpushのみを実行条件へ追加した。公開repo限定・標準ubuntu-latest、contents:readのみ、デプロイ/Secrets/外部送信なし。artifact uploadを外し、計算結果はjobログへ出す。料金の追加が必要な機能は使わない。

参照：[手動workflowのdefault-branch条件](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)、[公開repo標準runnerとログの扱い](https://docs.github.com/en/billing/concepts/product-billing/github-actions)。この時点のHosted実測はchecks.jsonに記載し、ローカルPASSを転記しない。

## 残る条件

中本先生による実レビュー・署名（今回修正したコード差分を含む）、PIの臨床8項目決裁、配備時の単一writer/整合バックアップ/接続binding実測、実機試験と独立QA結果が必要。既存の包括承認をQA承認として使わない。MAIL-02/03は通知実装と限定宛先/送信承認が別途必要で、現在の候補は送信停止を維持する。全体の復元リハーサル、通信障害/同時実行、実機UIの保存中表示・再開は未実測。

**正式UAT：PASS 0／FAIL 0／BLOCKED 74／NOT RUN 0、新規PASS 0。** 今回、GAS・Sheets・ACL・Streamlit設定・本番・既存TEST・Stage1・固定S2-01・mainは変更していない。
