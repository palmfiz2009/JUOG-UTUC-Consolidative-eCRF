"""Offline review artifact only; never edits the source application."""
import ast,difflib,hashlib,json
from pathlib import Path
OUT=Path(__file__).parent
BASE=Path('/workspace/scratch/426ea3aa0205/auth-connect/juog_common.py')
PROVEN=Path('/workspace/scratch/426ea3aa0205/uat/integrated_core/streamlit_connection_candidate/juog_common.py')
def functions(text):
 lines=text.splitlines(keepends=True)
 return {n.name:(n,''.join(lines[n.lineno-1:n.end_lineno])) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
base=BASE.read_text();source=PROVEN.read_text();b,p=functions(base),functions(source)
names=['capture_draft_state','restore_draft_state','is_direct_identifier_key','redact_draft_identifiers']
lines=base.splitlines(keepends=True)
for name in sorted(names[:2],key=lambda n:b[n][0].lineno,reverse=True):
 node=b[name][0];lines[node.lineno-1:node.end_lineno]=[p[name][1]+'\n']
candidate=''.join(lines)+'\n\n'+p[names[2]][1]+'\n\n'+p[names[3]][1]+'\n'
ast.parse(candidate)
(OUT/'juog_common.py').write_text(candidate)
(OUT/'capture_restore_redaction.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),candidate.splitlines(True),fromfile='a/juog_common.py',tofile='b/juog_common.py')))
hashof=lambda s:hashlib.sha256(s.encode()).hexdigest()
(OUT/'source_identity.json').write_text(json.dumps(dict(status='REVIEW_ONLY_NOT_DEPLOYED',base=str(BASE),base_sha256=hashof(base),proven=str(PROVEN),proven_sha256=hashof(source),candidate_sha256=hashof(candidate),changed_functions=names),indent=2)+'\n')
