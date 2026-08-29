"""Enforce the core purity rule.

Revision 1 of the architecture asserted that ``core/`` imports nothing touching
the network, the disk, or a database -- and then placed an OSRM client inside
``core/distance/``. Prose drifts. This does not.

Walks every module under ``core/`` with the :mod:`ast` module and fails if it
imports a forbidden module or calls ``open()``. Runs in the test suite and is
usable standalone in CI::

    python -m tools.check_purity
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

#: Top-level modules ``core/`` must never import. Anything that reaches a
#: socket, the filesystem, a database, or a subprocess belongs in ``adapters/``.
FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "socket", "ssl", "http", "urllib", "urllib3", "ftplib", "telnetlib",
        "requests", "httpx", "aiohttp", "websockets",
        "psycopg", "psycopg2", "sqlite3", "sqlalchemy", "redis", "pymongo",
        "subprocess", "multiprocessing", "shutil", "tempfile", "pathlib",
        "os", "io", "pickle", "shelve",
        "fastapi", "flask", "django", "starlette", "uvicorn",
    }
)

#: Builtins that perform I/O.
FORBIDDEN_CALLS: frozenset[str] = frozenset({"open", "input", "print"})


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.detail}"


def _root_module(name: str) -> str:
    return name.split(".", 1)[0]


def check_file(path: Path) -> list[Violation]:
    """Return every purity violation in one module."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - a syntax error fails elsewhere
        return [Violation(path, exc.lineno or 0, f"syntax error: {exc.msg}")]

    violations: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _root_module(alias.name)
                if root in FORBIDDEN_IMPORTS:
                    violations.append(
                        Violation(path, node.lineno, f"imports {alias.name!r}")
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import, stays inside the package
                continue
            if node.module and _root_module(node.module) in FORBIDDEN_IMPORTS:
                violations.append(
                    Violation(path, node.lineno, f"imports from {node.module!r}")
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                violations.append(
                    Violation(path, node.lineno, f"calls {func.id}()")
                )

    return violations


def check_tree(root: Path) -> list[Violation]:
    """Check every ``.py`` file under ``root``."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(check_file(path))
    return violations


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "core"

    if not root.is_dir():
        sys.stderr.write(f"not a directory: {root}\n")
        return 2

    violations = check_tree(root)
    if violations:
        sys.stderr.write(f"core purity violated ({len(violations)}):\n")
        for v in violations:
            sys.stderr.write(f"  {v}\n")
        sys.stderr.write(
            "\nEvery implementation that touches the network, the disk, or a "
            "database belongs in adapters/.\n"
        )
        return 1

    count = sum(1 for _ in root.rglob("*.py"))
    sys.stdout.write(f"core purity OK ({count} modules checked)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
