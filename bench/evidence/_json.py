"""Canonical JSON helpers shared by the evidence schema and bundle writer.

The evidence format deliberately accepts only JSON values.  Keeping the
normalisation in one place makes hashes independent of dictionary insertion
order and rejects values such as NaN that different JSON readers interpret in
different ways.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping


def canonical_json_bytes(value: object) -> bytes:
    """Return the one canonical byte representation used for content hashes."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def pretty_json(value: object) -> str:
    """Return deterministic, human-readable JSON terminated by one newline."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalise_json(value: Any, *, location: str) -> Any:
    """Validate and copy a JSON value into a deterministic representation."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{location} keys must be strings")
            result[key] = _normalise_json(child, location=f"{location}.{key}")
        return {key: result[key] for key in sorted(result)}
    if isinstance(value, (list, tuple)):
        return [
            _normalise_json(child, location=f"{location}[{index}]")
            for index, child in enumerate(value)
        ]
    raise TypeError(
        f"{location} contains {type(value).__name__}; only JSON values are allowed"
    )


@dataclass(frozen=True, slots=True)
class FrozenJsonObject:
    """An immutable, canonical JSON object.

    The canonical string is the stored value, so callers cannot retain a
    mutable dictionary reference and silently change evidence after creation.
    """

    _canonical: str

    def __post_init__(self) -> None:
        try:
            value = json.loads(self._canonical)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("FrozenJsonObject must contain valid JSON") from exc
        if not isinstance(value, dict):
            raise TypeError("FrozenJsonObject must contain a JSON object")
        canonical = canonical_json_bytes(
            _normalise_json(value, location="FrozenJsonObject")
        ).decode("utf-8")
        if canonical != self._canonical:
            raise ValueError("FrozenJsonObject must use canonical JSON encoding")

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, Any] | "FrozenJsonObject" | None
    ) -> "FrozenJsonObject":
        if isinstance(value, cls):
            return value
        normalised = _normalise_json(value or {}, location="JSON object")
        if not isinstance(normalised, dict):  # defensive; Mapping always gives dict
            raise TypeError("expected a JSON object")
        return cls(canonical_json_bytes(normalised).decode("utf-8"))

    @classmethod
    def from_value(cls, value: object, *, location: str) -> "FrozenJsonObject":
        if not isinstance(value, Mapping):
            raise TypeError(f"{location} must be an object")
        normalised = _normalise_json(value, location=location)
        return cls(canonical_json_bytes(normalised).decode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        # json.loads returns a new object, preserving immutability of this value.
        return json.loads(self._canonical)

    def __bool__(self) -> bool:
        return self._canonical != "{}"


def require_exact_keys(
    value: object, expected: set[str], *, location: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{location} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise ValueError(f"{location} has invalid fields: {'; '.join(details)}")
    return value


def require_string(value: object, *, location: str, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{location} must be a string")
    if nonempty and not value.strip():
        raise ValueError(f"{location} must not be empty")
    return value


def require_bool(value: object, *, location: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{location} must be a boolean")
    return value


def require_optional_int(value: object, *, location: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{location} must be an integer or null")
    return value


def require_optional_number(value: object, *, location: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{location} must be a number or null")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{location} must be finite")
    return number


def require_number(value: object, *, location: str) -> float:
    number = require_optional_number(value, location=location)
    if number is None:
        raise TypeError(f"{location} must be a number")
    return number
