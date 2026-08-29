"""The core purity rule is enforced, and the enforcement itself works."""

import textwrap
from pathlib import Path

from tools.check_purity import check_file, check_tree

CORE = Path(__file__).resolve().parent.parent / "core"


def test_core_is_pure():
    violations = check_tree(CORE)
    assert violations == [], "core/ must not touch network, disk, or database:\n" + "\n".join(
        str(v) for v in violations
    )


def test_core_has_modules_to_check():
    """Guard against the rule passing because it scanned nothing."""
    assert len(list(CORE.rglob("*.py"))) > 5


def test_checker_catches_planted_network_import(tmp_path):
    """The test that tests the test: a planted violation must be caught."""
    planted = tmp_path / "leaky.py"
    planted.write_text(
        textwrap.dedent(
            """
            import requests

            def fetch():
                return requests.get("http://example.com")
            """
        )
    )
    violations = check_file(planted)
    assert any("requests" in v.detail for v in violations)


def test_checker_catches_planted_open_call(tmp_path):
    planted = tmp_path / "reader.py"
    planted.write_text("def load():\n    return open('/etc/hosts').read()\n")
    violations = check_file(planted)
    assert any("open()" in v.detail for v in violations)


def test_checker_catches_from_import(tmp_path):
    planted = tmp_path / "dbish.py"
    planted.write_text("from sqlalchemy import create_engine\n")
    violations = check_file(planted)
    assert any("sqlalchemy" in v.detail for v in violations)


def test_checker_allows_clean_module(tmp_path):
    clean = tmp_path / "pure.py"
    clean.write_text("import math\n\ndef area(r):\n    return math.pi * r * r\n")
    assert check_file(clean) == []
