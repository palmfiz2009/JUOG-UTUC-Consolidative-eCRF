/* Three administrative domain plans. Only copied views change; original rows remain.
 * Deployment, VOID policy and secure code handover require explicit approval. */
function juogAdminPlanV3_(action,p,tables,who,rt) {
 const fail=c=>({ok:false,error:c}),copy=x=>JSON.parse(JSON.stringify(x));
 if(!who||!who.enabled||who.role!=='admin'||!who.id)return fail('ROLE_NOT_ALLOWED');
 const allowed=['registration_id','crf_type','visit','reason','new_reporter_email','approval_ref'];
 if(!p||Object.keys(p).some(k=>!allowed.includes(k)))return fail('UNKNOWN_ADMIN_FIELD');
 if(typeof p.reason!=='string'||!p.reason.trim()||p.reason.length>1000)return fail('REASON_REQUIRED');
 if(rt.privacy(p))return fail('DIRECT_IDENTIFIER_NOT_ALLOWED');
 const after=copy(tables),index=rows=>Object.fromEntries(rows[0].map((h,i)=>[h,i]));
 const reg=after.Registry;if(!reg)return fail('REGISTRY_MISSING');const ri=index(reg);
 const matches=reg.slice(1).filter(r=>r[ri.registration_id]===p.registration_id);
 if(matches.length!==1)return fail('REGISTRY_NOT_UNIQUE');const row=matches[0],facility=row[ri.facility_code];
 if(!facility||!Array.isArray(who.facilities)||!who.facilities.includes(facility))return fail('FACILITY_FORBIDDEN');
 if(row[ri.status]!=='ACTIVE')return fail('REGISTRY_NOT_ACTIVE');
 const result={ok:true,registration_id:p.registration_id,action};
 const event={actor:who.id,action,reason:p.reason,registration_id:p.registration_id,at:rt.now(),changes:[]};
 if(action==='void_registration') {
  if(!rt.voidPolicyApproved||typeof p.approval_ref!=='string'||!p.approval_ref.trim())return fail('VOID_APPROVAL_REQUIRED');
  const screen=after.Screening,si=screen&&index(screen);if(!si)return fail('SCREENING_MISSING');
  const sm=screen.slice(1).filter(r=>r[si.screening_id]===row[ri.screening_id]&&r[si.registration_id]===p.registration_id);
  if(sm.length!==1||sm[0][si.status]!=='REGISTERED')return fail('SCREENING_REGISTRY_CONFLICT');
  row[ri.status]='VOID';sm[0][si.status]='VOID';
  event.changes=[{table:'Registry',field:'status',before:'ACTIVE',after:'VOID'},{table:'Screening',field:'status',before:'REGISTERED',after:'VOID'}];event.approval_ref=p.approval_ref;
  // IDs, all CRFs, MDT reviews and past audits are deliberately retained.
 } else if(['reset_draft_code','update_draft_email'].includes(action)) {
  if(!['perioperative_30d','day90','followup'].includes(p.crf_type)||!p.visit)return fail('DRAFT_KEY_INVALID');
  const drafts=after.CRF_Drafts,di=drafts&&index(drafts);if(!di)return fail('DRAFTS_MISSING');
  const key=[p.registration_id,p.crf_type,p.visit].join('|');const ds=drafts.slice(1).filter(r=>r[di.draft_key]===key);
  if(ds.length!==1)return fail('DRAFT_NOT_UNIQUE');const d=ds[0];if(d[di.facility_code]!==facility)return fail('DRAFT_FACILITY_CONFLICT');
  if(action==='reset_draft_code') {
   // Derived server-side per operation, never accepted from caller or persisted in plaintext.
   const code=rt.resumeCode();if(!/^\d{6}$/.test(code))return fail('CODE_GENERATION_FAILED');
   d[di.resume_code_hash]=rt.codeHash(code);d[di.failed_attempts]=0;d[di.locked_until]='';d[di.code_reset_at]=event.at;d[di.code_reset_by]=who.id;
   event.changes=[{table:'CRF_Drafts',field:'resume_code_hash',before:'REDACTED',after:'ROTATED'}];result.code_rotated=true;
  } else {
   const email=String(p.new_reporter_email||'').trim().toLowerCase();if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return fail('EMAIL_INVALID');
   const old=d[di.reporter_email];d[di.reporter_email]=email;d[di.email_reset_at]=event.at;d[di.email_reset_by]=who.id;
   // Email changes contact data only, never principal or access ACL.
   event.changes=[{table:'CRF_Drafts',field:'reporter_email',before:old,after:email}];
  }
 } else return fail('ACTION_NOT_ALLOWED');
 return {ok:true,result,after,audit_detail:event};
}
