import base64,json,unittest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import generate_encrypted_bundle as g

class BundleTests(unittest.TestCase):
    def test_roundtrip_and_shared_signer(self):
        m=g.material(bytes(range(48)))
        self.assertEqual(m["gas"]["ADMIN_BRIDGE_SIGNING_KEY"],m["streamlit"]["juog_identity_bridge.signing_key"])
        self.assertNotEqual(m["gas"]["ADMIN_RESUME_DERIVATION_KEY"],m["gas"]["ADMIN_DRAFT_PEPPER"])
        password="OFFLINE-FIXTURE-PASSPHRASE-ONLY"
        b=g.encrypt_bundle(m,password,bytes(range(16)),bytes(range(12)))
        for value in m["gas"].values(): self.assertNotIn(value,json.dumps(b))
        key=Scrypt(salt=bytes(range(16)),length=32,n=2**15,r=8,p=1).derive(password.encode())
        self.assertEqual(json.loads(AESGCM(key).decrypt(bytes(range(12)),base64.b64decode(b["ciphertext"]),g.AAD)),m)
        with self.assertRaises(Exception): AESGCM(bytes(32)).decrypt(bytes(range(12)),base64.b64decode(b["ciphertext"]),g.AAD)
    def test_reject_short_password(self):
        with self.assertRaises(ValueError): g.encrypt_bundle({},"short",bytes(16),bytes(12))

if __name__=="__main__": unittest.main()
