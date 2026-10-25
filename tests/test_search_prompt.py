from unittest import TestCase
from unittest.mock import MagicMock, patch

from InquirerPy import inquirer
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from mikancli.cli import input_parsing, prompts, search_flow


class SearchPromptTests(TestCase):
    def test_search_frame_survives_empty_retry_and_exit(self) -> None:
        answers = iter(["", "  One   Piece  ", "quit", "other", "redirected"])
        frames = []

        def execute(widget):
            frames.append(widget._session.show_frame)
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
            terminal.is_terminal = False
            self.assertEqual(search_flow.prompt_search_keyword(), "redirected")
        self.assertEqual(frames, [True, True, True, False, False])
        warning.assert_called_once()
