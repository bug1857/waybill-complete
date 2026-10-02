"""Release evidence cannot silently describe an uncommitted source tree."""

import pytest

from bench.evidence.provenance import GitState
from tools import generate_evidence


def test_release_refuses_dirty_source_before_running(monkeypatch):
    monkeypatch.setattr("sys.argv", ["generate_evidence", "--release"])
    monkeypatch.setattr(generate_evidence, "capture_git_state",
                        lambda _: GitState(revision="a" * 40, dirty=True))
    with pytest.raises(SystemExit) as failure:
        generate_evidence.main()
    assert failure.value.code == 2
