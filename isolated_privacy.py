"""Fixture privacy functions preserved for integration rejection (not silent scrub)."""
def is_direct_identifier_key(key: str) -> bool:
    import re, unicodedata
    s = unicodedata.normalize('NFKC', str(key))
    if re.search(r'(?:^|[^一-龯ぁ-んァ-ヶ])(?:患者氏名|患者姓名|カルテ番号|診療録番号|生年月日)$', s):
        return True
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    s = re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
    return bool(re.search(r'(?:^|_)(?:birth_date|dob|full_dob|date_of_birth|patient_name|patient_full_name|full_patient_name|first_name|last_name|given_name|family_name|patient_surname|mrn|medical_record_number|patient_address|personal_address|patient_phone)$', s))


def redact_draft_identifiers(value):
    import re, json, unicodedata
    if isinstance(value, str):
        if value.lstrip().startswith(('{', '[')):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list)):
                    return json.dumps(redact_draft_identifiers(parsed), ensure_ascii=False)
            except (ValueError, TypeError):
                pass
        s = unicodedata.normalize('NFKC', value)
        patterns = [r'(?:生年月日|患者氏名|カルテ番号)\s*(?:は|が|[:=])\s*\S', r'(?:date\s+of\s+birth|\bDOB\b|\bMRN\b|patient\s+name)\s*[:=]\s*\S', r'(?:生年月日|date\s+of\s+birth|\bDOB\b)\s*(?:は|が|[:=])?\s*[0-9]{4}\s*[-/年.]']
        return '[REDACTED]' if any(re.search(p, s, re.I) for p in patterns) else value
    if isinstance(value, list):
        return [redact_draft_identifiers(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_draft_identifiers(v) for k, v in value.items() if not is_direct_identifier_key(k)}
    return value


