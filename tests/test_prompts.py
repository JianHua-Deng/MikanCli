from __future__ import annotations

import unittest
from io import StringIO

from mikancli.cli.prompts import (
    EXIT_OPTION,
    ExitRequested,
    MENU_SEPARATOR_LABEL,
    PROMPT_SEPARATOR,
    confirm_choice,
    prompt_password,
    prompt_text,
    select_option,
)


class PromptWrapperTests(unittest.TestCase):
    def test_select_option_uses_inquirer_select(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "one"
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt

        stdout = StringIO()

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=stdout
        ):
            selected = select_option("Choose", [("one", "One")], default="one")

        self.assertEqual(selected, "one")
        self.assertEqual(stdout.getvalue(), f"{PROMPT_SEPARATOR}\n")
        fake_inquirer.select.assert_called_once()
        self.assertEqual(
            fake_inquirer.select.call_args.kwargs["message"],
            "Choose",
        )

    def test_select_option_can_raise_exit_requested(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = EXIT_OPTION
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=StringIO()
        ):
            with self.assertRaises(ExitRequested):
                select_option("Choose", [("one", "One")], default="one", allow_exit=True)

    def test_select_option_can_group_navigation_choices_with_exit(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "search-again"
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt
        separator = object()

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "mikancli.cli.prompts.get_menu_separator",
            return_value=separator,
        ), patch("sys.stdout", new=StringIO()):
            selected = select_option(
                "Choose",
                [
                    ("one", "One"),
                    ("search-again", "Search with different words"),
                ],
                default="one",
                allow_exit=True,
                separator_before_values=("search-again",),
                separator_before_exit=False,
            )

        self.assertEqual(selected, "search-again")
        self.assertEqual(
            fake_inquirer.select.call_args.kwargs["choices"],
            [
                {"value": "one", "name": "One"},
                separator,
                {
                    "value": "search-again",
                    "name": "Search with different words",
                },
                {"value": EXIT_OPTION, "name": "Exit MikanCli"},
            ],
        )

    def test_select_option_separates_exit_by_default(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "one"
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt
        separator = object()

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "mikancli.cli.prompts.get_menu_separator",
            return_value=separator,
        ), patch("sys.stdout", new=StringIO()):
            selected = select_option(
                "Choose",
                [("one", "One")],
                default="one",
                allow_exit=True,
            )

        self.assertEqual(selected, "one")
        self.assertEqual(
            fake_inquirer.select.call_args.kwargs["choices"],
            [
                {"value": "one", "name": "One"},
                separator,
                {"value": EXIT_OPTION, "name": "Exit MikanCli"},
            ],
        )

    def test_menu_separator_label_is_blank_spacer(self) -> None:
        self.assertEqual(MENU_SEPARATOR_LABEL, "")

    def test_prompt_text_uses_inquirer_text(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "  solo leveling  "
        fake_inquirer = Mock()
        fake_inquirer.text.return_value = prompt

        stdout = StringIO()

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=stdout
        ):
            entered = prompt_text("Enter keyword")

        self.assertEqual(entered, "solo leveling")
        self.assertEqual(stdout.getvalue(), f"{PROMPT_SEPARATOR}\n")
        fake_inquirer.text.assert_called_once()
        self.assertEqual(
            fake_inquirer.text.call_args.kwargs["message"],
            "Enter keyword",
        )

    def test_prompt_text_can_raise_exit_requested(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = " exit "
        fake_inquirer = Mock()
        fake_inquirer.text.return_value = prompt

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=StringIO()
        ):
            with self.assertRaises(ExitRequested):
                prompt_text("Enter keyword", allow_exit=True)

    def test_prompt_password_uses_inquirer_secret(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "secret"
        fake_inquirer = Mock()
        fake_inquirer.secret.return_value = prompt

        stdout = StringIO()

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=stdout
        ):
            entered = prompt_password("Enter password")

        self.assertEqual(entered, "secret")
        self.assertEqual(stdout.getvalue(), f"{PROMPT_SEPARATOR}\n")
        fake_inquirer.secret.assert_called_once()
        self.assertEqual(
            fake_inquirer.secret.call_args.kwargs["message"],
            "Enter password",
        )

    def test_prompt_password_can_raise_exit_requested(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "exit"
        fake_inquirer = Mock()
        fake_inquirer.secret.return_value = prompt

        with patch("mikancli.cli.prompts.get_inquirer", return_value=fake_inquirer), patch(
            "sys.stdout", new=StringIO()
        ):
            with self.assertRaises(ExitRequested):
                prompt_password("Enter password", allow_exit=True)

    def test_confirm_choice_uses_select_style_yes_no(self) -> None:
        from unittest.mock import patch

        with patch("mikancli.cli.prompts.select_option", return_value="yes") as select_mock:
            confirmed = confirm_choice("Save?", default=True)

        self.assertTrue(confirmed)
        select_mock.assert_called_once_with(
            "Save?",
            [("yes", "Yes"), ("no", "No")],
            default="yes",
            allow_exit=False,
        )

    def test_confirm_choice_can_raise_exit_requested(self) -> None:
        from unittest.mock import patch

        with patch("mikancli.cli.prompts.select_option", side_effect=ExitRequested):
            with self.assertRaises(ExitRequested):
                confirm_choice("Save?", default=True, allow_exit=True)
