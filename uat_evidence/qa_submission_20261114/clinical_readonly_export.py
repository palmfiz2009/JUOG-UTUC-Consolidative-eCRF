"""Offline review export of the approved fictional snapshot. No network or writes to EDC.

This is not a deployed app route or a clinical endpoint adjudicator.
Only latest versions enter summary; all versions remain in the history export.
"""
import csv
import hashlib
import io
import json
from datetime import date
from pathlib import Path

SOURCE_JOURNAL = '1414934e5e059e3cc7882486fa7cf5ee14afe99b4ab5dce9736a3c665d0b0797'
TABLES = {'CRF_30d','CRF_90d','CRF_Followup'}
FIELDS = ('table','version','latest','reference_date','visit_date','event_date','event_day','grade','window','recurrence_date','progression_date','death_date','blood_loss_ml','pathology_size_mm','crp')

def build(snapshot):
    if snapshot.get('journal_sha256') != SOURCE_JOURNAL:
        raise ValueError('UNVERIFIED_SNAPSHOT')
    records = snapshot['records']
    seen=set(); latest={}
    for row in records:
        table=row['table'];version=row['version']
        if table not in TABLES or type(version) is not int or version < 1:
            raise ValueError('INVALID_RECORD')
        key=(table,version)
        if key in seen:
            raise ValueError('DUPLICATE_VERSION')
        seen.add(key);latest[table]=max(latest.get(table,0),version)
    for table,version in latest.items():
        if {v for t,v in seen if t==table} != set(range(1,version+1)):
            raise ValueError('MISSING_HISTORY')
    history=[]
    for row in sorted(records,key=lambda r:(r['table'],r['version'])):
        d=row['data'];table=row['table'];ref=d.get('reference_date','')
        event=d.get('cd_event_date_30' if table=='CRF_30d' else 'cd_event_date','')
        day=(date.fromisoformat(event)-date.fromisoformat(ref)).days if event and ref else ''
        # Window classification only; no endpoint eligibility/renal exception inference.
        window=('day0_30' if 0<=day<=30 else 'day31_90' if 31<=day<=90 else 'outside') if day!='' else 'no_event_date'
        item=dict(table=table,version=row['version'],latest=row['version']==latest[table],reference_date=ref,
            visit_date=d.get('day30_visit_date',d.get('visit_date','')),event_date=event,event_day=day,
            grade=d.get('cd_grade_30',d.get('cd_grade_day31_90','')),window=window,
            recurrence_date=d.get('intraluminal_recurrence_date',''),progression_date=d.get('progression_date',''),death_date=d.get('death_date',''),
            blood_loss_ml=d.get('blood_loss_ml',''),pathology_size_mm=d.get('pathology',{}).get('size_mm',''),crp=d.get('day30_labs',d.get('labs',{})).get('CRP',''))
        history.append(item)
    current=[r for r in history if r['latest']]
    summary={'record_count_history':len(history),'record_count_latest':len(current),
             'latest_events_day0_30':sum(r['window']=='day0_30' for r in current),
             'latest_events_day31_90':sum(r['window']=='day31_90' for r in current),
             'latest_followup_with_recurrence':sum(r['table']=='CRF_Followup' and bool(r['recurrence_date']) for r in current),
             'latest_followup_with_progression':sum(r['table']=='CRF_Followup' and bool(r['progression_date']) for r in current),
             'latest_followup_with_death':sum(r['table']=='CRF_Followup' and bool(r['death_date']) for r in current)}
    return history,current,summary

def csv_text(rows):
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader()
    for row in rows:
        # Defend spreadsheet interpretation without emitting arbitrary free text.
        safe={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()}
        w.writerow(safe)
    return out.getvalue()

if __name__=='__main__':
    p=Path(__file__).parent;source=p/'clinical_projection.json';before=source.read_bytes()
    history,current,summary=build(json.loads(before))
    (p/'clinical_history_review.csv').write_text(csv_text(history),encoding='utf-8')
    (p/'clinical_latest_review.csv').write_text(csv_text(current),encoding='utf-8')
    summary.update(scope='OFFLINE_REVIEW_EXPORT_NOT_DEPLOYED_APPLICATION',clinical_endpoint_adjudication=False,formal_pass_delta=0,projection_sha256=hashlib.sha256(before).hexdigest())
    (p/'clinical_review_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    assert source.read_bytes()==before
    print('Review export: 6 history rows, 3 latest rows; source unchanged')
