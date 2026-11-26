import unittest
from isolated_connection_feedback import connection_stop_message, PERMISSION_MESSAGES, KEY_MESSAGES


class ConnectionFeedback(unittest.TestCase):
    def test_known_permission_codes_have_fixed_messages(self):
        for code, expected in PERMISSION_MESSAGES.items():
            with self.subTest(code=code):
                self.assertEqual(connection_stop_message(PermissionError(code)), expected + ' 接続・保存は停止しています。')

    def test_known_missing_keys_have_fixed_messages(self):
        for code, expected in KEY_MESSAGES.items():
            with self.subTest(code=code):
                self.assertEqual(connection_stop_message(KeyError(code)), expected + ' 接続・保存は停止しています。')

    def test_unknown_and_secret_bearing_errors_are_not_rendered(self):
        secret = 'FICTIONAL_SECRET_MUST_NOT_BE_RENDERED'
        for error in [ValueError(secret), PermissionError(secret), KeyError(secret),
                      PermissionError('RELOGIN_REQUIRED', secret),
                      PermissionError({'signing_key': secret})]:
            with self.subTest(kind=type(error).__name__):
                result = connection_stop_message(error)
                self.assertNotIn(secret, result)
                self.assertIn('管理者', result)
                self.assertIn('停止', result)

    def test_exception_string_is_never_called(self):
        class UnsafeError(Exception):
            def __str__(self):
                raise AssertionError('exception string must not be called')
        self.assertIn('停止', connection_stop_message(UnsafeError('secret')))


if __name__ == '__main__':
    unittest.main()
