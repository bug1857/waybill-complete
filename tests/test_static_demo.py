"""The static demo must render generated evidence without a server."""

import json
from pathlib import Path

from bench.evidence.bundle import EvidenceBundle


ROOT = Path(__file__).resolve().parent.parent


def test_static_demo_embeds_the_validated_evidence_bundle() -> None:
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    payload = (ROOT / "web" / "evidence.js").read_text(encoding="utf-8")

    assert 'src="evidence.js"' in index
    assert 'src="app.js"' in index
    assert "window.WAYBILL_EVIDENCE" in app
    assert "fetch(" not in app
    embedded = json.loads(payload.removeprefix("window.WAYBILL_EVIDENCE = ").rstrip(";\n"))
    bundle = EvidenceBundle.from_dict(embedded)
    assert bundle.content_hash == embedded["content_sha256"]


def test_live_workbench_exposes_each_connected_surface() -> None:
    html = (ROOT / "web" / "live.html").read_text(encoding="utf-8")
    script = (ROOT / "web" / "live.js").read_text(encoding="utf-8")
    for panel in ("dispatch", "real-data", "sandbox", "asymmetry", "evidence", "invariants", "report"):
        assert f'id="{panel}"' in html
    assert 'src="evidence.js"' in html
    assert 'request("/api/solve"' in script
    assert "window.WAYBILL_EVIDENCE" in script
    assert "Matrix identity" in script
    for live_surface in ("header-matrix", "fleet-utilization", "eta-timeline", "solve-report-dialog"):
        assert f'id="{live_surface}"' in html
    assert "renderFleet(data, payload)" in script
    assert "renderTimeline()" in script
    assert "function solveHeldKarp" not in script
    assert 'src="route-motion.js?v=3"' in html
    assert 'src="real-data.js?v=2"' in html
    for control in ("play-route", "step-route", "reset-route", "route-progress", "map-overview", "map-labels", "map-stop"):
        assert f'id="{control}"' in html
