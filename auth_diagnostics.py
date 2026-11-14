"""Fixed-vocabulary AUTH_CONNECT failure diagnostics. No raw errors/responses."""
import json,time,socket
from urllib.error import HTTPError,URLError
CODES=frozenset(('ACL_DENIED','AUTH_REQUIRED','AUTH_INVALID','AUTH_EXPIRED','ASSERTION_REPLAY','SESSION_REVOKED','SESSION_INVALID','SESSION_STORE_INVALID','SESSION_STORE_UNAVAILABLE','LOCK_TIMEOUT','ISOLATION_NOT_APPROVED','AUTH_CONNECT_NOT_APPROVED','AUTH_CONNECT_CONTEXT_ONLY','UNIFIED_TRANSACTION_INCOMPLETE'))
class ContextFailure(PermissionError):
 def __init__(self,code,elapsed_ms):
  self.code=code;self.elapsed_ms=elapsed_ms;super().__init__(code)
def checked_context(send,envelope,valid):
 start=time.monotonic()
 def failure(code):return ContextFailure(code,round((time.monotonic()-start)*1000))
 try:r=send(envelope)
 except HTTPError:raise failure('HTTP_ERROR') from None
 except (TimeoutError,socket.timeout):raise failure('TRANSPORT_TIMEOUT') from None
 except URLError as e:raise failure('TRANSPORT_TIMEOUT' if isinstance(e.reason,(TimeoutError,socket.timeout)) else 'TRANSPORT_ERROR') from None
 except (json.JSONDecodeError,UnicodeError):raise failure('INVALID_RESPONSE') from None
 except Exception:raise failure('TRANSPORT_ERROR') from None
 if not isinstance(r,dict):raise failure('INVALID_RESPONSE')
 if not valid(r):
  error=r.get('error')
  raise failure(error if isinstance(error,str) and error in CODES else 'CONTEXT_REJECTED')
 return r

def expired_native_login(user,now):
    """Only offer logout for demonstrably expired native claims; never clear halt."""
    iat,exp=user.get('iat'),user.get('exp')
    return type(iat) is int and type(exp) is int and type(now) is int and iat<=now and exp>iat and now>=min(iat+3600,exp)
