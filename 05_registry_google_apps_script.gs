/**
 * JUOG UTUC_Consolidative central eCRF service (v2.2.2)
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
const SETTINGS_SHEET = 'Settings';
const TIMEZONE = 'Asia/Tokyo';

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

function setupRegistry() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Run setupRegistry from a script bound to the registry spreadsheet.');

  const props = PropertiesService.getScriptProperties();
  props.setProperty('SPREADSHEET_ID', ss.getId());
  if (!props.getProperty('JUOG_API_TOKEN')) {
    props.setProperty('JUOG_API_TOKEN', Utilities.getUuid() + Utilities.getUuid());
  }

  ensureSheetHeaders_(ss, REGISTRY_SHEET, REGISTRY_HEADERS);
  const screening = ensureSheetHeaders_(ss, SCREENING_SHEET, SCREENING_HEADERS);
  ensureSheetHeaders_(ss, SCREENING_AUDIT_SHEET, SCREENING_AUDIT_HEADERS);
  ensureSheetHeaders_(ss, MDT_REVIEW_SHEET, MDT_REVIEW_HEADERS);
  ensureSheetHeaders_(ss, SCREENING_CRF_SHEET, CRF_BASE_HEADERS);
  ensureSheetHeaders_(ss, CRF_30D_SHEET, CRF_BASE_HEADERS);
  ensureSheetHeaders_(ss, CRF_90D_SHEET, CRF_BASE_HEADERS);
  ensureSheetHeaders_(ss, CRF_FOLLOWUP_SHEET, CRF_BASE_HEADERS);
  ensureSheetHeaders_(ss, CRF_AUDIT_SHEET, CRF_AUDIT_HEADERS);

  // Migrate existing v2.1 screening rows to review round 1.
  const values = screening.getDataRange().getValues();
  if (values.length > 1) {
    const idx = headerIndex_(values[0]);
    for (let r = 1; r < values.length; r++) {
      if (String(values[r][idx.screening_id] || '').trim() && !String(values[r][idx.review_round] || '').trim()) {
        screening.getRange(r + 1, idx.review_round + 1).setValue(1);
      }
    }
  }

  let settings = ss.getSheetByName(SETTINGS_SHEET);
  if (!settings) settings = ss.insertSheet(SETTINGS_SHEET);
  if (settings.getLastRow() === 0) {
    settings.appendRow(['key', 'value']);
    settings.setFrozenRows(1);
  }
  ensureSetting_(settings, 'TOTAL_MAX', '42');
  ensureSetting_(settings, 'ALLOW_TOTAL_AFTER_MAX', 'FALSE');
  ensureSetting_(settings, 'CN1_MAX', '20');
  ensureSetting_(settings, 'SD_HOLD_THRESHOLD', '12');
  ensureSetting_(settings, 'ALLOW_SD_AFTER_THRESHOLD', 'FALSE');
  ensureSetting_(settings, 'ALLOW_LEGACY_DIRECT_REGISTER', 'FALSE');

  // v2.2.1: backfill site/central RECIST concordance for already registered cases when possible.
  backfillRecistFields_();

  SpreadsheetApp.flush();
  Logger.log('SPREADSHEET_ID=' + ss.getId());
  Logger.log('JUOG_API_TOKEN=' + props.getProperty('JUOG_API_TOKEN'));
}

function rotateApiToken() {
  const token = Utilities.getUuid() + Utilities.getUuid();
  PropertiesService.getScriptProperties().setProperty('JUOG_API_TOKEN', token);
  Logger.log('JUOG_API_TOKEN=' + token);
}

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const props = PropertiesService.getScriptProperties();
    if (!body.token || body.token !== props.getProperty('JUOG_API_TOKEN')) {
      return jsonResponse_({ok: false, error: 'UNAUTHORIZED'});
    }
    const action = String(body.action || '');
    const payload = body.payload || {};

    if (action === 'submit_screening') return jsonResponse_(submitScreening_(payload));
    if (action === 'list_screenings') return jsonResponse_(listScreenings_(payload));
    if (action === 'list_review_cases') return jsonResponse_(listReviewCases_(payload));
    if (action === 'get_screening') return jsonResponse_(getScreening_(payload));
    if (action === 'get_screening_crf') return jsonResponse_(getScreeningCrf_(payload));
    if (action === 'get_own_review') return jsonResponse_(getOwnReview_(payload));
    if (action === 'submit_mdt_review') return jsonResponse_(submitMdtReview_(payload));
    if (action === 'get_mdt_reviews') return jsonResponse_(getMdtReviews_(payload));
    if (action === 'finalize_mdt') return jsonResponse_(finalizeMdt_(payload));
    if (action === 'save_crf') return jsonResponse_(saveCrf_(payload));
    if (action === 'validate') return jsonResponse_(validateSubject_(payload));
    if (action === 'stats') return jsonResponse_(getStats_());
    if (action === 'register') return jsonResponse_(legacyRegister_(payload));

    return jsonResponse_({ok: false, error: 'UNKNOWN_ACTION'});
  } catch (err) {
    return jsonResponse_({ok: false, error: 'SERVER_ERROR', message: String(err)});
  }
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
    const cn1Count = activeRows.filter(row => String(row[rIdx.cN]) === 'cN1').length;
    const sdCount = activeRows.filter(row => String(row[rIdx.best_effect]).toUpperCase() === 'SD').length;
    const settings = getSettings_();
    const totalMax = parseInt(settings.TOTAL_MAX || '42', 10);
    const allowTotalAfterMax = String(settings.ALLOW_TOTAL_AFTER_MAX || 'FALSE').toUpperCase() === 'TRUE';
    const cn1Max = parseInt(settings.CN1_MAX || '20', 10);
    const sdThreshold = parseInt(settings.SD_HOLD_THRESHOLD || '12', 10);
    const allowSdAfter = String(settings.ALLOW_SD_AFTER_THRESHOLD || 'FALSE').toUpperCase() === 'TRUE';
    const bestEffect = String(found.row[found.idx.best_effect] || '').toUpperCase();

    if (activeRows.length >= totalMax && !allowTotalAfterMax) return {ok: false, error: 'TOTAL_CAP_REACHED', message: `目標登録数 ${totalMax} 例に到達しています`};
    if (String(found.row[found.idx.cN]) === 'cN1' && cn1Count >= cn1Max) return {ok: false, error: 'CN1_CAP_REACHED', message: `cN1登録上限 ${cn1Max} 例に到達しています`};
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
    return {ok: true, existing: false, screening_id: screeningId, status: 'REGISTERED', registration_id: registrationId, registration_date: Utilities.formatDate(now, TIMEZONE, 'yyyy-MM-dd'), site_recist: siteRecist, central_recist: centralRecist, recist_concordance: recistConcordance, counts_after: {total: activeRows.length + 1, cN1: cn1Count + (String(found.row[found.idx.cN]) === 'cN1' ? 1 : 0), SD: sdCount + (bestEffect === 'SD' ? 1 : 0)}};
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

function saveCrf_(p) {
  const payload = p.payload;
  if (!payload || typeof payload !== 'object') return {ok: false, error: 'MISSING_PAYLOAD'};
  const crfType = String(payload.crf_type || '');
  const sheetName = crfSheetForType_(crfType);
  if (!sheetName) return {ok: false, error: 'UNSUPPORTED_CRF_TYPE'};

  const validation = validateSubject_({registration_id: payload.registration_id, facility_code: payload.facility_code});
  if (!validation.ok) return validation;
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

function legacyRegister_(p) {
  const settings = getSettings_();
  if (String(settings.ALLOW_LEGACY_DIRECT_REGISTER || 'FALSE').toUpperCase() !== 'TRUE') return {ok: false, error: 'LEGACY_REGISTER_DISABLED', message: '施設側からの直接正式登録は禁止されています。'};
  return {ok: false, error: 'LEGACY_REGISTER_NOT_IMPLEMENTED'};
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

  return {ok: true, total: activeRows.length, cN1: activeRows.filter(row => String(row[rIdx.cN]) === 'cN1').length, SD: activeRows.filter(row => String(row[rIdx.best_effect]).toUpperCase() === 'SD').length, screenings: screeningCounts};
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
