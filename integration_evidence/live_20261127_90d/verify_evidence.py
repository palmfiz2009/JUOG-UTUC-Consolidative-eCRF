"""Read-only verification of captured fictional isolated Sheet evidence."""
import json, hashlib
from pathlib import Path
P=Path(__file__).parent
def rows(name): return json.loads((P/name).read_text())['values']
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
events=rows('draft_rows.json')[1:]
ids=set(); latest={}
for raw,h in events:
    assert digest(raw)==h
    e=json.loads(raw);assert e['operation_id'] not in ids;ids.add(e['operation_id'])
    if e['key']=='JUOG-901|day90|90d':
        assert e['actor']=='UAT_TEST01_PI_01' and e['record_version']==0
        assert e['revision']==latest.get(e['section'],{}).get('revision',0)+1
        latest[e['section']]=e
assert set(latest)==set('123456')
assert latest['2']['data']['d90_cystoscopy_result']['value']=='腫瘍なし'
assert latest['6']['data']['d90_last_alive_date']['value']=='2026-04-10'
uid='e68de6b2-f6de-45a5-b117-24a04ce6bfd6'
for prefix in ['after_initial','after_retry']:
    assert len(rows(prefix+'_CRF_90d.json'))==1
    audit=rows(prefix+'_CRFSubmissionAudit.json')
    assert len(audit)==3 and [r[3] for r in audit[1:]]==[1,2]
    ops=[]
    for seq,raw,h in rows(prefix+'_R1_Operations.json')[1:]:
        assert seq==len(ops)+1 and digest(raw)==h;ops.append(json.loads(raw))
    pending=[e for e in ops if e['uuid']==uid]
    assert len(pending)==1 and pending[0]['kind']=='INTENT'
    assert digest(json.dumps(pending[0]['payload'],ensure_ascii=False,separators=(',',':')))==pending[0]['digest']
    assert pending[0]['key']=='JUOG-901|day90|90d' and pending[0]['expected']==0
print('Captured evidence verified: six draft sections; 90d INTENT only, no CRF/audit/COMMIT; prior 30d audit V1/V2 unchanged. NOT formal UAT PASS.')
