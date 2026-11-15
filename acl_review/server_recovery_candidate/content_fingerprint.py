"""Shared offline recovery fingerprint; matches the existing GAS typed encoding."""
import hashlib,struct,math,json
from canonical_v9_bridge import BridgeError
def recovery_fingerprint(value):
 def typed(v):
  if v is None:return ['null']
  if isinstance(v,bool):return ['boolean',v]
  if isinstance(v,str):return ['string',v]
  if isinstance(v,(int,float)):
   if not math.isfinite(v):raise BridgeError('RECOVERY_NUMBER_INVALID')
   return ['number',struct.pack('>d',0.0 if v==0 else float(v)).hex()]
  if isinstance(v,list):return ['array',[typed(x) for x in v]]
  if isinstance(v,dict):return ['object',[[k,typed(v[k])] for k in sorted(v,key=lambda x:x.encode('utf-16-be','surrogatepass'))]]
  raise BridgeError('RECOVERY_VALUE_INVALID')
 return hashlib.sha256(json.dumps(typed(value),ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
