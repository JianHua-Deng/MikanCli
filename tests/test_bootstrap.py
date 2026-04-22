from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from mikancli.bootstrap import (
    ensure_runtime_dependencies,
    find_missing_dependencies,
    load_project_dependencies,
    requirement_to_import_name,
)

TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_bootstrap"


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = TEST_TMP_ROOT / self._testMethodName
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_requirement_to_import_name_preserves_inquirerpy(self) -> None:
        self.assertEqual(requirement_to_import_name("InquirerPy>=0.3"), "InquirerPy")

    def test_load_project_dependencies_reads_pyproject(self) -> None:
        pyproject_path = self.temp_dir / "pyproject.toml"
        pyproject_path.write_text(
            "[project]\ndependencies = [\"InquirerPy>=0.3\", \"rich>=13\"]\n",
            encoding="utf-8",
        )

        self.assertEqual(
            load_project_dependencies(pyproject_path),
            ["InquirerPy>=0.3", "rich>=13"],
        )

    def test_find_missing_dependencies_returns_only_missing(self) -> None:
        from unittest.mock import patch

        with patch("mikancli.bootstrap.importlib.util.find_spec") as find_spec:
            find_spec.side_effect = [object(), None]
            missing = find_missing_dependencies(["rich>=13", "InquirerPy>=0.3"])

        self.assertEqual(missing, ["InquirerPy>=0.3"])

    def test_ensure_runtime_dependencies_installs_missing(self) -> None:
        pyproject_path = self.temp_dir / "pyproject.toml"
        pyproject_path.write_text(
            "[project]\ndependencies = [\"InquirerPy>=0.3\"]\n",
            encoding="utf-8",
        )

        from unittest.mock import patch

        with patch("mikancli.bootstrap.importlib.util.find_spec", return_value=None), patch(
            "mikancli.bootstrap.install_dependencies"
        ) as install_mock:
            installed = ensure_runtime_dependencies(pyproject_path)

        self.assertEqual(installed, ["InquirerPy>=0.3"])
        install_mock.assert_called_once_with(["InquirerPy>=0.3"])

    def test_ensure_runtime_dependencies_skips_when_present(self) -> None:
        pyproject_path = self.temp_dir / "pyproject.toml"
        pyproject_path.write_text(
            "[project]\ndependencies = [\"InquirerPy>=0.3\"]\n",
            encoding="utf-8",
        )

        from unittest.mock import patch

        with patch("mikancli.bootstrap.importlib.util.find_spec", return_value=object()), patch(
            "mikancli.bootstrap.install_dependencies"
        ) as install_mock:
            installed = ensure_runtime_dependencies(pyproject_path)

        self.assertEqual(installed, [])
        install_mock.assert_not_called()
