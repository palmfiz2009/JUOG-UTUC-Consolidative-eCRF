# AUTH-04 既存TEST・隔離環境の読取専用点検報告

**Document ID:** AUTH04-READONLY-OBS-20261116  
**Date:** 2026-11-16 (JST)  
**Status:** 読取専用の技術的観測。正式UAT・独立QAではない。  
**実行:** Google Sheets接続の承認済み読取操作。入力・保存・デプロイ・削除・データ修正なし。  
**保護:** 元の生年月日、氏名、MRN、メールアドレス、施設コード、患者・症例ID、トークンは取得結果から出力・GitHub転記していない。

## 対象を限定した確認

| 区分 | 対象 | 使用した範囲 | 集計結果 |
|---|---|---|---|
| UAT staging | 本番に使用しないと表示されるTEST専用Sheets | CRF_Drafts!J2:J250（draft_jsonのみ） | 非空JSON 2件中、full DOBに該当するキーを含む1件を発見。その値は非空でYYYY-MM-DD形式。JSON構文エラー0 |
| 旧TEST（本番ではない） | 既存TEST用Sheets | CRF_Drafts!J2:J250 | 非空JSON 3件中、full DOBに該当するキーを含む1件を発見。その値は非空でYYYY-MM-DD形式。JSON構文エラー0 |
| 隔離AUTH04 | JUOG_AUTH04_INTEGRATION_DISABLED_20261111 | D3_Journal!A2:E250（メタデータ） | データ行164、batch/kind/sha空欄0、batch+kind+partの重複0。**これだけで監査ログの完全性は保証できない** |
| 隔離AUTH04 | 同上 | D3_Journal!F2:F250（断片化された合成ログ内容を集計のみ） | 非空チャンク94中、識別子関連のキーワードを含むチャンク13。ラベル付きの値を検出したチャンク0、明示DOB表記を検出したチャンク0 |

**重要:** いずれもTEST/隔離データに対する限定読取であり、本番データの監査は行っていない。保存形式の存在は確認できたが、実患者のデータ漏洩を示すものではない。新規の画面入力→GAS→Sheets書込→読出し→監査の一連の実機試験は実施していない。

## 解釈と制約
1. **旧TEST仮保存の完全DOB残存を実測。** 旧版にfull DOBを中央保存し得る既知の不具合は、単にコードを変えるだけでは過去レコードから消えない。所有者/データ管理者の承認に基づき、保持・保全・修復/削除の適切な処理を別途決定する必要がある。匿名化・リスク評価の前に勝手な削除・上書きをしない。
2. 検索式は既知のキー・ラベルに限定。氏名と思われる非ラベル自由記載、分割チャンクにまたがる文字列、別シートやブラウザ/HTTP/GAS/Google Cloudログ、外部メール・Dropbox等を網羅していない。**「漏洩がない」とは判定不可**。
3. `D3_Journal`のkindとsha欄の存在・重複なしはハッシュ検証ではない。真正性・完全性・権限主体・履歴再生は別途検証が必要。
4. 既存TESTと隔離AUTH04は別環境。PR #20修正コードは**未デプロイ**で、現在のGAS実機を検証したことにはならない。
5. 独立QA（別人の品質担当）によるレビュー・正式承認が未実施。PR #20に指定レビュアー・承認レビューは現時点ではない。研究者/AIの自己評価を独立QAと呼ばない。
6. 正式UAT AUTH-04は**FAILのまま**。67項目はPASS32/FAIL1/BLOCKED29/NOT RUN5。

## 次の実行と承認ゲート
1. 本番等の保護環境に触れず、隔離AUTH04の有効化/切替方法と、実在のGAS deployment ID・Sheets ID・フロントエンドSHA・固定fixtureを独立技術担当が一致確認する。
2. 入力→仮保存→シート実記録→読出し→監査ログ照合→保存APIログ非露出の15シナリオ（`quality/CSV_OQ_AUTH04_PRIVACY_PROTOCOL_20261116.md`）を、独立承認されたTEST01架空fixtureだけで実行する。
3. 許容データ（年齢、生年月の年月、同意日等）の正しい保存を確認し、否定試験でのサーバ書込0と、API/画面/ログ非露出を証明する。
4. 旧TESTに識別子が残った件は、権限者が実データの保持区分を確認し、削除/修復/保全の根拠を文書化する。結果だけを限定集計で共有。
5. 合格/失敗の証拠をバージョン固定したRTMへ追加し、別人のQA担当が適切に評価する。正式リリースやUAT判定変更は承認後に行う。

**判定:** Restricted read-only scan COMPLETE; live write/read/audit/non-leak E2E NOT EXECUTED; INDEPENDENT QA NOT DONE; AUTH-04 FAIL remains unchanged.

## 追補：隔離ACL構造およびAPI例外応答の安全化

- 隔離環境の`V3_Users!D2:G100`を読み取り専用で限定調査：1行存在し、enabled 1件、facilityロール 1件、TEST01施設への権限記載 1件、従前PI指定の2026-11-19を含む有効期限記載 1件。issuer/subject/user_id（A–C列）は読み出していない。**実ログイン・有効なセッション・GASへの到達・実機保存の証明ではない**。
- 本番mainのGASには、内部例外の生メッセージをAPIへ返す経路があったため、PR #20候補では `SERVER_ERROR` / `DRAFT_PARSE_ERROR` / `SOURCE_PAYLOAD_PARSE_ERROR` の応答を固定コードに変更（生の例外文字列を出さない）。
- `tests/test_auth04_error_boundary.mjs` で、実際の`doPost`関数を架空の秘密値を含む例外で呼び出し、応答が`SERVER_ERROR`だけで秘密値を返さないことを検証。GitHub Actionsのオフラインテストで成功。
- 実際のGAS・Google Cloud・Streamlit運用ログは接続していない。監査ジャーナルの限定文字列走査と、架空例外に対する単体テストを**実機ログ漏洩検証と同一視しない**。
- 実保存・読出し・独立QAについては、専用隔離デプロイへ正規認証して操作できるブラウザ実行環境と、独立QA担当者の正式指定/承認が必要。現利用可能な無料Google Sheets/GitHub操作にはGAS Web Appを認証して操作する機能がなく、別途有料ブラウザ実行は事前の費用制約に基づき利用していない。

### 追補後の状態
- TEST旧データ残存: **検出**（匿名化した集計証拠のみ）
- 新コードのPrivacy/例外応答オフライン検証: **PASS**
- 隔離GAS + Streamlitの実入力→保存→復元→監査照合: **NOT EXECUTED**
- GAS/Cloud/HTTP実ログの非漏洩確認: **NOT EXECUTED**
- 独立QA: **NOT ASSIGNED / NOT APPROVED**
- 正式UAT AUTH-04: **FAIL継続**
