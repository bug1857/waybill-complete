"""Versioned evidence bundles with tamper-evident, stable JSON serialization."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from bench.evidence._json import (
    FrozenJsonObject,
    pretty_json,
    require_exact_keys,
    require_string,
    sha256_json,
)
from bench.evidence.schema import (
    SCHEMA_VERSION,
    EvidenceManifest,
    EvidenceResult,
    validate_sha256,
)


class EvidenceIntegrityError(ValueError):
    """Raised when a bundle's declared hash does not match its contents."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    manifest: EvidenceManifest
    result: EvidenceResult

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, EvidenceManifest):
            raise TypeError("record.manifest must be an EvidenceManifest")
        if not isinstance(self.result, EvidenceResult):
            raise TypeError("record.result must be an EvidenceResult")
        if self.result.objective_unit is not None:
            if self.result.objective_unit != self.manifest.matrix_unit:
                raise ValueError(
                    "result objective_unit must match manifest matrix_unit; "
                    "mixed-unit evidence is not comparable"
                )

    @property
    def content_hash(self) -> str:
        return sha256_json(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.to_dict(),
            "result": self.result.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "EvidenceRecord":
        data = require_exact_keys(
            value, {"manifest", "result"}, location="evidence record"
        )
        return cls(
            manifest=EvidenceManifest.from_dict(data["manifest"]),
            result=EvidenceResult.from_dict(data["result"]),
        )


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """A self-validating collection of solver evidence records."""

    records: tuple[EvidenceRecord, ...]
    metadata: FrozenJsonObject = FrozenJsonObject("{}")
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported bundle schema {self.schema_version!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )
        if not isinstance(self.records, tuple) or not self.records:
            raise ValueError("an evidence bundle must contain at least one record")
        if not all(isinstance(record, EvidenceRecord) for record in self.records):
            raise TypeError("bundle records must all be EvidenceRecord values")
        if not isinstance(self.metadata, FrozenJsonObject):
            raise TypeError("bundle metadata must be a FrozenJsonObject")

    @classmethod
    def create(
        cls,
        records: tuple[EvidenceRecord, ...] | list[EvidenceRecord],
        *,
        metadata: Mapping[str, Any] | FrozenJsonObject | None = None,
    ) -> "EvidenceBundle":
        return cls(
            records=tuple(records),
            metadata=FrozenJsonObject.from_mapping(metadata),
        )

    def _payload_dict(self) -> dict[str, object]:
        return {
            "metadata": self.metadata.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "schema_version": self.schema_version,
        }

    @property
    def content_hash(self) -> str:
        """SHA-256 of the canonical bundle payload, excluding the hash field."""
        return sha256_json(self._payload_dict())

    def to_dict(self) -> dict[str, object]:
        result = self._payload_dict()
        result["content_sha256"] = self.content_hash
        return result

    def to_json(self) -> str:
        """Stable, pretty JSON. Equal bundles always produce equal bytes."""
        return pretty_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: object, *, verify_hash: bool = True) -> "EvidenceBundle":
        data = require_exact_keys(
            value,
            {"schema_version", "metadata", "records", "content_sha256"},
            location="evidence bundle",
        )
        records_value = data["records"]
        if not isinstance(records_value, list):
            raise TypeError("evidence bundle.records must be an array")
        metadata = FrozenJsonObject.from_value(
            data["metadata"], location="evidence bundle.metadata"
        )
        bundle = cls(
            schema_version=require_string(
                data["schema_version"], location="evidence bundle.schema_version"
            ),
            metadata=metadata,
            records=tuple(EvidenceRecord.from_dict(item) for item in records_value),
        )
        declared = require_string(
            data["content_sha256"], location="evidence bundle.content_sha256"
        )
        validate_sha256(declared, field="evidence bundle.content_sha256")
        if verify_hash and declared != bundle.content_hash:
            raise EvidenceIntegrityError(
                "evidence bundle content hash mismatch: "
                f"declared {declared}, computed {bundle.content_hash}"
            )
        return bundle

    @classmethod
    def from_json(cls, text: str | bytes, *, verify_hash: bool = True) -> "EvidenceBundle":
        try:
            value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid evidence JSON: {exc}") from exc
        return cls.from_dict(value, verify_hash=verify_hash)

    @classmethod
    def read(cls, path: Path | str) -> "EvidenceBundle":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def atomic_write_text(path: Path | str, text: str) -> None:
    """Durably replace ``path`` with UTF-8 text without exposing a partial file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, destination)
        temporary_name = None
        # Persist the directory entry where the platform supports directory fsync.
        try:
            directory_fd = os.open(destination.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def write_bundle(bundle: EvidenceBundle, path: Path | str) -> str:
    """Atomically write a bundle and return its content SHA-256."""
    atomic_write_text(path, bundle.to_json())
    return bundle.content_hash
