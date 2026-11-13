import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from durable_observer import Journal, Observer, provision

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'evidence.db'
        provision(self.path);self.j=Journal(self.path)
        self.s=dict(phase='WAITING',started=1000,deadline=4600,duration=3600,
                    token_identity='DO_NOT_STORE',before_sid='DO_NOT_STORE',pending_envelope={'identity_assertion':'DO_NOT_STORE'},reason='DO_NOT_STORE')
        self.o=Observer(self.j,self.s,'a'*64,Mock(),clock=lambda:1000)
    def tearDown(self): self.tmp.cleanup()
    def test_reopen_after_ui_loss(self):
        self.o.tick(); rows=Journal(self.path).recover(self.o.run)
        self.assertEqual([r['event'] for r in rows],['START','TICK_BEGIN','TICK_END'])
        self.assertNotIn('DO_NOT_STORE',json.dumps(rows))
        self.assertNotIn(b'DO_NOT_STORE',self.path.read_bytes())
    def test_fixed_deadline_before_signing(self):
        self.s['deadline']+=1
        with self.assertRaises(PermissionError): self.o.tick()
        self.o.advance.assert_not_called()
    def test_lost_store_refuses_without_recreate(self):
        self.path.unlink()
        with self.assertRaises(PermissionError): self.o.tick()
        self.o.advance.assert_not_called();self.assertFalse(self.path.exists())
    def test_clock_rollback(self):
        self.o.clock=lambda:999
        with self.assertRaises(PermissionError): self.o.tick()
        self.o.advance.assert_not_called()
    def test_concurrent_tick_intents_only_one_wins(self):
        def append(_):
            try: return Journal(self.path).append(self.o.run,1,'TICK_BEGIN',1001,self.s)
            except PermissionError: return None
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(append,range(2)))
        self.assertEqual(results.count(2),1); self.assertEqual(results.count(None),1)
    def test_tampering_detected(self):
        with sqlite3.connect(self.path) as db: db.execute("UPDATE evidence SET body='{}'")
        with self.assertRaises((PermissionError,KeyError)): self.j.recover(self.o.run)
    def test_incomplete_done_rejected(self):
        self.s['phase']='DONE'
        with self.assertRaises(ValueError): self.j.append(self.o.run,1,'TICK_END',4600,self.s)
    def test_process_loss_does_not_invent_done(self):
        self.j.append(self.o.run,1,'TICK_BEGIN',4599,self.s)
        rows=Journal(self.path).recover(self.o.run)
        self.assertEqual(rows[-1]['event'],'TICK_BEGIN');self.assertNotEqual(rows[-1]['result']['phase'],'DONE')
    def test_new_process_cannot_overwrite_existing_run(self):
        with self.assertRaises(PermissionError): self.j.append(self.o.run,0,'START',1000,self.s)
    def test_post_send_store_failure_no_replay(self):
        def once(*args): self.path.unlink()
        self.o.advance.side_effect=once
        with self.assertRaises(PermissionError): self.o.tick()
        self.o.tick();self.assertEqual(self.o.advance.call_count,1)
    def test_complete_result_recovers_without_browser(self):
        def advance(*args):
            self.s.update(phase='DONE',before_ok=True,signer_denied=True,gas_expired_denied=True,cookie_still_present=True,pending_sent=True)
        self.o.advance.side_effect=advance;self.o.clock=lambda:4601;self.o.tick()
        self.assertEqual(Journal(self.path).recover(self.o.run)[-1]['result']['phase'],'DONE')
        self.o.tick();self.assertEqual(self.o.advance.call_count,1)
    def test_worker_not_dependent_on_ui_tick(self):
        self.o.advance.side_effect=lambda *args:self.s.update(phase='FAILED')
        self.o.run_until_terminal((),wait=Mock(side_effect=AssertionError('unexpected wait')))
        self.assertEqual(self.o.advance.call_count,1)

if __name__=='__main__':unittest.main(verbosity=2)
