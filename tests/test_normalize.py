import unittest

from autofeedsync.normalize import normalize_keyword, sanitize_folder_name


class NormalizeTests(unittest.TestCase):
    def test_normalize_keyword_collapses_case_and_whitespace(self) -> None:
        self.assertEqual(normalize_keyword("  Solo   Leveling  "), "solo leveling")

    def test_sanitize_folder_name_removes_windows_invalid_characters(self) -> None:
        self.assertEqual(sanitize_folder_name("Solo: Leveling?"), "Solo Leveling")


if __name__ == "__main__":
    unittest.main()
