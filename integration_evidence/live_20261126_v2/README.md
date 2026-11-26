# 2026-11-26 隔離実機：30日CRF訂正Version 2と復旧

## 実施範囲・結果

ユーザーがこの会話で承認した既存隔離GASの2ファイル反映・既存URLの更新を実施。候補コード `f95866b3abfdbd564909b37556cfb6a00d6918d2`。本番、既存TEST、Stage 1、固定S2-01、mainには変更なし。外部メール停止、ACL・Secrets・署名期限・セッション失効は変更なし。新しいアプリ・デプロイIDは作成していない。

- GAS管理UIは **バージョン2（2026/11/26 16:15 JST）** 更新完了を表示。同じデプロイID/URLを維持。
- 編集前に2ファイル全文をUIのコピーで取得し、基準コミットのSHA256と一致することを確認。他者差分なし。
- 本人認証期限切れによる接続停止を実測。ログアウト後、許可されたGoogleアカウントを選択して再ログイン。新しいパスワード入力・直近再認証の保証はしていない。
- JUOG-901（TEST01・完全架空）の既存Version 1を保持して訂正入力。自動仮保存の局所オーバーレイ、保存完了表示を実測。
- 16:22 JST頃に画面が消失。コンソールには `Cannot send rerun backMessage when disconnected from server.`。リロード後に本人・症例を再照合し、サーバ保存済みの訂正理由・日付・病理データから再開。
- **16:29:08 JSTに訂正の正式保存を1回実行。UI応答は AUTH_EXPIRED（不合格）**。成功表示なし。
- 新しいUUID `af16acfd-e8aa-4d56-87ef-926b42a20af1` のINTENTは07:29:18.246Z、COMMITは07:29:26.929Z。CRF Version 2と監査行は各1件。COMMIT receiptはexisting=false/audit_verified=true。
- 復旧画面への切替時にも画面消失。コンソールで **Bad delta path index 10 (should be between [0, 3])** を捕捉。
- リロード後、既存復旧画面の「サーバの記録を照合」を実行。**Version 1とVersion 2のUUID・監査一致を実画面に表示**。Version 2の再送・新しいUUIDの生成は行わなかった。
- 独立したSheetsコネクタ読取りで、照合操作の前後にCRF・監査・操作履歴が不変であることを確認。Version 1・2のみ、重複なし。臨床dataの差はWBCの数値5→6・raw文字列"5"→"6"のみ。

## コード照合

| ファイル | 変更前SHA256 | 変更後SHA256 |
| --- | --- | --- |
| 05_registry_google_apps_script.gs | 593f516524393ba7b95772fec2df4eb2dcdf7b9dfc77ee865e2450f88bbff092 | eb9c5fd1cf3b52391878d5d470f2c538ed93863bd1e9c7ec2699b3af3a409667 |
| isolated_crf_endpoint.gs | ea44ee5814cd23f54904ffbdc4d91cdf32276c0199dd02ac920a3b6e9ca3396a | 1763bf1dd265a310111b653a081ba2ac1a3d36d1d468ceb46c2e38db8c3b8919 |

Registryは保存後にUIコピーで全文ハッシュを再検証。endpointは貼付前の全文ハッシュ一致・保存操作・デプロイ完了までを確認（保存後再コピーは未実施）。他7ファイルは変更していない。

## 未解決の重大事項

1. I/O削減後も正式保存応答がAUTH_EXPIRED。Version 2はCOMMITまで到達したが、通常経路で保存完了を表示できない。解消扱いにしない。保存後の署名期限チェックを削除・延長していない。
2. Streamlit描画消失/Bad delta path。認証停止または復旧画面へ移った後に旧CRFの定期fragmentが出力し得る点への抑止候補を `isolated_autosave_ui.py` に追加。停止・復旧中は出力もAPI呼出しもしない回帰試験を追加。**このUI修正は隔離開発ブランチのみ、Streamlitへ未反映、実機解消は未確認**。通信断全体の根本原因を確定したとは主張しない。
3. 訂正を新しいブラウザ状態から始める場合、正式保存済みpayloadが自動で編集フォームに入らず、手入力が必要だった。今回、入力値を保存後に全data比較してWBC以外不変を確認した。

## 証拠・判定の限界

- `juog_deployment_v2_20261126.txt`：管理UIの更新完了。
- `after_disconnect_*.json` / `after_disconnect_checks.json`：画面消失時の独立Sheets読取り。CRF・監査・操作履歴は旧Version 1のまま。下書き46イベント中、訂正用15イベント。全イベント外側digest一致。
- `juog_correction_resumed_20261126.txt`：サーバ下書き復元。
- `juog_v2_before_submit_20261126.txt`：送信前の全画面値・必須検証完了。
- `juog_v2_auth_expired_20261126.txt`：失敗表示。
- `after_save_*.json`：独立Sheets読取り。
- `juog_v2_reconciled_20261126.png` / `.txt`：実画面でV1/V2監査一致。
- `verify_evidence.py` / `comparison.json`：実測採取データの12整合性チェック。これはオフラインの証拠再検算であり、独立QAではない。
- 生HTTP原応答は未取得。保存receiptは操作台帳から読取り。CRF/監査/操作台帳の取得範囲はA1:Z20（payload_json全文を含む）。Zより右のflattened列は独立比較していない。

**正式UATの新規PASSは0。既存台帳PASS0/BLOCKED74のPASSを増やさない。開始前QA承認は既存記録を再利用するが、この実測結果の独立QA判定を代行しない。上記2事象は技術的FAILとして明示する。90日・6〜24か月の今回実機試験は未実行。**

ロールバックが必要な場合は同じdeploymentを旧GAS Version 1へ戻す。Sheets行・監査・B2 headを巻き戻さない。旧writerは再開しない。
