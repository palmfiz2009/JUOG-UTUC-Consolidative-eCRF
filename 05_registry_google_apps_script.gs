/**
 * JUOG UTUC_Consolidative central screening / registration service (v2)
 * Google Apps Script Web App bound to a dedicated Google Sheet.
 *
 * Workflow enforced by the service:
 *   Facility screening CRF -> Screening ID (JUOG-SCR-001...)
 *   -> Central MDT decision by study office
 *   -> only ELIGIBLE cases receive JUOG-001, JUOG-002... registration IDs.
 *
 * The registry stores only the minimum data needed for workflow and enrollment control.
 * Do NOT put patient name, medical record number, full date of birth, or image data here.
 */

const REGISTRY_SHEET = 'Registry';
const SCREENING_SHEET = 'Screening';
const AUDIT_SHEET = 'ScreeningAudit';
const SETTINGS_SHEET = 'Settings';
const TIMEZONE = 'Asia/Tokyo';

const REGISTRY_HEADERS = [
  'registered_at', 'registration_id', 'status',
  'facility_code', 'facility_name', 'local_subject_code',
  'reporter_email', 'consent_date', 'mdt_date', 'cN', 'best_effect',
  'screening_id', 'central_recist'
];

const SCREENING_HEADERS = [
  'screening_id', 'created_at', 'updated_at', 'status',
  'facility_code', 'facility_name', 'local_subject_code', 'reporter_email',
  'submission_id', 'consent_date', 'cT', 'cN', 'cM', 'best_effect', 'site_recist',
  'planned_surgery', 'planned_surgery_date',
  'mdt_date', 'central_recist', 'mdt_decision', 'mdt_reason',
  'registration_id', 'registered_at', 'admin_user'
];

const AUDIT_HEADERS = [
  'timestamp', 'screening_id', 'action', 'status_after',
  'facility_code', 'local_subject_code', 'submission_id',
  'mdt_date', 'central_recist', 'mdt_decision', 'mdt_reason',
  'registration_id', 'admin_user'
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
  ensureSheetHeaders_(ss, SCREENING_SHEET, SCREENING_HEADERS);
  ensureSheetHeaders_(ss, AUDIT_SHEET, AUDIT_HEADERS);

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
  // Fail-safe: old v1 apps must not be able to bypass central MDT.
  ensureSetting_(settings, 'ALLOW_LEGACY_DIRECT_REGISTER', 'FALSE');

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
    if (action === 'get_screening') return jsonResponse_(getScreening_(payload));
    if (action === 'finalize_mdt') return jsonResponse_(finalizeMdt_(payload));
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

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};

  try {
    const ss = getSpreadsheet_();
    const screenSh = ss.getSheetByName(SCREENING_SHEET);
    const regSh = ss.getSheetByName(REGISTRY_SHEET);
    const auditSh = ss.getSheetByName(AUDIT_SHEET);

    const regValues = regSh.getDataRange().getValues();
    const regIdx = headerIndex_(regValues[0]);
    for (let r = 1; r < regValues.length; r++) {
      const row = regValues[r];
      if (String(row[regIdx.facility_code]) === String(p.facility_code) &&
          String(row[regIdx.local_subject_code]) === String(p.local_subject_code) &&
          String(row[regIdx.status] || 'ACTIVE') !== 'VOID') {
        return {
          ok: false,
          error: 'ALREADY_REGISTERED',
          message: 'この施設内研究対象者識別コードはすでに正式登録されています',
          registration_id: String(row[regIdx.registration_id])
        };
      }
    }

    const values = screenSh.getDataRange().getValues();
    const idx = headerIndex_(values[0]);

    // Submission-id idempotency.
    for (let r = 1; r < values.length; r++) {
      const row = values[r];
      if (String(row[idx.submission_id]) === String(p.submission_id)) {
        return {
          ok: true,
          existing: true,
          screening_id: String(row[idx.screening_id]),
          status: String(row[idx.status]),
          registration_id: String(row[idx.registration_id] || '')
        };
      }
    }

    // Re-submission after PENDING/HOLD uses the same screening ID and returns to PENDING.
    let existingRow = -1;
    for (let r = 1; r < values.length; r++) {
      const row = values[r];
      if (String(row[idx.facility_code]) === String(p.facility_code) &&
          String(row[idx.local_subject_code]) === String(p.local_subject_code)) {
        existingRow = r + 1; // Sheet row number
        const status = String(row[idx.status] || 'PENDING');
        if (status === 'REGISTERED') {
          return {ok: false, error: 'ALREADY_REGISTERED', registration_id: String(row[idx.registration_id] || '')};
        }
        if (status === 'INELIGIBLE') {
          return {
            ok: false,
            error: 'SCREENING_CLOSED',
            message: '中央MDTで不適格確定済みです。再審査が必要な場合は研究事務局へ連絡してください。',
            screening_id: String(row[idx.screening_id])
          };
        }
        break;
      }
    }

    const now = new Date();
    let screeningId;
    if (existingRow > 0) {
      screeningId = String(screenSh.getRange(existingRow, idx.screening_id + 1).getValue());
      setByHeader_(screenSh, existingRow, idx, {
        updated_at: now,
        status: 'PENDING',
        facility_name: String(p.facility_name),
        reporter_email: String(p.reporter_email),
        submission_id: String(p.submission_id),
        consent_date: String(p.consent_date),
        cT: String(p.ct), cN: String(p.cn), cM: String(p.cm),
        best_effect: String(p.best_effect), site_recist: String(p.site_recist),
        planned_surgery: String(p.planned_surgery || ''),
        planned_surgery_date: String(p.planned_surgery_date || ''),
        mdt_date: '', central_recist: '', mdt_decision: '', mdt_reason: '',
        registration_id: '', registered_at: '', admin_user: ''
      });
    } else {
      screeningId = nextScreeningId_(values, idx);
      appendByHeaders_(screenSh, SCREENING_HEADERS, {
        screening_id: screeningId,
        created_at: now,
        updated_at: now,
        status: 'PENDING',
        facility_code: String(p.facility_code),
        facility_name: String(p.facility_name),
        local_subject_code: String(p.local_subject_code),
        reporter_email: String(p.reporter_email),
        submission_id: String(p.submission_id),
        consent_date: String(p.consent_date),
        cT: String(p.ct), cN: String(p.cn), cM: String(p.cm),
        best_effect: String(p.best_effect), site_recist: String(p.site_recist),
        planned_surgery: String(p.planned_surgery || ''),
        planned_surgery_date: String(p.planned_surgery_date || '')
      });
    }

    appendAudit_(auditSh, {
      timestamp: now,
      screening_id: screeningId,
      action: existingRow > 0 ? 'SCREENING_RESUBMIT' : 'SCREENING_SUBMIT',
      status_after: 'PENDING',
      facility_code: String(p.facility_code),
      local_subject_code: String(p.local_subject_code),
      submission_id: String(p.submission_id)
    });
    SpreadsheetApp.flush();

    return {ok: true, existing: existingRow > 0, screening_id: screeningId, status: 'PENDING'};
  } finally {
    lock.releaseLock();
  }
}

function listScreenings_(p) {
  const statusesRaw = String(p.statuses || 'PENDING,HOLD');
  const statuses = statusesRaw.split(',').map(x => x.trim().toUpperCase()).filter(Boolean);
  const sh = getSpreadsheet_().getSheetByName(SCREENING_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  const rows = [];

  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    const status = String(row[idx.status] || 'PENDING').toUpperCase();
    if (statuses.length && statuses.indexOf(status) < 0) continue;
    rows.push(screeningObject_(row, idx, false));
  }
  rows.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
  return {ok: true, screenings: rows, count: rows.length, stats: getStats_()};
}

function getScreening_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return {ok: false, error: 'INVALID_SCREENING_ID'};
  const sh = getSpreadsheet_().getSheetByName(SCREENING_SHEET);
  const values = sh.getDataRange().getValues();
  const idx = headerIndex_(values[0]);
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (String(row[idx.screening_id]).toUpperCase() === screeningId) {
      return {ok: true, screening: screeningObject_(row, idx, true), stats: getStats_()};
    }
  }
  return {ok: false, error: 'SCREENING_NOT_FOUND'};
}

function finalizeMdt_(p) {
  const screeningId = String(p.screening_id || '').trim().toUpperCase();
  const decision = String(p.decision || '').trim().toUpperCase();
  const mdtDate = String(p.mdt_date || '').trim();
  const centralRecist = String(p.central_recist || '').trim().toUpperCase();
  const reason = String(p.reason || '').trim();
  const adminUser = String(p.admin_user || '').trim();

  if (!/^JUOG-SCR-\d{3,4}$/.test(screeningId)) return {ok: false, error: 'INVALID_SCREENING_ID'};
  if (['ELIGIBLE', 'INELIGIBLE', 'HOLD'].indexOf(decision) < 0) return {ok: false, error: 'INVALID_DECISION'};
  if (!mdtDate) return {ok: false, error: 'MISSING_MDT_DATE'};
  if (['CR', 'PR', 'SD', 'PD', 'NE'].indexOf(centralRecist) < 0) return {ok: false, error: 'INVALID_CENTRAL_RECIST'};
  if (!adminUser) return {ok: false, error: 'MISSING_ADMIN_USER'};
  if ((decision === 'INELIGIBLE' || decision === 'HOLD') && !reason) {
    return {ok: false, error: 'MISSING_REASON', message: '不適格・保留では理由が必須です'};
  }
  if (decision === 'ELIGIBLE' && ['CR', 'PR', 'SD'].indexOf(centralRecist) < 0) {
    return {ok: false, error: 'RECIST_NOT_ELIGIBLE', message: '正式登録には中央RECISTがCR/PR/SDである必要があります'};
  }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return {ok: false, error: 'LOCK_TIMEOUT'};

  try {
    const ss = getSpreadsheet_();
    const screenSh = ss.getSheetByName(SCREENING_SHEET);
    const auditSh = ss.getSheetByName(AUDIT_SHEET);
    const regSh = ss.getSheetByName(REGISTRY_SHEET);
    const screenValues = screenSh.getDataRange().getValues();
    const sIdx = headerIndex_(screenValues[0]);

    let sheetRow = -1;
    let row = null;
    for (let r = 1; r < screenValues.length; r++) {
      if (String(screenValues[r][sIdx.screening_id]).toUpperCase() === screeningId) {
        sheetRow = r + 1;
        row = screenValues[r];
        break;
      }
    }
    if (sheetRow < 0) return {ok: false, error: 'SCREENING_NOT_FOUND'};

    const currentStatus = String(row[sIdx.status] || 'PENDING').toUpperCase();
    if (currentStatus === 'REGISTERED') {
      return {
        ok: true,
        existing: true,
        screening_id: screeningId,
        status: 'REGISTERED',
        registration_id: String(row[sIdx.registration_id] || ''),
        registration_date: isoDate_(row[sIdx.registered_at])
      };
    }
    if (currentStatus === 'INELIGIBLE') {
      return {ok: false, error: 'SCREENING_CLOSED', message: '不適格確定済みです'};
    }

    const now = new Date();
    if (decision === 'HOLD' || decision === 'INELIGIBLE') {
      const newStatus = decision === 'HOLD' ? 'HOLD' : 'INELIGIBLE';
      setByHeader_(screenSh, sheetRow, sIdx, {
        updated_at: now,
        status: newStatus,
        mdt_date: mdtDate,
        central_recist: centralRecist,
        mdt_decision: decision,
        mdt_reason: reason,
        admin_user: adminUser
      });
      appendAudit_(auditSh, {
        timestamp: now,
        screening_id: screeningId,
        action: 'MDT_' + decision,
        status_after: newStatus,
        facility_code: String(row[sIdx.facility_code]),
        local_subject_code: String(row[sIdx.local_subject_code]),
        submission_id: String(row[sIdx.submission_id]),
        mdt_date: mdtDate,
        central_recist: centralRecist,
        mdt_decision: decision,
        mdt_reason: reason,
        admin_user: adminUser
      });
      SpreadsheetApp.flush();
      return {ok: true, screening_id: screeningId, status: newStatus, decision: decision};
    }

    // ELIGIBLE -> formal registration. Recheck all enrollment controls atomically here.
    const bestEffect = String(row[sIdx.best_effect] || '').toUpperCase();
    if (['CR', 'PR', 'SD'].indexOf(bestEffect) < 0) {
      return {ok: false, error: 'BEST_EFFECT_NOT_ELIGIBLE', message: 'EVP最良総合効果がCR/PR/SDではありません'};
    }

    const regValues = regSh.getDataRange().getValues();
    const rIdx = headerIndex_(regValues[0]);

    // Duplicate subject safeguard.
    for (let r = 1; r < regValues.length; r++) {
      const regRow = regValues[r];
      if (String(regRow[rIdx.facility_code]) === String(row[sIdx.facility_code]) &&
          String(regRow[rIdx.local_subject_code]) === String(row[sIdx.local_subject_code]) &&
          String(regRow[rIdx.status] || 'ACTIVE') !== 'VOID') {
        const existingId = String(regRow[rIdx.registration_id]);
        setByHeader_(screenSh, sheetRow, sIdx, {
          updated_at: now,
          status: 'REGISTERED',
          mdt_date: mdtDate,
          central_recist: centralRecist,
          mdt_decision: 'ELIGIBLE',
          mdt_reason: '',
          registration_id: existingId,
          registered_at: regRow[rIdx.registered_at],
          admin_user: adminUser
        });
        return {ok: true, existing: true, screening_id: screeningId, status: 'REGISTERED', registration_id: existingId, registration_date: isoDate_(regRow[rIdx.registered_at])};
      }
    }

    const activeRows = regValues.slice(1).filter(regRow => String(regRow[rIdx.status] || 'ACTIVE') !== 'VOID');
    const cn1Count = activeRows.filter(regRow => String(regRow[rIdx.cN]) === 'cN1').length;
    const sdCount = activeRows.filter(regRow => String(regRow[rIdx.best_effect]).toUpperCase() === 'SD').length;
    const settings = getSettings_();
    const totalMax = parseInt(settings.TOTAL_MAX || '42', 10);
    const allowTotalAfterMax = String(settings.ALLOW_TOTAL_AFTER_MAX || 'FALSE').toUpperCase() === 'TRUE';
    const cn1Max = parseInt(settings.CN1_MAX || '20', 10);
    const sdThreshold = parseInt(settings.SD_HOLD_THRESHOLD || '12', 10);
    const allowSdAfter = String(settings.ALLOW_SD_AFTER_THRESHOLD || 'FALSE').toUpperCase() === 'TRUE';

    if (activeRows.length >= totalMax && !allowTotalAfterMax) {
      return {ok: false, error: 'TOTAL_CAP_REACHED', message: `目標登録数 ${totalMax} 例に到達しています`};
    }
    if (String(row[sIdx.cN]) === 'cN1' && cn1Count >= cn1Max) {
      return {ok: false, error: 'CN1_CAP_REACHED', message: `cN1登録上限 ${cn1Max} 例に到達しています`};
    }
    if (bestEffect === 'SD' && sdCount >= sdThreshold && !allowSdAfter) {
      return {
        ok: false,
        error: 'SD_CAP_HOLD',
        message: `SD症例が ${sdThreshold} 例に到達しているため、研究計画書に従い新規SD登録は一時保留です。研究事務局・統計解析責任者等で協議後、Settings の ALLOW_SD_AFTER_THRESHOLD を TRUE にした場合のみ再開できます。`
      };
    }

    let maxNo = 0;
    regValues.slice(1).forEach(regRow => {
      const m = String(regRow[rIdx.registration_id] || '').match(/^JUOG-(\d+)$/);
      if (m) maxNo = Math.max(maxNo, parseInt(m[1], 10));
    });
    const registrationId = 'JUOG-' + String(maxNo + 1).padStart(3, '0');

    appendByHeaders_(regSh, REGISTRY_HEADERS, {
      registered_at: now,
      registration_id: registrationId,
      status: 'ACTIVE',
      facility_code: String(row[sIdx.facility_code]),
      facility_name: String(row[sIdx.facility_name]),
      local_subject_code: String(row[sIdx.local_subject_code]),
      reporter_email: String(row[sIdx.reporter_email]),
      consent_date: String(row[sIdx.consent_date]),
      mdt_date: mdtDate,
      cN: String(row[sIdx.cN]),
      best_effect: bestEffect,
      screening_id: screeningId,
      central_recist: centralRecist
    });

    setByHeader_(screenSh, sheetRow, sIdx, {
      updated_at: now,
      status: 'REGISTERED',
      mdt_date: mdtDate,
      central_recist: centralRecist,
      mdt_decision: 'ELIGIBLE',
      mdt_reason: '',
      registration_id: registrationId,
      registered_at: now,
      admin_user: adminUser
    });

    appendAudit_(auditSh, {
      timestamp: now,
      screening_id: screeningId,
      action: 'MDT_ELIGIBLE_REGISTER',
      status_after: 'REGISTERED',
      facility_code: String(row[sIdx.facility_code]),
      local_subject_code: String(row[sIdx.local_subject_code]),
      submission_id: String(row[sIdx.submission_id]),
      mdt_date: mdtDate,
      central_recist: centralRecist,
      mdt_decision: 'ELIGIBLE',
      mdt_reason: '',
      registration_id: registrationId,
      admin_user: adminUser
    });
    SpreadsheetApp.flush();

    return {
      ok: true,
      existing: false,
      screening_id: screeningId,
      status: 'REGISTERED',
      registration_id: registrationId,
      registration_date: Utilities.formatDate(now, TIMEZONE, 'yyyy-MM-dd'),
      counts_after: {
        total: activeRows.length + 1,
        cN1: cn1Count + (String(row[sIdx.cN]) === 'cN1' ? 1 : 0),
        SD: sdCount + (bestEffect === 'SD' ? 1 : 0)
      }
    };
  } finally {
    lock.releaseLock();
  }
}

function legacyRegister_(p) {
  const settings = getSettings_();
  const allowed = String(settings.ALLOW_LEGACY_DIRECT_REGISTER || 'FALSE').toUpperCase() === 'TRUE';
  if (!allowed) {
    return {
      ok: false,
      error: 'LEGACY_REGISTER_DISABLED',
      message: 'v2では施設側からの直接正式登録は禁止されています。中央MDT管理画面から正式登録してください。'
    };
  }
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
      if (facilityCode && String(row[idx.facility_code]) !== facilityCode) {
        return {ok: false, error: 'FACILITY_MISMATCH', message: 'JUOG登録番号と施設が一致しません'};
      }
      return {
        ok: true,
        registration_id: id,
        facility_code: String(row[idx.facility_code]),
        facility_name: String(row[idx.facility_name]),
        registration_date: isoDate_(row[idx.registered_at])
      };
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
  screenValues.slice(1).forEach(row => {
    const status = String(row[sIdx.status] || 'PENDING').toUpperCase();
    if (Object.prototype.hasOwnProperty.call(screeningCounts, status)) screeningCounts[status]++;
  });

  return {
    ok: true,
    total: activeRows.length,
    cN1: activeRows.filter(row => String(row[rIdx.cN]) === 'cN1').length,
    SD: activeRows.filter(row => String(row[rIdx.best_effect]).toUpperCase() === 'SD').length,
    screenings: screeningCounts
  };
}

function getSpreadsheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured. Run setupRegistry().');
  return SpreadsheetApp.openById(id);
}

function ensureSheetHeaders_(ss, sheetName, headers) {
  let sh = ss.getSheetByName(sheetName);
  if (!sh) sh = ss.insertSheet(sheetName);
  if (sh.getLastRow() === 0) {
    sh.appendRow(headers);
    sh.setFrozenRows(1);
    return sh;
  }
  const lastCol = Math.max(sh.getLastColumn(), 1);
  const current = sh.getRange(1, 1, 1, lastCol).getValues()[0].map(String);
  let changed = false;
  headers.forEach(h => {
    if (current.indexOf(h) < 0) {
      current.push(h);
      changed = true;
    }
  });
  if (changed) sh.getRange(1, 1, 1, current.length).setValues([current]);
  sh.setFrozenRows(1);
  return sh;
}

function ensureSetting_(settings, key, defaultValue) {
  if (settings.getLastRow() < 2) {
    settings.appendRow([key, defaultValue]);
    return;
  }
  const rows = settings.getRange(2, 1, settings.getLastRow() - 1, 2).getValues();
  if (!rows.some(r => String(r[0]) === key)) settings.appendRow([key, defaultValue]);
}

function getSettings_() {
  const sh = getSpreadsheet_().getSheetByName(SETTINGS_SHEET);
  const out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  const rows = sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues();
  rows.forEach(r => out[String(r[0])] = String(r[1]));
  return out;
}

function nextScreeningId_(values, idx) {
  let maxNo = 0;
  values.slice(1).forEach(row => {
    const m = String(row[idx.screening_id] || '').match(/^JUOG-SCR-(\d+)$/);
    if (m) maxNo = Math.max(maxNo, parseInt(m[1], 10));
  });
  return 'JUOG-SCR-' + String(maxNo + 1).padStart(3, '0');
}

function appendByHeaders_(sh, headers, obj) {
  // Use actual sheet header order, allowing migration from v1 sheets with appended headers.
  const actualHeaders = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
  sh.appendRow(actualHeaders.map(h => Object.prototype.hasOwnProperty.call(obj, h) ? obj[h] : ''));
}

function setByHeader_(sh, rowNo, idx, obj) {
  Object.keys(obj).forEach(k => {
    if (idx[k] !== undefined) sh.getRange(rowNo, idx[k] + 1).setValue(obj[k]);
  });
}

function appendAudit_(sh, obj) {
  appendByHeaders_(sh, AUDIT_HEADERS, obj);
}

function screeningObject_(row, idx, includeContact) {
  const out = {
    screening_id: String(row[idx.screening_id] || ''),
    created_at: isoDateTime_(row[idx.created_at]),
    updated_at: isoDateTime_(row[idx.updated_at]),
    status: String(row[idx.status] || ''),
    facility_code: String(row[idx.facility_code] || ''),
    facility_name: String(row[idx.facility_name] || ''),
    local_subject_code: String(row[idx.local_subject_code] || ''),
    consent_date: isoDate_(row[idx.consent_date]),
    ct: String(row[idx.cT] || ''),
    cn: String(row[idx.cN] || ''),
    cm: String(row[idx.cM] || ''),
    best_effect: String(row[idx.best_effect] || ''),
    site_recist: String(row[idx.site_recist] || ''),
    planned_surgery: String(row[idx.planned_surgery] || ''),
    planned_surgery_date: isoDate_(row[idx.planned_surgery_date]),
    mdt_date: isoDate_(row[idx.mdt_date]),
    central_recist: String(row[idx.central_recist] || ''),
    mdt_decision: String(row[idx.mdt_decision] || ''),
    mdt_reason: String(row[idx.mdt_reason] || ''),
    registration_id: String(row[idx.registration_id] || ''),
    registered_at: isoDateTime_(row[idx.registered_at]),
    admin_user: String(row[idx.admin_user] || '')
  };
  if (includeContact) out.reporter_email = String(row[idx.reporter_email] || '');
  return out;
}

function headerIndex_(headers) {
  const out = {};
  headers.forEach((h, i) => out[String(h)] = i);
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
