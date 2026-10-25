from unittest import TestCase
from unittest.mock import MagicMock, patch

from InquirerPy import inquirer
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from mikancli.cli import input_parsing, prompts, search_flow


class SearchPromptTests(TestCase):
    def test_search_frame_survives_empty_retry_and_exit(self) -> None:
        answers = iter(["", "  One   Piece  ", "quit", "other", "  secret  ", "redirected"])
        frames = []

        def execute(widget):
            frames.append(widget._session.show_frame)
            if isinstance(widget, inquirer.secret):
                self.assertTrue(widget._session.is_password)
            return next(answers)

        terminal = MagicMock(is_terminal=True)
        with (
            create_app_session(input=DummyInput(), output=DummyOutput()),
            patch.object(inquirer.text, "execute", autospec=True, side_effect=execute),
            patch.object(prompts, "console", terminal),
            patch.object(input_parsing, "print_message") as warning,
        ):
            self.assertEqual(search_flow.prompt_search_keyword(), "One Piece")
            with self.assertRaises(prompts.ExitRequested):
                search_flow.prompt_search_keyword(retry=True)
            self.assertEqual(prompts.prompt_text("Other"), "other")
            self.assertEqual(prompts.prompt_password("Password"), "  secret  ")
            terminal.is_terminal = False
            self.assertEqual(search_flow.prompt_search_keyword(), "redirected")
        self.assertEqual(frames, [True, True, True, True, True, False])
        warning.assert_called_once()

    def test_menu_frames_keep_focus_results_and_exit(self) -> None:
        answers = iter(["en", "yes", prompts.EXIT_OPTION])
        factory = inquirer.select

        def create(**kwargs):
            widget = factory(**kwargs)
            layout = widget.application.layout
            focused = layout.current_window
            original = layout.container

            def execute():
                self.assertIs(layout.current_window, focused)
                self.assertIsNot(layout.container, original)
                self.assertIn(original, list(layout.walk()))
                self.assertFalse(kwargs["border"])
                return next(answers)

            widget.execute = execute
            return widget

        with create_app_session(input=DummyInput(), output=DummyOutput()), patch.object(
            prompts, "console", MagicMock(is_terminal=True)
        ), patch.object(inquirer, "select", side_effect=create):
            self.assertEqual(prompts.select_option("Language", [("en", "English"), ("zh-CN", "中文")]), "en")
            self.assertTrue(prompts.confirm_choice("Continue?"))
            with self.assertRaises(prompts.ExitRequested):
                prompts.select_option("Language", [("en", "English")], allow_exit=True)
