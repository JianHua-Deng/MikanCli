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


def load_project_dependencies(pyproject_path: Path = PYPROJECT_PATH) -> list[str]:
    if tomllib is None:
        return []

    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    dependencies = project.get("dependencies", [])
    return [str(dependency) for dependency in dependencies]


def requirement_to_import_name(requirement: str) -> str:
    package_name = re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip()
    if package_name in IMPORT_NAME_OVERRIDES:
        return IMPORT_NAME_OVERRIDES[package_name]
    return package_name.replace("-", "_")


def find_missing_dependencies(dependencies: list[str]) -> list[str]:
    missing: list[str] = []

    for dependency in dependencies:
        import_name = requirement_to_import_name(dependency)
        if importlib.util.find_spec(import_name) is None:
            missing.append(dependency)

    return missing


def install_dependencies(dependencies: list[str]) -> None:
    if not dependencies:
        return

    print(f"Installing missing dependencies: {', '.join(dependencies)}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *dependencies])


def ensure_runtime_dependencies(pyproject_path: Path = PYPROJECT_PATH) -> list[str]:
    dependencies = load_project_dependencies(pyproject_path)
    missing = find_missing_dependencies(dependencies)
    if not missing:
        return []

    install_dependencies(missing)
    return missing
