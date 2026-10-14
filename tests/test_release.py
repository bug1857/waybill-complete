"""Release evidence cannot silently describe an uncommitted source tree."""

import pytest
import hashlib
from pathlib import Path

from bench.evidence.provenance import GitState
from tools import generate_evidence


def test_bundled_road_input_is_pinned_in_build_and_runtime():
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256((root / "data/roads/monaco-jaipur-release.osm.pbf").read_bytes()).hexdigest()
    assert digest == "3a31b6f8f58812732870d619f7e5de5c34dbc62b15ae4c5d77e10ed797f52b09"
    assert digest in (root / "Dockerfile").read_text()
    assert digest in (root / "infra/start-hosted.sh").read_text()


def test_release_refuses_dirty_source_before_running(monkeypatch):
    monkeypatch.setattr("sys.argv", ["generate_evidence", "--release"])
    monkeypatch.setattr(generate_evidence, "capture_git_state",
                        lambda _: GitState(revision="a" * 40, dirty=True))
    with pytest.raises(SystemExit) as failure:
        generate_evidence.main()
    assert failure.value.code == 2
