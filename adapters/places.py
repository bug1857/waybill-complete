"""Small, user-triggered OSM queries. Never accepts a remote URL or raw query."""

import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Listed public OSM instance; the main endpoint was unreachable from our host.
ENDPOINT = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
MAX_RESPONSE_BYTES = 512 * 1024
CACHE_SECONDS = 6 * 3600
REGIONS = {
    "monaco": {"name": "Monaco", "bbox": [43.725, 7.405, 43.752, 7.44], "roads": True},
    "jaipur": {"name": "Jaipur · city centre", "bbox": [26.895, 75.785, 26.945, 75.84], "road_name": "Jaipur · city, airport & western corridor", "road_bbox": [26.72, 75.50, 27.13, 76.02], "roads": True},
    "delhi": {"name": "New Delhi · central", "bbox": [28.605, 77.195, 28.655, 77.245], "roads": False},
    "bengaluru": {"name": "Bengaluru · central", "bbox": [12.95, 77.565, 13.0, 77.615], "roads": False},
    "mumbai": {"name": "Mumbai · south", "bbox": [18.915, 72.805, 18.965, 72.855], "roads": False},
}
CATEGORIES = {
    "restaurants": {"name": "Restaurants", "key": "amenity", "value": "restaurant"},
    "pharmacies": {"name": "Pharmacies", "key": "amenity", "value": "pharmacy"},
    "supermarkets": {"name": "Supermarkets", "key": "shop", "value": "supermarket"},
    "hotels": {"name": "Hotels", "key": "tourism", "value": "hotel"},
}
_cache = {}
_attempts = deque()
_fetch_lock = Lock()
SEARCH_ENDPOINT = "https://photon.komoot.io/api/"
_search_cache = {}
_search_attempts = deque()


class PlacesError(Exception):
    pass


class PlacesBusy(PlacesError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def road_regions(dataset_id):
    if dataset_id and dataset_id.startswith("monaco-jaipur-"):
        keys = ("monaco", "jaipur")
    elif dataset_id and dataset_id.startswith("monaco-"):
        keys = ("monaco",)
    else:
        keys = ()
    return {key: {"name": REGIONS[key].get("road_name", REGIONS[key]["name"]), "bbox": REGIONS[key].get("road_bbox", REGIONS[key]["bbox"])} for key in keys}


def places_options(dataset_id=None):
    coverage = road_regions(dataset_id)
    return {"regions": {key: {**region, "roads": key in coverage} for key, region in REGIONS.items()},
            "categories": CATEGORIES, "road_regions": coverage}


def search_places(payload):
    if not isinstance(payload, dict) or set(payload) != {"query"} or not isinstance(payload["query"], str):
        raise ValueError("provide a place search query only")
    query = " ".join(payload["query"].split())
    if not 3 <= len(query) <= 200:
        raise ValueError("place search must contain 3–200 characters; include the city")
    if not _fetch_lock.acquire(blocking=False):
        raise PlacesBusy("A places request is already running. Retry shortly.")
    try:
        now = time.monotonic()
        if query in _search_cache and now - _search_cache[query][0] < CACHE_SECONDS:
            return {**_search_cache[query][1], "cached": True}
        while _search_attempts and now - _search_attempts[0] >= 86400:
            _search_attempts.popleft()
        # shortcut: limits are per process, use a shared limiter before adding replicas.
        if len(_search_attempts) >= 100 or (_search_attempts and now - _search_attempts[-1] < 1):
            raise PlacesBusy("Search limit reached. Wait at least one second; at most 100 new searches/day.")
        _search_attempts.append(now)
        request = Request(SEARCH_ENDPOINT + "?" + urlencode({"q": query, "limit": 5, "lang": "en"}), headers={
            "User-Agent": "WaybillAcademic/1.0 (https://github.com/bug1857/waybill-complete)", "Accept": "application/json"})
        try:
            with build_opener(NoRedirect()).open(request, timeout=15) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise PlacesError("Place search response exceeded the safety limit.")
            data = json.loads(raw)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise PlacesError("Place search is unavailable. Retry later or add coordinates manually.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("features"), list):
            raise PlacesError("Place search returned an invalid response.")
        places = []
        retrieved = datetime.now(timezone.utc).isoformat()
        for feature in data["features"][:5]:
            if not isinstance(feature, dict):
                continue
            props, geometry = feature.get("properties"), feature.get("geometry")
            if not isinstance(props, dict) or not isinstance(geometry, dict) or geometry.get("type") != "Point":
                continue
            coords = geometry.get("coordinates")
            if not isinstance(coords, list) or len(coords) != 2 or any(type(v) not in (int, float) for v in coords):
                continue
            lon, lat = coords
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                continue
            labels = [props.get(k) for k in ("name", "housenumber", "street", "city", "state", "country")]
            name = ", ".join(dict.fromkeys(v for v in labels if isinstance(v, str) and v))[:240]
            if not name:
                continue
            places.append({"name": name, "lat": lat, "lon": lon, "coordinate_kind": "mapped search result",
                           "source": "OpenStreetMap via Photon", "query": query, "retrieved_at": retrieved,
                           "response_sha256": hashlib.sha256(raw).hexdigest()})
        result = {"places": places, "cached": False}
        if len(_search_cache) >= 100:
            _search_cache.pop(next(iter(_search_cache)))
        _search_cache[query] = (time.monotonic(), result)
        return result
    finally:
        _fetch_lock.release()


def fetch_places(payload):
    if not isinstance(payload, dict) or set(payload) != {"region", "category"}:
        raise ValueError("choose a region and a category; other fields are not supported")
    region, category = payload["region"], payload["category"]
    if not isinstance(region, str) or region not in REGIONS or not isinstance(category, str) or category not in CATEGORIES:
        raise ValueError("choose a supported region and category")
    key = (region, category)
    if not _fetch_lock.acquire(blocking=False):
        raise PlacesBusy("A places query is already running. Retry shortly.")
    try:
        now = time.monotonic()
        if key in _cache and now - _cache[key][0] < CACHE_SECONDS:
            return {**_cache[key][1], "cached": True}
        while _attempts and now - _attempts[0] >= 86400:
            _attempts.popleft()
        # ponytail: per-process fair-use cap; use a shared limiter for multiple replicas.
        if len(_attempts) >= 20 or (_attempts and now - _attempts[-1] < 60):
            raise PlacesBusy("Public data query limit reached. Use a cached selection, or retry later (at least 60 seconds between new queries).")
        _attempts.append(now)
        selection, tag = REGIONS[region], CATEGORIES[category]
        bounds = ",".join(map(str, selection["bbox"]))
        query = f'[out:json][timeout:20][maxsize:33554432];nwr["{tag["key"]}"="{tag["value"]}"]({bounds});out body center 200;'
        request = Request(ENDPOINT, data=urlencode({"data": query}).encode(), headers={
            "User-Agent": "WaybillAcademic/1.0 (https://github.com/bug1857/waybill-complete)",
            "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json",
        })
        try:
            with build_opener(NoRedirect()).open(request, timeout=25) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise PlacesError("Places response exceeded the safety limit. Try a different category.")
            data = json.loads(raw)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise PlacesError("OpenStreetMap's public data service is unavailable or busy. Nothing was fabricated; retry later or import your own stops.") from exc
        if not isinstance(data, dict) or data.get("remark") or not isinstance(data.get("elements"), list):
            raise PlacesError("The public service returned an incomplete response. Retry later.")
        places, seen = [], set()
        south, west, north, east = selection["bbox"]
        for item in data["elements"][:200]:
            if not isinstance(item, dict):
                continue
            tags = item.get("tags", {})
            point = item.get("center", item)
            if not isinstance(tags, dict) or not isinstance(point, dict) or tags.get(tag["key"]) != tag["value"]:
                continue
            lat, lon = point.get("lat"), point.get("lon")
            if any(type(v) not in (int, float) for v in (lat, lon)):
                continue
            if not south <= lat <= north or not west <= lon <= east:
                continue
            osm_type, osm_id = item.get("type"), item.get("id")
            if osm_type not in ("node", "way", "relation") or type(osm_id) is not int or osm_id <= 0:
                continue
            location = (round(lat, 6), round(lon, 6))
            if location in seen:
                continue
            seen.add(location)
            name = str(tags.get("name") or tags.get("brand") or f'{tag["name"]} · OSM {osm_type} {osm_id}')[:160]
            places.append({"name": name, "lat": lat, "lon": lon, "osm_type": osm_type, "osm_id": osm_id,
                           "url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                           "coordinate_kind": "mapped point" if osm_type == "node" else "mapped feature centre"})
        places.sort(key=lambda p: (p["osm_type"], p["osm_id"]))
        result = {"places": places, "region": region, "category": category, "cached": False,
                  "provenance": {"source": "OpenStreetMap via Overpass", "endpoint": ENDPOINT,
                                 "query": query, "response_sha256": hashlib.sha256(raw).hexdigest(),
                                 "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                 "osm_base_timestamp": data["osm3s"].get("timestamp_osm_base") if isinstance(data.get("osm3s"), dict) else None,
                                 "bbox": selection["bbox"], "attribution": "© OpenStreetMap contributors · ODbL",
                                 "selection_limit": 200, "locations_only": True}}
        if len(_cache) >= 20:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), result)
        return result
    finally:
        _fetch_lock.release()
