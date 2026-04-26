from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
IMPORT_NAME_OVERRIDES = {
    "InquirerPy": "InquirerPy",
}
_REQUIREMENT_SPLIT_RE = re.compile(r"[<>=!~;\[]")
"""
Matches the first character that starts a version pin, environment marker, or extras block in a dependency string.
It is used to split a package requirement down to the importable package name before checking whether it is installed.
Example: before "InquirerPy>=0.3" -> result "InquirerPy".
"""


def load_project_dependencies(pyproject_path: Path = PYPROJECT_PATH) -> list[str]:
    """Read project dependencies from pyproject.toml. Returns dependency strings from the project table, or an empty list when tomllib is unavailable."""
    if tomllib is None:
        return []

    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    dependencies = project.get("dependencies", [])
    return [str(dependency) for dependency in dependencies]


def requirement_to_import_name(requirement: str) -> str:
    """Convert a package requirement into the module name used for import checks. Example: requirement_to_import_name("rich>=13") returns "rich"."""
    package_name = _REQUIREMENT_SPLIT_RE.split(requirement, maxsplit=1)[0].strip()
    if package_name in IMPORT_NAME_OVERRIDES:
        return IMPORT_NAME_OVERRIDES[package_name]
    return package_name.replace("-", "_")


def find_missing_dependencies(dependencies: list[str]) -> list[str]:
    """Return the dependency strings whose import modules are not installed. The return value preserves the original requirement strings so they can be passed directly to pip."""
    missing: list[str] = []

    for dependency in dependencies:
        import_name = requirement_to_import_name(dependency)
        if importlib.util.find_spec(import_name) is None:
            missing.append(dependency)

    return missing


def install_dependencies(dependencies: list[str]) -> None:
    """Install missing dependencies with the current Python interpreter. Returns None and lets subprocess errors bubble up when pip fails."""
    if not dependencies:
        return

    print(f"Installing missing dependencies: {', '.join(dependencies)}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *dependencies])


def ensure_runtime_dependencies(pyproject_path: Path = PYPROJECT_PATH) -> list[str]:
    """Install any project dependencies that are missing before interactive code runs. Returns the dependency strings that were installed, or an empty list when nothing was missing."""
    dependencies = load_project_dependencies(pyproject_path)
    missing = find_missing_dependencies(dependencies)
    if not missing:
        return []

    install_dependencies(missing)
    return missing
