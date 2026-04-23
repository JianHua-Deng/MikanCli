from __future__ import annotations

import unittest

from mikancli.cli.prompts import EXIT_OPTION, ExitRequested, confirm_choice, prompt_text, select_option


class PromptWrapperTests(unittest.TestCase):
    def test_select_option_uses_inquirer_select(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "one"
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt

        with patch("mikancli.cli.prompts._get_inquirer", return_value=fake_inquirer):
            selected = select_option("Choose", [("one", "One")], default="one")

        self.assertEqual(selected, "one")
        fake_inquirer.select.assert_called_once()

    def test_select_option_can_raise_exit_requested(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = EXIT_OPTION
        fake_inquirer = Mock()
        fake_inquirer.select.return_value = prompt

        with patch("mikancli.cli.prompts._get_inquirer", return_value=fake_inquirer):
            with self.assertRaises(ExitRequested):
                select_option("Choose", [("one", "One")], default="one", allow_exit=True)

    def test_prompt_text_uses_inquirer_text(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = "  solo leveling  "
        fake_inquirer = Mock()
        fake_inquirer.text.return_value = prompt

        with patch("mikancli.cli.prompts._get_inquirer", return_value=fake_inquirer):
            entered = prompt_text("Enter keyword")

        self.assertEqual(entered, "solo leveling")
        fake_inquirer.text.assert_called_once()

    def test_prompt_text_can_raise_exit_requested(self) -> None:
        from unittest.mock import Mock, patch

        prompt = Mock()
        prompt.execute.return_value = " exit "
        fake_inquirer = Mock()
        fake_inquirer.text.return_value = prompt

        with patch("mikancli.cli.prompts._get_inquirer", return_value=fake_inquirer):
            with self.assertRaises(ExitRequested):
                prompt_text("Enter keyword", allow_exit=True)

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
