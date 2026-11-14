"""Undeployed scoped signed read adapter. Both guards deny by default."""
from signed_channel import SignedChannel,deny_execution
from canonical_v9_bridge import BridgeError,CASE,FACILITY,PAIR
from uat_b2_auth_bridge import signed_request
class RecoveryChannel(SignedChannel):
 def __init__(self,native_provider,envelope_transport,guard=deny_execution,recovery_guard=deny_execution):
  super().__init__(native_provider,envelope_transport,guard);self.recovery_guard=recovery_guard
 def __call__(self,action,payload):
  if action!='list_requests':return super().__call__(action,payload)
  self.guard();self.recovery_guard()
  if payload!={'registration_id':CASE,'facility_code':FACILITY,'record_key':'|'.join((CASE,*PAIR))}:raise BridgeError('RECOVERY_SCOPE_DENIED')
  return self.envelope_transport(signed_request(self._native(),action,payload))
