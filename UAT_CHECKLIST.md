# v2.2.2 本番前UATチェックリスト

- [ ] Streamlitに6ページ表示
- [ ] 施設申請でJUOG-SCR番号を発行
- [ ] Screeningに現在状態が保存
- [ ] ScreeningCRFに詳細CRFが保存
- [ ] 中央保存データにfull DOB/氏名/MRNが含まれない
- [ ] 放射線診断役が独立判定を保存
- [ ] 腫瘍内科役が独立判定を保存
- [ ] 泌尿器科役が独立判定を保存
- [ ] 判定者ページで他者の判定を表示しない
- [ ] MDTReviewsに3名分が保存
- [ ] 3名未完了では正式登録不可
- [ ] 3名不一致時に自動多数決せず、合意形成記録が必須
- [ ] 適格例のみJUOG番号を発行
- [ ] 不適格例はScreeningに保持、Registryには入らない
- [ ] 保留→再提出でreview_roundが増える
- [ ] 42例/cN1 20例/SD 12例制御が有効
- [ ] 30日CRFがCRF_30dへ保存
- [ ] 90日CRFがCRF_90dへ保存
- [ ] Follow-upがCRF_Followupへ保存
- [ ] 同じrecord_keyの二重「初回報告」を拒否
- [ ] 「訂正報告」はversion 2として追記
- [ ] 90日評価76〜104日が許容され、固定の84日注釈なし
- [ ] 尿一般検査なし、尿細胞診あり
- [ ] スクリーニング血糖あり、HbA1cなし
- [ ] Google Sheet保存後にメール失敗しても再入力を促さない
- [ ] 本番前にRegistry tokenを再発行
- [ ] 本番前にGmail App Passwordを再発行
- [ ] 本番MDTメール送信先はUAT完了後に設定


## RECIST乖離UAT
- [ ] 施設RECIST=PR、中央RECIST=SDのダミー例で、事務局画面に乖離警告が表示される
- [ ] 中央RECISTがCR/PR/SDであれば、他の適格条件を満たす限り登録可能
- [ ] Registryに site_recist / central_recist / recist_concordance が保存される
- [ ] 中央RECIST=PDまたはNEでは正式登録が拒否される
- [ ] SD 12例カウントはEVP最良総合効果（best_effect）に基づく


### v2.2.2 hard-stop UAT
- [ ] 身長300 cmが送信不可
- [ ] 体重200 kgは送信可、300 kgは送信不可
- [ ] Hb 5 g/dLはrange理由だけでは拒否されない
- [ ] 拡張期血圧 >= 収縮期血圧が送信不可
- [ ] 手術日 < 同意取得日が送信不可
- [ ] EVP最終投与日 > 手術日が送信不可
- [ ] 90日評価日 < 手術日/予定日が送信不可
- [ ] 死亡日 < 研究登録日がGoogle Sheet保存時にも拒否される
