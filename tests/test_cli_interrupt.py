from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

from mikancli.cli import entrypoint, qbittorrent_flow, search_flow
from mikancli.core.models import AppConfig
from mikancli.i18n import get_language, set_language, t


class InterruptTests(TestCase):
    def setUp(self) -> None:
        self.addCleanup(set_language, get_language())
        terminal_input = patch("sys.stdin.isatty", return_value=True)
        terminal_input.start()
        self.addCleanup(terminal_input.stop)

    def test_url_interrupt_exits_cleanly_without_saving(self) -> None:
        for language in ("en", "zh-CN"):
            for args in ([], ["--setup-qbittorrent"]):
                with self.subTest(language=language, args=args):
                    output, error = StringIO(), StringIO()
                    with (
                        patch.object(entrypoint, "load_config", return_value=AppConfig()),
                        patch.object(entrypoint, "prompt_startup_action", return_value=entrypoint.STARTUP_ACTION_QBITTORRENT),
                        patch.object(qbittorrent_flow, "print_section"),
                        patch.object(qbittorrent_flow, "prompt_text", side_effect=KeyboardInterrupt),
                        patch.object(qbittorrent_flow, "save_config") as save,
                        redirect_stdout(output), redirect_stderr(error),
                    ):
                        self.assertEqual(entrypoint.main(args + ["--language", language]), 130)
                    self.assertEqual(output.getvalue(), "")
                    self.assertEqual(error.getvalue(), t("common.cancelled") + "\n")
                    save.assert_not_called()

    def test_network_interrupt_stops_loading_and_preserves_json_stdout(self) -> None:
        for json_mode in (False, True):
            with self.subTest(json_mode=json_mode):
                output, error = StringIO(), StringIO()
                terminal = MagicMock(is_terminal=True, is_interactive=True)
                failure = KeyboardInterrupt()
                args = ["Anime", "--language", "en", "--save-path", "C:/Anime"]
                with (
                    patch.object(entrypoint, "load_config", return_value=AppConfig(qbittorrent_url="http://localhost:8080")),
                    patch.object(search_flow, "search_mikan_bangumi", side_effect=failure),
                    patch("mikancli.display.console", terminal),
                    redirect_stdout(output), redirect_stderr(error),
                ):
                    self.assertEqual(entrypoint.main(args + (["--json"] if json_mode else [])), 130)
                self.assertEqual(output.getvalue(), "")
                self.assertEqual(error.getvalue(), "Cancelled. Exited MikanCli.\n")
                if json_mode:
                    terminal.status.assert_not_called()
                else:
                    terminal.status.return_value.__exit__.assert_called_once_with(KeyboardInterrupt, failure, ANY)

    def test_explicit_exit_remains_successful(self) -> None:
        output, error = StringIO(), StringIO()
        with (
            patch.object(entrypoint, "load_config", return_value=AppConfig()),
            patch.object(entrypoint, "prompt_startup_action", side_effect=entrypoint.ExitRequested),
            redirect_stdout(output), redirect_stderr(error),
        ):
            self.assertEqual(entrypoint.main(["--language", "en"]), 0)
        self.assertEqual(output.getvalue(), "Exited MikanCli.\n")
        self.assertEqual(error.getvalue(), "")
