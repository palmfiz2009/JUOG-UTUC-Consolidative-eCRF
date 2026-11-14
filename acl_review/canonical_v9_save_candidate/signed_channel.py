"""Transport adapter candidate. No HTTP implementation, default execution denied.
Native provider must be the existing pinned uat_auth_connect.context(st).
A separately reviewed business-stage provider is required before live activation.
"""
from uat_b2_auth_bridge import signed_request
from canonical_v9_bridge import BridgeError
ALLOWED=frozenset(['read_crf','prepare_request','execute_request','request_status'])
def deny_execution():raise BridgeError('BUSINESS_EXECUTION_NOT_APPROVED')
class SignedChannel:
 def __init__(self,native_provider,envelope_transport,guard=deny_execution):
  self.native_provider,self.envelope_transport,self.guard=native_provider,envelope_transport,guard
  self.bound=None
 def _native(self):
  native=self.native_provider()
  # Validate current native claims and B2 expiry using the unchanged signer.
  signed_request(native,'ui_context',{'id':'identity_check','action':'ui_context','payload':{'registration_id':''}})
  cfg=native.secrets['juog_identity_bridge']
  identity={'issuer':native.user['iss'],'subject':native.user['sub'],'environment':cfg['session_environment']}
  if self.bound is None:self.bound=identity
  if self.bound!=identity:raise BridgeError('PRINCIPAL_CHANGED')
  return native
 def identity(self):
  self._native();return dict(self.bound)
 def __call__(self,action,payload):
  self.guard()
  if action not in ALLOWED:raise BridgeError('ACTION_NOT_ALLOWED')
  return self.envelope_transport(signed_request(self._native(),action,payload))
