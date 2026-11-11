/* Review-only read authorization adapter. No writes, no HTTP, no default grants.
 * policy and resource resolver MUST be server-owned, never supplied by payload.
 * Existing business routes are not wired by this file. */
function juogAclReadGate_(envelope, config, ss, policy, resolveResource) {
  const decoded=juogV3DecodeBridge_(envelope,config);
  const action=decoded.request.action;
  if(!policy || !Object.prototype.hasOwnProperty.call(policy,action))throw Error('ACTION_DENIED');
  const rule=policy[action];
  if(!rule || rule.readOnly!==true || !Array.isArray(rule.roles) || !rule.roles.length)throw Error('ACTION_DENIED');
  const actor=juogV3ReadIndividualAcl_(ss,decoded.principal.issuer,decoded.principal.subject);
  if(!actor || actor.enabled!==true || !actor.id)throw Error('ACCESS_DENIED');
  if(!rule.roles.includes(actor.role))throw Error('ROLE_DENIED');
  if(typeof resolveResource!=='function')throw Error('RESOURCE_UNVERIFIED');
  const resource=resolveResource(decoded.request);
  if(!resource || typeof resource.facilityId!=='string' || !resource.facilityId.trim())throw Error('RESOURCE_UNVERIFIED');
  if(!actor.facilities.includes(resource.facilityId))throw Error('FACILITY_DENIED');
  return {request:decoded.request,actor:{id:actor.id,role:actor.role},resource};
}
