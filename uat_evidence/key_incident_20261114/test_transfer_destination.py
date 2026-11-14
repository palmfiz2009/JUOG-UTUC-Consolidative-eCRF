import unittest
import generate_encrypted_bundle as g
from local_admin_transfer import transfer_fields

class DestinationTests(unittest.TestCase):
    def test_legacy_bundle_routes_to_actual_frontend(self):
        m = g.material(bytes(range(48)))
        before = repr(m)
        fields = dict(transfer_fields(m))
        self.assertEqual(len(fields), 4)
        self.assertNotIn('Streamlit / juog_identity_bridge.signing_key', fields)
        self.assertEqual(fields['Streamlit / auth_connect.signing_key'], m['gas']['ADMIN_BRIDGE_SIGNING_KEY'])
        self.assertEqual(repr(m), before)
        for k, v in m['gas'].items():
            self.assertEqual(fields['GAS / ' + k], v)

if __name__ == '__main__':
    unittest.main()
