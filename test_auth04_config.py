import copy
import unittest
from unittest.mock import patch
from pathlib import Path
import auth04_config as c


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.base = c.load_config()

    def test_disabled_default(self):
        self.assertIs(self.base['enabled'], False)

    def test_enabled_requires_evidence_and_safety(self):
        ready = dict(self.base, enabled=True, prerequisites_verified=True,
                     review_ref='review-commit/path')
        self.assertTrue(c.validate_config(ready)['enabled'])
        for key, value in [('review_ref', ''), ('approval_ref', ''),
                           ('prerequisites_verified', False),
                           ('notifications_disabled', False)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_config(dict(ready, **{key: value}))

    def test_unknown_fields_and_secrets_rejected(self):
        for key in ('signing_key', 'client_secret', 'cookie_secret', 'actor'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_config(dict(self.base, **{key: 'sentinel'}))

    def test_pin_and_boolean_drift_denied(self):
        for key, value in [('enabled', 1), ('facility_code', 'TEST02'),
                           ('fixture_id', 'JUOG-971'), ('url', 'elsewhere'),
                           ('session_store_generation', 'other'),
                           ('write_actions', ['save_crf', 'delete_draft'])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_config(dict(self.base, **{key: value}))

    def test_unreadable_and_malformed_fail_closed_without_input(self):
        for value in ('SECRET_SENTINEL', '{"client_secret":"SECRET_SENTINEL"}'):
            with patch.object(Path, 'read_text', return_value=value):
                with self.assertRaises(PermissionError) as cm:
                    c.load_config()
                self.assertEqual(str(cm.exception), 'AUTH04_CONFIG_UNAVAILABLE')
        with patch.object(Path, 'read_text', side_effect=OSError('SECRET_SENTINEL')):
            with self.assertRaises(PermissionError) as cm:
                c.load_config()
            self.assertNotIn('SECRET_SENTINEL', str(cm.exception))

    def test_return_does_not_alias_actions(self):
        cfg = c.validate_config(self.base)
        cfg['write_actions'].append('delete_draft')
        self.assertEqual(self.base['write_actions'], ['save_draft', 'save_crf'])


if __name__ == '__main__':
    unittest.main()
