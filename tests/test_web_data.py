"""The web app's generated data must stay derived from the verified files.

The TypeScript instance data is a build artefact of
``tools/generate_web_data.py``. If someone edits it by hand -- or a model
"helpfully" fills in coordinates -- regeneration produces a different file and
this test fails.

That is the whole defence against the failure mode found in review: a parallel
implementation inlined coordinates into source and had 17 of 52 wrong in
berlin52, which made every downstream gap meaningless while looking entirely
plausible.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "reference" / "google-ui" / "src" / "data" / "instances.generated.ts"


@pytest.mark.skipif(not GENERATED.exists(), reason="web app not present")
def test_generated_file_is_up_to_date():
    before = GENERATED.read_text()
    result = subprocess.run(
        [sys.executable, "-m", "tools.generate_web_data"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"generator failed:\n{result.stderr}"
    after = GENERATED.read_text()
    assert after == before, (
        "web/src/data/instances.generated.ts is out of date or was edited by hand.\n"
        "Run: python -m tools.generate_web_data"
    )


@pytest.mark.skipif(not GENERATED.exists(), reason="web app not present")
def test_generated_file_declares_itself_generated():
    text = GENERATED.read_text()
    assert "GENERATED FILE -- DO NOT EDIT BY HAND" in text
    assert "sha256=" in text, "provenance checksums missing from the header"


@pytest.mark.skipif(not GENERATED.exists(), reason="web app not present")
def test_no_coordinates_are_hand_written_in_web_source():
    """No file under web/src may carry a TSPLIB coordinate table except the
    generated one."""
    web_src = ROOT / "reference" / "google-ui" / "src"
    offenders = []
    for path in web_src.rglob("*.ts*"):
        if path == GENERATED:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # A coordinate table looks like a long array of [number, number] pairs.
        if text.count("], [") > 20 and "COORDS" in text.upper():
            offenders.append(path.relative_to(ROOT))
    assert not offenders, (
        "hand-written coordinate tables found in web source: "
        + ", ".join(str(p) for p in offenders)
        + "\nGenerate them from data/tsplib/ instead."
    )
