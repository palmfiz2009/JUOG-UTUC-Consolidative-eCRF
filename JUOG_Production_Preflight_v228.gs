/**
 * JUOG-UTUC01 v2.2.8 – READ-ONLY production deployment preflight.
 *
 * Usage:
 *   1. Add this as a separate .gs file to the PRODUCTION Apps Script project.
 *   2. In Script Properties configure JUOG_EXPECTED_PRODUCTION_SHEET_ID to the
 *      ID of the separately verified real production registry spreadsheet.
 *   3. Run juogProductionPreflight_v228 from Apps Script editor.
 *   4. Never paste credentials, patient details, or raw Script Properties in logs.
 *
 * This function does NOT change Google Sheets, create clinical study records,
 * send email, perform authorization bypasses, or deploy any version.
 */
function juogProductionPreflight_v228() {
  const props = PropertiesService.getScriptProperties();
  const errors = [];
  const info = [];

  const expectedBackendVersion = 'v2.2.8';
  if (typeof BACKEND_VERSION === 'undefined' || BACKEND_VERSION !== expectedBackendVersion) {
    errors.push('BACKEND_VERSION_MISMATCH');
  } else {
    info.push('BACKEND_VERSION=' + BACKEND_VERSION);
  }

  const configuredId = String(props.getProperty('SPREADSHEET_ID') || '').trim();
  const expectedId = String(props.getProperty('JUOG_EXPECTED_PRODUCTION_SHEET_ID') || '').trim();
  if (!configuredId) errors.push('SPREADSHEET_ID_MISSING');
  if (!expectedId) errors.push('EXPECTED_PRODUCTION_SHEET_ID_MISSING');
  if (configuredId && expectedId && configuredId !== expectedId) {
    errors.push('PRODUCTION_SHEET_ID_MISMATCH');
  }

  const tokenProperties = [
    'JUOG_API_TOKEN',
    'JUOG_ADMIN_ACTION_TOKEN',
    'JUOG_REVIEWER_RADIOLOGY_ACTION_TOKEN',
    'JUOG_REVIEWER_MEDICAL_ONCOLOGY_ACTION_TOKEN',
    'JUOG_REVIEWER_UROLOGY_ACTION_TOKEN',
    'DRAFT_CODE_PEPPER'
  ];
  const tokenValues = {};
  tokenProperties.forEach(function(key) {
    const secret = String(props.getProperty(key) || '').trim();
    if (!secret) errors.push('MISSING_' + key);
    tokenValues[key] = secret;
  });
  const allSecrets = tokenProperties.map(function(key) { return tokenValues[key]; }).filter(Boolean);
  if ((new Set(allSecrets)).size !== allSecrets.length) errors.push('REUSED_SERVER_SECRET');

  let ss = null;
  if (configuredId && expectedId && configuredId === expectedId) {
    try {
      ss = SpreadsheetApp.openById(configuredId);
      const name = String(ss.getName() || '');
      if (name !== 'JUOG_UTUC_Registry') errors.push('UNEXPECTED_PRODUCTION_SHEET_NAME');
      if (/TEST|UAT|STAGING|DO_NOT_USE/i.test(name)) errors.push('TEST_SHEET_SELECTED');
      info.push('sheet_name=' + name);
      const required = [
        'Screening', 'ScreeningCRF', 'ScreeningAudit', 'MDTReviews',
        'Registry', 'CRF_30d', 'CRF_90d', 'CRF_Followup',
        'CRFSubmissionAudit', 'CRF_Drafts', 'Settings'
      ];
      required.forEach(function(name) {
        const sh = ss.getSheetByName(name);
        if (!sh) { errors.push('MISSING_SHEET_' + name); return; }
        if (sh.getLastRow() < 1) { errors.push('MISSING_HEADER_' + name); return; }
        const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getDisplayValues()[0];
        if (!headers || !headers.some(Boolean)) errors.push('EMPTY_HEADER_' + name);
      });
      const registry = ss.getSheetByName('Registry');
      const screening = ss.getSheetByName('Screening');
      if (registry && screening) {
        info.push('registry_rows=' + Math.max(0, registry.getLastRow() - 1));
        info.push('screening_rows=' + Math.max(0, screening.getLastRow() - 1));
      }
    } catch (e) {
      errors.push('PRODUCTION_SHEET_READ_FAILED');
    }
  }

  // Only test the authorization predicate; do NOT dispatch any clinical API action.
  if (typeof authorizeJuogAction_ !== 'function') {
    errors.push('ROLE_AUTH_IMPLEMENTATION_MISSING');
  } else {
    const missing = authorizeJuogAction_('finalize_mdt', null, {}, props);
    if (missing.ok || missing.error !== 'ROLE_AUTH_REQUIRED') errors.push('ADMIN_ROLE_GUARD_FAILED');
    const good = tokenValues['JUOG_ADMIN_ACTION_TOKEN'];
    if (good) {
      const valid = authorizeJuogAction_('finalize_mdt', {kind:'admin', key:good}, {}, props);
      if (!valid.ok) errors.push('ADMIN_ROLE_SECRET_MISMATCH');
    }
    const invalid = authorizeJuogAction_('finalize_mdt', {kind:'reviewer',role:'urology',key:'invalid'}, {}, props);
    if (invalid.ok) errors.push('REVIEWER_PRIVILEGE_ESCALATION');
  }

  const verdict = errors.length ? 'NOT_READY' : 'PASS_READ_ONLY';
  Logger.log('JUOG_PRODUCTION_PREFLIGHT ' + verdict);
  info.forEach(function(line) { Logger.log('INFO ' + line); });
  errors.forEach(function(err) { Logger.log('BLOCKER ' + err); });
  Logger.log('LIMITATION: SMTP delivery, Streamlit Secrets/URL, real HTTP role isolation, formal UAT and institutional approval NOT tested.');
  return {status:verdict, errors:errors, info:info};
}
