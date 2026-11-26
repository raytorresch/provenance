from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

# domain/ and application/ are the business-logic core: they must stay
# importable and testable without a database, an HTTP framework or any
# third-party SDK. Adapters translate to/from those SDKs; the core never
# should.
PROTECTED_PACKAGES = ["app.domain", "app.application"]

INTERNAL_TOP_LEVEL_PACKAGE = "app"


def _iter_python_files(package: str) -> list[Path]:
    package_dir = SRC_ROOT / Path(package.replace(".", "/"))
    files = sorted(package_dir.rglob("*.py"))
    assert files, f"no .py files found under {package_dir}, check the path"
    return files


def _top_level_imports(source: str) -> set[str]:
    """Every module name a file imports, one level deep (`sqlalchemy.orm` -> `sqlalchemy`).
    Relative imports (`from . import x`) are skipped: they can only resolve
    inside the same package, so they're internal by construction."""
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                continue
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def _is_sdk_import(module_name: str) -> bool:
    if module_name in sys.stdlib_module_names:
        return False
    return module_name != INTERNAL_TOP_LEVEL_PACKAGE


@pytest.mark.parametrize("package", PROTECTED_PACKAGES)
def test_package_only_imports_stdlib_or_internal_modules(package: str) -> None:
    offenders: dict[str, set[str]] = {}
    for path in _iter_python_files(package):
        source = path.read_text(encoding="utf-8")
        sdk_imports = {m for m in _top_level_imports(source) if _is_sdk_import(m)}
        if sdk_imports:
            offenders[str(path.relative_to(SRC_ROOT))] = sdk_imports

    assert not offenders, (
        f"{package} must stay free of SDK/infra imports (sqlalchemy, openai, "
        f"fastapi, psycopg, pydantic, ...) — move the dependency behind an "
        f"adapter. Offending files: {offenders}"
    )


# --- Sanity checks for the detector itself, so the test above isn't ---
# --- silently vacuous if _top_level_imports or _is_sdk_import regress. ---


def test_is_sdk_import_flags_known_third_party_packages() -> None:
    assert _is_sdk_import("sqlalchemy") is True
    assert _is_sdk_import("openai") is True
    assert _is_sdk_import("fastapi") is True
    assert _is_sdk_import("psycopg") is True


def test_is_sdk_import_allows_stdlib_and_internal_modules() -> None:
    assert _is_sdk_import("re") is False
    assert _is_sdk_import("hashlib") is False
    assert _is_sdk_import("__future__") is False
    assert _is_sdk_import("app") is False


def test_top_level_imports_extracts_plain_and_from_imports_but_skips_relative() -> None:
    source = textwrap.dedent(
        """
        from __future__ import annotations

        import re
        import sqlalchemy.orm
        from pathlib import Path
        from openai import OpenAI
        from . import sibling
        from .sibling import helper
        """
    )

    assert _top_level_imports(source) == {
        "__future__",
        "re",
        "sqlalchemy",
        "pathlib",
        "openai",
    }


def test_package_only_imports_stdlib_or_internal_modules_catches_a_violation(
    tmp_path: Path,
) -> None:
    fake_package = tmp_path / "app" / "domain"
    fake_package.mkdir(parents=True)
    (fake_package / "leaky.py").write_text("import sqlalchemy\n", encoding="utf-8")

    offenders: dict[str, set[str]] = {}
    for path in sorted(fake_package.rglob("*.py")):
        sdk_imports = {
            m
            for m in _top_level_imports(path.read_text(encoding="utf-8"))
            if _is_sdk_import(m)
        }
        if sdk_imports:
            offenders[str(path)] = sdk_imports

    assert offenders == {str(fake_package / "leaky.py"): {"sqlalchemy"}}
