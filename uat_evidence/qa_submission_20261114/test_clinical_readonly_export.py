import copy,csv,io,json,unittest
from pathlib import Path
from clinical_readonly_export import build,csv_text
P=Path(__file__).parent
class ExportTests(unittest.TestCase):
    def setUp(self):self.s=json.loads((P/'clinical_projection.json').read_text())
    def test_latest_does_not_double_count_corrections(self):
        h,c,s=build(self.s)
        self.assertEqual((len(h),len(c)),(6,3))
        self.assertEqual([s[k] for k in ('latest_events_day0_30','latest_events_day31_90','latest_followup_with_recurrence','latest_followup_with_progression','latest_followup_with_death')],[1]*5)
    def test_export_roundtrip_zero_and_dates(self):
        _,c,_=build(self.s);rows=list(csv.DictReader(io.StringIO(csv_text(c))))
        a=next(r for r in rows if r['table']=='CRF_30d')
        self.assertEqual([a[k] for k in ('blood_loss_ml','pathology_size_mm','crp')],['0']*3)
        self.assertEqual((a['event_day'],a['event_date']),('30','2026-05-13'))
        self.assertEqual(next(r for r in rows if r['table']=='CRF_90d')['event_day'],'31')
    def test_input_is_immutable(self):
        old=copy.deepcopy(self.s);build(self.s);self.assertEqual(old,self.s)
    def test_duplicate_version_rejected(self):
        self.s['records'].append(copy.deepcopy(self.s['records'][0]))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_VERSION'):build(self.s)
    def test_missing_old_version_rejected(self):
        self.s['records']=self.s['records'][1:]
        with self.assertRaisesRegex(ValueError,'MISSING_HISTORY'):build(self.s)
    def test_unverified_snapshot_rejected(self):
        self.s['journal_sha256']='bad'
        with self.assertRaisesRegex(ValueError,'UNVERIFIED_SNAPSHOT'):build(self.s)
    def test_free_text_and_identity_fields_excluded(self):
        for r in self.s['records']:r['data'].update(patient_name='SYNTHETIC-PRIVACY-MARKER',note='SYNTHETIC-PRIVACY-MARKER',reporter_email='SYNTHETIC-PRIVACY-MARKER')
        h,_,_=build(self.s);self.assertNotIn('SYNTHETIC-PRIVACY-MARKER',csv_text(h))
    def test_csv_formula_neutralized(self):
        self.assertIn("'=1+1",csv_text([{'table':'=1+1'}]))
if __name__=='__main__':unittest.main()
