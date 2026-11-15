# CAPA-AUTH04-001 — TEST/隔離仮保存における完全生年月日の残存

**Status:** OPEN / QUALITY REVIEW PENDING / NOT A RELEASE APPROVAL  
**Created:** 2026-11-16 JST  
**Classification:** Privacy and data-integrity potential nonconformity; affected data is in TEST-only Sheets (not verified in production)  
**System:** JUOG-UTUC01 Streamlit + GAS + Google Sheets  
**Links:** PR #20, `quality/AUTH04_READONLY_EVIDENCE_20261116.md`, `quality/CSV_OQ_AUTH04_PRIVACY_PROTOCOL_20261116.md`

## 1. 事実関係（識別情報は転記しない）
- UAT staging のCRF_Drafts（非空2件）から、直接識別情報に当たる完全生年月日型フィールドが非空の1件で検出された。
- 別の旧TEST CRF_Drafts（非空3件）にも同様の1件があった。
- いずれもセルの値そのもの・症例ID・氏名・MRN等は出力していない。完全DOB形式の値が実際にあることのみ検証した。
- 本番Google Sheetsは調査していないため、実患者に対する影響は**未評価**。同一の2つのTESTレコードが同一人物を指すかも判定していない。
- 現行UIの登録申請では生年月日入力が年齢計算に必要だが、仮保存 state のシリアライズに含まれ得る。正式申請では年齢と出生年月（年月）を使う。

## 2. 初期原因仮説（確定前）
- 広い session_state の capture が `reg_birth_date` を含み、仮保存先へ転送する。
- 旧GASの `containsDirectIdentifier_` は `birth_date` 等、限られたキー名しか検出しないため、`reg_birth_date` を見落とし得る。
- これらは静的コード分析から導かれる原因候補。個々の旧データの流入経路・日時・操作者の確認はこれから。

## 3. 既実施の封じ込め
- 本番・既存TEST・隔離環境の既存行を修正・削除・上書きしていない。
- PR #20の隔離修正候補：画面側で完全DOBを仮保存から除外し、GASで英語/日本語キー・JSON/明示ラベル付き自由記載を拒否、旧下書きの読出し時にマスク。エラー例外の文字列もAPIへ返さない。
- 新しい実GAS関数をメモリ内Sheetsに接続した8シナリオ（保存/読出し/拒否/マスク/所有者/破損データ）および従前の静的・オフライン試験がPASS。
- ただし **本番で「修正済み」とは言えない**：候補はmainへ未統合、GAS未デプロイ。

## 4. 残存リスク
- 保存済み過去データは読取マスクだけでは消えない。バックアップ、監査、履歴、共有権限を含む対応方針が必要。
- 入力自由記載の非ラベル姓名/日付は正規表現のみでは完全検出できない。
- 生年月日が画面・通信・例外・クラウド/アプリ・Webサーバログに露出しないことはまだ実測していない。
- QAの正式承認、サイト別アクセス/ロール管理、法令/研究計画書の要件レビューは未了。

## 5. 是正/予防計画（未承認の本番操作を伴わない）
| Action | 具体措置 | Exit evidence | Status |
|---|---|---|---|
| CA-01 | 画面仮保存から完全DOBを除外 | 申請・仮保存・再開の正常経路をGAS実機で照合 | Code candidate / live evidence pending |
| CA-02 | GAS保存前の全入力経路の識別情報拒否 | 事前承認15試験、業務表への書込0・入力保持等 | Code candidate / live evidence pending |
| CA-03 | 旧下書きの読取マスク | 旧レコードのハッシュ変更なし・画面/API非露出 | Offline PASS / isolated live pending |
| CA-04 | 内部例外メッセージの非露出 | HTTP APIおよび実Cloud/GASログと画面の照合 | Offline PASS / live pending |
| CA-05 | TEST過去データの取扱い方針 | 権限者による保全・保持/修復/削除とログの正式承認 | Pending |
| CA-06 | 本番の影響範囲の適切な管理者評価 | 最小限・権限分離・匿名集計・監査記録 | Not authorised / not performed |
| PA-01 | QAレビュー、運用SOP/入力禁止文言、定期漏洩スキャンと教育 | 文書・教育履歴・定期監査 | Pending |

## 6. 決定権限と完了基準
- PI/個人情報保護担当/データ管理責任者/独立QAが、対象研究の適用要件に従い、正式なリスク分類・対応・レビューを承認する。
- 記録の処分・本番への適用・認証情報の扱いは権限者だけが行う。AIは勝手に権限を変更したり削除・メール送信をしたりしない。
- **AUTH-04 formal FAIL remains** until version-pinned full real-system OQ and independent QA evidence is accepted.
- この文書の作成を正式なCAPA終了・GCP適合の宣言としない。
