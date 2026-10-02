"""Bounded public-data acquisition; fixtures are test doubles, not app fallbacks."""

import hashlib
import io
import json
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread
from urllib.error import URLError

import pytest

from adapters import places as p
from api import server as api


@pytest.fixture(autouse=True)
def reset_query_state():
    p._cache.clear()
    p._attempts.clear()
    yield
    p._cache.clear()
    p._attempts.clear()


def example_response():
    return {"osm3s": {"timestamp_osm_base": "2026-10-02T00:00:00Z"}, "elements": [
        {"type": "node", "id": 1, "lat": 43.73, "lon": 7.42, "tags": {"amenity": "restaurant", "name": "Test-only restaurant"}},
        {"type": "way", "id": 2, "center": {"lat": 43.74, "lon": 7.43}, "tags": {"amenity": "restaurant"}},
        {"type": "node", "id": 3, "lat": 43.73, "lon": 7.42, "tags": {"amenity": "restaurant"}},
        {"type": "node", "id": 4, "lat": 10**400, "lon": 7.42, "tags": {"amenity": "restaurant"}},
        {"type": "node", "id": 5, "lat": True, "lon": 7.42, "tags": {"amenity": "restaurant"}},
        {"type": "node", "id": 6, "lat": 43.74, "lon": 7.43, "tags": {"amenity": "pharmacy"}},
        {"type": "node", "id": 7, "lat": 0, "lon": 0, "tags": {"amenity": "restaurant"}},
    ]}


def mock_network(monkeypatch, raw):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return io.BytesIO(raw)
    monkeypatch.setattr(p, "build_opener", lambda _: Opener())
    return calls


def test_query_is_bounded_and_preserves_real_record_identity(monkeypatch):
    raw = json.dumps(example_response()).encode()
    calls = mock_network(monkeypatch, raw)
    result = p.fetch_places({"region": "monaco", "category": "restaurants"})
    assert len(result["places"]) == 2
    assert result["places"][0]["osm_id"] == 1
    assert result["places"][1]["coordinate_kind"] == "mapped feature centre"
    assert result["provenance"]["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["provenance"]["locations_only"]
    request, timeout = calls[0]
    assert request.full_url == p.ENDPOINT and timeout == 25
    assert "timeout%3A20" in request.data.decode()
    assert "center+200" in request.data.decode()
    cached = p.fetch_places({"region": "monaco", "category": "restaurants"})
    assert cached["cached"] and len(calls) == 1
    assert cached["provenance"] == result["provenance"]
    with pytest.raises(p.PlacesBusy):
        p.fetch_places({"region": "monaco", "category": "hotels"})
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [None, {}, {"region": [], "category": "hotels"},
    {"region": "jaipur", "category": "raw query"}, {"region": "http://127.0.0.1", "category": "hotels"},
    {"region": "monaco", "category": "hotels", "url": "http://example.com"}])
def test_invalid_query_cannot_reach_network(payload):
    with pytest.raises(ValueError):
        p.fetch_places(payload)
    assert not p._attempts


@pytest.mark.parametrize("raw", [b"not JSON", b"{}", b'{"remark":"timed out", "elements":[]}', b"x" * (p.MAX_RESPONSE_BYTES + 1)])
def test_upstream_failure_never_generates_replacement_places(monkeypatch, raw):
    mock_network(monkeypatch, raw)
    with pytest.raises(p.PlacesError):
        p.fetch_places({"region": "monaco", "category": "restaurants"})
    assert not p._cache


def test_timeout_and_redirects_are_not_silent_fallbacks(monkeypatch):
    class Unavailable:
        def open(self, request, timeout):
            raise URLError("unavailable")
    monkeypatch.setattr(p, "build_opener", lambda _: Unavailable())
    with pytest.raises(p.PlacesError):
        p.fetch_places({"region": "monaco", "category": "restaurants"})
    assert p.NoRedirect().redirect_request(None, None, 302, "", {}, "http://127.0.0.1") is None


def test_busy_and_daily_cap(monkeypatch):
    p._fetch_lock.acquire()
    try:
        with pytest.raises(p.PlacesBusy):
            p.fetch_places({"region": "monaco", "category": "hotels"})
    finally:
        p._fetch_lock.release()
    monkeypatch.setattr(p.time, "monotonic", lambda: 10000)
    p._attempts.extend(range(20))
    with pytest.raises(p.PlacesBusy):
        p.fetch_places({"region": "monaco", "category": "hotels"})


def test_http_routes_use_existing_origin_and_body_guards(monkeypatch):
    monkeypatch.setattr(api, "fetch_places", lambda _: {"places": []})
    server = HTTPServer(("127.0.0.1", 0), api.Handler)
    worker = Thread(target=server.serve_forever, daemon=True); worker.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("GET", "/api/places/options")
        response = client.getresponse()
        assert response.status == 200 and "jaipur" in json.loads(response.read())["regions"]
        for origin, status in [(f"http://127.0.0.1:{server.server_port}", 200), ("https://evil.test", 403)]:
            client.request("POST", "/api/places", "{}", {"Content-Type": "application/json", "Origin": origin})
            response = client.getresponse()
            assert response.status == status; response.read()
        client.request("GET", "/real-data.js?v=1")
        response = client.getresponse()
        assert response.status == 200; response.read()
    finally:
        client.close(); server.shutdown(); server.server_close(); worker.join()
