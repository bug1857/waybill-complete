"""Checksum manifests for immutable benchmark input data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from bench.evidence._json import require_exact_keys, require_string
from bench.evidence.provenance import sha256_file
from bench.evidence.schema import SCHEMA_VERSION, validate_sha256


class ChecksumVerificationError(ValueError):
    """One or more benchmark input files failed integrity verification."""

    def __init__(self, issues: list[str] | tuple[str, ...]) -> None:
        self.issues = tuple(issues)
        super().__init__("benchmark checksum verification failed:\n- " + "\n- ".join(issues))


@dataclass(frozen=True, slots=True)
class ChecksumEntry:
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        parsed = PurePosixPath(self.path)
        if parsed.is_absolute() or not self.path or ".." in parsed.parts or "." in parsed.parts:
            raise ValueError("checksum path must be a normalised relative POSIX path")
        validate_sha256(self.sha256, field=f"checksum for {self.path}")
        if (
            not isinstance(self.size_bytes, int)
            or isinstance(self.size_bytes, bool)
            or self.size_bytes < 0
        ):
            raise ValueError("size_bytes must be a non-negative integer")

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ChecksumEntry":
        data = require_exact_keys(
            value, {"path", "sha256", "size_bytes"}, location="checksum entry"
        )
        size = data["size_bytes"]
        if not isinstance(size, int) or isinstance(size, bool):
            raise TypeError("checksum entry.size_bytes must be an integer")
        return cls(
            path=require_string(data["path"], location="checksum entry.path"),
            sha256=require_string(data["sha256"], location="checksum entry.sha256"),
            size_bytes=size,
        )


@dataclass(frozen=True, slots=True)
class ChecksumManifest:
    files: tuple[ChecksumEntry, ...]
    schema_version: str = SCHEMA_VERSION
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported checksum schema {self.schema_version!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )
        if self.algorithm != "sha256":
            raise ValueError("only sha256 checksum manifests are supported")
        if not isinstance(self.files, tuple) or not self.files:
            raise ValueError("checksum manifest must contain at least one file")
        names = [entry.path for entry in self.files]
        if names != sorted(names):
            raise ValueError("checksum entries must be sorted by path")
        if len(names) != len(set(names)):
            raise ValueError("checksum entries must have unique paths")

    @classmethod
    def from_dict(cls, value: object) -> "ChecksumManifest":
        data = require_exact_keys(
            value,
            {"schema_version", "algorithm", "files"},
            location="checksum manifest",
        )
        files = data["files"]
        if not isinstance(files, list):
            raise TypeError("checksum manifest.files must be an array")
        return cls(
            schema_version=require_string(
                data["schema_version"], location="checksum manifest.schema_version"
            ),
            algorithm=require_string(
                data["algorithm"], location="checksum manifest.algorithm"
            ),
            files=tuple(ChecksumEntry.from_dict(item) for item in files),
        )

    @classmethod
    def load(cls, path: Path | str) -> "ChecksumManifest":
        source = Path(path)
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid checksum manifest {source}: {exc}") from exc
        return cls.from_dict(value)

    def verify(
        self,
        root: Path | str,
        *,
        require_complete: bool = True,
        input_suffixes: tuple[str, ...] = (".tsp", ".opt.tour"),
        excluded_paths: tuple[str, ...] = (),
    ) -> None:
        """Verify hashes, sizes, missing files, and unmanifested benchmark inputs."""
        directory = Path(root)
        expected = {entry.path for entry in self.files}
        issues: list[str] = []
        for entry in self.files:
            path = directory / entry.path
            if not path.is_file():
                issues.append(f"missing input: {entry.path}")
                continue
            actual_size = path.stat().st_size
            if actual_size != entry.size_bytes:
                issues.append(
                    f"size mismatch for {entry.path}: "
                    f"expected {entry.size_bytes}, got {actual_size}"
                )
            actual_hash = sha256_file(path)
            if actual_hash != entry.sha256:
                issues.append(
                    f"SHA-256 mismatch for {entry.path}: "
                    f"expected {entry.sha256}, got {actual_hash}"
                )
        if require_complete and directory.is_dir():
            actual = {
                path.relative_to(directory).as_posix()
                for path in directory.rglob("*")
                if path.is_file()
                and any(path.name.endswith(suffix) for suffix in input_suffixes)
            }
            for name in sorted(actual - expected - set(excluded_paths)):
                issues.append(f"unmanifested input: {name}")
        if issues:
            raise ChecksumVerificationError(issues)


def verify_manifest(
    manifest_path: Path | str,
    root: Path | str | None = None,
    *,
    input_suffixes: tuple[str, ...] = (".tsp", ".opt.tour"),
) -> ChecksumManifest:
    """Load and verify a checksum manifest; return it on success."""
    path = Path(manifest_path)
    manifest = ChecksumManifest.load(path)
    manifest.verify(
        root or path.parent,
        input_suffixes=input_suffixes,
        excluded_paths=(path.name,),
    )
    return manifest
