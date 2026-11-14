"""Compare locally downloaded native XLSX journal with previously fixed API digest.
Input is private scratch JSON extracted from XLSX; only sanitized results are saved.
"""
import json,hashlib
from pathlib import Path
P=Path(__file__).parent
rows=json.loads(Path('/tmp/juog_private_normalized_rows.json').read_text())
sha=lambda v:hashlib.sha256(v.encode()).hexdigest()
digest=sha(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
assert digest=='1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797'
groups={}
for row in rows[1:]:groups.setdefault(row[0],[]).append(row)
objects=[];sealed=0
for group in groups.values():
    chunks=sorted([r for r in group if r[2]!='SEALED'],key=lambda r:r[2])
    seals=[r for r in group if r[2]=='SEALED']
    if not chunks:raise AssertionError('ORPHAN_SEAL')
    assert [r[2] for r in chunks]==list(range(chunks[0][3]))
    raw=''.join(r[5] for r in chunks)
    assert sha(raw)==chunks[0][4]
    if seals:
        assert len(seals)==1 and seals[0][4]==chunks[0][4]
        sealed+=1
    objects.append((group[0][1],json.loads(raw)))
intents=[v for k,v in objects if k=='intents']
latest=max(intents,key=lambda v:v['revision'])
projection=json.loads((P.parent/'qa_submission_20261114/clinical_projection.json').read_text())
observed=[]
for table in ['CRF_30d','CRF_90d','CRF_Followup']:
    grid=latest['after'][table];header=grid[0]
    for raw in grid[1:]:
        r=dict(zip(header,raw))
        if r['registration_id']=='JUOG-971':
            payload=json.loads(r['payload_json'])
            observed.append({'table':table,'version':int(r['record_version']),'data':payload['data']})
assert observed==projection['records']
result={'mode':'LIVE_GOOGLE_SHEETS_NATIVE_XLSX_VS_LIVE_SHEETS_API','journal_rows':len(rows),'journal_sha256':digest,'api_digest_equal':True,'previous_165_rows_unchanged':True,'sealed_batches_verified':sealed,'legacy_unsealed_batches_preserved':len(groups)-sealed,'business_revision':latest['revision'],'all_six_971_clinical_payloads_equal':True,'numeric_conversion':'XLSX shared strings 0.0/1.0 etc in chunk part/total normalized to exact integer metadata; all other cells unchanged. Raw cell types differ, semantic content agrees.','POST01':'day30 Grade IIIa/date/relation and complete payload available in actual native export; candidate for QA','POST02':'day31 stored in 90d, excluded from 30d window; primary endpoint interpretation remains QA/medical review','FUP01':'6m history confirmed; 9/12/15/18/21/24m live records not supplied by existing fixture','formal_pass_delta':0,'xlsx_sha256':hashlib.sha256(Path('/tmp/juog_private_export_20261114.xlsx').read_bytes()).hexdigest(),'raw_export_published':False}
(P/'native_export_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
