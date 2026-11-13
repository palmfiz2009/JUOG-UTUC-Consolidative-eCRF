"""Isolated UAT evidence candidate, NOT deployed or an authentication store.

Requires an explicitly provisioned durable volume on a supervised single host.
No credentials, identities, session digests, assertions or exception strings persist.
Hash chaining detects accidental corruption, NOT privileged-writer forgery.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from contextlib import contextmanager


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def provision(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('ABSOLUTE_PATH_REQUIRED')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE runs(id TEXT PRIMARY KEY, deadline INTEGER, source_sha TEXT, seq INTEGER DEFAULT 0, head TEXT, terminal INTEGER DEFAULT 0)')
        db.execute('CREATE TABLE evidence(run TEXT, seq INTEGER, body TEXT, digest TEXT, PRIMARY KEY(run,seq))')


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute() or not self.path.is_file() or self.path.is_symlink():
            raise PermissionError('EVIDENCE_STORE_UNAVAILABLE')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=5)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def start(self, deadline, source_sha):
        if type(deadline) is not int or len(source_sha)!=64 or any(c not in '0123456789abcdef' for c in source_sha):
            raise ValueError('INVALID_RUN_METADATA')
        run = str(uuid.uuid4())  # Random evidence ID, not derived from the principal.
        with self.connect() as db:
            db.execute('INSERT INTO runs(id,deadline,source_sha,head) VALUES (?,?,?,?)', (run,deadline,source_sha,'0'*64))
        return run

    def append(self, run, expected_seq, event, at, state):
        if event not in {'START','TICK_BEGIN','TICK_END','INTERRUPTED'} or type(at) is not int:
            raise ValueError('INVALID_EVENT')
        safe = {}
        for key in ('before_ok','signer_denied','gas_expired_denied','cookie_still_present','pending_generated','pending_sent'):
            if key in state:
                if type(state[key]) is not bool: raise ValueError('INVALID_BOOLEAN')
                safe[key]=state[key]
        for key in ('started','duration','before_seconds_left','pending_seconds_left','observed_elapsed'):
            if key in state:
                if type(state[key]) is not int: raise ValueError('INVALID_INTEGER')
                safe[key]=state[key]
        if state.get('phase') not in {'WAITING','WAITING_EXPIRY','CHECKING_EXPIRY','DONE','FAILED','INTERRUPTED'}:
            raise ValueError('INVALID_PHASE')
        safe['phase']=state['phase']
        if safe['phase']=='DONE' and not all(safe.get(k) is True for k in ('before_ok','signer_denied','gas_expired_denied','cookie_still_present','pending_sent')):
            raise ValueError('INCOMPLETE_RESULT')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT deadline,source_sha,seq,head,terminal FROM runs WHERE id=?',(run,)).fetchone()
            if not row or row[2]!=expected_seq or row[4]: raise PermissionError('EVIDENCE_CONFLICT')
            deadline,source,seq,head,_=row
            if state.get('deadline')!=deadline: raise PermissionError('DEADLINE_CHANGED')
            prev=db.execute('SELECT body FROM evidence WHERE run=? ORDER BY seq DESC LIMIT 1',(run,)).fetchone()
            if prev and at<json.loads(prev[0])['at']: raise PermissionError('CLOCK_ROLLBACK')
            body=canonical(dict(run=run,seq=seq+1,previous=head,event=event,at=at,deadline=deadline,source_sha=source,result=safe))
            digest=hashlib.sha256(body.encode()).hexdigest()
            db.execute('INSERT INTO evidence VALUES (?,?,?,?)',(run,seq+1,body,digest))
            db.execute('UPDATE runs SET seq=?,head=?,terminal=? WHERE id=?',(seq+1,digest,int(safe['phase'] in {'DONE','FAILED','INTERRUPTED'}),run))
        return seq+1

    def recover(self, run):
        with self.connect() as db:
            db.execute('BEGIN')
            meta=db.execute('SELECT deadline,source_sha,seq,head FROM runs WHERE id=?',(run,)).fetchone()
            rows=db.execute('SELECT seq,body,digest FROM evidence WHERE run=? ORDER BY seq',(run,)).fetchall()
        if not meta: raise PermissionError('UNKNOWN_RUN')
        previous='0'*64; result=[]
        for seq,body,digest in rows:
            obj=json.loads(body)
            if (seq!=len(result)+1 or obj['seq']!=seq or obj['run']!=run or obj['previous']!=previous or
                obj['deadline']!=meta[0] or obj['source_sha']!=meta[1] or hashlib.sha256(body.encode()).hexdigest()!=digest):
                raise PermissionError('EVIDENCE_CORRUPTED')
            previous=digest;result.append(obj)
        if len(result)!=meta[2] or previous!=meta[3]: raise PermissionError('EVIDENCE_CORRUPTED')
        return result


class Observer:
    """Call on a supervised server worker, not in a Streamlit fragment.

    Callbacks must perform the existing real OIDC/B2 checks and ui_context only.
    A process loss leaves an incomplete durable trace. Never resume with a new
    identity or replay a pending request after such a loss.
    """
    def __init__(self, journal, state, source_sha, advance, clock=time.time):
        self.journal=journal;self.state=state;self.advance=advance;self.clock=clock
        self.run=journal.start(state['deadline'],source_sha);self.seq=0
        self._save('START')

    def _save(self,event):
        self.seq=self.journal.append(self.run,self.seq,event,int(self.clock()),self.state)

    def tick(self,*callbacks):
        if self.state['phase'] in {'DONE','FAILED','INTERRUPTED'}: return
        try:
            # Persist intent BEFORE calling sign/send. On store error, no send.
            self._save('TICK_BEGIN')
            self.advance(self.state,int(self.clock()),*callbacks)
            self._save('TICK_END')
        except Exception:
            self.state.pop('pending_envelope',None)
            self.state['phase']='FAILED'
            # Never print original exceptions or retry requests.
            raise PermissionError('OBSERVATION_STOPPED') from None

    def run_until_terminal(self, callbacks, wait=time.sleep):
        while self.state['phase'] not in {'DONE','FAILED','INTERRUPTED'}:
            self.tick(*callbacks)
            if self.state['phase'] not in {'DONE','FAILED','INTERRUPTED'}: wait(1)
