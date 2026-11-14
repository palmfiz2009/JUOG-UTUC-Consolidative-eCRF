from pathlib import Path
import hashlib,difflib,json
P=Path(__file__).parent
source=(P.parent/'b971_candidate/bundle_prepare_view_candidate.gs').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='6d75109c4fffda3ebe4aedb0d7990f1d694ef3a331dcdb2123c10399279970d6'
s=source
old="if(!['ui_context','session_revoke','prepare_request','execute_request','request_status','get_draft','read_crf'].includes(req.action))"
s=s.replace(old,old.replace("'get_draft'","'list_requests','get_draft'"),1)
s=s.replace(" }else if(req.action==='prepare_request'){", " }else if(req.action==='list_requests'){\n  juogCanonicalRecoveryScope_(req.payload);\n }else if(req.action==='prepare_request'){",1)
s=s.replace("if(req.action==='list_requests')return lifecycle.list();", "if(req.action==='list_requests')return auth04Scoped?juogCanonicalRecoveryList_(store,service,lifecycle,who,req.payload,c,hash):lifecycle.list();",1)
s=s.replace("if(req.action==='prepare_request')return lifecycle.prepare(req.payload);", "if(req.action==='prepare_request'){if(auth04Scoped&&c.canonicalRecoveryReadApproved===true){const denied=juogCanonicalRecoveryPrepareGuard_(store,service,lifecycle,who,req.payload,c,hash);if(denied)return denied;}return lifecycle.prepare(req.payload);}",1)
s=s.replace("if(auth04Scoped)juogAuth04Request_(req);", "if(auth04Scoped){juogAuth04Request_(req);juogCanonicalRecoveryRequest_(req,c);}",1)
s=s.replace("if(req.action==='execute_request')op=found[0].operation;", "if(auth04Scoped&&c.canonicalRecoveryReadApproved===true&&(found[0].operation.action!=='save_crf'||found[0].operation.payload.record_key!=='JUOG-971|perioperative_30d|30d'))throw Error('AUTH04_SCOPE_DENIED');if(req.action==='execute_request')op=found[0].operation;",1)
s+='\n'+(P/'recovery_scope.gs').read_text()
(P/'bundle_recovery_candidate.gs').write_text(s)
(P/'recovery.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),s.splitlines(True),fromfile='Version9',tofile='unapproved-recovery-candidate')))
(P/'source_identity.json').write_text(json.dumps({'base_version':9,'base_sha256':hashlib.sha256(source.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'deployed':False,'new_resources':0,'current_auth_connect_all_business_routes_still_denied':True,'requires_separate_scoped_route_approval':True},indent=2)+'\n')
