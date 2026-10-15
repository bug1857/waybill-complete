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
    p._search_cache.clear()
    p._search_attempts.clear()
    yield
    p._cache.clear()
    p._attempts.clear()
    p._search_cache.clear()
    p._search_attempts.clear()


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
    monkeypatch.setattr(api, "search_places", lambda _: {"places": []})
    server = HTTPServer(("127.0.0.1", 0), api.Handler)
    worker = Thread(target=server.serve_forever, daemon=True); worker.start()
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("GET", "/api/places/options")
        response = client.getresponse()
        assert response.status == 200 and "jaipur" in json.loads(response.read())["regions"]
        for origin, status in [(f"http://127.0.0.1:{server.server_port}", 200), ("https://evil.test", 403)]:
            for endpoint in ("/api/places", "/api/places/search"):
                client.request("POST", endpoint, "{}", {"Content-Type": "application/json", "Origin": origin})
                response = client.getresponse()
                assert response.status == status; response.read()
        client.request("GET", "/real-data.js?v=1")
        response = client.getresponse()
        assert response.status == 200; response.read()
    finally:
        client.close(); server.shutdown(); server.server_close(); worker.join()


def test_search_preserves_coordinates_identity_and_cached_retrieval(monkeypatch):
    feature = {"properties": {"name": "Test museum", "city": "Jaipur"}, "geometry": {"type": "Point", "coordinates": [75.82, 26.92]}}
    invalid = {**feature, "geometry": {"type": "Point", "coordinates": [True, 91]}}
    raw = json.dumps({"features": [feature, invalid, None]}).encode()
    calls = mock_network(monkeypatch, raw)
    result = p.search_places({"query": "Test museum Jaipur"})
    place, = result["places"]
    assert (place["lat"], place["lon"]) == (26.92, 75.82)
    assert place["name"] == "Test museum, Jaipur"
    assert place["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert calls[0][0].full_url.startswith(p.SEARCH_ENDPOINT + "?q=Test+museum+Jaipur")
    assert "limit=5" in calls[0][0].full_url and calls[0][1] == 15
    assert p.search_places({"query": "  Test museum   Jaipur "})["places"] == result["places"]
    assert len(calls) == 1
    with pytest.raises(p.PlacesBusy):
        p.search_places({"query": "Another place"})




@pytest.mark.parametrize("payload", [None, {}, {"query": []}, {"query": "ab"}, {"query": "x" * 201}, {"query": "place", "url": "https://evil.test"}])
def test_invalid_search_never_reaches_network(payload):
    with pytest.raises(ValueError):
        p.search_places(payload)
    assert not p._search_attempts


@pytest.mark.parametrize("raw", [b"not JSON", b"{}", b"x" * (p.MAX_RESPONSE_BYTES + 1)])
def test_search_upstream_errors_do_not_create_places(monkeypatch, raw):
    mock_network(monkeypatch, raw)
    with pytest.raises(p.PlacesError):
        p.search_places({"query": "Test museum Jaipur"})
    assert not p._search_cache


def test_search_empty_results_and_daily_limit(monkeypatch):
    mock_network(monkeypatch, b'{"features":[]}')
    assert p.search_places({"query": "Missing place"})["places"] == []
    monkeypatch.setattr(p.time, "monotonic", lambda: 10000)
    p._search_attempts.clear(); p._search_attempts.extend(range(100))
    with pytest.raises(p.PlacesBusy):
        p.search_places({"query": "Another place"})
@pytest.mark.parametrize("dataset_id, expected", [(None, set()), ("unknown:test", set()), ("monaco-260901:test", {"monaco"}), ("monaco-jaipur-261013:test", {"monaco", "jaipur"})])
def test_places_options_only_advertise_the_configured_road_extract(dataset_id, expected):
    result = p.places_options(dataset_id)
    assert set(result["road_regions"]) == expected
    assert {key for key, region in result["regions"].items() if region["roads"]} == expected
    assert result["regions"]["jaipur"]["bbox"] == [26.895, 75.785, 26.945, 75.84]
    if "jaipur" in expected:
        assert result["road_regions"]["jaipur"]["bbox"] == [26.72, 75.50, 27.13, 76.02]
        assert result["road_regions"]["jaipur"]["name"] == "Jaipur · city, airport & western corridor"
        assert result["regions"]["jaipur"]["name"] == "Jaipur · city centre"
