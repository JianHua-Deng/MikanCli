from contextlib import nullcontext
from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from mikancli.core.models import QBittorrentSettings
from mikancli.integrations import mikan, qbittorrent
from mikancli.integrations.qbittorrent_client import (
    QBittorrentClient,
    QBittorrentError,
)


SECRET = "private-password"
PRIVATE_URL = f"http://private-user:{SECRET}@example.test/private?token={SECRET}"


def http_error(status: int) -> HTTPError:
    return HTTPError(PRIVATE_URL, status, SECRET, {}, BytesIO(SECRET.encode()))


class QBittorrentNetworkContractTests(TestCase):
    def make_client(self, *, timeout: float = 15.0) -> QBittorrentClient:
        return QBittorrentClient(
            QBittorrentSettings(PRIVATE_URL, "private-user", SECRET),
            Mock(),
            timeout=timeout,
        )

    def assert_safe_error(self, error: Exception) -> None:
        self.assertNotIn(SECRET, str(error))
        self.assertNotIn("private-user", str(error))
        self.assertNotIn(PRIVATE_URL, str(error))

    def test_requests_use_default_timeout_and_keep_positional_opener(self) -> None:
        opener = Mock()
        opener.open.return_value.read.return_value = b"v5.0.0"
        client = QBittorrentClient(QBittorrentSettings("localhost:8080"), opener)

        self.assertEqual(client.get_version(), "v5.0.0")
        self.assertIs(client.opener, opener)
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 15.0})

    def test_requests_use_configured_timeout(self) -> None:
        client = self.make_client(timeout=2.5)
        client.opener.open.return_value.read.return_value = b"Ok."

        client.login()

        self.assertEqual(client.opener.open.call_args.kwargs, {"timeout": 2.5})

    def test_login_rejection_has_auth_code_without_echoing_body(self) -> None:
        client = self.make_client()
        client.opener.open.return_value.read.return_value = SECRET.encode()

        with self.assertRaises(QBittorrentError) as raised:
            client.login()

        self.assertEqual(raised.exception.code, "AUTH_FAILED")
        self.assertFalse(raised.exception.retryable)
        self.assert_safe_error(raised.exception)

    def test_http_errors_have_stable_codes_and_do_not_echo_body_or_url(self) -> None:
        cases = (
            (401, "AUTH_FAILED", False),
            (403, "AUTH_FAILED", False),
            (400, "UPSTREAM_ERROR", False),
            (408, "TIMEOUT", True),
            (503, "NETWORK_ERROR", True),
        )
        for status, code, retryable in cases:
            with self.subTest(status=status):
                client = self.make_client()
                error = http_error(status)
                self.addCleanup(error.close)
                client.opener.open.side_effect = error

                with self.assertRaises(QBittorrentError) as raised:
                    client.login()

                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.retryable, retryable)
                self.assertIn(f"HTTP {status}", str(raised.exception))
                self.assert_safe_error(raised.exception)
                self.assertTrue(error.closed)

    def test_connection_guidance_preserves_auth_error_metadata(self) -> None:
        for has_credentials in (True, False):
            with self.subTest(has_credentials=has_credentials):
                settings = QBittorrentSettings(
                    "http://example.test", "user" if has_credentials else None
                )
                error = QBittorrentError(
                    "qBittorrent request failed with HTTP 403.", code="AUTH_FAILED"
                )
                client = Mock()
                if has_credentials:
                    client.login.side_effect = error
                else:
                    client.get_version.side_effect = error

                with patch.object(qbittorrent, "QBittorrentClient", return_value=client):
                    with self.assertRaises(QBittorrentError) as raised:
                        qbittorrent.check_connection(settings)

                self.assertEqual(raised.exception.code, "AUTH_FAILED")
                self.assertFalse(raised.exception.retryable)

    def test_transport_errors_and_timeouts_are_retryable_and_redacted(self) -> None:
        cases = (
            (TimeoutError(SECRET), "TIMEOUT"),
            (URLError(TimeoutError(SECRET)), "TIMEOUT"),
            (URLError(PRIVATE_URL), "NETWORK_ERROR"),
            (ConnectionResetError(SECRET), "NETWORK_ERROR"),
        )
        for error, code in cases:
            with self.subTest(error=type(error), code=code):
                client = self.make_client()
                client.opener.open.side_effect = error

                with self.assertRaises(QBittorrentError) as raised:
                    client.get_version()

                self.assertEqual(raised.exception.code, code)
                self.assertTrue(raised.exception.retryable)
                self.assert_safe_error(raised.exception)

    def test_read_timeouts_are_also_wrapped(self) -> None:
        client = self.make_client()
        client.opener.open.return_value.read.side_effect = TimeoutError(SECRET)

        with self.assertRaises(QBittorrentError) as raised:
            client.get_version()

        self.assertEqual(raised.exception.code, "TIMEOUT")
        self.assertTrue(raised.exception.retryable)

    def test_invalid_json_and_shapes_have_invalid_response_code(self) -> None:
        for method in ("get_rss_items", "get_auto_downloading_rules", "get_preferences"):
            for body in (b"not JSON", b"[]", b"null"):
                with self.subTest(method=method, body=body):
                    client = self.make_client()
                    client.opener.open.return_value.read.return_value = body

                    with self.assertRaises(QBittorrentError) as raised:
                        getattr(client, method)()

                    self.assertEqual(raised.exception.code, "INVALID_RESPONSE")
                    self.assertFalse(raised.exception.retryable)
                    self.assert_safe_error(raised.exception)

    def test_empty_version_is_invalid_response(self) -> None:
        client = self.make_client()
        client.opener.open.return_value.read.return_value = b" "
        with self.assertRaises(QBittorrentError) as raised:
            client.get_version()
        self.assertEqual(raised.exception.code, "INVALID_RESPONSE")

    def test_error_defaults_preserve_exception_behavior(self) -> None:
        error = QBittorrentError("message")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "message")
        self.assertEqual(error.args, ("message",))
        self.assertEqual(error.code, "UPSTREAM_ERROR")
        self.assertFalse(error.retryable)


class MikanNetworkContractTests(TestCase):
    def test_fetch_uses_timeout(self) -> None:
        for timeout in (15.0, 3.0):
            with self.subTest(timeout=timeout):
                response = Mock()
                response.read.return_value = b"<html></html>"
                with patch.object(mikan, "urlopen", return_value=nullcontext(response)) as opener:
                    self.assertEqual(
                        mikan.fetch_html("https://example.test", timeout=timeout),
                        "<html></html>",
                    )
                self.assertEqual(opener.call_args.kwargs, {"timeout": timeout})

    def test_transport_errors_have_stable_codes_and_redacted_messages(self) -> None:
        cases = (
            (TimeoutError(SECRET), "TIMEOUT", True),
            (URLError(TimeoutError(SECRET)), "TIMEOUT", True),
            (URLError(PRIVATE_URL), "NETWORK_ERROR", True),
            (OSError(SECRET), "NETWORK_ERROR", True),
            (http_error(404), "UPSTREAM_ERROR", False),
            (http_error(408), "TIMEOUT", True),
            (http_error(503), "NETWORK_ERROR", True),
        )
        for error, code, retryable in cases:
            with self.subTest(error=type(error), code=code):
                if isinstance(error, HTTPError):
                    self.addCleanup(error.close)
                with patch.object(mikan, "urlopen", side_effect=error):
                    with self.assertRaises(mikan.MikanLookupError) as raised:
                        mikan.fetch_html(PRIVATE_URL)

                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.retryable, retryable)
                self.assertNotIn(SECRET, str(raised.exception))
                self.assertNotIn("private-user", str(raised.exception))
                self.assertNotIn(PRIVATE_URL, str(raised.exception))
                if isinstance(error, HTTPError):
                    self.assertTrue(error.closed)

    def test_invalid_feed_xml_or_shape_is_distinct_from_empty_feed(self) -> None:
        for body in ("<rss>", "<html><body>Login</body></html>", "<rss/>"):
            with self.subTest(body=body):
                with self.assertRaises(mikan.MikanLookupError) as raised:
                    mikan.parse_feed_items(body)
                self.assertEqual(raised.exception.code, "INVALID_RESPONSE")
                self.assertFalse(raised.exception.retryable)

        self.assertEqual(mikan.parse_feed_items("<rss><channel/></rss>"), ())

    def test_error_defaults_preserve_runtime_error_behavior(self) -> None:
        error = mikan.MikanLookupError("message")
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(str(error), "message")
        self.assertEqual(error.args, ("message",))
        self.assertEqual(error.code, "UPSTREAM_ERROR")
        self.assertFalse(error.retryable)
