// SOURCE: text_contract.gs
/* Saved Python helper compatibility. Character sets pinned; no identity claim.
Unicode database: 15.0.0. Does not map fullwidth digits to ASCII subject IDs. */
function juogPythonStripV3_(s){return typeof s==='string'?s.replace(/^[\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}]+|[\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}]+$/gu,''):'';}
function juogNormalizeRegistrationV3_(s){return juogPythonStripV3_(s).toUpperCase();}
function juogValidRegistrationV3_(s){return typeof s==='string' && /^JUOG-[\u{30}-\u{39}\u{660}-\u{669}\u{6f0}-\u{6f9}\u{7c0}-\u{7c9}\u{966}-\u{96f}\u{9e6}-\u{9ef}\u{a66}-\u{a6f}\u{ae6}-\u{aef}\u{b66}-\u{b6f}\u{be6}-\u{bef}\u{c66}-\u{c6f}\u{ce6}-\u{cef}\u{d66}-\u{d6f}\u{de6}-\u{def}\u{e50}-\u{e59}\u{ed0}-\u{ed9}\u{f20}-\u{f29}\u{1040}-\u{1049}\u{1090}-\u{1099}\u{17e0}-\u{17e9}\u{1810}-\u{1819}\u{1946}-\u{194f}\u{19d0}-\u{19d9}\u{1a80}-\u{1a89}\u{1a90}-\u{1a99}\u{1b50}-\u{1b59}\u{1bb0}-\u{1bb9}\u{1c40}-\u{1c49}\u{1c50}-\u{1c59}\u{a620}-\u{a629}\u{a8d0}-\u{a8d9}\u{a900}-\u{a909}\u{a9d0}-\u{a9d9}\u{a9f0}-\u{a9f9}\u{aa50}-\u{aa59}\u{abf0}-\u{abf9}\u{ff10}-\u{ff19}\u{104a0}-\u{104a9}\u{10d30}-\u{10d39}\u{11066}-\u{1106f}\u{110f0}-\u{110f9}\u{11136}-\u{1113f}\u{111d0}-\u{111d9}\u{112f0}-\u{112f9}\u{11450}-\u{11459}\u{114d0}-\u{114d9}\u{11650}-\u{11659}\u{116c0}-\u{116c9}\u{11730}-\u{11739}\u{118e0}-\u{118e9}\u{11950}-\u{11959}\u{11c50}-\u{11c59}\u{11d50}-\u{11d59}\u{11da0}-\u{11da9}\u{11f50}-\u{11f59}\u{16a60}-\u{16a69}\u{16ac0}-\u{16ac9}\u{16b50}-\u{16b59}\u{1d7ce}-\u{1d7ff}\u{1e140}-\u{1e149}\u{1e2f0}-\u{1e2f9}\u{1e4f0}-\u{1e4f9}\u{1e950}-\u{1e959}\u{1fbf0}-\u{1fbf9}]{3,4}$/u.test(juogNormalizeRegistrationV3_(s));}
function juogValidEmailV3_(s){return typeof s==='string' && /^[^\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}@]+@[^\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}@]+\.[^\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}@]+$/u.test(juogPythonStripV3_(s));}

// Clinical free-text boundary normalization; identity normalization stays unchanged.
function juogClinicalTextV3_(s){return typeof s==='string'?s.replace(/^[\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}\u{feff}]+|[\u{9}-\u{d}\u{1c}-\u{20}\u{85}\u{a0}\u{1680}\u{2000}-\u{200a}\u{2028}-\u{2029}\u{202f}\u{205f}\u{3000}\u{feff}]+$/gu,''):'';}
function juogNormalizeRequiredReasonV3_(p){const out=JSON.parse(JSON.stringify(p));if(out&&out.data&&typeof out.data.required_test_omission_reason==='string')out.data.required_test_omission_reason=juogClinicalTextV3_(out.data.required_test_omission_reason);return out;}


// SOURCE: auth_bridge.gs
/* Concrete server-to-server assertion verifier. OIDC authentication is performed by
 * Streamlit; this bridge trusts only the configured server signing key, not a form email.
 * Config and individual ACL provisioning require approval; no default secrets. */
function juogV3DecodeBridge_(envelope,config) {
  if(!envelope || typeof envelope.request_json!=='string' || typeof envelope.identity_assertion!=='string')throw Error('AUTH_REQUIRED');
  if(envelope.request_json.length>200000||envelope.identity_assertion.length>8192)throw Error('AUTH_INVALID');
  if(!config || typeof config.signingKey!=='string'||config.signingKey.length<32||!config.bridgeIssuer||!config.audience||!config.oidcIssuer)throw Error('AUTH_NOT_CONFIGURED');
  const parts=envelope.identity_assertion.split('.');if(parts.length!==2||parts.some(p=>!/^[A-Za-z0-9_-]+$/.test(p)))throw Error('AUTH_INVALID');
  const signature=Utilities.computeHmacSha256Signature(parts[0],config.signingKey,Utilities.Charset.UTF_8);
  const supplied=Utilities.base64DecodeWebSafe(parts[1]);
  let diff=signature.length^supplied.length;for(let i=0;i<signature.length;i++)diff|=(signature[i]&255)^((supplied[i]||0)&255);if(diff!==0)throw Error('AUTH_INVALID');
  const c=JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(parts[0])).getDataAsString('UTF-8'));
  const now=Math.floor(Date.now()/1000);
  if(c.v!==1||c.iss!==config.bridgeIssuer||c.aud!==config.audience||c.oidc_issuer!==config.oidcIssuer||typeof c.sub!=='string'||!c.sub||!Number.isInteger(c.iat)||!Number.isInteger(c.exp)||c.iat>now+5||c.exp-c.iat>60||c.exp<=c.iat)throw Error('AUTH_INVALID');
  if(c.exp<=now)throw Error('AUTH_EXPIRED');
  const digest=Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,envelope.request_json,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  if(digest!==c.request_hash)throw Error('REQUEST_SIGNATURE_MISMATCH');
  const request=JSON.parse(envelope.request_json);
  if(!request||typeof request!=='object'||Array.isArray(request)||Object.keys(request).some(k=>!['action','payload'].includes(k))||typeof request.action!=='string')throw Error('REQUEST_INVALID');
  return {request,principal:{issuer:c.oidc_issuer,subject:c.sub},expires:c.exp};
}
function juogV3ReadIndividualAcl_(ss,issuer,subject) {
  const sh=ss.getSheetByName('V3_Users');if(!sh)throw Error('ACL_NOT_CONFIGURED');
  const rows=sh.getDataRange().getValues();
  if(!rows.length || !Array.isArray(rows[0]))throw Error('ACL_SCHEMA');
  const h=rows[0],idx={};
  if(new Set(h).size!==h.length)throw Error('ACL_SCHEMA');
  h.forEach((k,i)=>idx[k]=i);
  const required=['issuer','subject','user_id','enabled','role','facility_ids_json','valid_until'];if(required.some(k=>idx[k]===undefined))throw Error('ACL_SCHEMA');
  const matches=rows.slice(1).filter(r=>String(r[idx.issuer])===issuer&&String(r[idx.subject])===subject);
  if(matches.length!==1)return null;const r=matches[0],facilities=JSON.parse(String(r[idx.facility_ids_json]||'[]'));
  if(!Array.isArray(facilities)||facilities.some(x=>typeof x!=='string'||!x))throw Error('ACL_INVALID');
  const roles=['facility','admin','recovery_admin','radiology','medical_oncology','urology'];
  if(!roles.includes(r[idx.role]))throw Error('ACL_INVALID');
  const expiry=new Date(r[idx.valid_until]);const enabled=(r[idx.enabled]===true||r[idx.enabled]==='TRUE')&&Number.isFinite(expiry.getTime())&&expiry.getTime()>Date.now();
  const id=String(r[idx.user_id]||'').trim();
  if(!id)throw Error('ACL_INVALID');
  return {id,enabled,role:r[idx.role],facilities};
}


// SOURCE: privacy_revision2.gs
function directIdentifierKey_(key) {
  const normalized = String(key || '').normalize('NFKC').replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2').replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return /(?:^|_)(?:full_patient_name|patient_name|patient_full_name|first_name|last_name|given_name|family_name|patient_surname|mrn|medical_record_number|patient_address|personal_address|patient_phone|birth_date|dob|full_dob|date_of_birth)$/.test(normalized);
}

function parsedNestedJson_(value) {
  if (typeof value !== 'string' || !/^\s*[\[{]/.test(value)) return null;
  try { const parsed = JSON.parse(value); return parsed && typeof parsed === 'object' ? parsed : null; }
  catch (err) { return null; }
}

function containsLabeledIdentifierText_(value) {
  if (typeof value !== 'string') return false;
  const s = value.normalize('NFKC');
  return /(?:生年月日|患者氏名|カルテ番号)\s*(?:は|が|[:=])\s*\S/i.test(s) ||
    /(?:date\s+of\s+birth|\bDOB\b|\bMRN\b|patient\s+name)\s*[:=]\s*\S/i.test(s) ||
    /(?:生年月日|date\s+of\s+birth|\bDOB\b)\s*(?:は|が|[:=])?\s*[0-9]{4}\s*[-/年.]/i.test(s);
}

function containsDirectIdentifier_(value) {
  const parsed = parsedNestedJson_(value);
  if (parsed) return containsDirectIdentifier_(parsed);
  // Labeled free text is prohibited; an unlabeled clinical date cannot safely
  // be classified as a birth date by syntax alone and needs QA/SOP controls.
  if (containsLabeledIdentifierText_(value)) return true;
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some(containsDirectIdentifier_);
  return Object.keys(value).some(key => directIdentifierKey_(key) || containsDirectIdentifier_(value[key]));
}

// Read-time protection for older drafts. This never modifies the stored row.
function stripDirectIdentifiers_(value) {
  const parsed = parsedNestedJson_(value);
  if (parsed) return JSON.stringify(stripDirectIdentifiers_(parsed));
  if (containsLabeledIdentifierText_(value)) return '[REDACTED]';
  if (Array.isArray(value)) return value.map(stripDirectIdentifiers_);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  Object.keys(value).forEach(key => {
    if (!directIdentifierKey_(key)) out[key] = stripDirectIdentifiers_(value[key]);
  });
  return out;
}



// SOURCE: field_catalog.gs
const JUOG_FIELD_CATALOG_V3 = {
  "perioperative_30d": {
    "fields": {
      "surgery_performed": {
        "source": "surgery_performed",
        "enum": [
          "実施した",
          "実施しなかった"
        ]
      },
      "reference_date": {
        "source": "date_str(planned_or_reference_date)",
        "enum": [],
        "date": true
      },
      "last_evp_date": {
        "source": "date_str(last_evp_date)",
        "enum": [],
        "date": true
      },
      "admission_date": {
        "source": "date_str(op_admission_date)",
        "enum": [],
        "date": true
      },
      "operation_date": {
        "source": "date_str(op_date)",
        "enum": [],
        "date": true
      },
      "initial_hospital_outcome": {
        "source": "initial_hospital_outcome",
        "enum": [
          "退院済み",
          "入院継続中",
          "初回入院中に死亡"
        ]
      },
      "discharge_date": {
        "source": "date_str(op_discharge_date)",
        "enum": [],
        "date": true
      },
      "readmission_30d": {
        "source": "readmission_30d",
        "enum": [
          "なし",
          "あり",
          "N/A（術後30日まで初回入院）"
        ]
      },
      "readmission_date": {
        "source": "date_str(readmission_date)",
        "enum": [],
        "date": true
      },
      "readmission_reason": {
        "source": "text(readmission_reason)",
        "enum": []
      },
      "readmission_day30_status": {
        "source": "readmission_day30_status",
        "enum": [
          "再退院済み",
          "再入院継続中",
          "再入院中に死亡"
        ]
      },
      "readmission_discharge_date": {
        "source": "date_str(readmission_discharge_date)",
        "enum": [],
        "date": true
      },
      "operation_type": {
        "source": "op_type",
        "enum": [
          "選択してください",
          "根治的腎尿管全摘除術",
          "尿管部分切除術",
          "その他（プロトコル逸脱）"
        ]
      },
      "operation_type_other": {
        "source": "text(st.session_state.get('peri_op_other', ''))",
        "enum": []
      },
      "approach": {
        "source": "'＋'.join(approaches)",
        "enum": []
      },
      "approaches": {
        "source": "approaches",
        "enum": [
          "開腹",
          "腹腔鏡",
          "ロボット支援"
        ]
      },
      "approach_pattern": {
        "source": "approach_pattern",
        "enum": [
          "予定されたハイブリッド",
          "予定外のアプローチ変更（conversion）",
          "",
          "単一アプローチ"
        ]
      },
      "conversion_reason": {
        "source": "text(conversion_reason)",
        "enum": []
      },
      "operation_completed": {
        "source": "op_completed",
        "enum": [
          "はい",
          "いいえ"
        ]
      },
      "incomplete_reason": {
        "source": "text(op_incomplete_detail)",
        "enum": []
      },
      "operation_time_min": {
        "source": "op_time",
        "enum": []
      },
      "blood_loss_ml": {
        "source": "bleeding",
        "enum": []
      },
      "eauiaic": {
        "source": "eau_grade",
        "enum": [
          "選択してください",
          "Grade 0",
          "Grade 1",
          "Grade 2",
          "Grade 3",
          "Grade 4A",
          "Grade 4B",
          "Grade 5A",
          "Grade 5B"
        ]
      },
      "eauiaic_detail": {
        "source": "text(eau_detail)",
        "enum": []
      },
      "ln_dissection": {
        "source": "ln_dissection",
        "enum": [
          "実施した",
          "実施しなかった"
        ]
      },
      "ln_range": {
        "source": "ln_range",
        "enum": [
          "腎門部",
          "下大静脈周囲",
          "大動脈周囲",
          "傍大動脈",
          "大動脈静脈間",
          "総腸骨",
          "外腸骨",
          "内腸骨",
          "閉鎖",
          "その他"
        ]
      },
      "unrecovered_grade2plus_relevant_ae": {
        "source": "unrecovered_g2_relevant",
        "enum": [
          "なし",
          "あり"
        ]
      },
      "unrecovered_ae_detail": {
        "source": "text(st.session_state.get('peri_g2_detail', ''))",
        "enum": []
      },
      "surgery_timing_reason_or_deviation": {
        "source": "text(protocol_deviation_reason)",
        "enum": []
      },
      "no_operation_reason": {
        "source": "no_op_reason if surgery_performed == '実施しなかった' else ''",
        "enum": [
          "選択してください",
          "病勢進行",
          "EVP関連有害事象",
          "中央MDT/手術適応変更",
          "同意撤回",
          "患者希望",
          "その他",
          ""
        ]
      },
      "no_operation_other": {
        "source": "text(st.session_state.get('peri_noop_other', ''))",
        "enum": []
      },
      "day0_vitals": {
        "source": "{'timepoint': 'postoperative_care_area_arrival', 'sbp': day0_sbp, 'dbp': day0_dbp, 'pulse': day0_pulse, 'temperature': day0_temp}",
        "enum": []
      },
      "inpatient_vitals": {
        "source": "{'timepoint': 'discharge', 'sbp': discharge_sbp, 'dbp': discharge_dbp, 'pulse': discharge_pulse, 'temperature': discharge_temp}",
        "enum": []
      },
      "discharge_vitals": {
        "source": "{'available': initial_hospital_outcome == '退院済み', 'sbp': discharge_sbp, 'dbp': discharge_dbp, 'pulse': discharge_pulse, 'temperature': discharge_temp}",
        "enum": []
      },
      "inpatient_lab_available": {
        "source": "discharge_lab_available",
        "enum": [
          "あり",
          "なし"
        ]
      },
      "inpatient_lab_date": {
        "source": "date_str(discharge_lab_date)",
        "enum": [],
        "date": true
      },
      "inpatient_labs": {
        "source": "discharge_labs_parsed",
        "enum": []
      },
      "inpatient_required_test_omission_reason": {
        "source": "''",
        "enum": []
      },
      "pathology": {
        "source": "path if surgery_performed == '実施した' else {}",
        "enum": []
      },
      "day30_visit_date": {
        "source": "date_str(visit_date_30)",
        "enum": [],
        "date": true
      },
      "day30_window_deviation_reason": {
        "source": "text(window_deviation_reason)",
        "enum": []
      },
      "day30_lab_available": {
        "source": "day30_lab_available",
        "enum": [
          "あり"
        ]
      },
      "day30_lab_date": {
        "source": "date_str(day30_lab_date)",
        "enum": [],
        "date": true
      },
      "day30_labs": {
        "source": "day30_parsed",
        "enum": []
      },
      "day30_required_test_omission_reason": {
        "source": "''",
        "enum": []
      },
      "cd_grade_30": {
        "source": "cd_grade",
        "enum": [
          "選択してください",
          "Grade 0",
          "Grade I",
          "Grade II",
          "Grade IIIa",
          "Grade IIIb",
          "Grade IVa",
          "Grade IVb",
          "Grade V",
          "N/A"
        ]
      },
      "cd_event_date_30": {
        "source": "date_str(cd_date)",
        "enum": [],
        "date": true
      },
      "cd_detail_30": {
        "source": "text(cd_detail)",
        "enum": []
      },
      "cd_surgery_relation": {
        "source": "cd_relation",
        "enum": [
          "選択してください",
          "関連する",
          "否定できない",
          "関連しない",
          "N/A"
        ]
      },
      "renal_exception": {
        "source": "renal_exception",
        "enum": [
          false,
          true
        ]
      },
      "renal_exception_detail": {
        "source": "text(renal_exception_detail)",
        "enum": []
      },
      "major_surgery_related_complication_30d": {
        "source": "major30",
        "enum": []
      },
      "ctcae_event": {
        "source": "has_ctcae",
        "enum": [
          false,
          true
        ]
      },
      "ctcae_detail": {
        "source": "text(ctcae_detail)",
        "enum": []
      },
      "postop_treatment": {
        "source": "adj_plan",
        "enum": [
          "選択してください",
          "無治療（経過観察）",
          "術前からのEVP継続投与",
          "術前からのEV単独継続（間欠療法等を含む）",
          "術前からのペムブロリズマブ単剤継続",
          "ニボルマブ単剤（術後補助療法）",
          "GC療法（術後補助療法）",
          "GCarbo療法（術後補助療法）",
          "HER2標的ADC",
          "サシツズマブ ゴビテカン（SG）",
          "FGFR阻害薬",
          "放射線治療",
          "治験（TROP2標的ADC、その他）",
          "その他"
        ]
      },
      "postop_treatment_detail": {
        "source": "text(adj_detail)",
        "enum": []
      },
      "postop_treatment_start": {
        "source": "date_str(adj_start)",
        "enum": [],
        "date": true
      },
      "postop_treatment_end": {
        "source": "date_str(adj_end)",
        "enum": [],
        "date": true
      },
      "postop_treatment_ongoing": {
        "source": "adj_ongoing",
        "enum": [
          false,
          true
        ]
      },
      "vital_status": {
        "source": "status_alive",
        "enum": [
          "生存",
          "死亡"
        ]
      },
      "last_alive_date": {
        "source": "date_str(final_visit_date)",
        "enum": [],
        "date": true
      },
      "death_date": {
        "source": "date_str(death_date)",
        "enum": [],
        "date": true
      },
      "death_cause": {
        "source": "death_cause",
        "enum": [
          "選択してください",
          "癌死 (原疾患による)",
          "治療関連死",
          "他病死",
          "不明",
          ""
        ]
      }
    },
    "pathology_keys": [
      "pcr",
      "pcr_ypt0n0",
      "histology",
      "subtype_presence",
      "size_mm",
      "locations",
      "ypt",
      "lvi",
      "r0",
      "trg",
      "histology_other",
      "subtypes",
      "ypn",
      "ln_count_examined",
      "ypn_sites",
      "eval_failed_reason"
    ],
    "pathology_options": {
      "pcr": [],
      "pcr_ypt0n0": [],
      "histology": [
        "選択してください",
        "Urothelial carcinoma",
        "Urothelial carcinoma（亜型・分化を含む）",
        "その他",
        "評価不能"
      ],
      "subtype_presence": [
        "なし",
        "あり"
      ],
      "size_mm": [],
      "locations": [
        "腎盂",
        "上部尿管",
        "中部尿管",
        "下部尿管",
        "その他"
      ],
      "ypt": [
        "選択してください",
        "ypT0",
        "ypTa",
        "ypTis",
        "ypT1",
        "ypT2",
        "ypT3",
        "ypT4",
        "評価不能"
      ],
      "lvi": [
        "なし",
        "あり",
        "評価不能"
      ],
      "r0": [
        "R0",
        "R1/R2",
        "評価不能"
      ],
      "trg": [
        "TRG 1",
        "TRG 2",
        "TRG 3",
        "評価不能"
      ],
      "histology_other": [],
      "subtypes": [
        "Nested",
        "Micropapillary",
        "Plasmacytoid",
        "Sarcomatoid",
        "Squamous differentiation",
        "Glandular differentiation",
        "その他"
      ],
      "ypn": [
        "選択してください",
        "ypN0",
        "ypN1",
        "ypN2",
        "ypNX（評価不能）",
        "ypNX（郭清なし）"
      ],
      "ln_count_examined": [],
      "ypn_sites": [
        "腎門部",
        "下大静脈周囲",
        "大動脈周囲",
        "傍大動脈",
        "大動脈静脈間",
        "総腸骨",
        "外腸骨",
        "内腸骨",
        "閉鎖",
        "その他"
      ],
      "eval_failed_reason": []
    },
    "source_sha256": "0d04c2dfbe5f166c191df7fef2e05ed2de860e331db7aa6dc9c00f380dd6df6b"
  },
  "day90": {
    "fields": {
      "source_30d_linked": {
        "source": "source_found",
        "enum": []
      },
      "source_30d_record_version": {
        "source": "source_30d_record_version if source_found else None",
        "enum": []
      },
      "source_30d_submission_id": {
        "source": "source_30d_submission_id if source_found else ''",
        "enum": []
      },
      "surgery_performed": {
        "source": "surgery_performed",
        "enum": [
          "実施した",
          "実施しなかった"
        ]
      },
      "reference_date": {
        "source": "date_str(reference_date)",
        "enum": [],
        "date": true
      },
      "visit_date": {
        "source": "date_str(visit_date)",
        "enum": [],
        "date": true
      },
      "visit_deviation_reason": {
        "source": "text(visit_deviation_reason)",
        "enum": []
      },
      "lab_available": {
        "source": "lab_available",
        "enum": [
          "あり",
          "なし"
        ]
      },
      "lab_date": {
        "source": "date_str(lab_date)",
        "enum": [],
        "date": true
      },
      "labs": {
        "source": "parsed_labs",
        "enum": []
      },
      "urine_cytology": {
        "source": "cytology",
        "enum": [
          "選択してください",
          "Negative (クラスI・II)",
          "AUC (非定型細胞)",
          "SHGUC (高異型度癌疑い)",
          "HGUC (クラスIV・V相当)",
          "LGUC (低異型度腫瘍)",
          "判定不能",
          "未実施"
        ]
      },
      "required_test_omission_reason": {
        "source": "text(required_test_omission_reason)",
        "enum": []
      },
      "imaging_status": {
        "source": "imaging_status",
        "enum": [
          "実施",
          "未実施"
        ]
      },
      "imaging_date": {
        "source": "date_str(imaging_date)",
        "enum": [],
        "date": true
      },
      "imaging_not_done_reason": {
        "source": "text(imaging_not_done_reason)",
        "enum": []
      },
      "recist_progression_status": {
        "source": "recist_status",
        "enum": [
          "選択してください",
          "PDなし",
          "PDあり",
          "NE（評価不能）",
          "NE（未実施）"
        ]
      },
      "progression_date": {
        "source": "date_str(progression_date)",
        "enum": [],
        "date": true
      },
      "progression_sites": {
        "source": "progression_sites",
        "enum": [
          "原発/手術局所",
          "リンパ節",
          "肺",
          "肝",
          "骨",
          "その他"
        ]
      },
      "progression_detail": {
        "source": "text(progression_detail)",
        "enum": []
      },
      "cystoscopy_status": {
        "source": "cystoscopy_status",
        "enum": [
          "実施",
          "未実施"
        ]
      },
      "cystoscopy_date": {
        "source": "date_str(cystoscopy_date)",
        "enum": [],
        "date": true
      },
      "cystoscopy_result": {
        "source": "cystoscopy_result",
        "enum": [
          "選択してください",
          "腫瘍なし",
          "腫瘍あり",
          "評価不能",
          "未実施"
        ]
      },
      "cystoscopy_detail": {
        "source": "text(cystoscopy_detail)",
        "enum": []
      },
      "cystoscopy_not_done_reason": {
        "source": "text(cystoscopy_not_done_reason)",
        "enum": []
      },
      "new_surgical_complication_day31_90": {
        "source": "new_complication",
        "enum": [
          "なし",
          "あり",
          "N/A"
        ]
      },
      "cd_grade_day31_90": {
        "source": "cd_grade",
        "enum": [
          "選択してください",
          "Grade I",
          "Grade II",
          "Grade IIIa",
          "Grade IIIb",
          "Grade IVa",
          "Grade IVb",
          "Grade V",
          "N/A",
          "Grade 0"
        ]
      },
      "cd_event_date": {
        "source": "date_str(cd_date)",
        "enum": [],
        "date": true
      },
      "cd_detail": {
        "source": "text(cd_detail)",
        "enum": []
      },
      "cd_surgery_relation": {
        "source": "cd_relation",
        "enum": [
          "選択してください",
          "関連する",
          "否定できない",
          "関連しない",
          "N/A"
        ]
      },
      "renal_exception": {
        "source": "renal_exception",
        "enum": [
          false,
          true
        ]
      },
      "renal_exception_detail": {
        "source": "text(renal_exception_detail)",
        "enum": []
      },
      "major_surgery_related_complication_day31_90": {
        "source": "major_31_90",
        "enum": []
      },
      "ctcae_event": {
        "source": "has_ctcae",
        "enum": [
          false,
          true
        ]
      },
      "ctcae_detail": {
        "source": "text(ctcae_detail)",
        "enum": []
      },
      "intraluminal_recurrence": {
        "source": "intra_status",
        "enum": [
          "なし",
          "あり"
        ]
      },
      "intraluminal_recurrence_date": {
        "source": "date_str(intra_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_sites": {
        "source": "intra_sites",
        "enum": [
          "膀胱",
          "対側腎盂",
          "対側尿管",
          "同側残存尿管",
          "その他"
        ]
      },
      "intraluminal_site_other": {
        "source": "text(intra_site_other)",
        "enum": []
      },
      "intraluminal_treatment": {
        "source": "intra_tx",
        "enum": [
          "経過観察",
          "TURBT",
          "BCG注入療法",
          "抗がん剤注入療法",
          "上部尿路内視鏡的治療",
          "手術（腎尿管全摘等）",
          "その他"
        ]
      },
      "intraluminal_treatment_other": {
        "source": "text(intra_tx_other)",
        "enum": []
      },
      "intraluminal_treatment_status": {
        "source": "intra_tx_status",
        "enum": [
          "実施済み・継続中",
          "今後の予定"
        ]
      },
      "intraluminal_procedure_date": {
        "source": "date_str(intra_procedure_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_start": {
        "source": "date_str(intra_instill_start)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_end": {
        "source": "date_str(intra_instill_end)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_ongoing": {
        "source": "intra_instill_ongoing",
        "enum": [
          false,
          true
        ]
      },
      "intraluminal_other_treatment_date": {
        "source": "date_str(intra_other_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_pathology": {
        "source": "text(intra_path)",
        "enum": []
      },
      "postop_treatment": {
        "source": "adj_plan",
        "enum": [
          "選択してください",
          "無治療（経過観察）",
          "術前からのEVP継続投与",
          "術前からのEV単独継続（間欠療法等を含む）",
          "術前からのペムブロリズマブ単剤継続",
          "ニボルマブ単剤（術後補助療法）",
          "GC療法（術後補助療法）",
          "GCarbo療法（術後補助療法）",
          "HER2標的ADC",
          "サシツズマブ ゴビテカン（SG）",
          "FGFR阻害薬",
          "放射線治療",
          "治験（TROP2標的ADC、その他）",
          "その他"
        ]
      },
      "postop_treatment_detail": {
        "source": "text(adj_detail)",
        "enum": []
      },
      "postop_treatment_start": {
        "source": "date_str(adj_start)",
        "enum": [],
        "date": true
      },
      "postop_treatment_end": {
        "source": "date_str(adj_end)",
        "enum": [],
        "date": true
      },
      "postop_treatment_ongoing": {
        "source": "adj_ongoing",
        "enum": [
          false,
          true
        ]
      },
      "vital_status": {
        "source": "vital_status",
        "enum": [
          "生存",
          "死亡"
        ]
      },
      "last_alive_date": {
        "source": "date_str(last_alive_date)",
        "enum": [],
        "date": true
      },
      "death_date": {
        "source": "date_str(death_date)",
        "enum": [],
        "date": true
      },
      "death_cause": {
        "source": "death_cause",
        "enum": [
          "選択してください",
          "癌死 (原疾患による)",
          "治療関連死",
          "他病死",
          "不明",
          ""
        ]
      }
    },
    "pathology_keys": [],
    "pathology_options": {},
    "source_sha256": "8a5b77a42a8109a9ddb0052016524f88aaf58da99c38d359266013e7f83efb2b"
  },
  "followup": {
    "fields": {
      "source_30d_linked": {
        "source": "True",
        "enum": []
      },
      "source_30d_record_version": {
        "source": "source_30d_record_version",
        "enum": []
      },
      "source_30d_submission_id": {
        "source": "source_30d_submission_id",
        "enum": []
      },
      "surgery_performed": {
        "source": "surgery_performed",
        "enum": []
      },
      "reference_date": {
        "source": "date_str(reference_date)",
        "enum": [],
        "date": true
      },
      "visit_month": {
        "source": "visit_month",
        "enum": [
          "選択してください",
          "6ヶ月",
          "9ヶ月",
          "12ヶ月",
          "15ヶ月",
          "18ヶ月",
          "21ヶ月",
          "24ヶ月（終了）"
        ]
      },
      "visit_date": {
        "source": "date_str(visit_date)",
        "enum": [],
        "date": true
      },
      "timing_note": {
        "source": "text(timing_note)",
        "enum": []
      },
      "urine_cytology": {
        "source": "cytology",
        "enum": [
          "選択してください",
          "Negative (クラスI・II)",
          "AUC (非定型細胞)",
          "SHGUC (高異型度癌疑い)",
          "HGUC (クラスIV・V相当)",
          "LGUC (低異型度腫瘍)",
          "判定不能",
          "未実施"
        ]
      },
      "required_test_omission_reason": {
        "source": "text(required_test_omission_reason)",
        "enum": []
      },
      "imaging_status": {
        "source": "imaging_status",
        "enum": [
          "実施",
          "未実施"
        ]
      },
      "imaging_date": {
        "source": "date_str(imaging_date)",
        "enum": [],
        "date": true
      },
      "imaging_not_done_reason": {
        "source": "text(imaging_not_done_reason)",
        "enum": []
      },
      "recist_progression_status": {
        "source": "recist_status",
        "enum": [
          "選択してください",
          "PDなし",
          "今回PDあり",
          "既報PD（今回新規PDなし）",
          "NE（評価不能）",
          "NE（未実施）"
        ]
      },
      "progression_date": {
        "source": "date_str(progression_date)",
        "enum": [],
        "date": true
      },
      "progression_sites": {
        "source": "progression_sites",
        "enum": [
          "手術局所",
          "リンパ節",
          "肺",
          "肝",
          "骨",
          "その他"
        ]
      },
      "progression_detail": {
        "source": "text(progression_detail)",
        "enum": []
      },
      "cystoscopy_status": {
        "source": "cystoscopy_status",
        "enum": [
          "実施",
          "未実施"
        ]
      },
      "cystoscopy_date": {
        "source": "date_str(cystoscopy_date)",
        "enum": [],
        "date": true
      },
      "cystoscopy_result": {
        "source": "cystoscopy_result",
        "enum": [
          "選択してください",
          "腫瘍なし",
          "腫瘍あり",
          "評価不能",
          "未実施"
        ]
      },
      "cystoscopy_detail": {
        "source": "text(cystoscopy_detail)",
        "enum": []
      },
      "cystoscopy_not_done_reason": {
        "source": "text(cystoscopy_not_done_reason)",
        "enum": []
      },
      "labs_performed": {
        "source": "lab_status == '実施あり'",
        "enum": []
      },
      "labs": {
        "source": "parsed_labs",
        "enum": []
      },
      "intraluminal_recurrence_status": {
        "source": "intra_status",
        "enum": [
          "選択してください",
          "なし",
          "今回新規あり",
          "既報あり（今回新規なし）"
        ]
      },
      "intraluminal_recurrence_date": {
        "source": "date_str(intra_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_sites": {
        "source": "intra_sites",
        "enum": [
          "膀胱",
          "対側腎盂",
          "対側尿管",
          "同側残存尿管",
          "その他"
        ]
      },
      "intraluminal_site_other": {
        "source": "text(intra_site_other)",
        "enum": []
      },
      "intraluminal_treatment": {
        "source": "intra_tx",
        "enum": [
          "経過観察",
          "TURBT",
          "BCG注入療法",
          "抗がん剤注入療法",
          "上部尿路内視鏡的治療",
          "手術（腎尿管全摘等）",
          "その他"
        ]
      },
      "intraluminal_treatment_other": {
        "source": "text(intra_tx_other)",
        "enum": []
      },
      "intraluminal_treatment_status": {
        "source": "intra_tx_status",
        "enum": [
          "実施済み・継続中",
          "今後の予定"
        ]
      },
      "intraluminal_procedure_date": {
        "source": "date_str(intra_procedure_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_start": {
        "source": "date_str(intra_instill_start)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_end": {
        "source": "date_str(intra_instill_end)",
        "enum": [],
        "date": true
      },
      "intraluminal_instillation_ongoing": {
        "source": "intra_instill_ongoing",
        "enum": [
          false,
          true
        ]
      },
      "intraluminal_other_treatment_date": {
        "source": "date_str(intra_other_date)",
        "enum": [],
        "date": true
      },
      "intraluminal_pathology": {
        "source": "text(intra_path)",
        "enum": []
      },
      "current_treatment": {
        "source": "current_treatment",
        "enum": [
          "選択してください",
          "無治療（経過観察）",
          "術前からのEVP継続投与",
          "術前からのEV単独継続（間欠療法等を含む）",
          "術前からのペムブロリズマブ単剤継続",
          "ニボルマブ単剤（術後補助療法）",
          "GC療法（術後補助療法）",
          "GCarbo療法（術後補助療法）",
          "HER2標的ADC",
          "サシツズマブ ゴビテカン（SG）",
          "FGFR阻害薬",
          "放射線治療",
          "治験（TROP2標的ADC、その他）",
          "その他",
          "上記尿路内再発に対する治療を継続中",
          "転移巣切除",
          "緩和ケア"
        ]
      },
      "current_treatment_detail": {
        "source": "text(current_treatment_detail)",
        "enum": []
      },
      "treatment_start": {
        "source": "date_str(treatment_start)",
        "enum": [],
        "date": true
      },
      "treatment_end": {
        "source": "date_str(treatment_end)",
        "enum": [],
        "date": true
      },
      "treatment_ongoing": {
        "source": "treatment_ongoing",
        "enum": [
          false,
          true
        ]
      },
      "event_present": {
        "source": "has_event",
        "enum": [
          false,
          true
        ]
      },
      "cd_grade": {
        "source": "cd_grade",
        "enum": [
          "N/A",
          "Grade 0",
          "Grade I",
          "Grade II",
          "Grade IIIa",
          "Grade IIIb",
          "Grade IVa",
          "Grade IVb",
          "Grade V"
        ]
      },
      "event_detail": {
        "source": "text(ae_detail)",
        "enum": []
      },
      "vital_status": {
        "source": "vital_status",
        "enum": [
          "生存",
          "死亡"
        ]
      },
      "last_alive_date": {
        "source": "date_str(last_alive_date)",
        "enum": [],
        "date": true
      },
      "death_date": {
        "source": "date_str(death_date)",
        "enum": [],
        "date": true
      },
      "death_cause": {
        "source": "death_cause",
        "enum": [
          "選択してください",
          "癌死 (原疾患による)",
          "治療関連死",
          "他病死",
          "不明",
          ""
        ]
      }
    },
    "pathology_keys": [],
    "pathology_options": {},
    "source_sha256": "f16f3611b3b9f0d9093b6260f65297695868d3886b79acaacfc2b870272193e0"
  },
  "_labs": [
    "WBC",
    "Hb",
    "PLT",
    "Neutro",
    "Lympho",
    "Mono",
    "Eosino",
    "Baso",
    "ALP",
    "T_Bil",
    "Alb",
    "AST",
    "ALT",
    "TP",
    "LDH",
    "Cre",
    "eGFR",
    "BUN",
    "Na",
    "K",
    "Cl",
    "CRP"
  ]
};


// SOURCE: clinical_contract.gs
/* Candidate contract for all three official CRFs. Parity approval is a release gate. */
function validateClinicalV3(p,reg,today,store) {
 const errors=[],warnings=[], need=(obj,keys)=>keys.forEach(k=>{if(obj[k]===undefined||obj[k]===null||(typeof obj[k]==='string'&&!juogClinicalTextV3_(obj[k]))||obj[k]==='選択してください'||(Array.isArray(obj[k])&&!obj[k].length))errors.push('REQUIRED:'+k);});
 const requireBoolean=(obj,key)=>{if(typeof obj[key]!=='boolean')errors.push('BOOLEAN_REQUIRED:'+key);};
 const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
 const meta=['study_code','schema_version','crf_type','visit','registration_id','facility_code','facility_name','reporter_email','submission_kind','correction_reason','submission_id','record_key','submitted_at','expected_record_version'];
 if(!object(p))return {ok:false,errors:['OBJECT_REQUIRED']};
 for(const k of Object.keys(p)){if(!meta.includes(k)&&k!=='data')errors.push('UNKNOWN_METADATA');if(meta.includes(k)&&k!=='expected_record_version'&&typeof p[k]!=='string')errors.push('METADATA_TYPE:'+k);}
 if(p.study_code!=='JUOG_UTUC_Consolidative'||p.schema_version!=='review-v3-unapproved')errors.push('SCHEMA_VERSION');
 need(p,['crf_type','visit','registration_id','facility_code','facility_name','reporter_email','submission_kind','submission_id','record_key']);
 if(!juogValidRegistrationV3_(p.registration_id))errors.push('REGISTRATION_FORMAT');
 if(!juogValidEmailV3_(p.reporter_email))errors.push('EMAIL_FORMAT');
 if(!Number.isInteger(p.expected_record_version)||p.expected_record_version<0)errors.push('BASE_VERSION_REQUIRED');
 if(!['初回報告','訂正報告'].includes(p.submission_kind))errors.push('SUBMISSION_KIND');
 if(p.submission_kind==='訂正報告')need(p,['correction_reason']);
 const spec=JUOG_FIELD_CATALOG_V3[p.crf_type],d=p.data;
 if(!spec||!object(d))return {ok:false,errors:['SCHEMA_REQUIRED']};
 const arrays=['approaches','ln_range','progression_sites','intraluminal_sites','intraluminal_treatment'];
 const bools=['renal_exception','major_surgery_related_complication_30d','ctcae_event','postop_treatment_ongoing','source_30d_linked','major_surgery_related_complication_day31_90','intraluminal_instillation_ongoing','labs_performed','treatment_ongoing','event_present'];
 const nums=['operation_time_min','blood_loss_ml','source_30d_record_version'];
 const objects=['day0_vitals','inpatient_vitals','discharge_vitals','inpatient_labs','pathology','day30_labs','labs'];
 const dateValid=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(new Date(v+'T00:00:00Z').getTime())&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
 for(const [k,v] of Object.entries(d)){
  const f=spec.fields[k];if(!f){errors.push('UNKNOWN_FIELD:'+k);continue;}
  if(v===null||v==='')continue;
  if(arrays.includes(k)){if(!Array.isArray(v)||v.some(x=>typeof x!=='string'))errors.push('ARRAY_TYPE:'+k);}
  else if(bools.includes(k)){if(typeof v!=='boolean')errors.push('BOOLEAN_TYPE:'+k);}
  else if(nums.includes(k)){if(typeof v!=='number'||!Number.isFinite(v)||v<0)errors.push('NUMBER_TYPE:'+k);}
  else if(objects.includes(k)){if(!object(v))errors.push('OBJECT_TYPE:'+k);}
  else if(typeof v!=='string')errors.push('STRING_TYPE:'+k);
  if(f.date){if(!dateValid(v))errors.push('DATE:'+k);else if(k!=='reference_date'&&v>today)errors.push('FUTURE_DATE:'+k);}
  if(f.enum.length){const a=Array.isArray(v)?v:[v];if(a.some(x=>!f.enum.includes(x)))errors.push('ENUM:'+k);}
 }
 // Invalid types must not flow into conditional operations.
 if(errors.some(e=>!e.startsWith('FUTURE_DATE:')))return {ok:false,errors};
 const order=(a,b)=>{if(d[a]&&d[b]&&d[a]>d[b])errors.push('ORDER:'+a+':'+b);};
 const days=(a,b)=>Math.round((new Date(a+'T00:00:00Z')-new Date(b+'T00:00:00Z'))/86400000);
 const lab=(key,required)=>{const x=d[key];if(!object(x)){if(required)errors.push('LAB_REQUIRED:'+key);return;}if(required&&!Object.values(x).some(v=>v!==null&&v!==''))errors.push('LAB_REQUIRED:'+key);for(const [k,v] of Object.entries(x)){if(!JUOG_FIELD_CATALOG_V3._labs.includes(k))errors.push('UNKNOWN_LAB');if(v!==null&&(typeof v!=='number'||!Number.isFinite(v)||v<0||(['Neutro','Lympho','Mono','Eosino','Baso'].includes(k)&&v>100)))errors.push('LAB_VALUE:'+k);}};
 const vit=(key,required)=>{const x=d[key];if(!object(x)){if(required)errors.push('VITALS_REQUIRED:'+key);return;}for(const k of Object.keys(x))if(!['sbp','dbp','pulse','temperature','timepoint','available'].includes(k))errors.push('UNKNOWN_VITAL');if(required)need(x,['sbp','dbp','pulse','temperature']);for(const [k,lo,hi] of [['sbp',40,300],['dbp',20,200],['pulse',20,250],['temperature',25,45]])if(x[k]!=null&&(typeof x[k]!=='number'||x[k]<lo||x[k]>hi))errors.push('VITALS_RANGE:'+k);if(x.sbp!=null&&x.dbp!=null&&x.dbp>=x.sbp)errors.push('VITALS_ORDER');};
 need(d,['surgery_performed','reference_date','vital_status']);
 if(!['実施した','実施しなかった'].includes(d.surgery_performed))errors.push('SURGERY_ENUM');
 if(!['生存','死亡'].includes(d.vital_status))errors.push('VITAL_ENUM');
 const performed=d.surgery_performed==='実施した',visit=p.crf_type==='perioperative_30d'?'day30_visit_date':'visit_date';need(d,[visit]);
 order('reference_date',visit);
 for(const k of ['reference_date','operation_date','death_date'])if(d[k]&&reg.registration_date&&d[k]<reg.registration_date)errors.push('BEFORE_REGISTRATION:'+k);
 if(d.operation_date&&reg.consent_date&&d.operation_date<reg.consent_date)errors.push('BEFORE_CONSENT');
 if(performed&&d.reference_date>today)errors.push('FUTURE_SURGERY');
 if(d.vital_status==='生存')need(d,['last_alive_date']);else if(d.vital_status==='死亡')need(d,['death_date','death_cause']);
 const grade=d.cd_grade_30||d.cd_grade_day31_90||d.cd_grade;
 if(grade==='Grade V'&&d.vital_status==='生存')errors.push('DEATH_CONTRADICTION');
 if(performed)order('operation_date','death_date');
 function treatment(prefix){need(d,[prefix]);if(['その他','治験（TROP2標的ADC、その他）'].includes(d[prefix]))need(d,[prefix+'_detail']);const start=prefix==='current_treatment'?'treatment_start':prefix+'_start',end=prefix==='current_treatment'?'treatment_end':prefix+'_end';if(!['無治療（経過観察）','上記尿路内再発に対する治療を継続中','緩和ケア','選択してください',''].includes(d[prefix]))need(d,[start]);order(start,end);}
 if(p.crf_type==='perioperative_30d'){
  if(p.visit!=='30d')errors.push('VISIT');need(d,['last_evp_date','day30_lab_date']);lab('day30_labs',true);lab('inpatient_labs',false);
  if(d.day30_visit_date&&d.reference_date){const n=days(d.day30_visit_date,d.reference_date);if(n<16||n>44){need(d,['day30_window_deviation_reason']);warnings.push('30D_WINDOW_DEVIATION');}}
  if(d.day30_lab_date&&d.reference_date){const n=days(d.day30_lab_date,d.reference_date);if(n<16||n>44)errors.push('LAB_WINDOW');}
  if(performed){
   need(d,['admission_date','operation_date','initial_hospital_outcome','operation_type','approaches','operation_completed','operation_time_min','blood_loss_ml','eauiaic','ln_dissection','unrecovered_grade2plus_relevant_ae','cd_grade_30']);
   if(d.operation_date!==d.reference_date)errors.push('REFERENCE_OPERATION_MISMATCH');
   if(!(d.operation_time_min>0))errors.push('OP_TIME');
   if(d.operation_type==='その他（プロトコル逸脱）')need(d,['operation_type_other']);
   if((d.approaches||[]).length>=2)need(d,['approach_pattern']);
   if(d.approach_pattern==='予定外のアプローチ変更（conversion）')need(d,['conversion_reason']);
   if(d.operation_completed==='いいえ')need(d,['incomplete_reason']);
   if(d.eauiaic && !['選択してください','Grade 0'].includes(d.eauiaic))need(d,['eauiaic_detail']);
   if(d.ln_dissection==='実施した')need(d,['ln_range']);
   if(d.unrecovered_grade2plus_relevant_ae==='あり')need(d,['unrecovered_ae_detail']);
   order('last_evp_date','operation_date');order('admission_date','operation_date');order('operation_date','discharge_date');order('admission_date','discharge_date');
   if(d.operation_date&&d.last_evp_date){const n=days(d.operation_date,d.last_evp_date);if(n<28||n>56)need(d,['surgery_timing_reason_or_deviation']);}
   vit('day0_vitals',true);vit('inpatient_vitals',false);vit('discharge_vitals',false);
   if(d.initial_hospital_outcome==='退院済み'){
    need(d,['discharge_date','inpatient_lab_available']);vit('inpatient_vitals',true);
    if(d.discharge_date&&d.operation_date&&days(d.discharge_date,d.operation_date)<=30)need(d,['readmission_30d']);
    if(d.inpatient_lab_available==='あり'){need(d,['inpatient_lab_date']);lab('inpatient_labs',true);order('operation_date','inpatient_lab_date');order('inpatient_lab_date','discharge_date');}
    if(d.readmission_30d==='あり'){need(d,['readmission_date','readmission_reason','readmission_day30_status']);if(d.readmission_day30_status==='再退院済み')need(d,['readmission_discharge_date']);order('discharge_date','readmission_date');order('readmission_date','readmission_discharge_date');if(d.readmission_date&&d.operation_date&&days(d.readmission_date,d.operation_date)>30)errors.push('READMISSION_WINDOW');}
   }
   const path=d.pathology;if(!object(path))errors.push('PATHOLOGY_REQUIRED');else{
    for(const k of Object.keys(path))if(!spec.pathology_keys.includes(k))errors.push('UNKNOWN_PATHOLOGY');
    need(path,['histology','ypt','lvi','r0','trg','subtype_presence','size_mm','locations','ypn']);
    for(const [k,options] of Object.entries(spec.pathology_options))if(path[k]!=null&&path[k]!==''&&options.length&&(Array.isArray(path[k])?path[k]:[path[k]]).some(v=>!options.includes(v)))errors.push('PATHOLOGY_ENUM:'+k);
    if(path.size_mm!=null&&(typeof path.size_mm!=='number'||path.size_mm<0))errors.push('PATHOLOGY_SIZE');
    if(path.histology==='その他')need(path,['histology_other']);if(path.subtype_presence==='あり')need(path,['subtypes']);if(d.ln_dissection==='実施した')need(path,['ln_count_examined']);if(['ypN1','ypN2'].includes(path.ypn))need(path,['ypn_sites']);if(path.ypn==='ypNX（評価不能）'||['histology','ypt','lvi','r0','trg'].some(k=>path[k]==='評価不能'))need(path,['eval_failed_reason']);
   }
   if(d.cd_grade_30 && !['選択してください','Grade 0'].includes(d.cd_grade_30)){need(d,['cd_event_date_30','cd_detail_30','cd_surgery_relation']);if(d.cd_event_date_30&&d.operation_date&&(days(d.cd_event_date_30,d.operation_date)<0||days(d.cd_event_date_30,d.operation_date)>30))errors.push('COMPLICATION_WINDOW');if(d.renal_exception)need(d,['renal_exception_detail']);}
   if((d.initial_hospital_outcome==='初回入院中に死亡'||d.readmission_day30_status==='再入院中に死亡')&&d.vital_status!=='死亡')errors.push('INPATIENT_DEATH_CONTRADICTION');
  }else{need(d,['no_operation_reason']);if(d.no_operation_reason==='その他')need(d,['no_operation_other']);}
  if(d.operation_type==='その他（プロトコル逸脱）')warnings.push('PROTOCOL_OPERATION_DEVIATION');
  if(d.unrecovered_grade2plus_relevant_ae==='あり')warnings.push('UNRECOVERED_G2_AE');
  if(d.last_alive_date&&d.day30_visit_date&&d.last_alive_date<d.day30_visit_date)warnings.push('LAST_ALIVE_BEFORE_VISIT');
  if(d.ctcae_event)need(d,['ctcae_detail']);treatment('postop_treatment');
 }else{
  const fup=p.crf_type==='followup';if(!fup&&p.visit!=='90d')errors.push('VISIT');
  if(fup){need(d,['visit_month']);if(!['6m','9m','12m','15m','18m','21m','24m'].includes(p.visit)||p.visit!==String(d.visit_month||'').replace('ヶ月（終了）','m').replace('ヶ月','m'))errors.push('VISIT');if(d.source_30d_linked!==true)errors.push('SOURCE_REQUIRED');if(typeof d.labs_performed!=='boolean')errors.push('LAB_STATUS');lab('labs',false);}
  else{need(d,['lab_available']);if(d.reference_date&&d.visit_date){const n=days(d.visit_date,d.reference_date);if(n<76||n>104){need(d,['visit_deviation_reason']);warnings.push('90D_WINDOW_DEVIATION');}}if(d.lab_available==='あり'){need(d,['lab_date']);lab('labs',true);if(d.lab_date&&d.reference_date&&(days(d.lab_date,d.reference_date)<76||days(d.lab_date,d.reference_date)>104))errors.push('LAB_WINDOW');}else lab('labs',false);}
  if(d.source_30d_linked){const candidates=store.records.filter(x=>x.payload&&x.payload.registration_id===p.registration_id&&x.payload.crf_type==='perioperative_30d'&&store.events.some(e=>e.transaction_id===x.transaction_id&&e.kind==='COMMITTED')).sort((a,b)=>b.record_version-a.record_version);const prev=candidates[0];if(!prev||prev.record_version!==d.source_30d_record_version||prev.submission_id!==d.source_30d_submission_id||prev.payload.facility_code!==p.facility_code||prev.payload.data.reference_date!==d.reference_date||prev.payload.data.surgery_performed!==d.surgery_performed)errors.push('SOURCE_STALE_OR_MISMATCH');}
  need(d,['urine_cytology','imaging_status','cystoscopy_status']);if(d.urine_cytology==='未実施')need(d,['required_test_omission_reason']);
  if(d.imaging_status==='実施'){need(d,['imaging_date','recist_progression_status']);if(['PDあり','今回PDあり'].includes(d.recist_progression_status))need(d,['progression_date','progression_sites','progression_detail']);}else if(d.imaging_status==='未実施')need(d,['imaging_not_done_reason']);
  if(d.cystoscopy_status==='実施'){need(d,['cystoscopy_date','cystoscopy_result']);if(['腫瘍あり','評価不能'].includes(d.cystoscopy_result))need(d,['cystoscopy_detail']);}else if(d.cystoscopy_status==='未実施')need(d,['cystoscopy_not_done_reason']);
  for(const k of ['imaging_date','cystoscopy_date','progression_date'])order(k,'visit_date');
  if(!fup&&d.lab_date&&d.visit_date&&d.lab_date>d.visit_date)warnings.push('LAB_AFTER_VISIT');
  for(const k of ['imaging_date','cystoscopy_date'])if(d[k]&&d.reference_date){
    if(!fup&&(days(d[k],d.reference_date)<76||days(d[k],d.reference_date)>104))warnings.push('90D_TEST_WINDOW:'+k);
    if(fup&&d.visit_month){const months=parseInt(d.visit_month,10),ref=new Date(d.reference_date+'T00:00:00Z');const target=new Date(Date.UTC(ref.getUTCFullYear(),ref.getUTCMonth()+months,1));const last=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate();target.setUTCDate(Math.min(ref.getUTCDate(),last));if(Math.abs(days(d[k],target.toISOString().slice(0,10)))>30)warnings.push('FOLLOWUP_TEST_WINDOW:'+k);}
  }
  if(fup&&d.labs_performed===true&&(!d.labs||!Object.values(d.labs).some(v=>v!==null&&v!=='')))warnings.push('FOLLOWUP_LAB_VALUES_EMPTY');
  if(!fup&&performed){need(d,['new_surgical_complication_day31_90']);if(d.new_surgical_complication_day31_90==='あり'){need(d,['cd_grade_day31_90','cd_event_date','cd_detail','cd_surgery_relation']);if(['Grade 0','N/A'].includes(d.cd_grade_day31_90))errors.push('COMPLICATION_GRADE');if(d.renal_exception)need(d,['renal_exception_detail']);if(d.cd_event_date&&d.reference_date&&(days(d.cd_event_date,d.reference_date)<31||days(d.cd_event_date,d.reference_date)>90))errors.push('COMPLICATION_WINDOW');}}
  const recur=fup?'intraluminal_recurrence_status':'intraluminal_recurrence';need(d,[recur]);
  if(['あり','今回新規あり'].includes(d[recur])){
   need(d,['intraluminal_recurrence_date','intraluminal_sites','intraluminal_treatment']);const sites=d.intraluminal_sites||[],tx=d.intraluminal_treatment||[];
   if(sites.includes('その他'))need(d,['intraluminal_site_other']);if(tx.includes('その他'))need(d,['intraluminal_treatment_other']);if(tx.includes('経過観察')&&tx.length>1)errors.push('RECURRENCE_TREATMENT_CONFLICT');if(tx.length&&!tx.includes('経過観察'))need(d,['intraluminal_treatment_status']);
   if(d.intraluminal_treatment_status==='実施済み・継続中'){if(tx.some(x=>['TURBT','上部尿路内視鏡的治療','手術（腎尿管全摘等）'].includes(x)))need(d,['intraluminal_procedure_date','intraluminal_pathology']);if(tx.some(x=>['BCG注入療法','抗がん剤注入療法'].includes(x))){requireBoolean(d,'intraluminal_instillation_ongoing');need(d,['intraluminal_instillation_start']);if(!d.intraluminal_instillation_ongoing)need(d,['intraluminal_instillation_end']);order('intraluminal_instillation_start','intraluminal_instillation_end');}}
   for(const k of ['intraluminal_procedure_date','intraluminal_instillation_start','intraluminal_other_treatment_date'])order('intraluminal_recurrence_date',k);
  }
  treatment(fup?'current_treatment':'postop_treatment');if(d.ctcae_event)need(d,['ctcae_detail']);if(fup&&d.event_present)need(d,['event_detail']);
 }
 return {ok:errors.length===0,errors:[...new Set(errors)],warnings:[...new Set(warnings)]};
}


// SOURCE: transaction_core.gs
/* Integrated redesign candidate. Pure core; adapters must be reviewed before deployment.
 * No network, properties, SpreadsheetApp, emails or hidden fallback in this file.
 * deps identity/ACL/store/clock/hash/lock/schema are trusted server dependencies.
 */
function JuogSaveServiceV3(deps) {
  const deny = code => { const e = new Error(code); e.safeCode=code; throw e; };
  const clone = v => JSON.parse(JSON.stringify(v));
  function canonical(v, depth) {
    depth=depth||0;if(depth>24)deny('JSON_DEPTH_LIMIT');
    if(v===null || typeof v==='boolean')return JSON.stringify(v);
    if(typeof v==='number'){if(!Number.isFinite(v))deny('INVALID_NUMBER');return JSON.stringify(v);}
    if(typeof v==='string'){if(v.length>16000)deny('STRING_LIMIT');return JSON.stringify(v);}
    if(Array.isArray(v)){if(v.length>512)deny('ARRAY_LIMIT');return '['+v.map(x=>canonical(x,depth+1)).join(',')+']';}
    if(!v || typeof v!=='object' || ![Object.prototype,null].includes(Object.getPrototypeOf(v)))deny('INVALID_JSON_TYPE');
    return '{'+Object.keys(v).sort().map(k=>{if(['__proto__','constructor','prototype'].includes(k))deny('UNSAFE_KEY');return JSON.stringify(k)+':'+canonical(v[k],depth+1);}).join(',')+'}';
  }
  const eq=(a,b)=>canonical(a)===canonical(b);
  function identity(assertion) {
    // verifyIdentity MUST verify signature/issuer/audience/expiry; no decoded-JWT fallback.
    const claim=deps.verifyIdentity(assertion);
    if(!claim || !claim.subject || !claim.issuer)deny('AUTHENTICATION_REQUIRED');
    const user=deps.directory(claim.issuer,claim.subject);
    if(!user || !user.enabled || !user.id)deny('ACCOUNT_DISABLED_OR_UNKNOWN');
    return user;
  }
  function permitted(user,p) {
    if(user.role!=='facility')deny('ROLE_NOT_ALLOWED');
    if(typeof p.facility_code!=='string' || !p.facility_code.trim())deny('FACILITY_REQUIRED');
    if(!Array.isArray(user.facilities) || !user.facilities.includes(p.facility_code))deny('FACILITY_FORBIDDEN');
    const subject=deps.registry(p.registration_id);
    if(!subject || subject.status!=='ACTIVE' || subject.facility_code!==p.facility_code)deny('SUBJECT_FORBIDDEN');
    return subject;
  }
  function snapshot() { return deps.store.read(); }
  function events(s,id,kind){return s.events.filter(e=>e.transaction_id===id&&e.kind===kind);}
  function stateFor(s,id){const a=s.intents.filter(x=>x.transaction_id===id);if(a.length>1)deny('JOURNAL_CONFLICT');return a[0];}
  function committed(s,i){return events(s,i.transaction_id,'COMMITTED').length===1;}
  function verifyRows(s,i, requireCommit) {
    const rows=s.records.filter(x=>x.transaction_id===i.transaction_id),audit=s.audits.filter(x=>x.transaction_id===i.transaction_id);
    if(rows.length!==1 || audit.length!==1)deny('RECONCILIATION_REQUIRED');
    if(!eq(rows[0],i.record) || !eq(audit[0].evidence,i.auditEvidence))deny('RECONCILIATION_REQUIRED');
    if(!audit[0].materialized_at || !audit[0].materialized_by)deny('RECONCILIATION_REQUIRED');
    if(requireCommit && !committed(s,i))deny('RECONCILIATION_REQUIRED');
  }
  function finish(i,executor,recovery) {
    // Only recover transactions backed by this new durable intent; never legacy rows.
    let s=snapshot();
    if(committed(s,i)){verifyRows(s,i,true);return {ok:true,existing:true,transaction_id:i.transaction_id,record_version:i.record.record_version};}
    let rows=s.records.filter(x=>x.transaction_id===i.transaction_id);
    if(rows.length>1 || (rows.length===1&&!eq(rows[0],i.record)))deny('RECONCILIATION_REQUIRED');
    if(!rows.length)deps.store.appendRecord(clone(i.record));
    s=snapshot();rows=s.records.filter(x=>x.transaction_id===i.transaction_id);
    if(rows.length!==1 || !eq(rows[0],i.record))deny('RECONCILIATION_REQUIRED');
    const a=s.audits.filter(x=>x.transaction_id===i.transaction_id);
    if(a.length>1 || (a.length===1&&!eq(a[0].evidence,i.auditEvidence)))deny('RECONCILIATION_REQUIRED');
    if(!a.length)deps.store.appendAudit({transaction_id:i.transaction_id,evidence:clone(i.auditEvidence),materialized_at:deps.now(),materialized_by:executor.id,recovered:recovery});
    verifyRows(snapshot(),i,false);
    deps.store.appendEvent({transaction_id:i.transaction_id,kind:'COMMITTED',at:deps.now(),by:executor.id});
    verifyRows(snapshot(),i,true);
    return {ok:true,existing:false,transaction_id:i.transaction_id,record_version:i.record.record_version};
  }
  function save(assertion,p) {
    try {
      const u=identity(assertion);let serialized=canonical(p);if(serialized.length>200000)deny('REQUEST_LIMIT');
      if(deps.privacy(p))deny('DIRECT_IDENTIFIER_NOT_ALLOWED');
      p=juogNormalizeRequiredReasonV3_(p);serialized=canonical(p);
      // hash is over the full approved canonical request; request actor fields not accepted.
      const digest=deps.hash(serialized);
      return deps.withLock(()=>{
        const current=identity(assertion);if(current.id!==u.id)deny('AUTH_CHANGED');
        const registry=permitted(current,p);
        const sourceState=snapshot();
        if(p.data && p.data.source_30d_linked===true) {
          const source=sourceState.intents.filter(i=>i.record.payload.registration_id===p.registration_id && i.record.payload.crf_type==='perioperative_30d');
          if(!source.length)deny('SOURCE_REQUIRED');
          for(const i of source)verifyRows(sourceState,i,true);
        }
        const validation=deps.validate(p,registry,deps.today(),sourceState);
        if(!validation || !validation.ok)deny('VALIDATION_FAILED');
        const id=p.submission_id,key=p.record_key;
        if(!id || key!==[p.registration_id,p.crf_type,p.visit].join('|'))deny('INVALID_RECORD_IDENTITY');
        if(!['初回報告','訂正報告'].includes(p.submission_kind))deny('INVALID_SUBMISSION_KIND');
        if(p.submission_kind==='訂正報告'&&!String(p.correction_reason||'').trim())deny('CORRECTION_REASON_REQUIRED');
        let s=snapshot(),existing=stateFor(s,id);
        if(existing){if(existing.request_hash!==digest||existing.actor.id!==current.id)deny('SUBMISSION_ID_CONFLICT');return finish(existing,current,true);}
        // Never infer intent or prior execution details from unjournaled historical rows.
        if(s.records.some(x=>x.submission_id===id || (x.record_key===key&&!stateFor(s,x.transaction_id))))deny('LEGACY_RECONCILIATION_REQUIRED');
        const related=s.intents.filter(x=>x.record.record_key===key);
        if(related.some(x=>!committed(s,x)))deny('PENDING_TRANSACTION');
        for(const i of related)verifyRows(s,i,true);
        const prior=related.map(x=>x.record).sort((a,b)=>a.record_version-b.record_version);
        if(prior.some((x,k)=>x.record_version!==k+1))deny('VERSION_HISTORY_CONFLICT');
        const latest=prior[prior.length-1]||null,base=latest?latest.record_version:0;
        if(p.submission_kind==='初回報告'&&base!==0)deny('INITIAL_ALREADY_EXISTS');
        if(p.submission_kind==='訂正報告'&&base===0)deny('NO_PRIOR_RECORD');
        if(p.expected_record_version!==base)deny('STALE_VERSION');
        const actual=deps.now();
        const record={transaction_id:id,submission_id:id,record_key:key,record_version:base+1,request_hash:digest,payload:clone(p),accepted_at:actual,actor_id:current.id};
        const i={transaction_id:id,request_hash:digest,actor:{id:current.id,role:current.role,facility:p.facility_code},record,auditEvidence:{transaction_id:id,actor_id:current.id,role:current.role,facility:p.facility_code,accepted_at:actual,record_key:key,submission_id:id,record_version:base+1,previous_version:base,previous_hash:latest?latest.request_hash:null,current_hash:digest,reason:p.correction_reason||'',action:base?'CORRECT':'CREATE',before:latest?clone(latest.payload):null,after:clone(p)}};
        deps.store.assertFits(i);
        deps.store.appendIntent(clone(i));
        const persisted=stateFor(snapshot(),id);if(!persisted || !eq(persisted,i))deny('INTENT_NOT_DURABLE');
        return finish(persisted,current,false);
      });
    } catch(e){return {ok:false,error:e.safeCode||'SAVE_INCOMPLETE'};} // never echo raw exception/payload
  }
  function recover(assertion,id,reason){
    try {return deps.withLock(()=>{const u=identity(assertion);if(u.role!=='recovery_admin')deny('ROLE_NOT_ALLOWED');if(!String(reason||'').trim())deny('RECOVERY_REASON_REQUIRED');if(deps.privacy(reason))deny('DIRECT_IDENTIFIER_NOT_ALLOWED');const i=stateFor(snapshot(),id);if(!i)deny('NO_DURABLE_INTENT');
      deps.store.appendEvent({transaction_id:id,kind:'RECOVERY_ATTEMPT',at:deps.now(),by:u.id,reason});return finish(i,u,true);
    });}catch(e){return {ok:false,error:e.safeCode||'RECOVERY_INCOMPLETE'};}
  }
  function read(assertion,key){try{const u=identity(assertion);return deps.withLock(()=>{const s=snapshot(),all=s.intents.filter(i=>i.record.record_key===key&&committed(s,i));const out=[];for(const i of all){permitted(u,i.record.payload);verifyRows(s,i,true);out.push(deps.redact(clone(i.record)));}return {ok:true,records:out};});}catch(e){return {ok:false,error:e.safeCode||'READ_INCOMPLETE'};}}
  return {save,recover,read};
}


// SOURCE: domain_transaction.gs
/* Append-only migration transaction prototype: underlying legacy sheets stay immutable.
 * Each committed intent contains a materialized view; real storage/size/read adapters
 * and migration approval are required. Never call this on a current clinical ledger.
 */
function JuogDomainServiceV3(deps){
 const copy=x=>JSON.parse(JSON.stringify(x));
 const fail=code=>{const e=Error(code);e.safeCode=code;throw e;};
 const hash=x=>deps.hash(JSON.stringify(x));
 function verify(i,s){const audits=s.audits.filter(a=>a.id===i.id);if(audits.length!==1||audits[0].after_hash!==i.after_hash||audits[0].before_hash!==i.before_hash||audits[0].actor!==i.actor||audits[0].action!==i.action||hash(audits[0].detail||null)!==hash(i.audit_detail||null))fail('DOMAIN_AUDIT_MISMATCH');if(hash(i.after)!==i.after_hash)fail('DOMAIN_VIEW_HASH_MISMATCH');}
 function committed(s){if(s.commits.some(c=>s.commits.filter(x=>x.id===c.id).length!==1||s.intents.filter(i=>i.id===c.id).length!==1))fail('DOMAIN_COMMIT_CONFLICT');return s.intents.filter(i=>s.commits.filter(c=>c.id===i.id).length===1).sort((a,b)=>a.revision-b.revision);}
 function view(s){const done=committed(s);let current=s.baseline,rev=0;for(const i of done){verify(i,s);if(i.revision!==rev+1||i.before_hash!==hash(current))fail('DOMAIN_HISTORY_CONFLICT');current=i.after;rev=i.revision;}return {tables:copy(current),revision:rev};}
 function finish(i,who){let s=deps.store.read();if(s.commits.some(c=>c.id===i.id)){if(s.commits.filter(c=>c.id===i.id).length!==1)fail('DOMAIN_COMMIT_CONFLICT');verify(i,s);return {ok:true,existing:true,revision:i.revision,result:i.result};}let a=s.audits.filter(x=>x.id===i.id);if(a.length>1)fail('DOMAIN_AUDIT_MISMATCH');if(!a.length)deps.store.appendAudit({id:i.id,actor:i.actor,action:i.action,detail:i.audit_detail||null,before_hash:i.before_hash,after_hash:i.after_hash,accepted_at:i.accepted_at,materialized_at:deps.now(),materialized_by:who.id});verify(i,deps.store.read());deps.store.appendCommit({id:i.id,at:deps.now(),by:who.id});s=deps.store.read();if(s.commits.filter(c=>c.id===i.id).length!==1)fail('DOMAIN_COMMIT_CONFLICT');verify(i,s);return {ok:true,existing:false,revision:i.revision,result:i.result};}
 return {execute:function(assertion,operation){try{return deps.withLock(()=>{
  const who=deps.authenticate(assertion);if(!who?.enabled)fail('AUTH_REQUIRED');
  if(!/^[A-Za-z0-9_-]{1,128}$/.test(operation.id||''))fail('OPERATION_ID');
  if(deps.privacy(operation.payload))fail('DIRECT_IDENTIFIER_NOT_ALLOWED');
  const s=deps.store.read(),v=view(s);const authorization=deps.authorize(who,operation.action,operation.payload,v.tables);if(!authorization.ok)fail(authorization.error);
  const h=hash({action:operation.action,payload:operation.payload}),prior=s.intents.filter(i=>i.id===operation.id);
  if(prior.length>1)fail('DOMAIN_INTENT_CONFLICT');if(prior.length){if(prior[0].request_hash!==h||prior[0].actor!==who.id)fail('OPERATION_ID_CONFLICT');return finish(prior[0],who);}
  if(s.intents.length!==committed(s).length)fail('DOMAIN_RECOVERY_REQUIRED');
  if(operation.expected_revision!==v.revision)fail('STALE_DOMAIN_REVISION');
  const planned=deps.plan(operation.action,copy(operation.payload),v.tables,who,operation.id);if(!planned.ok)return {...planned,rejected_before_intent:true};
  // No transport/authentication secrets may be persisted in results.
  const result=copy(planned.result||{});delete result.resume_code;delete result.token;
  const i={id:operation.id,actor:who.id,action:operation.action,request_hash:h,revision:v.revision+1,before_hash:hash(v.tables),after_hash:hash(planned.after),after:planned.after,audit_detail:planned.audit_detail||null,result,accepted_at:deps.now()};
  deps.store.assertFits(i);deps.store.appendIntent(copy(i));const saved=deps.store.read().intents.filter(x=>x.id===i.id);if(saved.length!==1||hash(saved[0])!==hash(i))fail('DOMAIN_INTENT_NOT_DURABLE');return finish(i,who);
 });}catch(e){return {ok:false,error:e.safeCode||'DOMAIN_INCOMPLETE'};}},readView:function(){return view(deps.store.read());}};
}


// SOURCE: domain_sheets_store.gs
/* Append-only chunk journal for a NEW approved isolation workbook only.
 * Precreated sheet D3_Journal: batch_id,kind,part,total,sha256,data.
 * No create/delete/overwrite. Incomplete chunk batches remain uncommitted evidence.
 * Must run under the same project-wide ScriptLock for every reader and writer. */
function juogDomainSheetsStoreV3_(ss,hash,uuid) {
 const sh=ss.getSheetByName('D3_Journal'),header=['batch_id','kind','part','total','sha256','data'];
 if(!sh||JSON.stringify(sh.getRange(1,1,1,6).getValues()[0])!==JSON.stringify(header))throw Error('DOMAIN_STORE_SCHEMA');
 function append(kind,value){const text=JSON.stringify(value);if(text.length>4000000)throw Error('DOMAIN_SIZE_LIMIT');const id=uuid(),n=Math.max(1,Math.ceil(text.length/20000)),digest=hash(text);
  for(let k=0;k<n;k++)sh.appendRow([id,kind,k,n,digest,text.slice(k*20000,(k+1)*20000)]);
  SpreadsheetApp.flush();sh.appendRow([id,kind,'SEALED',n,digest,'']);SpreadsheetApp.flush();
 }
 function read(){const rows=sh.getDataRange().getValues().slice(1),groups={};
  for(const row of rows){const id=String(row[0]);if(!groups[id])groups[id]=[];groups[id].push(row);}
  const data={baseline:null,intents:[],audits:[],commits:[],requests:[],requestEvents:[]};
  for(const entries of Object.values(groups)){
   const seals=entries.filter(r=>r[2]==='SEALED');if(!seals.length)continue;if(seals.length!==1)throw Error('JOURNAL_DUPLICATE_SEAL');
   const seal=seals[0],kind=seal[1],n=Number(seal[3]),parts=entries.filter(r=>r[2]!=='SEALED');
   if(!Number.isInteger(n)||n<1||parts.length!==n)throw Error('JOURNAL_INCOMPLETE');
   parts.sort((a,b)=>Number(a[2])-Number(b[2]));if(parts.some((r,i)=>Number(r[2])!==i||r[1]!==kind||r[3]!==seal[3]||r[4]!==seal[4]))throw Error('JOURNAL_CONFLICT');
   const text=parts.map(r=>r[5]).join('');if(hash(text)!==seal[4])throw Error('JOURNAL_HASH_MISMATCH');const value=JSON.parse(text);
   if(kind==='baseline'){if(data.baseline)throw Error('BASELINE_DUPLICATE');data.baseline=value;}
   else if(['intents','audits','commits','requests','requestEvents'].includes(kind))data[kind].push(value);else throw Error('JOURNAL_KIND');
  }
  if(!data.baseline)throw Error('BASELINE_MISSING');return data;
 }
 return {read,assertFits:i=>{if(JSON.stringify(i).length>4000000)throw Error('DOMAIN_SIZE_LIMIT');},appendIntent:i=>append('intents',i),appendAudit:a=>append('audits',a),appendCommit:c=>append('commits',c),appendRequest:r=>append('requests',r),appendRequestEvent:e=>append('requestEvents',e)};
}


// SOURCE: shadow_spreadsheet.gs
function juogShadowSpreadsheetV3_(snapshot) {
 const copy=v=>JSON.parse(JSON.stringify(v)),values=copy(snapshot),sheets={};
 function sheet(name){if(!Object.prototype.hasOwnProperty.call(values,name))return null;
  if(sheets[name])return sheets[name];
  function range(r,c,n,m){if(!Number.isInteger(r)||r<1||!Number.isInteger(c)||c<1)throw Error('INVALID_RANGE');n=n||1;m=m||1;return {
   getValues:()=>Array.from({length:n},(_,i)=>Array.from({length:m},(_,j)=>values[name][r+i-1]?.[c+j-1]??'')),
   getValue:()=>values[name][r-1]?.[c-1]??'',
   setValues:v=>{if(v.length!==n||v.some(row=>row.length!==m))throw Error('RANGE_SHAPE');v.forEach((row,i)=>{if(values[name][r+i-1]===null||values[name][r+i-1]===undefined)values[name][r+i-1]=[];row.forEach((x,j)=>values[name][r+i-1][c+j-1]=x);});},
   setValue:v=>{if(values[name][r-1]===null||values[name][r-1]===undefined)values[name][r-1]=[];values[name][r-1][c-1]=v;},clearContent:()=>{for(let i=0;i<n;i++)for(let j=0;j<m;j++){if(values[name][r+i-1]===null||values[name][r+i-1]===undefined)values[name][r+i-1]=[];values[name][r+i-1][c+j-1]='';}}
  };}
  return sheets[name]={getName:()=>name,getDataRange:()=>({getValues:()=>copy(values[name])}),getLastColumn:()=>Math.max(0,...values[name].map(r=>r.length)),getLastRow:()=>values[name].length,getRange:range,appendRow:r=>values[name].push(copy(r)),deleteRow:r=>values[name].splice(r-1,1),setFrozenRows:()=>{}};
 }
 return {getSheetByName:sheet,getName:()=> 'LOCAL SHADOW TEST',exportValues:()=>copy(values)};
}


// SOURCE: legacy_shadow_planner.gs
/* Offline/planning adapter. All legacy SpreadsheetApp writes target copied arrays.
No call to actual SpreadsheetApp, PropertiesService, network or logger is available.
This is NOT a deployed write handler. Auth must be enforced by migration_planner.
Source snapshot SHA256: 11ee6acc469266c7ffea0b31bd5b938fbc374d010d93047f43e70c77410e60c7 */
function juogLegacyPlanV3_(action, request, snapshot, runtime) {
 const shadow = juogShadowSpreadsheetV3_(snapshot);
 const SpreadsheetApp={openById:()=>shadow,flush:()=>{}};
 const PropertiesService={getScriptProperties:()=>({getProperty:k=>({SPREADSHEET_ID:'SHADOW_ONLY',DRAFT_CODE_PEPPER:runtime.draftPepper}[k]||null),setProperty:()=>{throw Error('CONFIG_MUTATION_FORBIDDEN');}})};
 const LockService={getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{}})};
 const Utilities=runtime.utilities;
 const Date=runtime.Date;
 const Logger={log:()=>{throw Error('LOGGING_FORBIDDEN');}};
/**
 * JUOG UTUC_Consolidative central eCRF service (v2.2.7)
 * Google Apps Script Web App bound to a dedicated Google Sheet.
 *
 * Workflow:
 *   Facility screening CRF -> Screening ID (JUOG-SCR-001...)
 *   -> independent reviews by radiology / medical oncology / urology
 *   -> study-office confirmation of MDT consensus
 *   -> only ELIGIBLE cases receive JUOG-001, JUOG-002... registration IDs
 *   -> subsequent eCRFs are stored append-only in dedicated Google Sheet tabs.
 *
 * Privacy: do NOT store name, MRN, address, or full DOB in this spreadsheet.
 */

const REGISTRY_SHEET = 'Registry';
const SCREENING_SHEET = 'Screening';
const SCREENING_CRF_SHEET = 'ScreeningCRF';
const SCREENING_AUDIT_SHEET = 'ScreeningAudit';
const MDT_REVIEW_SHEET = 'MDTReviews';
const CRF_30D_SHEET = 'CRF_30d';
const CRF_90D_SHEET = 'CRF_90d';
const CRF_FOLLOWUP_SHEET = 'CRF_Followup';
const CRF_AUDIT_SHEET = 'CRFSubmissionAudit';
const CRF_DRAFT_SHEET = 'CRF_Drafts';
const SETTINGS_SHEET = 'Settings';
const TIMEZONE = 'Asia/Tokyo';
const BACKEND_VERSION = 'v2.2.8-candidate';

const REVIEWER_ROLES = ['radiology', 'medical_oncology', 'urology'];

const REGISTRY_HEADERS = [
  'registered_at', 'registration_id', 'status',
  'facility_code', 'facility_name', 'local_subject_code',
  'reporter_email', 'consent_date', 'mdt_date', 'cN', 'best_effect',
  'site_recist', 'screening_id', 'central_recist', 'recist_concordance'
];

const SCREENING_HEADERS = [
  'screening_id', 'created_at', 'updated_at', 'status', 'review_round',
  'facility_code', 'facility_name', 'local_subject_code', 'reporter_email',
  'submission_id', 'consent_date', 'cT', 'cN', 'cM', 'best_effect', 'site_recist',
  'planned_surgery', 'planned_surgery_date',
  'mdt_date', 'central_recist', 'recist_concordance', 'mdt_decision', 'mdt_reason', 'consensus_note',
  'registration_id', 'registered_at', 'admin_user'
];

const SCREENING_AUDIT_HEADERS = [
  'timestamp', 'screening_id', 'review_round', 'action', 'status_after',
  'facility_code', 'local_subject_code', 'submission_id',
  'mdt_date', 'site_recist', 'central_recist', 'recist_concordance', 'mdt_decision', 'mdt_reason', 'consensus_note',
  'registration_id', 'admin_user'
];

const MDT_REVIEW_HEADERS = [
  'review_id', 'submitted_at', 'screening_id', 'review_round',
  'reviewer_role', 'reviewer_name', 'review_version', 'is_correction', 'correction_reason',
  'decision', 'comment',
  'central_recist', 'organ_invasion', 'vessel_invasion', 'cm1_status',
  'g3_ae_recovered', 'ecog_0_1', 'medical_safety',
  'technically_resectable', 'surgery_appropriate'
];

const CRF_BASE_HEADERS = [
  'saved_at', 'record_version', 'submission_id', 'record_key', 'submission_kind',
  'correction_reason', 'submitted_at', 'registration_id', 'facility_code',
  'facility_name', 'reporter_email', 'crf_type', 'visit', 'schema_version',
  'study_code', 'payload_json'
];

const CRF_AUDIT_HEADERS = [
  'saved_at', 'sheet_name', 'record_key', 'record_version', 'submission_id',
  'submission_kind', 'registration_id', 'facility_code'
];

const CRF_DRAFT_HEADERS = [
  'draft_key', 'updated_at', 'registration_id', 'crf_type', 'visit',
  'facility_code', 'facility_name', 'reporter_email', 'schema_version', 'draft_json',
  'resume_code_hash', 'failed_attempts', 'locked_until',
  'code_reset_at', 'code_reset_by', 'email_reset_at', 'email_reset_by'
];

function authorizeJuogAction_(action, actor, payload, props) {
  const adminOnly = ['list_screenings', 'get_screening', 'finalize_mdt',
    'reset_draft_code', 'update_draft_email', 'stats'];
  const reviewerOnly = ['list_review_cases', 'get_screening_crf',
    'get_own_review', 'submit_mdt_review'];
  const both = ['get_mdt_reviews'];
  if (adminOnly.indexOf(action) < 0 && reviewerOnly.indexOf(action) < 0 && both.indexOf(action) < 0) {
    return {ok:true, kind:'facility'};
  }
  if (!actor || typeof actor !== 'object' || Array.isArray(actor)) {
    return {ok:false, error:'ROLE_AUTH_REQUIRED'};
  }
  const kind = String(actor.kind || '');
  const actualKey = String(actor.key || '');
  let expectedKey = '';
  if (kind === 'admin') {
    if (reviewerOnly.indexOf(action) >= 0) return {ok:false, error:'ROLE_NOT_ALLOWED'};
    expectedKey = String(props.getProperty('JUOG_ADMIN_ACTION_TOKEN') || '');
  } else if (kind === 'reviewer') {
    if (adminOnly.indexOf(action) >= 0) return {ok:false, error:'ROLE_NOT_ALLOWED'};
    const role = String(actor.role || '');
    if (REVIEWER_ROLES.indexOf(role) < 0) return {ok:false, error:'ROLE_NOT_ALLOWED'};
    if (['list_review_cases', 'get_own_review', 'submit_mdt_review'].indexOf(action) >= 0 &&
        String((payload || {}).reviewer_role || '') !== role) {
      return {ok:false, error:'REVIEWER_ROLE_MISMATCH'};
    }
    expectedKey = String(props.getProperty('JUOG_REVIEWER_' + role.toUpperCase() + '_ACTION_TOKEN') || '');
  } else {
    return {ok:false, error:'ROLE_AUTH_REQUIRED'};
  }
  if (!expectedKey) return {ok:false, error:'ROLE_AUTH_NOT_CONFIGURED'};
  if (!actualKey || actualKey !== expectedKey) return {ok:false, error:'ROLE_AUTH_FAILED'};
  return {ok:true, kind:kind, role:kind === 'reviewer' ? String(actor.role) : ''};
}

// Reviewer notification screens may see submission counts, not other reviewers' clinical judgments.
function reviewerMdtProgressOnly_(result) {
  if (!result || !result.ok) return result;
  const statuses = {};
  REVIEWER_ROLES.forEach(function(role) {
    statuses[role] = result.reviews && result.reviews[role] ? {submitted:true} : null;
  });
  return {
    ok:true, screening_id:result.screening_id, review_round:result.review_round,
    completed:result.completed, required:result.required,
    all_complete:result.all_complete, reviews:statuses
  };
}

function submitScreening_(p) {
  const required = [
    'facility_code', 'facility_name', 'local_subject_code', 'reporter_email',
    'submission_id', 'consent_date', 'ct', 'cn', 'cm', 'best_effect', 'site_recist'
  ];
  const missing = required.filter(k => !String(p[k] || '').trim());
  if (missing.length) return {ok: false, error: 'MISSING_FIELDS', message: missing.join(', ')};
  if (!p.crf_payload || typeof p.crf_payload !== 'object') {
    return {ok: false, error: 'MISSING_CRF_PAYLOAD', message: 'screening CRF snapshot is required'};
  }
  if (containsDirectIdentifier_(p.crf_payload)) return {ok:false, error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};
  const hardCheck = validateScreeningHardStops_(p);
  if (!hardCheck.ok) return hardCheck;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const screenSh = ss.getSheetByName(SCREENING_SHEET);
    const regSh = ss.getSheetByName(REGISTRY_SHEET);
    const auditSh = ss.getSheetByName(SCREENING_AUDIT_SHEET);

    const regValues = regSh.getDataRange().getValues();
    const regIdx = headerIndex_(regValues[0]);
    for (let r = 1; r < regValues.length; r++) {
      const row = regValues[r];
      if (String(row[regIdx.facility_code]) === String(p.facility_code) &&
          String(row[regIdx.local_subject_code]) === String(p.local_subject_code) &&
          String(row[regIdx.status] || 'ACTIVE') !== 'VOID') {
        return {ok: false, error: 'ALREADY_REGISTERED', message: 'この症例はすでに正式登録されています', registration_id: String(row[regIdx.registration_id])};
      }
    }

    const values = screenSh.getDataRange().getValues();
    const idx = headerIndex_(values[0]);

    // Idempotency for network retry.
    for (let r = 1; r < values.length; r++) {
      const row = values[r];
      if (String(row[idx.submission_id]) === String(p.submission_id)) {
        const existingScreeningId = String(row[idx.screening_id]);
        const existingRound = parseInt(row[idx.review_round] || '1', 10) || 1;
        if (!submissionExistsInSheet_(SCREENING_CRF_SHEET, String(p.submission_id))) {
          const retryPayload = JSON.parse(JSON.stringify(p.crf_payload));
          retryPayload.screening_id = existingScreeningId;
          retryPayload.review_round = existingRound;
          const retrySave = savePayloadToSheet_(SCREENING_CRF_SHEET, retryPayload, false);
          if (!retrySave.ok) return {ok: false, error: 'SCREENING_CRF_SAVE_FAILED', message: retrySave.message || retrySave.error};
        }
        return {ok: true, existing: true, screening_id: existingScreeningId, review_round: existingRound, status: String(row[idx.status]), registration_id: String(row[idx.registration_id] || '')};
      }
    }

    let existingRow = -1;
    let oldRound = 0;
    for (let r = 1; r < values.length; r++) {
      const row = values[r];
      if (String(row[idx.facility_code]) === String(p.facility_code) && String(row[idx.local_subject_code]) === String(p.local_subject_code)) {
        existingRow = r + 1;
        const status = String(row[idx.status] || 'PENDING').toUpperCase();
        oldRound = parseInt(row[idx.review_round] || '1', 10) || 1;
        if (status === 'REGISTERED') return {ok: false, error: 'ALREADY_REGISTERED', registration_id: String(row[idx.registration_id] || '')};
        if (status === 'INELIGIBLE') return {ok: false, error: 'SCREENING_CLOSED', message: '中央MDTで不適格確定済みです。', screening_id: String(row[idx.screening_id])};
        break;
      }
    }

    const now = new Date();
    let screeningId;
    let reviewRound;
    if (existingRow > 0) {
      screeningId = String(screenSh.getRange(existingRow, idx.screening_id + 1).getValue());
      reviewRound = oldRound + 1;
      setByHeader_(screenSh, existingRow, idx, {
        updated_at: now, status: 'PENDING', review_round: reviewRound,
        facility_name: String(p.facility_name), reporter_email: String(p.reporter_email), submission_id: String(p.submission_id),
        consent_date: String(p.consent_date), cT: String(p.ct), cN: String(p.cn), cM: String(p.cm),
        best_effect: String(p.best_effect), site_recist: String(p.site_recist),
        planned_surgery: String(p.planned_surgery || ''), planned_surgery_date: String(p.planned_surgery_date || ''),
        mdt_date: '', central_recist: '', mdt_decision: '', mdt_reason: '', consensus_note: '',
        registration_id: '', registered_at: '', admin_user: ''
      });
    } else {
      screeningId = nextScreeningId_(values, idx);
      reviewRound = 1;
      appendByHeaders_(screenSh, {
        screening_id: screeningId, created_at: now, updated_at: now, status: 'PENDING', review_round: reviewRound,
        facility_code: String(p.facility_code), facility_name: String(p.facility_name), local_subject_code: String(p.local_subject_code),
        reporter_email: String(p.reporter_email), submission_id: String(p.submission_id), consent_date: String(p.consent_date),
        cT: String(p.ct), cN: String(p.cn), cM: String(p.cm), best_effect: String(p.best_effect), site_recist: String(p.site_recist),
        planned_surgery: String(p.planned_surgery || ''), planned_surgery_date: String(p.planned_surgery_date || '')
      });
    }

    const crfPayload = JSON.parse(JSON.stringify(p.crf_payload));
    crfPayload.screening_id = screeningId;
    crfPayload.review_round = reviewRound;
    const crfSave = savePayloadToSheet_(SCREENING_CRF_SHEET, crfPayload, false);
    if (!crfSave.ok) throw new Error('SCREENING_CRF_SAVE_FAILED: ' + (crfSave.message || crfSave.error || 'unknown'));

    appendByHeaders_(auditSh, {
      timestamp: now, screening_id: screeningId, review_round: reviewRound,
      action: existingRow > 0 ? 'SCREENING_RESUBMIT' : 'SCREENING_SUBMIT', status_after: 'PENDING',
      facility_code: String(p.facility_code), local_subject_code: String(p.local_subject_code), submission_id: String(p.submission_id)
    });
    SpreadsheetApp.flush();
    return {ok: true, existing: existingRow > 0, screening_id: screeningId, review_round: reviewRound, status: 'PENDING'};
  } finally {
    lock.releaseLock();
  }
}

function listScreenings_(p) {
  const statuses = String(p.statuses || 'PENDING,HOLD').split(',').map(x => x.trim().toUpperCase()).filter(Boolean);
  const sh = getSpreadsheet_().getSheetByName(SCREENING_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  const rows = [];
  for (let r = 1; r < values.length; r++) {
    const status = String(values[r][idx.status] || 'PENDING').toUpperCase();
    if (statuses.length && statuses.indexOf(status) < 0) continue;
    rows.push(screeningObject_(values[r], idx, false));
  }
  rows.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
  return {ok: true, screenings: rows, count: rows.length, stats: getStats_()};
}

function listReviewCases_(p) {
  const role = String(p.reviewer_role || '').trim();
  if (REVIEWER_ROLES.indexOf(role) < 0) return {ok: false, error: 'INVALID_REVIEWER_ROLE'};
  const ss = getSpreadsheet_();
  const sh = ss.getSheetByName(SCREENING_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  const rows = [];
  for (let r = 1; r < values.length; r++) {
    const status = String(values[r][idx.status] || 'PENDING').toUpperCase();
    if (status !== 'PENDING') continue;
    const obj = screeningObject_(values[r], idx, false);
    const own = latestReview_(obj.screening_id, obj.review_round, role);
    obj.review_submitted = !!own;
    obj.review_version = own ? own.review_version : 0;
    rows.push(obj);
  }
  rows.sort((a, b) => {
    if (a.review_submitted !== b.review_submitted) return a.review_submitted ? 1 : -1;
    return String(b.updated_at).localeCompare(String(a.updated_at));
  });
  return {ok: true, cases: rows};
}

function getScreening_(p) {
  const found = findScreening_(p.screening_id);
  if (!found) return {ok: false, error: 'SCREENING_NOT_FOUND'};
  return {ok: true, screening: screeningObject_(found.row, found.idx, true), stats: getStats_()};
}

function getScreeningCrf_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return {ok: false, error: 'INVALID_SCREENING_ID'};
  const sh = getSpreadsheet_().getSheetByName(SCREENING_CRF_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  let best = null;
  let bestVersion = -1;
  for (let r = 1; r < values.length; r++) {
    const sid = idx.screening_id !== undefined ? String(values[r][idx.screening_id] || '').toUpperCase() : '';
    if (sid !== screeningId) continue;
    const v = Number(values[r][idx.record_version] || 0);
    if (v >= bestVersion) {
      try {
        best = JSON.parse(String(values[r][idx.payload_json] || '{}'));
        bestVersion = v;
      } catch (err) {
        return {ok: false, error: 'SCREENING_CRF_JSON_ERROR'};
      }
    }
  }
  if (!best) return {ok: false, error: 'SCREENING_CRF_NOT_FOUND'};
  return {ok: true, payload: best, record_version: bestVersion};
}

function getOwnReview_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  const role = String(p.reviewer_role || '').trim();
  const round = parseInt(p.review_round || '0', 10);
  if (REVIEWER_ROLES.indexOf(role) < 0) return {ok: false, error: 'INVALID_REVIEWER_ROLE'};
  const review = latestReview_(screeningId, round, role);
  return {ok: true, review: review || null};
}

function submitMdtReview_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  const role = String(p.reviewer_role || '').trim();
  const reviewerName = String(p.reviewer_name || '').trim();
  const decision = String(p.decision || '').trim().toUpperCase();
  const comment = String(p.comment || '').trim();
  const round = parseInt(p.review_round || '0', 10);
  const isCorrection = !!p.is_correction;
  const correctionReason = String(p.correction_reason || '').trim();

  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return {ok: false, error: 'INVALID_SCREENING_ID'};
  if (REVIEWER_ROLES.indexOf(role) < 0) return {ok: false, error: 'INVALID_REVIEWER_ROLE'};
  if (!reviewerName) return {ok: false, error: 'MISSING_REVIEWER_NAME'};
  if (['ELIGIBLE', 'INELIGIBLE', 'HOLD'].indexOf(decision) < 0) return {ok: false, error: 'INVALID_DECISION'};
  if (!round) return {ok: false, error: 'INVALID_REVIEW_ROUND'};
  if ((decision === 'INELIGIBLE' || decision === 'HOLD') && !comment) return {ok: false, error: 'MISSING_COMMENT'};

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};
  try {
    const found = findScreening_(screeningId);
  if (!found) return {ok: false, error: 'SCREENING_NOT_FOUND'};
  const currentStatus = String(found.row[found.idx.status] || '').toUpperCase();
  const currentRound = parseInt(found.row[found.idx.review_round] || '1', 10) || 1;
  if (currentStatus !== 'PENDING') return {ok: false, error: 'SCREENING_NOT_OPEN', message: '現在この症例は判定入力受付中ではありません'};
  if (round !== currentRound) return {ok: false, error: 'STALE_REVIEW_ROUND', message: '申請内容が更新されています。画面を再読み込みしてください。'};

  const prior = latestReview_(screeningId, round, role);
  if (prior && !isCorrection) return {ok: false, error: 'REVIEW_ALREADY_SUBMITTED', message: 'この審査ラウンドではすでに判定済みです。訂正再提出を選択してください。'};
  if (isCorrection && !prior) return {ok: false, error: 'NO_PRIOR_REVIEW'};
  if (isCorrection && !correctionReason) return {ok: false, error: 'MISSING_CORRECTION_REASON'};

  const record = {
    review_id: Utilities.getUuid(), submitted_at: new Date(), screening_id: screeningId, review_round: round,
    reviewer_role: role, reviewer_name: reviewerName, review_version: prior ? Number(prior.review_version) + 1 : 1,
    is_correction: isCorrection ? 'TRUE' : 'FALSE', correction_reason: correctionReason,
    decision: decision, comment: comment,
    central_recist: '', organ_invasion: '', vessel_invasion: '', cm1_status: '',
    g3_ae_recovered: '', ecog_0_1: '', medical_safety: '',
    technically_resectable: '', surgery_appropriate: ''
  };

  if (role === 'radiology') {
    const recist = String(p.central_recist || '').trim().toUpperCase();
    const organ = String(p.organ_invasion || '').trim();
    const vessel = String(p.vessel_invasion || '').trim();
    const cm1 = String(p.cm1_status || '').trim();
    if (['CR', 'PR', 'SD', 'PD', 'NE'].indexOf(recist) < 0 || !organ || !vessel || !cm1) return {ok: false, error: 'MISSING_RADIOLOGY_FIELDS'};
    record.central_recist = recist; record.organ_invasion = organ; record.vessel_invasion = vessel; record.cm1_status = cm1;
  } else if (role === 'medical_oncology') {
    const ae = String(p.g3_ae_recovered || '').trim();
    const ecog = String(p.ecog_0_1 || '').trim();
    const safety = String(p.medical_safety || '').trim();
    if (!ae || !ecog || !safety) return {ok: false, error: 'MISSING_MEDICAL_ONCOLOGY_FIELDS'};
    record.g3_ae_recovered = ae; record.ecog_0_1 = ecog; record.medical_safety = safety;
  } else if (role === 'urology') {
    const resectable = String(p.technically_resectable || '').trim();
    const appropriate = String(p.surgery_appropriate || '').trim();
    if (!resectable || !appropriate) return {ok: false, error: 'MISSING_UROLOGY_FIELDS'};
    record.technically_resectable = resectable; record.surgery_appropriate = appropriate;
  }

  appendByHeaders_(getSpreadsheet_().getSheetByName(MDT_REVIEW_SHEET), record);
    SpreadsheetApp.flush();
    return {ok: true, review_id: record.review_id, review_version: record.review_version, screening_id: screeningId, review_round: round};
  } finally {
    lock.releaseLock();
  }
}

function getMdtReviews_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  const found = findScreening_(screeningId);
  if (!found) return {ok: false, error: 'SCREENING_NOT_FOUND'};
  const round = parseInt(found.row[found.idx.review_round] || '1', 10) || 1;
  const reviews = {};
  REVIEWER_ROLES.forEach(role => { reviews[role] = latestReview_(screeningId, round, role); });
  const completed = REVIEWER_ROLES.filter(role => !!reviews[role]).length;
  return {ok: true, screening_id: screeningId, review_round: round, completed: completed, required: REVIEWER_ROLES.length, all_complete: completed === REVIEWER_ROLES.length, reviews: reviews};
}

function finalizeMdt_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  const decision = String(p.decision || '').trim().toUpperCase();
  const mdtDate = String(p.mdt_date || '').trim();
  const reason = String(p.reason || '').trim();
  const consensusNote = String(p.consensus_note || '').trim();
  const adminUser = String(p.admin_user || '').trim();
  const consensusConfirmed = !!p.consensus_confirmed;

  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return {ok: false, error: 'INVALID_SCREENING_ID'};
  if (['ELIGIBLE', 'INELIGIBLE', 'HOLD'].indexOf(decision) < 0) return {ok: false, error: 'INVALID_DECISION'};
  if (!mdtDate || !adminUser || !consensusConfirmed) return {ok: false, error: 'MISSING_FINAL_CONFIRMATION'};
  if ((decision === 'INELIGIBLE' || decision === 'HOLD') && !reason) return {ok: false, error: 'MISSING_REASON'};

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};
  try {
    const found = findScreening_(screeningId);
    if (!found) return {ok: false, error: 'SCREENING_NOT_FOUND'};
    const currentStatus = String(found.row[found.idx.status] || 'PENDING').toUpperCase();
    if (currentStatus === 'REGISTERED') return {ok: true, existing: true, status: 'REGISTERED', registration_id: String(found.row[found.idx.registration_id] || ''), registration_date: isoDate_(found.row[found.idx.registered_at])};
    if (currentStatus === 'INELIGIBLE') return {ok: false, error: 'SCREENING_CLOSED'};
    if (currentStatus !== 'PENDING') return {ok: false, error: 'SCREENING_NOT_READY'};

    const round = parseInt(found.row[found.idx.review_round] || '1', 10) || 1;
    const reviews = {};
    REVIEWER_ROLES.forEach(role => { reviews[role] = latestReview_(screeningId, round, role); });
    if (REVIEWER_ROLES.some(role => !reviews[role])) return {ok: false, error: 'REVIEWS_INCOMPLETE', message: '3名の中央MDT判定が揃っていません'};

    const individualDecisions = REVIEWER_ROLES.map(role => String(reviews[role].decision || ''));
    const unanimous = individualDecisions.every(x => x === individualDecisions[0]);
    if ((!unanimous || individualDecisions[0] !== decision) && !consensusNote) {
      return {ok: false, error: 'CONSENSUS_NOTE_REQUIRED', message: '個別判定と最終合意が一致しない場合は、合意形成内容を記録してください'};
    }

    const centralRecist = String(reviews.radiology.central_recist || '').toUpperCase();
    const siteRecist = String(found.row[found.idx.site_recist] || '').toUpperCase();
    const recistConcordance = recistConcordance_(siteRecist, centralRecist);
    if (decision === 'ELIGIBLE' && ['CR', 'PR', 'SD'].indexOf(centralRecist) < 0) {
      return {ok: false, error: 'RECIST_NOT_ELIGIBLE', message: '正式登録には放射線診断医の中央RECISTがCR/PR/SDである必要があります'};
    }

    // v2.2.6: chronology hard stops for ELIGIBLE formal registration.
    // The study workflow requires central MDT approval and formal registration
    // before surgery. HOLD / INELIGIBLE decisions are not blocked by these checks.
    if (decision === 'ELIGIBLE') {
      const plannedSurgeryDate = dateOnly_(found.row[found.idx.planned_surgery_date]);
      const mdtDateOnly = dateOnly_(mdtDate);
      const registrationDate = Utilities.formatDate(new Date(), TIMEZONE, 'yyyy-MM-dd');

      if (plannedSurgeryDate && mdtDateOnly && plannedSurgeryDate < mdtDateOnly) {
        return {
          ok: false,
          error: 'SURGERY_BEFORE_MDT',
          message: `手術予定日（${plannedSurgeryDate}）が中央MDT最終判定日（${mdtDateOnly}）より前です。日付を確認してください。`
        };
      }

      if (plannedSurgeryDate && plannedSurgeryDate < registrationDate) {
        return {
          ok: false,
          error: 'SURGERY_BEFORE_REGISTRATION',
          message: `手術予定日（${plannedSurgeryDate}）が正式登録日（${registrationDate}）より前です。正式登録は手術前に完了する必要があります。`
        };
      }
    }

    const ss = getSpreadsheet_();
    const screenSh = ss.getSheetByName(SCREENING_SHEET);
    const auditSh = ss.getSheetByName(SCREENING_AUDIT_SHEET);
    const now = new Date();

    if (decision === 'HOLD' || decision === 'INELIGIBLE') {
      const newStatus = decision === 'HOLD' ? 'HOLD' : 'INELIGIBLE';
      setByHeader_(screenSh, found.sheetRow, found.idx, {
        updated_at: now, status: newStatus, mdt_date: mdtDate, central_recist: centralRecist, recist_concordance: recistConcordance,
        mdt_decision: decision, mdt_reason: reason, consensus_note: consensusNote, admin_user: adminUser
      });
      appendByHeaders_(auditSh, {
        timestamp: now, screening_id: screeningId, review_round: round, action: 'MDT_' + decision, status_after: newStatus,
        facility_code: String(found.row[found.idx.facility_code]), local_subject_code: String(found.row[found.idx.local_subject_code]),
        submission_id: String(found.row[found.idx.submission_id]), mdt_date: mdtDate, site_recist: siteRecist, central_recist: centralRecist, recist_concordance: recistConcordance,
        mdt_decision: decision, mdt_reason: reason, consensus_note: consensusNote, admin_user: adminUser
      });
      SpreadsheetApp.flush();
      return {ok: true, screening_id: screeningId, status: newStatus, decision: decision, site_recist: siteRecist, central_recist: centralRecist, recist_concordance: recistConcordance};
    }

    const regSh = ss.getSheetByName(REGISTRY_SHEET);
    const regValues = regSh.getDataRange().getValues();
    const rIdx = headerIndex_(regValues[0]);

    for (let r = 1; r < regValues.length; r++) {
      const regRow = regValues[r];
      if (String(regRow[rIdx.facility_code]) === String(found.row[found.idx.facility_code]) &&
          String(regRow[rIdx.local_subject_code]) === String(found.row[found.idx.local_subject_code]) &&
          String(regRow[rIdx.status] || 'ACTIVE') !== 'VOID') {
        const existingId = String(regRow[rIdx.registration_id]);
        setByHeader_(screenSh, found.sheetRow, found.idx, {updated_at: now, status: 'REGISTERED', mdt_date: mdtDate, central_recist: centralRecist, recist_concordance: recistConcordance, mdt_decision: 'ELIGIBLE', mdt_reason: '', consensus_note: consensusNote, registration_id: existingId, registered_at: regRow[rIdx.registered_at], admin_user: adminUser});
        return {ok: true, existing: true, screening_id: screeningId, status: 'REGISTERED', registration_id: existingId, registration_date: isoDate_(regRow[rIdx.registered_at])};
      }
    }

    const activeRows = regValues.slice(1).filter(row => String(row[rIdx.status] || 'ACTIVE') !== 'VOID');
    const cn1Count = countCn1OnlyRegistered_(activeRows, rIdx, found.values, found.idx);
    const sdCount = activeRows.filter(row => String(row[rIdx.best_effect]).toUpperCase() === 'SD').length;
    const settings = getSettings_();
    const totalMax = parseInt(settings.TOTAL_MAX || '42', 10);
    const allowTotalAfterMax = String(settings.ALLOW_TOTAL_AFTER_MAX || 'FALSE').toUpperCase() === 'TRUE';
    const cn1Max = parseInt(settings.CN1_MAX || '20', 10);
    const sdThreshold = parseInt(settings.SD_HOLD_THRESHOLD || '12', 10);
    const allowSdAfter = String(settings.ALLOW_SD_AFTER_THRESHOLD || 'FALSE').toUpperCase() === 'TRUE';
    const bestEffect = String(found.row[found.idx.best_effect] || '').toUpperCase();

    if (activeRows.length >= totalMax && !allowTotalAfterMax) return {ok: false, error: 'TOTAL_CAP_REACHED', message: `目標登録数 ${totalMax} 例に到達しています`};
    if (isCn1Only_(found.row[found.idx.cT], found.row[found.idx.cN], found.row[found.idx.cM]) && cn1Count >= cn1Max) return {ok: false, error: 'CN1_CAP_REACHED', message: `cN1登録上限 ${cn1Max} 例に到達しています`};
    if (bestEffect === 'SD' && sdCount >= sdThreshold && !allowSdAfter) return {ok: false, error: 'SD_CAP_HOLD', message: `SD症例が ${sdThreshold} 例に到達しているため、新規SD登録は一時保留です`};

    let maxNo = 0;
    regValues.slice(1).forEach(row => { const m = String(row[rIdx.registration_id] || '').match(/^JUOG-(\d+)$/); if (m) maxNo = Math.max(maxNo, parseInt(m[1], 10)); });
    const registrationId = 'JUOG-' + String(maxNo + 1).padStart(3, '0');

    appendByHeaders_(regSh, {
      registered_at: now, registration_id: registrationId, status: 'ACTIVE',
      facility_code: String(found.row[found.idx.facility_code]), facility_name: String(found.row[found.idx.facility_name]),
      local_subject_code: String(found.row[found.idx.local_subject_code]), reporter_email: String(found.row[found.idx.reporter_email]),
      consent_date: String(found.row[found.idx.consent_date]), mdt_date: mdtDate, cN: String(found.row[found.idx.cN]),
      best_effect: bestEffect, site_recist: siteRecist, screening_id: screeningId, central_recist: centralRecist, recist_concordance: recistConcordance
    });
    setByHeader_(screenSh, found.sheetRow, found.idx, {
      updated_at: now, status: 'REGISTERED', mdt_date: mdtDate, central_recist: centralRecist, recist_concordance: recistConcordance,
      mdt_decision: 'ELIGIBLE', mdt_reason: '', consensus_note: consensusNote,
      registration_id: registrationId, registered_at: now, admin_user: adminUser
    });
    appendByHeaders_(auditSh, {
      timestamp: now, screening_id: screeningId, review_round: round, action: 'MDT_ELIGIBLE_REGISTER', status_after: 'REGISTERED',
      facility_code: String(found.row[found.idx.facility_code]), local_subject_code: String(found.row[found.idx.local_subject_code]),
      submission_id: String(found.row[found.idx.submission_id]), mdt_date: mdtDate, site_recist: siteRecist, central_recist: centralRecist, recist_concordance: recistConcordance,
      mdt_decision: 'ELIGIBLE', mdt_reason: '', consensus_note: consensusNote, registration_id: registrationId, admin_user: adminUser
    });
    SpreadsheetApp.flush();
    return {ok: true, existing: false, screening_id: screeningId, status: 'REGISTERED', registration_id: registrationId, registration_date: Utilities.formatDate(now, TIMEZONE, 'yyyy-MM-dd'), site_recist: siteRecist, central_recist: centralRecist, recist_concordance: recistConcordance, counts_after: {total: activeRows.length + 1, cN1: cn1Count + (isCn1Only_(found.row[found.idx.cT], found.row[found.idx.cN], found.row[found.idx.cM]) ? 1 : 0), SD: sdCount + (bestEffect === 'SD' ? 1 : 0)}};
  } finally {
    lock.releaseLock();
  }
}

function numOrNull_(v) {
  if (v === null || v === undefined || String(v).trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function dateOnly_(v) {
  const s = isoDate_(v);
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : '';
}

function validateScreeningHardStops_(p) {
  const data = (p.crf_payload && p.crf_payload.data) || {};
  const errors = [];
  const h = numOrNull_(data.height_cm), w = numOrNull_(data.weight_kg);
  if (h !== null && (h < 80 || h > 250)) errors.push('身長は80〜250 cmの範囲で入力してください（桁・単位を確認してください）');
  if (w !== null && (w < 20 || w >= 300)) errors.push('体重は20〜300 kg未満の範囲で入力してください（桁・単位を確認してください）');
  const vit = data.screening_vitals || {};
  const sbp = numOrNull_(vit.sbp), dbp = numOrNull_(vit.dbp), pulse = numOrNull_(vit.pulse), temp = numOrNull_(vit.temperature);
  if (sbp !== null && (sbp < 40 || sbp > 300)) errors.push('収縮期血圧の桁を確認してください');
  if (dbp !== null && (dbp < 20 || dbp > 200)) errors.push('拡張期血圧の桁を確認してください');
  if (pulse !== null && (pulse < 20 || pulse > 250)) errors.push('脈拍の桁を確認してください');
  if (temp !== null && (temp < 25 || temp > 45)) errors.push('体温の桁・単位を確認してください');
  if (sbp !== null && dbp !== null && dbp >= sbp) errors.push('拡張期血圧が収縮期血圧以上です');

  const consent = dateOnly_(p.consent_date || data.consent_date);
  const planned = dateOnly_(p.planned_surgery_date || data.planned_surgery_date);
  const evpEnd = dateOnly_(data.evp_end);
  if (consent && planned && planned < consent) errors.push('手術予定日が同意取得日より前です');
  if (evpEnd && planned && evpEnd > planned) errors.push('EVP最終投与日が手術予定日より後です');
  if (errors.length) return {ok:false, error:'HARD_VALIDATION_FAILED', message:errors.join(' / ')};
  return {ok:true};
}

function validateVitalBlockHardStops_(v, label, errors) {
  if (!v || typeof v !== 'object') return;
  const sbp=numOrNull_(v.sbp), dbp=numOrNull_(v.dbp), pulse=numOrNull_(v.pulse), temp=numOrNull_(v.temperature);
  if (sbp !== null && (sbp < 40 || sbp > 300)) errors.push(label+'：収縮期血圧の桁を確認してください');
  if (dbp !== null && (dbp < 20 || dbp > 200)) errors.push(label+'：拡張期血圧の桁を確認してください');
  if (pulse !== null && (pulse < 20 || pulse > 250)) errors.push(label+'：脈拍の桁を確認してください');
  if (temp !== null && (temp < 25 || temp > 45)) errors.push(label+'：体温の桁・単位を確認してください');
  if (sbp !== null && dbp !== null && dbp >= sbp) errors.push(label+'：拡張期血圧が収縮期血圧以上です');
}

function validateCrfHardStops_(payload, registryInfo) {
  const data = payload.data || {};
  const errors = [];
  const regDate = dateOnly_(registryInfo.registration_date);
  const consentDate = dateOnly_(registryInfo.consent_date);
  const deathDate = dateOnly_(data.death_date);
  const refDate = dateOnly_(data.reference_date);
  const opDate = dateOnly_(data.operation_date);
  const evpEnd = dateOnly_(data.last_evp_date);
  const visitDate = dateOnly_(data.visit_date || data.day30_visit_date);

  if (deathDate && regDate && deathDate < regDate) errors.push('死亡日が研究登録日より前です');
  if (refDate && regDate && refDate < regDate) errors.push('手術日/予定日が研究登録日より前です');
  if (opDate && regDate && opDate < regDate) errors.push('手術実施日が研究登録日より前です');
  if (opDate && consentDate && opDate < consentDate) errors.push('手術実施日が同意取得日より前です');
  if (evpEnd && opDate && evpEnd > opDate) errors.push('EVP最終投与日が手術実施日より後です');
  if (visitDate && refDate && visitDate < refDate) errors.push('評価日が手術日/予定日より前です');

  validateVitalBlockHardStops_(data.day0_vitals, 'Day0バイタル', errors);
  validateVitalBlockHardStops_(data.inpatient_vitals, '入院中バイタル', errors);
  if (errors.length) return {ok:false, error:'HARD_VALIDATION_FAILED', message:errors.join(' / ')};
  return {ok:true};
}


function getLatestCrfPayload_(sheetName, registrationId, crfType) {
  const sh = getSpreadsheet_().getSheetByName(sheetName);
  if (!sh) return {ok:false, error:'SOURCE_SHEET_NOT_FOUND'};

  const values = sh.getDataRange().getValues();
  if (!values || values.length < 2) return {ok:true, found:false};

  const idx = headerIndex_(values[0]);
  if (idx.registration_id === undefined || idx.payload_json === undefined) {
    return {ok:false, error:'SOURCE_SHEET_SCHEMA_ERROR'};
  }

  let best = null;
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (String(row[idx.registration_id] || '').trim().toUpperCase() !== String(registrationId || '').trim().toUpperCase()) continue;
    if (idx.crf_type !== undefined && crfType && String(row[idx.crf_type] || '') !== String(crfType)) continue;

    const version = idx.record_version !== undefined ? Number(row[idx.record_version] || 0) : 0;
    const savedAt = idx.saved_at !== undefined && row[idx.saved_at] instanceof Date ? row[idx.saved_at].getTime() : 0;

    if (!best || version > best.version || (version === best.version && savedAt > best.savedAt)) {
      let payload = null;
      try {
        payload = JSON.parse(String(row[idx.payload_json] || '{}'));
      } catch (err) {
        return {ok:false, error:'SOURCE_PAYLOAD_PARSE_ERROR', message:String(err)};
      }
      best = {
        version: version,
        savedAt: savedAt,
        submissionId: idx.submission_id !== undefined ? String(row[idx.submission_id] || '') : '',
        facilityCode: idx.facility_code !== undefined ? String(row[idx.facility_code] || '') : '',
        facilityName: idx.facility_name !== undefined ? String(row[idx.facility_name] || '') : '',
        payload: payload
      };
    }
  }

  if (!best) return {ok:true, found:false};
  return {
    ok:true,
    found:true,
    record_version:best.version,
    submission_id:best.submissionId,
    facility_code:best.facilityCode,
    facility_name:best.facilityName,
    payload:best.payload
  };
}


function getCrfLinkage_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const sourceType = String(p.source_crf_type || 'perioperative_30d').trim();

  const registry = validateSubject_({registration_id:id, facility_code:''});
  if (!registry.ok) return registry;

  if (sourceType !== 'perioperative_30d') {
    return {ok:false, error:'UNSUPPORTED_SOURCE_CRF_TYPE'};
  }

  const latest = getLatestCrfPayload_(CRF_30D_SHEET, id, 'perioperative_30d');
  if (!latest.ok) return latest;

  if (!latest.found) {
    return {
      ok:true,
      source_found:false,
      registration_id:id,
      facility_code:String(registry.facility_code || ''),
      facility_name:String(registry.facility_name || ''),
      message:'周術期・30日CRFがまだ保存されていません。手術情報は手入力してください。'
    };
  }

  // Hard consistency check: source CRF must belong to the same registered facility.
  if (
    String(latest.facility_code || '') &&
    String(registry.facility_code || '') &&
    String(latest.facility_code) !== String(registry.facility_code)
  ) {
    return {
      ok:false,
      error:'SOURCE_FACILITY_MISMATCH',
      message:'周術期・30日CRFの施設情報が中央登録台帳と一致しません。事務局へ確認してください。'
    };
  }

  const data = (latest.payload && latest.payload.data) || {};
  const surgeryPerformed = String(data.surgery_performed || '');
  let referenceDate = '';

  if (surgeryPerformed === '実施した') {
    referenceDate = String(data.operation_date || data.reference_date || '');
  } else if (surgeryPerformed === '実施しなかった') {
    referenceDate = String(data.reference_date || '');
  }

  if (!['実施した', '実施しなかった'].includes(surgeryPerformed) || !referenceDate) {
    return {
      ok:false,
      error:'SOURCE_SURGERY_INFO_INCOMPLETE',
      message:'周術期・30日CRFから手術実施有無または基準日を安全に取得できません。事務局へ確認してください。',
      facility_code:String(registry.facility_code || ''),
      facility_name:String(registry.facility_name || '')
    };
  }

  return {
    ok:true,
    source_found:true,
    registration_id:id,
    facility_code:String(registry.facility_code || ''),
    facility_name:String(registry.facility_name || ''),
    surgery_performed:surgeryPerformed,
    reference_date:referenceDate,
    record_version:Number(latest.record_version || 0),
    submission_id:String(latest.submission_id || '')
  };
}


function validateDay90SourceLink_(payload) {
  const data = payload.data || {};
  if (String(payload.crf_type || '') !== 'day90') return {ok:true};
  if (data.source_30d_linked !== true) return {ok:true};

  const id = String(payload.registration_id || '').trim().toUpperCase();
  const latest = getLatestCrfPayload_(CRF_30D_SHEET, id, 'perioperative_30d');
  if (!latest.ok) return latest;
  if (!latest.found) {
    return {ok:false, error:'SOURCE_CRF_MISSING', message:'参照元の周術期・30日CRFが見つかりません。'};
  }

  const expectedVersion = Number(data.source_30d_record_version || 0);
  const expectedSubmissionId = String(data.source_30d_submission_id || '');

  if (
    Number(latest.record_version || 0) !== expectedVersion ||
    String(latest.submission_id || '') !== expectedSubmissionId
  ) {
    return {
      ok:false,
      error:'SOURCE_CRF_UPDATED',
      message:'参照元の周術期・30日CRFが更新されています。90日CRFで「既存情報を取得」をやり直してください。'
    };
  }
  return {ok:true};
}


function draftKey_(registrationId, crfType, visit) {
  return [
    String(registrationId || '').trim().toUpperCase(),
    String(crfType || '').trim(),
    String(visit || '').trim()
  ].join('|');
}

function draftCodePepper_() {
  const props = PropertiesService.getScriptProperties();
  let pepper = props.getProperty('DRAFT_CODE_PEPPER');
  if (!pepper) {
    pepper = Utilities.getUuid() + Utilities.getUuid();
    props.setProperty('DRAFT_CODE_PEPPER', pepper);
  }
  return pepper;
}

function draftCodeHash_(code) {
  const value = String(code || '').trim();
  if (!/^\d{6}$/.test(value)) return '';
  const signature = Utilities.computeHmacSha256Signature(value, draftCodePepper_());
  return Utilities.base64EncodeWebSafe(signature).replace(/=+$/g, '');
}

function generateDraftResumeCode_() {
  const seed = Utilities.getUuid() + '|' + String(new Date().getTime()) + '|' + String(Math.random());
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, seed);
  let n = 0;
  for (let i = 0; i < 4; i++) n = n * 256 + (digest[i] & 0xff);
  return ('000000' + String(n % 1000000)).slice(-6);
}

function normalizeDraftEmail_(value) {
  return String(value || '').trim().toLowerCase();
}

function validDraftEmail_(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizeDraftEmail_(value));
}

function screeningDraftId_(facilityCode, localSubjectCode) {
  const raw = String(facilityCode || '').trim().toUpperCase() + '|' + String(localSubjectCode || '').trim();
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, raw, Utilities.Charset.UTF_8);
  const hex = digest.map(function(b) { const v = (b < 0 ? b + 256 : b); return ('0' + v.toString(16)).slice(-2); }).join('');
  return 'PREMDT-' + hex.slice(0, 24).toUpperCase();
}

function saveScreeningDraft_(p) {
  const facilityCode = String(p.facility_code || '').trim();
  const facilityName = String(p.facility_name || '').trim();
  const localCode = String(p.local_subject_code || '').trim();
  const ownerEmail = normalizeDraftEmail_(p.reporter_email);
  const draftState = p.draft_state;
  if (!facilityCode || !facilityName || !localCode) return {ok:false, error:'MISSING_SCREENING_DRAFT_KEY'};
  if (!validDraftEmail_(ownerEmail)) return {ok:false, error:'INVALID_DRAFT_EMAIL'};
  if (!draftState || typeof draftState !== 'object' || Array.isArray(draftState)) return {ok:false, error:'MISSING_DRAFT_STATE'};
  if (containsDirectIdentifier_(draftState)) return {ok:false, error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};

  const syntheticId = screeningDraftId_(facilityCode, localCode);
  const key = draftKey_(syntheticId, 'screening', 'mdt_application');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    const idx = headerIndex_(values[0]);
    let existingRow = -1;
    let existingOwner = '';
    for (let r = 1; r < values.length; r++) {
      if (String(values[r][idx.draft_key] || '') === key) {
        existingRow = r + 1;
        existingOwner = normalizeDraftEmail_(values[r][idx.reporter_email]);
        break;
      }
    }
    if (existingRow > 0 && existingOwner && ownerEmail !== existingOwner) return {ok:false, error:'DRAFT_EMAIL_MISMATCH'};
    const now = new Date();
    const rowObj = {
      draft_key:key, updated_at:now, registration_id:syntheticId, crf_type:'screening', visit:'mdt_application',
      facility_code:facilityCode, facility_name:facilityName, reporter_email:ownerEmail,
      schema_version:String(p.schema_version || ''), draft_json:JSON.stringify(draftState)
    };
    if (existingRow > 0) setByHeader_(sh, existingRow, idx, rowObj);
    else appendByHeaders_(sh, rowObj);
    SpreadsheetApp.flush();
    return {ok:true, existing:existingRow > 0, updated_at:Utilities.formatDate(now, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"), facility_code:facilityCode, facility_name:facilityName, reporter_email:ownerEmail};
  } finally { lock.releaseLock(); }
}

function getScreeningDraft_(p) {
  const facilityCode = String(p.facility_code || '').trim();
  const localCode = String(p.local_subject_code || '').trim();
  const suppliedEmail = normalizeDraftEmail_(p.reporter_email);
  if (!facilityCode || !localCode) return {ok:false, error:'MISSING_SCREENING_DRAFT_KEY'};
  if (!validDraftEmail_(suppliedEmail)) return {ok:false, error:'INVALID_DRAFT_EMAIL'};
  const syntheticId = screeningDraftId_(facilityCode, localCode);
  const key = draftKey_(syntheticId, 'screening', 'mdt_application');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, source_found:false};
    const idx = headerIndex_(values[0]);
    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') !== key) continue;
      const storedEmail = normalizeDraftEmail_(values[r][idx.reporter_email]);
      if (suppliedEmail !== storedEmail) return {ok:false, error:'DRAFT_EMAIL_MISMATCH'};
      let draftState = {};
      try { draftState = JSON.parse(String(values[r][idx.draft_json] || '{}')); }
      catch (err) { return {ok:false, error:'DRAFT_PARSE_ERROR', message:String(err)}; }
      return {ok:true, source_found:true, updated_at:isoDateTime_(values[r][idx.updated_at]), facility_code:String(values[r][idx.facility_code] || facilityCode), facility_name:String(values[r][idx.facility_name] || ''), reporter_email:storedEmail, schema_version:String(values[r][idx.schema_version] || ''), draft_state:draftState};
    }
    return {ok:true, source_found:false};
  } finally { lock.releaseLock(); }
}

function deleteScreeningDraft_(p) {
  const facilityCode = String(p.facility_code || '').trim();
  const localCode = String(p.local_subject_code || '').trim();
  if (!facilityCode || !localCode) return {ok:false, error:'MISSING_SCREENING_DRAFT_KEY'};
  const syntheticId = screeningDraftId_(facilityCode, localCode);
  const key = draftKey_(syntheticId, 'screening', 'mdt_application');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, deleted:false};
    const idx = headerIndex_(values[0]);
    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') === key) { sh.deleteRow(r + 1); return {ok:true, deleted:true}; }
    }
    return {ok:true, deleted:false};
  } finally { lock.releaseLock(); }
}

function saveDraft_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const crfType = String(p.crf_type || '').trim();
  const visit = String(p.visit || '').trim();
  const draftState = p.draft_state;
  const ownerEmail = normalizeDraftEmail_(p.reporter_email);
  if (!id || !crfType || !visit) return {ok:false, error:'MISSING_DRAFT_KEY'};
  if (!draftState || typeof draftState !== 'object' || Array.isArray(draftState)) {
    return {ok:false, error:'MISSING_DRAFT_STATE'};
  }
  if (containsDirectIdentifier_(draftState)) return {ok:false, error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};
  if (!validDraftEmail_(ownerEmail)) return {ok:false, error:'INVALID_DRAFT_EMAIL'};

  const registry = validateSubject_({registration_id:id, facility_code:String(p.facility_code || '').trim()});
  if (!registry.ok) return registry;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    const idx = headerIndex_(values[0]);
    const key = draftKey_(id, crfType, visit);
    const now = new Date();

    let existingRow = -1;
    let existingOwner = '';
    for (let r = 1; r < values.length; r++) {
      if (String(values[r][idx.draft_key] || '') === key) {
        existingRow = r + 1;
        existingOwner = normalizeDraftEmail_(values[r][idx.reporter_email]);
        break;
      }
    }

    // A saved draft belongs to the e-mail used when it was first saved.
    // It cannot be overwritten with another address from the facility screen.
    if (existingRow > 0 && existingOwner && ownerEmail !== existingOwner) {
      return {ok:false, error:'DRAFT_EMAIL_MISMATCH'};
    }

    const rowObj = {
      draft_key:key,
      updated_at:now,
      registration_id:id,
      crf_type:crfType,
      visit:visit,
      facility_code:String(registry.facility_code || p.facility_code || ''),
      facility_name:String(registry.facility_name || p.facility_name || ''),
      reporter_email:ownerEmail,
      schema_version:String(p.schema_version || ''),
      draft_json:JSON.stringify(draftState)
    };

    if (existingRow > 0) setByHeader_(sh, existingRow, idx, rowObj);
    else appendByHeaders_(sh, rowObj);
    SpreadsheetApp.flush();
    return {
      ok:true,
      existing:existingRow > 0,
      updated_at:Utilities.formatDate(now, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"),
      registration_id:id,
      facility_code:String(registry.facility_code || ''),
      facility_name:String(registry.facility_name || ''),
      reporter_email:ownerEmail
    };
  } finally {
    lock.releaseLock();
  }
}

function getDraft_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const crfType = String(p.crf_type || '').trim();
  const visit = String(p.visit || '').trim();
  const suppliedEmail = normalizeDraftEmail_(p.reporter_email);
  if (!id || !crfType || !visit) return {ok:false, error:'MISSING_DRAFT_KEY'};
  if (!validDraftEmail_(suppliedEmail)) return {ok:false, error:'INVALID_DRAFT_EMAIL'};

  const registry = validateSubject_({registration_id:id, facility_code:''});
  if (!registry.ok) return registry;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, source_found:false, registration_id:id};
    const idx = headerIndex_(values[0]);
    const key = draftKey_(id, crfType, visit);

    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') !== key) continue;
      const storedEmail = normalizeDraftEmail_(values[r][idx.reporter_email]);
      if (!storedEmail) return {ok:false, error:'DRAFT_EMAIL_NOT_SET'};
      if (suppliedEmail !== storedEmail) return {ok:false, error:'DRAFT_EMAIL_MISMATCH'};

      let draftState = {};
      try {
        draftState = JSON.parse(String(values[r][idx.draft_json] || '{}'));
      } catch (err) {
        return {ok:false, error:'DRAFT_PARSE_ERROR', message:String(err)};
      }
      return {
        ok:true,
        source_found:true,
        registration_id:id,
        crf_type:crfType,
        visit:visit,
        updated_at:isoDateTime_(values[r][idx.updated_at]),
        facility_code:String(registry.facility_code || values[r][idx.facility_code] || ''),
        facility_name:String(registry.facility_name || values[r][idx.facility_name] || ''),
        reporter_email:storedEmail,
        schema_version:String(values[r][idx.schema_version] || ''),
        draft_state:draftState
      };
    }
    return {ok:true, source_found:false, registration_id:id};
  } finally {
    lock.releaseLock();
  }
}

function resetDraftCode_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const crfType = String(p.crf_type || '').trim();
  const visit = String(p.visit || '').trim();
  const adminUser = String(p.admin_user || '').trim();
  if (!id || !crfType || !visit) return {ok:false, error:'MISSING_DRAFT_KEY'};
  if (!adminUser) return {ok:false, error:'MISSING_ADMIN_USER'};

  const registry = validateSubject_({registration_id:id, facility_code:''});
  if (!registry.ok) return registry;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, source_found:false, registration_id:id};
    const idx = headerIndex_(values[0]);
    const key = draftKey_(id, crfType, visit);

    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') !== key) continue;
      const row = r + 1;
      const newCode = generateDraftResumeCode_();
      const newHash = draftCodeHash_(newCode);
      if (!newHash) return {ok:false, error:'DRAFT_CODE_GENERATION_FAILED'};
      const now = new Date();
      setByHeader_(sh, row, idx, {
        resume_code_hash:newHash,
        failed_attempts:0,
        locked_until:'',
        code_reset_at:now,
        code_reset_by:adminUser
      });
      SpreadsheetApp.flush();
      return {
        ok:true,
        source_found:true,
        registration_id:id,
        crf_type:crfType,
        visit:visit,
        resume_code:newCode,
        reporter_email:String(values[r][idx.reporter_email] || ''),
        facility_code:String(registry.facility_code || values[r][idx.facility_code] || ''),
        facility_name:String(registry.facility_name || values[r][idx.facility_name] || ''),
        updated_at:isoDateTime_(values[r][idx.updated_at]),
        code_reset_at:Utilities.formatDate(now, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"),
        code_reset_by:adminUser
      };
    }
    return {ok:true, source_found:false, registration_id:id};
  } finally {
    lock.releaseLock();
  }
}


function updateDraftEmail_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const crfType = String(p.crf_type || '').trim();
  const visit = String(p.visit || '').trim();
  const newEmail = normalizeDraftEmail_(p.new_reporter_email);
  const adminUser = String(p.admin_user || '').trim();
  if (!id || !crfType || !visit) return {ok:false, error:'MISSING_DRAFT_KEY'};
  if (!validDraftEmail_(newEmail)) return {ok:false, error:'INVALID_DRAFT_EMAIL'};
  if (!adminUser) return {ok:false, error:'MISSING_ADMIN_USER'};

  const registry = validateSubject_({registration_id:id, facility_code:''});
  if (!registry.ok) return registry;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, source_found:false, registration_id:id};
    const idx = headerIndex_(values[0]);
    const key = draftKey_(id, crfType, visit);
    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') !== key) continue;
      const row = r + 1;
      const oldEmail = normalizeDraftEmail_(values[r][idx.reporter_email]);
      const now = new Date();
      setByHeader_(sh, row, idx, {
        reporter_email:newEmail,
        email_reset_at:now,
        email_reset_by:adminUser
      });
      SpreadsheetApp.flush();
      return {
        ok:true,
        source_found:true,
        registration_id:id,
        old_reporter_email:oldEmail,
        reporter_email:newEmail,
        email_reset_at:Utilities.formatDate(now, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"),
        email_reset_by:adminUser
      };
    }
    return {ok:true, source_found:false, registration_id:id};
  } finally {
    lock.releaseLock();
  }
}

function deleteDraft_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const crfType = String(p.crf_type || '').trim();
  const visit = String(p.visit || '').trim();
  if (!id || !crfType || !visit) return {ok:false, error:'MISSING_DRAFT_KEY'};

  const registry = validateSubject_({registration_id:id, facility_code:''});
  if (!registry.ok) return registry;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok:false, error:'LOCK_TIMEOUT'};
  try {
    const ss = getSpreadsheet_();
    const sh = ensureSheetHeaders_(ss, CRF_DRAFT_SHEET, CRF_DRAFT_HEADERS);
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return {ok:true, deleted:false};
    const idx = headerIndex_(values[0]);
    const key = draftKey_(id, crfType, visit);
    for (let r = values.length - 1; r >= 1; r--) {
      if (String(values[r][idx.draft_key] || '') === key) {
        sh.deleteRow(r + 1);
        SpreadsheetApp.flush();
        return {ok:true, deleted:true};
      }
    }
    return {ok:true, deleted:false};
  } finally {
    lock.releaseLock();
  }
}

function saveCrf_(p) {
  const payload = p.payload;
  if (!payload || typeof payload !== 'object') return {ok: false, error: 'MISSING_PAYLOAD'};
  if (containsDirectIdentifier_(payload)) return {ok:false, error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};
  const crfType = String(payload.crf_type || '');
  const sheetName = crfSheetForType_(crfType);
  if (!sheetName) return {ok: false, error: 'UNSUPPORTED_CRF_TYPE'};

  const validation = validateSubject_({registration_id: payload.registration_id, facility_code: payload.facility_code});
  if (!validation.ok) return validation;

  const sourceCheck = validateDay90SourceLink_(payload);
  if (!sourceCheck.ok) return sourceCheck;

  const hardCheck = validateCrfHardStops_(payload, validation);
  if (!hardCheck.ok) return hardCheck;

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};
  try {
    return savePayloadToSheet_(sheetName, payload, true);
  } finally {
    lock.releaseLock();
  }
}

function savePayloadToSheet_(sheetName, payload, enforceVersionRules) {
  // Only for official CRFs: ensure the record key matches the actual study subject.
  if (enforceVersionRules) {
    const expectedKey = [String(payload.registration_id || ''), String(payload.crf_type || ''), String(payload.visit || '')].join('|');
    if (String(payload.record_key || '') !== expectedKey) return {ok:false, error:'RECORD_KEY_MISMATCH'};
  }
  const ss = getSpreadsheet_();
  const sh = ss.getSheetByName(sheetName);
  const submissionId = String(payload.submission_id || '').trim();
  const recordKey = String(payload.record_key || '').trim();
  const kind = String(payload.submission_kind || (sheetName === SCREENING_CRF_SHEET ? '初回報告' : '')).trim();
  if (!submissionId || !recordKey) return {ok: false, error: 'MISSING_SUBMISSION_METADATA'};

  const values = sh.getDataRange().getValues();
  const headers = values[0] || [];
  const idx = headerIndex_(headers);
  let priorCount = 0;
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (String(row[idx.submission_id] || '') === submissionId) {
      if (enforceVersionRules) {
        const isSameKey = String(row[idx.record_key] || '') === recordKey;
        const isSameSubject = String(row[idx.registration_id] || '') === String(payload.registration_id || '');
        const isSameSite = String(row[idx.facility_code] || '') === String(payload.facility_code || '');
        const isSamePayload = String(row[idx.payload_json] || '') === JSON.stringify(payload);
        if (!isSameKey || !isSameSubject || !isSameSite || !isSamePayload) return {ok:false, error:'SUBMISSION_ID_CONFLICT'};
      }
      return {ok: true, existing: true, record_version: Number(row[idx.record_version] || 1), submission_id: submissionId};
    }
    if (String(row[idx.record_key] || '') === recordKey) priorCount++;
  }

  if (enforceVersionRules) {
    if (kind === '初回報告' && priorCount > 0) return {ok: false, error: 'INITIAL_ALREADY_EXISTS', message: 'この時点の初回報告はすでに保存されています。訂正報告を選択してください。'};
    if (kind === '訂正報告' && priorCount === 0) return {ok: false, error: 'NO_PRIOR_RECORD_FOR_CORRECTION', message: '訂正対象となる既存報告がありません。'};
    if (kind === '訂正報告' && !String(payload.correction_reason || '').trim()) return {ok: false, error: 'MISSING_CORRECTION_REASON'};
  }

  const version = priorCount + 1;
  const flat = flattenObject_(payload);
  const rowObj = {
    saved_at: new Date(), record_version: version,
    submission_id: submissionId, record_key: recordKey, submission_kind: kind,
    correction_reason: String(payload.correction_reason || ''), submitted_at: String(payload.submitted_at || ''),
    registration_id: String(payload.registration_id || ''), facility_code: String(payload.facility_code || ''),
    facility_name: String(payload.facility_name || ''), reporter_email: String(payload.reporter_email || ''),
    crf_type: String(payload.crf_type || ''), visit: String(payload.visit || ''), schema_version: String(payload.schema_version || ''),
    study_code: String(payload.study_code || ''), payload_json: JSON.stringify(payload)
  };
  Object.keys(flat).forEach(k => { if (!Object.prototype.hasOwnProperty.call(rowObj, k)) rowObj[k] = flat[k]; });
  ensureDynamicHeaders_(sh, Object.keys(rowObj));
  appendByHeaders_(sh, rowObj);

  if (sheetName !== SCREENING_CRF_SHEET) {
    appendByHeaders_(ss.getSheetByName(CRF_AUDIT_SHEET), {
      saved_at: new Date(), sheet_name: sheetName, record_key: recordKey, record_version: version,
      submission_id: submissionId, submission_kind: kind, registration_id: String(payload.registration_id || ''), facility_code: String(payload.facility_code || '')
    });
  }
  SpreadsheetApp.flush();
  return {ok: true, existing: false, record_version: version, submission_id: submissionId};
}

function submissionExistsInSheet_(sheetName, submissionId) {
  const sh = getSpreadsheet_().getSheetByName(sheetName);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  if (idx.submission_id === undefined) return false;
  for (let r = 1; r < values.length; r++) if (String(values[r][idx.submission_id] || '') === String(submissionId)) return true;
  return false;
}

function crfSheetForType_(crfType) {
  if (crfType === 'perioperative_30d') return CRF_30D_SHEET;
  if (crfType === 'day90') return CRF_90D_SHEET;
  if (crfType === 'followup') return CRF_FOLLOWUP_SHEET;
  return '';
}

function validateSubject_(p) {
  const id = String(p.registration_id || '').trim().toUpperCase();
  const facilityCode = String(p.facility_code || '').trim();
  if (!/^JUOG-\d{3,4}$/.test(id)) return {ok: false, error: 'INVALID_ID_FORMAT'};
  const sh = getSpreadsheet_().getSheetByName(REGISTRY_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (String(row[idx.registration_id]).toUpperCase() === id) {
      if (String(row[idx.status] || 'ACTIVE') === 'VOID') return {ok: false, error: 'VOID_ID'};
      if (facilityCode && String(row[idx.facility_code]) !== facilityCode) return {ok: false, error: 'FACILITY_MISMATCH', message: 'JUOG登録番号と施設が一致しません'};
      return {ok: true, registration_id: id, facility_code: String(row[idx.facility_code]), facility_name: String(row[idx.facility_name]), registration_date: isoDate_(row[idx.registered_at]), consent_date: String(row[idx.consent_date] || '')};
    }
  }
  return {ok: false, error: 'ID_NOT_FOUND', message: '中央登録台帳に存在しないJUOG登録番号です'};
}

function getBackendInfo_() {
  const ss = getSpreadsheet_();
  const sheetName = String(ss.getName() || '');
  const environment = /(^|[^A-Z])TEST([^A-Z]|$)/i.test(sheetName) || /TEST/i.test(sheetName)
    ? 'TEST'
    : 'PRODUCTION';
  return {
    ok: true,
    backend_version: BACKEND_VERSION,
    environment: environment,
    spreadsheet_name: sheetName,
    server_time: Utilities.formatDate(new Date(), TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX")
  };
}

// Candidate privacy safeguard. Review against approved CRF field dictionary before deployment.
function directIdentifierKey_(key) {
  const normalized = String(key || '').normalize('NFKC').replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2').replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return /(?:^|_)(?:full_patient_name|patient_name|patient_full_name|first_name|last_name|given_name|family_name|patient_surname|mrn|medical_record_number|patient_address|personal_address|patient_phone|birth_date|dob|full_dob|date_of_birth)$/.test(normalized);
}

function parsedNestedJson_(value) {
  if (typeof value !== 'string' || !/^\s*[\[{]/.test(value)) return null;
  try { const parsed = JSON.parse(value); return parsed && typeof parsed === 'object' ? parsed : null; }
  catch (err) { return null; }
}

function containsLabeledIdentifierText_(value) {
  if (typeof value !== 'string') return false;
  const s = value.normalize('NFKC');
  return /(?:生年月日|患者氏名|カルテ番号)\s*(?:は|が|[:=])\s*\S/i.test(s) ||
    /(?:date\s+of\s+birth|\bDOB\b|\bMRN\b|patient\s+name)\s*[:=]\s*\S/i.test(s) ||
    /(?:生年月日|date\s+of\s+birth|\bDOB\b)\s*(?:は|が|[:=])?\s*[0-9]{4}\s*[-/年.]/i.test(s);
}

function containsDirectIdentifier_(value) {
  const parsed = parsedNestedJson_(value);
  if (parsed) return containsDirectIdentifier_(parsed);
  // Labeled free text is prohibited; an unlabeled clinical date cannot safely
  // be classified as a birth date by syntax alone and needs QA/SOP controls.
  if (containsLabeledIdentifierText_(value)) return true;
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some(containsDirectIdentifier_);
  return Object.keys(value).some(key => directIdentifierKey_(key) || containsDirectIdentifier_(value[key]));
}

// Read-time protection for older drafts. This never modifies the stored row.
function stripDirectIdentifiers_(value) {
  const parsed = parsedNestedJson_(value);
  if (parsed) return JSON.stringify(stripDirectIdentifiers_(parsed));
  if (containsLabeledIdentifierText_(value)) return '[REDACTED]';
  if (Array.isArray(value)) return value.map(stripDirectIdentifiers_);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  Object.keys(value).forEach(key => {
    if (!directIdentifierKey_(key)) out[key] = stripDirectIdentifiers_(value[key]);
  });
  return out;
}

function isCn1Only_(cT, cN, cM) {
  return ['cTa', 'cTis', 'cT1', 'cT2', 'cT3'].indexOf(String(cT || '').trim()) >= 0 &&
    String(cN || '').trim() === 'cN1' && String(cM || '').trim() === 'cM0';
}

function countCn1OnlyRegistered_(activeRows, rIdx, screenValues, sIdx) {
  const screeningById = {};
  screenValues.slice(1).forEach(row => {
    const id = String(row[sIdx.screening_id] || '').trim().toUpperCase();
    if (id) screeningById[id] = row;
  });
  return activeRows.filter(row => {
    if (String(row[rIdx.cN]) !== 'cN1') return false;
    const id = String(row[rIdx.screening_id] || '').trim().toUpperCase();
    const screening = screeningById[id];
    if (!screening || !String(screening[sIdx.cT] || '').trim() || !String(screening[sIdx.cM] || '').trim() ||
        String(screening[sIdx.cN] || '').trim() !== String(row[rIdx.cN] || '').trim()) {
      throw new Error('CN1_ONLY_COUNT_UNVERIFIABLE: ' + String(row[rIdx.registration_id] || id));
    }
    return isCn1Only_(screening[sIdx.cT], screening[sIdx.cN], screening[sIdx.cM]);
  }).length;
}

function getStats_() {
  const ss = getSpreadsheet_();
  const regSh = ss.getSheetByName(REGISTRY_SHEET);
  const regValues = regSh.getDataRange().getValues();
  const rIdx = headerIndex_(regValues[0]);
  const activeRows = regValues.slice(1).filter(row => String(row[rIdx.status] || 'ACTIVE') !== 'VOID');

  const screenSh = ss.getSheetByName(SCREENING_SHEET);
  const screenValues = screenSh.getDataRange().getValues();
  const sIdx = headerIndex_(screenValues[0]);
  const screeningCounts = {PENDING: 0, HOLD: 0, INELIGIBLE: 0, REGISTERED: 0};
  screenValues.slice(1).forEach(row => { const status = String(row[sIdx.status] || 'PENDING').toUpperCase(); if (Object.prototype.hasOwnProperty.call(screeningCounts, status)) screeningCounts[status]++; });

  return {ok: true, total: activeRows.length, cN1: countCn1OnlyRegistered_(activeRows, rIdx, screenValues, sIdx), SD: activeRows.filter(row => String(row[rIdx.best_effect]).toUpperCase() === 'SD').length, screenings: screeningCounts};
}

function findScreening_(screeningIdRaw) {
  const screeningId = String(screeningIdRaw || '').trim().toUpperCase();
  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return null;
  const sh = getSpreadsheet_().getSheetByName(SCREENING_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  for (let r = 1; r < values.length; r++) if (String(values[r][idx.screening_id]).toUpperCase() === screeningId) return {sh: sh, values: values, idx: idx, row: values[r], sheetRow: r + 1};
  return null;
}

function latestReview_(screeningId, reviewRound, role) {
  const sh = getSpreadsheet_().getSheetByName(MDT_REVIEW_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  let best = null;
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (String(row[idx.screening_id]).toUpperCase() !== String(screeningId).toUpperCase()) continue;
    if (Number(row[idx.review_round] || 0) !== Number(reviewRound)) continue;
    if (String(row[idx.reviewer_role]) !== role) continue;
    const obj = reviewObject_(row, idx);
    if (!best || Number(obj.review_version) > Number(best.review_version)) best = obj;
  }
  return best;
}

function reviewObject_(row, idx) {
  const keys = MDT_REVIEW_HEADERS;
  const out = {};
  keys.forEach(k => { out[k] = idx[k] === undefined ? '' : row[idx[k]]; });
  out.submitted_at = isoDateTime_(out.submitted_at);
  out.review_round = Number(out.review_round || 0);
  out.review_version = Number(out.review_version || 0);
  out.is_correction = String(out.is_correction).toUpperCase() === 'TRUE';
  Object.keys(out).forEach(k => { if (out[k] instanceof Date) out[k] = isoDateTime_(out[k]); });
  return out;
}

function screeningObject_(row, idx, includeContact) {
  const out = {
    screening_id: String(row[idx.screening_id] || ''), created_at: isoDateTime_(row[idx.created_at]), updated_at: isoDateTime_(row[idx.updated_at]),
    status: String(row[idx.status] || ''), review_round: parseInt(row[idx.review_round] || '1', 10) || 1,
    facility_code: String(row[idx.facility_code] || ''), facility_name: String(row[idx.facility_name] || ''), local_subject_code: String(row[idx.local_subject_code] || ''),
    consent_date: isoDate_(row[idx.consent_date]), ct: String(row[idx.cT] || ''), cn: String(row[idx.cN] || ''), cm: String(row[idx.cM] || ''),
    best_effect: String(row[idx.best_effect] || ''), site_recist: String(row[idx.site_recist] || ''), planned_surgery: String(row[idx.planned_surgery] || ''), planned_surgery_date: isoDate_(row[idx.planned_surgery_date]),
    mdt_date: isoDate_(row[idx.mdt_date]), central_recist: String(row[idx.central_recist] || ''), recist_concordance: String(row[idx.recist_concordance] || ''), mdt_decision: String(row[idx.mdt_decision] || ''), mdt_reason: String(row[idx.mdt_reason] || ''), consensus_note: String(row[idx.consensus_note] || ''),
    registration_id: String(row[idx.registration_id] || ''), registered_at: isoDateTime_(row[idx.registered_at]), admin_user: String(row[idx.admin_user] || '')
  };
  if (includeContact) out.reporter_email = String(row[idx.reporter_email] || '');
  return out;
}

function recistConcordance_(siteRecistRaw, centralRecistRaw) {
  const site = String(siteRecistRaw || '').trim().toUpperCase();
  const central = String(centralRecistRaw || '').trim().toUpperCase();
  if (!site || !central) return 'UNKNOWN';
  return site === central ? 'CONCORDANT' : 'DISCORDANT';
}

function backfillRecistFields_() {
  const ss = getSpreadsheet_();
  const screenSh = ss.getSheetByName(SCREENING_SHEET);
  const regSh = ss.getSheetByName(REGISTRY_SHEET);
  if (!screenSh || !regSh || screenSh.getLastRow() < 2 || regSh.getLastRow() < 2) return;

  const sValues = screenSh.getDataRange().getValues();
  const sIdx = headerIndex_(sValues[0]);
  const byScreening = {};
  for (let r = 1; r < sValues.length; r++) {
    const sid = String(sValues[r][sIdx.screening_id] || '').trim();
    if (!sid) continue;
    const site = String(sValues[r][sIdx.site_recist] || '').toUpperCase();
    const central = String(sValues[r][sIdx.central_recist] || '').toUpperCase();
    const conc = recistConcordance_(site, central);
    byScreening[sid] = {site_recist: site, central_recist: central, recist_concordance: conc};
    if (sIdx.recist_concordance !== undefined && String(sValues[r][sIdx.recist_concordance] || '') !== conc) {
      screenSh.getRange(r + 1, sIdx.recist_concordance + 1).setValue(conc);
    }
  }

  const rValues = regSh.getDataRange().getValues();
  const rIdx = headerIndex_(rValues[0]);
  for (let r = 1; r < rValues.length; r++) {
    const sid = String(rValues[r][rIdx.screening_id] || '').trim();
    const x = byScreening[sid];
    if (!x) continue;
    if (rIdx.site_recist !== undefined && !String(rValues[r][rIdx.site_recist] || '').trim()) regSh.getRange(r + 1, rIdx.site_recist + 1).setValue(x.site_recist);
    if (rIdx.central_recist !== undefined && !String(rValues[r][rIdx.central_recist] || '').trim()) regSh.getRange(r + 1, rIdx.central_recist + 1).setValue(x.central_recist);
    if (rIdx.recist_concordance !== undefined) regSh.getRange(r + 1, rIdx.recist_concordance + 1).setValue(x.recist_concordance);
  }
}

function flattenObject_(obj, prefix, out) {
  prefix = prefix || '';
  out = out || {};
  Object.keys(obj || {}).forEach(key => {
    const value = obj[key];
    const full = prefix ? prefix + '.' + key : key;
    if (value === null || value === undefined) out[full] = '';
    else if (Array.isArray(value)) out[full] = JSON.stringify(value);
    else if (typeof value === 'object' && !(value instanceof Date)) flattenObject_(value, full, out);
    else out[full] = value;
  });
  return out;
}

function ensureDynamicHeaders_(sh, headers) {
  const current = sh.getRange(1, 1, 1, Math.max(sh.getLastColumn(), 1)).getValues()[0].map(String);
  let changed = false;
  headers.forEach(h => { if (current.indexOf(h) < 0) { current.push(h); changed = true; } });
  if (changed) sh.getRange(1, 1, 1, current.length).setValues([current]);
}

function appendByHeaders_(sh, obj) {
  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
  sh.appendRow(headers.map(h => safeCell_(Object.prototype.hasOwnProperty.call(obj, h) ? obj[h] : '')));
}

function safeCell_(value) {
  if (value instanceof Date || typeof value === 'number' || typeof value === 'boolean') return value;
  const s = String(value === null || value === undefined ? '' : value);
  // Prevent formula injection from free-text fields while preserving displayed text.
  if (/^[=+\-@]/.test(s)) return "'" + s;
  return s;
}

function setByHeader_(sh, rowNo, idx, obj) {
  Object.keys(obj).forEach(k => { if (idx[k] !== undefined) sh.getRange(rowNo, idx[k] + 1).setValue(safeCell_(obj[k])); });
}

function ensureSheetHeaders_(ss, sheetName, headers) {
  let sh = ss.getSheetByName(sheetName);
  if (!sh) sh = ss.insertSheet(sheetName);
  if (sh.getLastRow() === 0) {
    sh.appendRow(headers);
  } else {
    const current = sh.getRange(1, 1, 1, Math.max(sh.getLastColumn(), 1)).getValues()[0].map(String);
    let changed = false;
    headers.forEach(h => { if (current.indexOf(h) < 0) { current.push(h); changed = true; } });
    if (changed) sh.getRange(1, 1, 1, current.length).setValues([current]);
  }
  sh.setFrozenRows(1);
  return sh;
}

function ensureSetting_(settings, key, defaultValue) {
  if (settings.getLastRow() < 2) { settings.appendRow([key, defaultValue]); return; }
  const rows = settings.getRange(2, 1, settings.getLastRow() - 1, 2).getValues();
  if (!rows.some(r => String(r[0]) === key)) settings.appendRow([key, defaultValue]);
}

function getSettings_() {
  const sh = getSpreadsheet_().getSheetByName(SETTINGS_SHEET);
  const out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(r => { out[String(r[0])] = String(r[1]); });
  return out;
}

function getSpreadsheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured. Run setupRegistry().');
  return SpreadsheetApp.openById(id);
}

function nextScreeningId_(values, idx) {
  let maxNo = 0;
  values.slice(1).forEach(row => { const m = String(row[idx.screening_id] || '').match(/^JUOG-SCR-(\d+)$/); if (m) maxNo = Math.max(maxNo, parseInt(m[1], 10)); });
  return 'JUOG-SCR-' + String(maxNo + 1).padStart(3, '0');
}

function headerIndex_(headers) {
  const out = {};
  headers.forEach((h, i) => { out[String(h)] = i; });
  return out;
}

function isoDate_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, TIMEZONE, 'yyyy-MM-dd');
  return String(v || '').substring(0, 10);
}

function isoDateTime_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ss");
  return String(v || '');
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
 const routes={"submit_screening":submitScreening_,"save_screening_draft":saveScreeningDraft_,"get_screening_draft":getScreeningDraft_,"delete_screening_draft":deleteScreeningDraft_,"save_draft":saveDraft_,"get_draft":getDraft_,"delete_draft":deleteDraft_,"get_crf_linkage":getCrfLinkage_,"validate":validateSubject_,"list_review_cases":listReviewCases_,"get_screening_crf":getScreeningCrf_,"get_own_review":getOwnReview_,"submit_mdt_review":submitMdtReview_,"list_screenings":listScreenings_,"get_screening":getScreening_,"finalize_mdt":finalizeMdt_,"get_mdt_reviews":getMdtReviews_,"stats":getStats_};
 if(!routes[action])return {ok:false,error:'DOMAIN_ADAPTER_NOT_READY'};
 const result=routes[action](request);
 if(!result.ok)return {ok:false,error:result.error};
 const after=shadow.exportValues();
 return {ok:true,planned_only:true,result,after};
}


// SOURCE: admin_routes.gs
/* Three administrative domain plans. Only copied views change; original rows remain.
 * Deployment, VOID policy and secure code handover require explicit approval. */
function juogAdminPlanV3_(action,p,tables,who,rt) {
 const fail=c=>({ok:false,error:c}),copy=x=>JSON.parse(JSON.stringify(x));
 if(!who||!who.enabled||who.role!=='admin'||!who.id)return fail('ROLE_NOT_ALLOWED');
 const allowed=['registration_id','crf_type','visit','reason','new_reporter_email','approval_ref'];
 if(!p||Object.keys(p).some(k=>!allowed.includes(k)))return fail('UNKNOWN_ADMIN_FIELD');
 if(typeof p.reason!=='string'||!p.reason.trim()||p.reason.length>1000)return fail('REASON_REQUIRED');
 if(rt.privacy(p))return fail('DIRECT_IDENTIFIER_NOT_ALLOWED');
 const after=copy(tables),index=rows=>Object.fromEntries(rows[0].map((h,i)=>[h,i]));
 const reg=after.Registry;if(!reg)return fail('REGISTRY_MISSING');const ri=index(reg);
 const matches=reg.slice(1).filter(r=>r[ri.registration_id]===p.registration_id);
 if(matches.length!==1)return fail('REGISTRY_NOT_UNIQUE');const row=matches[0],facility=row[ri.facility_code];
 if(!facility||!Array.isArray(who.facilities)||!who.facilities.includes(facility))return fail('FACILITY_FORBIDDEN');
 if(row[ri.status]!=='ACTIVE')return fail('REGISTRY_NOT_ACTIVE');
 const result={ok:true,registration_id:p.registration_id,action};
 const event={actor:who.id,action,reason:p.reason,registration_id:p.registration_id,at:rt.now(),changes:[]};
 if(action==='void_registration') {
  if(!rt.voidPolicyApproved||typeof p.approval_ref!=='string'||!p.approval_ref.trim())return fail('VOID_APPROVAL_REQUIRED');
  const screen=after.Screening,si=screen&&index(screen);if(!si)return fail('SCREENING_MISSING');
  const sm=screen.slice(1).filter(r=>r[si.screening_id]===row[ri.screening_id]&&r[si.registration_id]===p.registration_id);
  if(sm.length!==1||sm[0][si.status]!=='REGISTERED')return fail('SCREENING_REGISTRY_CONFLICT');
  row[ri.status]='VOID';sm[0][si.status]='VOID';
  event.changes=[{table:'Registry',field:'status',before:'ACTIVE',after:'VOID'},{table:'Screening',field:'status',before:'REGISTERED',after:'VOID'}];event.approval_ref=p.approval_ref;
  // IDs, all CRFs, MDT reviews and past audits are deliberately retained.
 } else if(['reset_draft_code','update_draft_email'].includes(action)) {
  if(!['perioperative_30d','day90','followup'].includes(p.crf_type)||!p.visit)return fail('DRAFT_KEY_INVALID');
  const drafts=after.CRF_Drafts,di=drafts&&index(drafts);if(!di)return fail('DRAFTS_MISSING');
  const key=[p.registration_id,p.crf_type,p.visit].join('|');const ds=drafts.slice(1).filter(r=>r[di.draft_key]===key);
  if(ds.length!==1)return fail('DRAFT_NOT_UNIQUE');const d=ds[0];if(d[di.facility_code]!==facility)return fail('DRAFT_FACILITY_CONFLICT');
  if(action==='reset_draft_code') {
   // Derived server-side per operation, never accepted from caller or persisted in plaintext.
   const code=rt.resumeCode();if(!/^\d{6}$/.test(code))return fail('CODE_GENERATION_FAILED');
   d[di.resume_code_hash]=rt.codeHash(code);d[di.failed_attempts]=0;d[di.locked_until]='';d[di.code_reset_at]=event.at;d[di.code_reset_by]=who.id;
   event.changes=[{table:'CRF_Drafts',field:'resume_code_hash',before:'REDACTED',after:'ROTATED'}];result.code_rotated=true;
  } else {
   const email=String(p.new_reporter_email||'').trim().toLowerCase();if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return fail('EMAIL_INVALID');
   const old=d[di.reporter_email];d[di.reporter_email]=email;d[di.email_reset_at]=event.at;d[di.email_reset_by]=who.id;
   // Email changes contact data only, never principal or access ACL.
   event.changes=[{table:'CRF_Drafts',field:'reporter_email',before:old,after:email}];
  }
 } else return fail('ACTION_NOT_ALLOWED');
 return {ok:true,result,after,audit_detail:event};
}


// SOURCE: unified_domain_service.gs
/* Unified domain bridge candidate. One durable domain journal for all materialized
 * business views and the CRF transaction state. No legacy live writes/fallback.
 * Only server-verified identities, assignments and settings may enter deps. */
function JuogUnifiedDomainV3(deps) {
 const clone=x=>JSON.parse(JSON.stringify(x));
 const facilityActions=['submit_screening','save_screening_draft','get_screening_draft','delete_screening_draft','save_draft','get_draft','delete_draft','get_crf_linkage','validate','save_crf','read_crf'];
 const reviewerActions=['list_review_cases','get_screening_crf','get_own_review','submit_mdt_review'];
 const adminActions=['list_screenings','get_screening','finalize_mdt','get_mdt_reviews','reset_draft_code','update_draft_email','stats','void_registration'];
 const objects=(t,n)=>{const rows=t[n];if(!rows)return [];return rows.slice(1).map(r=>Object.fromEntries(rows[0].map((k,i)=>[k,r[i]])));};
 const draftKey=p=>p.registration_id?[p.registration_id,p.crf_type,p.visit].join('|'):'PREMDT-'+deps.hash(String(p.facility_code||'').trim().toUpperCase()+'|'+String(p.local_subject_code||'').trim()).slice(0,24).toUpperCase()+'|screening|mdt_application';
 function authorize(u,a,p,t){
  const no=error=>({ok:false,error});if(!u||!u.enabled||!u.id||!Array.isArray(u.facilities))return no('AUTH_REQUIRED');
  if(!p||typeof p!=='object'||Array.isArray(p))return no('PAYLOAD_REQUIRED');
  if(['admin_user','actor_auth','actor_id','reviewer_name'].some(k=>k in p))return no('CALLER_ACTOR_FORBIDDEN');
  const regs=objects(t,'Registry'),screens=objects(t,'Screening');
  if(u.role==='facility'){
   if(!facilityActions.includes(a))return no('ROLE_NOT_ALLOWED');
   if(!p.facility_code||!u.facilities.includes(p.facility_code))return no('FACILITY_FORBIDDEN');
   if(p.registration_id){const found=regs.filter(r=>r.registration_id===p.registration_id);if(found.length!==1||found[0].facility_code!==p.facility_code||found[0].status!=='ACTIVE')return no('SUBJECT_FORBIDDEN');}
   if(a.includes('draft')){const key=draftKey(p),existing=objects(t,'CRF_Drafts').some(r=>r.draft_key===key),owner=(t.V3_DraftOwners||{})[key];if((owner&&owner!==u.id)||(existing&&!owner))return no('DRAFT_OWNER_REQUIRED');}
  } else if(['radiology','medical_oncology','urology'].includes(u.role)) {
   if(!reviewerActions.includes(a)&&a!=='get_mdt_reviews')return no('ROLE_NOT_ALLOWED');
   if(p.reviewer_role&&p.reviewer_role!==u.role)return no('REVIEW_ROLE_MISMATCH');
   if(a!=='list_review_cases'&&!deps.assignments(u).includes(p.screening_id))return no('REVIEW_ASSIGNMENT_REQUIRED');
   if(a!=='list_review_cases'&&!screens.some(s=>s.screening_id===p.screening_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
  } else if(u.role==='admin'){
   if(!adminActions.includes(a))return no('ROLE_NOT_ALLOWED');
   if(p.screening_id&&!screens.some(s=>s.screening_id===p.screening_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
   if(p.registration_id&&!regs.some(s=>s.registration_id===p.registration_id&&u.facilities.includes(s.facility_code)))return no('FACILITY_FORBIDDEN');
  } else return no('ROLE_NOT_ALLOWED');
  return {ok:true};
 }
 function scoped(t,u){const copy=clone(t);for(const n of ['Registry','Screening']){const h=copy[n][0],fi=h.indexOf('facility_code');copy[n]=[h,...copy[n].slice(1).filter(r=>u.facilities.includes(r[fi]))];}return copy;}
 function crfPlan(a,p,t,u){
  const after=clone(t),state=after.V3_CrfState||{intents:[],records:[],audits:[],events:[]};
  // Historical rows require separate reconciliation: never synthesize old intents.
  const legacy=['CRF_30d','CRF_90d','CRF_Followup'].flatMap(n=>objects(t,n));
  const service=new JuogSaveServiceV3({verifyIdentity:()=>({issuer:'verified-server',subject:u.id}),directory:()=>u,
   registry:id=>{const r=objects(t,'Registry').find(x=>x.registration_id===id);return r&&{status:r.status,facility_code:r.facility_code,registration_date:String(r.registered_at).slice(0,10),consent_date:String(r.consent_date).slice(0,10)};},
   hash:deps.hash,privacy:deps.privacy,redact:deps.redact,validate:deps.validate,today:deps.today,now:deps.now,withLock:f=>f(),
   store:{read:()=>clone(state),assertFits:()=>{},appendIntent:i=>state.intents.push(clone(i)),appendRecord:r=>state.records.push(clone(r)),appendAudit:a=>state.audits.push(clone(a)),appendEvent:e=>state.events.push(clone(e))}});
  if(a==='save_crf'&&legacy.some(r=>r.record_key===p.record_key)&&!state.intents.some(i=>i.record.record_key===p.record_key))return {ok:false,error:'LEGACY_RECONCILIATION_REQUIRED'};
  const result=a==='save_crf'?service.save('verified',p):service.read('verified',p.record_key);
  if(!result.ok)return result;
  if(a==='save_crf'||t.V3_CrfState)after.V3_CrfState=state;
  // Materialize only newly created records/audits to the same visible business views.
  for(const record of state.records){
   const payload=record.payload,n={perioperative_30d:'CRF_30d',day90:'CRF_90d',followup:'CRF_Followup'}[payload.crf_type];
   if(!n||!after[n]||!after.CRFSubmissionAudit)return {ok:false,error:'CRF_VIEW_SCHEMA'};
   const values={...payload,saved_at:record.accepted_at,record_version:record.record_version,payload_json:JSON.stringify(payload)};
   const av={...values,sheet_name:n},expectedRow=after[n][0].map(k=>values[k]??''),expectedAudit=after.CRFSubmissionAudit[0].map(k=>av[k]??'');
   const ri=after[n][0].indexOf('submission_id'),ai=after.CRFSubmissionAudit[0].indexOf('submission_id');
   const rows=after[n].slice(1).filter(r=>r[ri]===record.submission_id),audits=after.CRFSubmissionAudit.slice(1).filter(r=>r[ai]===record.submission_id);
   if(rows.length||audits.length){if(rows.length!==1||audits.length!==1||JSON.stringify(rows[0])!==JSON.stringify(expectedRow)||JSON.stringify(audits[0])!==JSON.stringify(expectedAudit))return {ok:false,error:'CRF_PROJECTION_MISMATCH'};}
   else {if((t.V3_CrfState?.records||[]).some(r=>r.submission_id===record.submission_id))return {ok:false,error:'CRF_PROJECTION_MISSING'};after[n].push(expectedRow);after.CRFSubmissionAudit.push(expectedAudit);}
  }
  return {ok:true,after,result,audit_detail:{actor:u.id,action:a,at:deps.now(),registration_id:p.registration_id,reason:p.correction_reason||'',record_key:p.record_key,submission_id:p.submission_id||''}};
 }
 function plan(a,p,t,u,id){
  if(['reset_draft_code','update_draft_email','void_registration'].includes(a))return juogAdminPlanV3_(a,p,t,u,deps.adminRuntime(u,id));
  if(['save_crf','read_crf'].includes(a))return crfPlan(a,p,t,u);
  const q=clone(p);if(['radiology','medical_oncology','urology'].includes(u.role)){q.reviewer_role=u.role;q.reviewer_name=u.id;}if(u.role==='admin')q.admin_user=u.id;
  // Lists/stats run on a scoped copy, but may not replace the complete materialized view.
  const isList=['list_screenings','list_review_cases','stats','get_screening'].includes(a);
  let input=isList?scoped(t,u):t;
  if(a==='list_review_cases'){const h=input.Screening[0],si=h.indexOf('screening_id');input.Screening=[h,...input.Screening.slice(1).filter(r=>deps.assignments(u).includes(r[si]))];}
  const r=deps.legacyPlan(a,q,input);if(!r.ok)return r;
  if(isList)r.after=clone(t);
  if(a==='get_mdt_reviews'&&u.role!=='admin'){
   const v=r.result;r.result={ok:true,screening_id:v.screening_id,review_round:v.review_round,completed:v.completed,required:v.required,all_complete:v.all_complete,reviews:Object.fromEntries(['radiology','medical_oncology','urology'].map(role=>[role,v.reviews&&v.reviews[role]?{submitted:true}:null]))};
  }
  if(a==='save_draft'||a==='save_screening_draft'){r.after.V3_DraftOwners={...(t.V3_DraftOwners||{}),[draftKey(p)]:u.id};}
  // Keep ownership tombstones after view deletion; another user cannot claim a deleted key.
  r.result=deps.redact(r.result);
  r.audit_detail={actor:u.id,action:a,at:deps.now(),reason:p.correction_reason||p.reason||'',screening_id:p.screening_id||r.result.screening_id||'',registration_id:p.registration_id||r.result.registration_id||''};
  return r;
 }
 const service=new JuogDomainServiceV3({...deps,authorize,plan});
 const readActions=['list_review_cases','get_screening_crf','get_own_review','list_screenings','get_screening','get_mdt_reviews','stats','get_screening_draft','get_draft','get_crf_linkage','validate','read_crf'];
 function execute(assertion,operation){
  const op=clone(operation);if(op.payload&&typeof op.payload==='object'){if(typeof op.payload.registration_id==='string')op.payload.registration_id=juogNormalizeRegistrationV3_(op.payload.registration_id);if(typeof op.payload.reporter_email==='string')op.payload.reporter_email=juogPythonStripV3_(op.payload.reporter_email);}
  if(!readActions.includes(op.action))return service.execute(assertion,op);
  try{return deps.withLock(()=>{const u=deps.authenticate(assertion),v=service.readView(),permit=authorize(u,op.action,op.payload,v.tables);if(!permit.ok)return permit;const r=plan(op.action,op.payload,v.tables,u,op.id);if(!r.ok)return r;if(JSON.stringify(r.after)!==JSON.stringify(v.tables))return {ok:false,error:'READ_MUTATION_REJECTED'};return {ok:true,revision:v.revision,result:r.result,read_only:true};});}catch(_){return {ok:false,error:'READ_INCOMPLETE'};}
 }

 return {execute,authorize,readView:service.readView,routeNames:()=>[...facilityActions,...reviewerActions,...adminActions]};
}


// SOURCE: request_lifecycle.gs
/* Durable request preparation precedes all business writes. Owned by verified
 * individual, serialized by the enclosing ScriptLock. No browser payload storage. */
function JuogRequestLifecycleV3(d){
 const copy=x=>JSON.parse(JSON.stringify(x));
 const canonical=x=>JSON.stringify(x);
 function subject(){const u=d.user();if(!u||!u.enabled||!u.id)throw Error('AUTH_REQUIRED');return u;}
 function own(s,id,u){const rs=(s.requests||[]).filter(r=>r.id===id);if(rs.length!==1||rs[0].actor!==u.id)throw Error('REQUEST_NOT_VISIBLE');return rs[0];}
 function check(s,r,u){
  const permit=d.authorize(u,r.operation.action,r.operation.payload,d.service.readView().tables);if(!permit.ok)throw Error('REQUEST_NOT_AUTHORIZED');
  const intents=s.intents.filter(i=>i.id===r.id),commits=s.commits.filter(c=>c.id===r.id),events=(s.requestEvents||[]).filter(e=>e.id===r.id);
  if(intents.length>1||commits.length>1)return {state:'UNKNOWN',phase:'CONFLICT'};
  if(intents.length===1){const i=intents[0];if(i.actor!==r.actor||i.action!==r.operation.action||i.request_hash!==d.hash(canonical({action:r.operation.action,payload:r.operation.payload})))return {state:'UNKNOWN',phase:'IDENTITY_MISMATCH'};
   if(commits.length===1){d.service.readView();const audit=s.audits.filter(a=>a.id===r.id);if(audit.length!==1)return {state:'UNKNOWN',phase:'AUDIT_MISSING'};return {state:'SAVED',phase:'COMMITTED',revision:i.revision};}
   return {state:'UNFINISHED',phase:'AUDIT_OR_COMMIT_PENDING'};
  }
  if(commits.length)return {state:'UNKNOWN',phase:'ORPHAN_COMMIT'};
  const failed=events.filter(e=>e.kind==='FAILED');if(failed.length===1)return {state:'FAILED',phase:'REJECTED_BEFORE_INTENT',error:failed[0].error};if(failed.length>1)return {state:'UNKNOWN',phase:'EVENT_CONFLICT'};
  return {state:'UNFINISHED',phase:'PREPARED'};
 }
 function status(id){try{const u=subject(),s=d.store.read(),r=own(s,id,u);return {ok:true,operation_id:id,action:r.operation.action,created_at:r.created_at,...check(s,r,u)};}catch(_){return {ok:false,state:'UNKNOWN',error:'STATUS_UNVERIFIABLE'};}}
 function list(){try{const u=subject(),s=d.store.read();const out=[];for(const r of (s.requests||[]).filter(r=>r.actor===u.id)){let v;try{v=check(s,r,u);}catch(_){v={state:'UNKNOWN',phase:'UNVERIFIABLE'};}out.push({operation_id:r.id,action:r.operation.action,created_at:r.created_at,...v});}return {ok:true,requests:out};}catch(_){return {ok:false,state:'UNKNOWN',error:'STATUS_UNVERIFIABLE'};}}
 function prepare(operation){try{
  const u=subject(),s=d.store.read(),v=d.service.readView();const op=copy(operation);
  if(!d.writeActions.includes(op.action)||!op.payload||typeof op.payload!=='object'||Array.isArray(op.payload))return {ok:false,error:'ACTION_NOT_PREPARABLE'};
  if(typeof op.payload.registration_id==='string')op.payload.registration_id=juogNormalizeRegistrationV3_(op.payload.registration_id);
  if(typeof op.payload.reporter_email==='string')op.payload.reporter_email=juogPythonStripV3_(op.payload.reporter_email);
  const unsafe=(v,depth=0)=>depth>24||(v&&typeof v==='object'&&Object.entries(v).some(([k,x])=>['password','token','identity_assertion','access_token','refresh_token','signing_key','resume_code'].includes(k.toLowerCase())||unsafe(x,depth+1)));
  if(unsafe(op.payload)||d.privacy(op.payload))return {ok:false,error:'DIRECT_IDENTIFIER_NOT_ALLOWED'};
  if(op.action==='save_crf')op.payload=juogNormalizeRequiredReasonV3_(op.payload);
  const permission=d.authorize(u,op.action,op.payload,v.tables);if(!permission.ok)return permission;
  const semantic=copy(op.payload);for(const p of [semantic,semantic.crf_payload||{}]){delete p.submission_id;delete p.submitted_at;}
  const fingerprint=d.hash(canonical({action:op.action,payload:semantic}));
  for(const r of (s.requests||[]).filter(r=>r.actor===u.id)){
   let state;try{state=check(s,r,u).state;}catch(_){state='UNKNOWN';}
   if(state==='UNKNOWN')return {ok:false,error:'UNKNOWN_REQUEST_BLOCKS_NEW_OPERATION'};
   if(state==='UNFINISHED'){if(r.fingerprint===fingerprint)return {ok:true,operation_id:r.id,existing:true};return {ok:false,error:'UNFINISHED_REQUEST_BLOCKS_NEW_OPERATION'};}
  }
  op.id=d.uuid();op.expected_revision=v.revision;
  const r={id:op.id,actor:u.id,created_at:d.now(),fingerprint,operation:op};
  d.store.assertFits(r);d.store.appendRequest(r);
  const saved=own(d.store.read(),op.id,u);if(canonical(saved)!==canonical(r))throw Error('REQUEST_NOT_DURABLE');
  return {ok:true,operation_id:op.id,existing:false};
 }catch(_){return {ok:false,state:'UNKNOWN',error:'PREPARATION_UNCERTAIN'};}}
 function execute(id){try{
  const u=subject(),s=d.store.read(),r=own(s,id,u),state=check(s,r,u);
  if(state.state==='UNKNOWN')return {ok:false,state:'UNKNOWN',error:'RECONCILIATION_REQUIRED'};
  if(state.state==='FAILED')return {ok:false,...state};
  const result=d.service.execute('server-verified',r.operation);
  if(!result.ok){
   const terminal=['STALE_DOMAIN_REVISION','VALIDATION_FAILED','STALE_VERSION','INITIAL_ALREADY_EXISTS','NO_PRIOR_RECORD','INVALID_RECORD_IDENTITY','CORRECTION_REASON_REQUIRED','DIRECT_IDENTIFIER_NOT_ALLOWED'];
   const after=d.store.read();
   if((result.rejected_before_intent===true||terminal.includes(result.error))&&!after.intents.some(i=>i.id===id)&&!(after.requestEvents||[]).some(e=>e.id===id&&e.kind==='FAILED'))d.store.appendRequestEvent({id,kind:'FAILED',actor:u.id,at:d.now(),error:result.error});
   return {...status(id),...result,ok:false}; // never promote a status-read success to save success
  }
  const verified=status(id);if(verified.state!=='SAVED')return {ok:false,state:'UNKNOWN',error:'AUDIT_NOT_CONFIRMED'};
  return {...result,state:'SAVED',operation_id:id};
 }catch(_){return {ok:false,state:'UNKNOWN',error:'EXECUTION_UNCERTAIN'};}}
 return {prepare,status,list,execute};
}


// SOURCE: unified_isolation_endpoint.gs
/* Unified candidate isolation entry, NOT current doPost. No configuration or sheet creation.
 * Requires auth_bridge.gs, privacy_revision2.gs, domain_transaction.gs,
 * domain_sheets_store.gs, admin_routes.gs. All unified routes require separate integration approval.
 * No legacy fallback, no mail, no network calls, no deployment at load. */
function juogUnifiedIsolationEntryV3_(envelope,c) {
 const forbidden=['1R1a55w19qfS7XTa6Ran7EnuTNZpFkGoXIFfqesv7zoc','1XEKihUvJBHP4BZNf8WMf14__zsiiZgY8ozFnhw_NZNE','1XaLdVGN39skmXVhiyPN-uOb9B8zjo3rmbNgYZCndJRs'];
 if(!c||c.environment!=='ISOLATED_TEST'||!c.approvalRef||c.backupVerified!==true||c.qaApproved!==true||c.fictionalBaselineVerified!==true||c.notificationsDisabled!==true||!c.spreadsheetId||c.spreadsheetId!==c.approvedSpreadsheetId||forbidden.includes(c.spreadsheetId))return {ok:false,error:'ISOLATION_NOT_APPROVED'};
 const lock=LockService.getScriptLock();if(!lock.tryLock(30000))return {ok:false,error:'LOCK_TIMEOUT'};
 try {
  const auth=juogV3DecodeBridge_(envelope,c),req=auth.request;
  if(c.allRoutesReviewed!==true||c.schemaParityApproved!==true)return {ok:false,error:'INTEGRATION_NOT_APPROVED'};
  const control=['prepare_request','request_status','list_requests','execute_request'];
  let op=req.payload;if(!op||(!control.includes(req.action)&&op.action!==req.action))return {ok:false,error:'ACTION_MISMATCH'};
  const ss=SpreadsheetApp.openById(c.spreadsheetId),who=juogV3ReadIndividualAcl_(ss,auth.principal.issuer,auth.principal.subject);
  if(!who || who.enabled!==true || typeof who.id!=='string' || !who.id.trim() || !Array.isArray(who.facilities))return {ok:false,error:'AUTH_REQUIRED'};
  const hash=s=>Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('');
  const store=juogDomainSheetsStoreV3_(ss,hash,()=>Utilities.getUuid());
  if(req.action==='execute_request'){
   const found=store.read().requests.filter(r=>r.id===req.payload.operation_id&&who&&r.actor===who.id);
   if(found.length!==1)return {ok:false,state:'UNKNOWN',error:'REQUEST_NOT_VISIBLE'};
   op=found[0].operation;
  }
  const mac=s=>Utilities.computeHmacSha256Signature(s,c.resumeDerivationKey,Utilities.Charset.UTF_8);
  if(typeof c.resumeDerivationKey!=='string'||c.resumeDerivationKey.length<32||typeof c.draftPepper!=='string'||c.draftPepper.length<32)throw Error('KEY_NOT_CONFIGURED');
  const code=()=>{const bytes=mac('resume-v3|'+who.id+'|'+op.id);let n=0;for(let i=0;i<6;i++)n=n*256+(bytes[i]&255);return String(n%1000000).padStart(6,'0');};
  const codeHash=s=>Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(s,c.draftPepper,Utilities.Charset.UTF_8)).replace(/=+$/g,'');
  const assignmentSheet=ss.getSheetByName('V3_Assignments');
  const assignments=u=>{if(!assignmentSheet)return [];const rows=assignmentSheet.getDataRange().getValues(),ix=Object.fromEntries(rows[0].map((k,i)=>[k,i]));if(['user_id','role','screening_id','enabled'].some(k=>ix[k]===undefined))throw Error('ASSIGNMENT_SCHEMA');return rows.slice(1).filter(r=>r[ix.user_id]===u.id&&r[ix.role]===u.role&&(r[ix.enabled]===true||r[ix.enabled]==='TRUE')).map(r=>r[ix.screening_id]);};
  let BusinessDate=Date;
  if(c.businessTestNow){
   if(!c.timeControlApprovalRef||!Number.isFinite(new Date(c.businessTestNow).getTime()))throw Error('TIME_CONTROL_NOT_APPROVED');
   const fixed=new Date(c.businessTestNow).getTime();BusinessDate=class extends Date{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}};
  }
  const service=new JuogUnifiedDomainV3({store,hash,now:()=>new Date().toISOString(),today:()=>Utilities.formatDate(new BusinessDate(),'Asia/Tokyo','yyyy-MM-dd'),withLock:f=>f(),privacy:containsDirectIdentifier_,redact:stripDirectIdentifiers_,validate:validateClinicalV3,authenticate:()=>who,assignments,
   legacyPlan:(a,p,t)=>juogLegacyPlanV3_(a,p,t,{Date:BusinessDate,utilities:Utilities,draftPepper:c.draftPepper}),
   adminRuntime:(u,id)=>({now:()=>new Date().toISOString(),privacy:containsDirectIdentifier_,resumeCode:code,codeHash,voidPolicyApproved:c.voidPolicyApproved===true})});

  if(req.action==='ui_context'){
   if(!who||!who.enabled)return {ok:false,error:'AUTH_REQUIRED'};
   const v=service.readView();let facility=null;
   if(op.payload&&op.payload.registration_id){const h=v.tables.Registry[0],ix=Object.fromEntries(h.map((k,i)=>[k,i]));const matches=v.tables.Registry.slice(1).filter(r=>r[ix.registration_id]===op.payload.registration_id&&who.facilities.includes(r[ix.facility_code]));if(matches.length!==1)return {ok:false,error:'SUBJECT_FORBIDDEN'};facility=matches[0][ix.facility_code];}
   return {ok:true,backend_version:'v3-unified-review',environment:'TEST',isolation:true,role:who.role,user_id:who.id,facilities:who.facilities,facility_code:facility,revision:v.revision,pending:store.read().intents.length!==store.read().commits.length};
  }
  const writes=['submit_screening','submit_mdt_review','finalize_mdt','save_screening_draft','delete_screening_draft','save_draft','delete_draft','reset_draft_code','update_draft_email','void_registration','save_crf'];
  const lifecycle=new JuogRequestLifecycleV3({user:()=>who,store,service,authorize:service.authorize,privacy:containsDirectIdentifier_,hash,uuid:()=>Utilities.getUuid(),now:()=>new Date().toISOString(),writeActions:writes});
  if(req.action==='prepare_request')return lifecycle.prepare(req.payload);
  if(req.action==='request_status')return lifecycle.status(req.payload.operation_id);
  if(req.action==='list_requests')return lifecycle.list();
  if(writes.includes(req.action))return {ok:false,error:'DURABLE_PREPARATION_REQUIRED'};
  const response=req.action==='execute_request'?lifecycle.execute(req.payload.operation_id):service.execute(envelope.identity_assertion,op);

  if(response.ok&&op.action==='reset_draft_code'){
   // Reveal only to the same currently-authorized actor after durable commit, and
   // only while this operation's code remains current. Do not log this response.
   const tables=service.readView().tables,d=tables.CRF_Drafts,di=Object.fromEntries(d[0].map((h,i)=>[h,i]));
   const key=[op.payload.registration_id,op.payload.crf_type,op.payload.visit].join('|'),rows=d.slice(1).filter(r=>r[di.draft_key]===key);
   if(rows.length===1&&rows[0][di.resume_code_hash]===codeHash(code()))response.resume_code=code();
   else response.code_delivery='SUPERSEDED';
  }
  return response;
 }catch(e){const safe=['AUTH_REQUIRED','AUTH_INVALID','AUTH_EXPIRED','REQUEST_SIGNATURE_MISMATCH'];return {ok:false,error:safe.includes(e.message)?e.message:'UNIFIED_TRANSACTION_INCOMPLETE'};}finally{lock.releaseLock();}
}



// SOURCE: isolation_unified_webapp.gs
/* Dedicated isolation project ONLY. Never add this doPost alongside legacy doPost.
 * All config is loaded server-side; request cannot supply gates or keys.
 * Properties are provisioned by administrator only after approval. */
function doPost(e){
 try{
  const props=PropertiesService.getScriptProperties(),raw=props.getProperty('UNIFIED_ISOLATION_CONFIG');
  if(!raw)return ContentService.createTextOutput(JSON.stringify({ok:false,error:'ISOLATION_NOT_APPROVED'})).setMimeType(ContentService.MimeType.JSON);
  const c=JSON.parse(raw);
  c.signingKey=props.getProperty('ADMIN_BRIDGE_SIGNING_KEY');
  c.resumeDerivationKey=props.getProperty('ADMIN_RESUME_DERIVATION_KEY');
  c.draftPepper=props.getProperty('ADMIN_DRAFT_PEPPER');
  const result=juogUnifiedIsolationEntryV3_(JSON.parse(e.postData.contents),c);
  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
 }catch(_){return ContentService.createTextOutput(JSON.stringify({ok:false,error:'REQUEST_REJECTED'})).setMimeType(ContentService.MimeType.JSON);}
}
