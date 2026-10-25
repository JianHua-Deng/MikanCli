from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

from rich.console import Console
from rich.theme import Theme

from mikancli.core.models import RuleDraft
from mikancli.display import loading, print_message, print_section, print_text_summary
from mikancli.i18n import get_language, set_language


class DisplayTests(TestCase):
    def test_sections_wrap_literal_context_and_stay_plain_when_redirected(self) -> None:
        title = "[bold]动画[/bold]"
        context = "https://example.test/rss?title=[literal]&padding=" + "x" * 60
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                output = StringIO()
                terminal = Console(file=output, width=40, height=40, force_terminal=interactive,
                                   color_system=None, theme=Theme({"heading": "cyan"}))
                with patch("mikancli.display.console", terminal):
                    print_section(title, context)
                rendered = output.getvalue()
                compact = "".join(c for c in rendered if not c.isspace() and c not in "╭╮╰╯┌┐└┘│─")
                self.assertIn(title, compact)
                self.assertIn(context, compact)
                if not interactive:
                    self.assertEqual(rendered, f"\n{title}\n\n{context}\n")

    def test_loading_gates_animation_and_cleans_up_when_requests_fail(self) -> None:
        literal = "[bold]正在加载[/bold] :smile:"
        for terminal, interactive in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(terminal=terminal, interactive=interactive):
                target = MagicMock(is_terminal=terminal, is_interactive=interactive)
                failure = ValueError("request failed")
                with patch("mikancli.display.console", target), patch("mikancli.display.print_message") as message:
                    with self.assertRaises(ValueError), loading(literal):
                        raise failure
                if terminal and interactive:
                    target.status.assert_called_once()
                    self.assertEqual(target.status.call_args.args[0].plain, literal)
                    target.status.return_value.__exit__.assert_called_once_with(ValueError, failure, ANY)
                    message.assert_not_called()
                else:
                    target.status.assert_not_called()
                    message.assert_called_once_with(literal)

    def test_messages_preserve_literal_text_in_terminals_and_redirects(self) -> None:
        literal = r"[bold]错误[/bold] C:\Anime\:smile: https://example.test/[title]"
        for style in ("note", "success", "warning", "error"):
            for interactive in (False, True):
                with self.subTest(style=style, interactive=interactive):
                    output = StringIO()
                    terminal = Console(file=output, width=40, force_terminal=interactive,
                                       color_system=None, theme=Theme({style: "red"}))
                    with patch("mikancli.display.console", terminal):
                        print_message(literal, style=style)
                    rendered = output.getvalue()
                    self.assertEqual("".join(rendered.split()), "".join(literal.split()))
                    self.assertNotIn("\x1b", rendered)
                    if not interactive:
                        self.assertEqual(rendered, literal + "\n")

    def test_summary_preserves_literal_values_and_language_when_redirected(self) -> None:
        self.addCleanup(set_language, get_language())
        literal = r"[bold]动画[/bold] C:\Anime\:smile:"
        url = "https://example.test/rss?title=[OnePiece]&group=534"
        draft = RuleDraft(literal, literal, literal, (), (), feed_url=url, save_path=literal, notes=(literal,))
        for language, label in (("en", "Keyword:"), ("zh-CN", "关键词：")):
            with self.subTest(language=language):
                set_language(language)
                output = StringIO()
                with redirect_stdout(output), patch(
                    "mikancli.display.console",
                    Console(width=120, force_terminal=False, theme=Theme({"heading": "cyan", "label": "cyan", "note": "dim"})),
                ):
                    self.assertEqual(print_text_summary(draft), 0)
                rendered = output.getvalue()
                self.assertEqual(rendered.count(literal), 5)
                self.assertIn(url, rendered)
                self.assertIn(label, rendered)
                self.assertNotIn("\x1b", rendered)
