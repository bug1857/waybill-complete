"""Benchmark fixtures are immutable inputs, not numbers typed into source."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from bench.data_manifest import (
    ChecksumManifest,
    ChecksumVerificationError,
    verify_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TSPLIB = PROJECT_ROOT / "data" / "tsplib"
CHECKSUMS = TSPLIB / "SHA256SUMS.json"
BENCHMARKS = PROJECT_ROOT / "data" / "benchmarks"
BENCHMARK_CHECKSUMS = BENCHMARKS / "SHA256SUMS.json"


def test_committed_tsplib_inputs_match_checksum_manifest():
    manifest = verify_manifest(CHECKSUMS)
    assert len(manifest.files) == 10
    assert {entry.path for entry in manifest.files} == {
        f"{name}{suffix}"
        for name in ("berlin52", "eil51", "kroA100", "pr76", "st70")
        for suffix in (".tsp", ".opt.tour")
    }


def test_committed_synthetic_benchmark_configs_match_checksum_manifest():
    manifest = verify_manifest(BENCHMARK_CHECKSUMS, input_suffixes=(".json",))
    assert {entry.path for entry in manifest.files} == {
        "clustered-cvrptw-150-v6-s240519.json",
        "exact-euclidean-n10-s17.json",
    }


def test_changed_input_fails_verification(tmp_path):
    destination = tmp_path / "tsplib"
    shutil.copytree(TSPLIB, destination)
    with (destination / "eil51.tsp").open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")

    with pytest.raises(ChecksumVerificationError) as caught:
        verify_manifest(destination / "SHA256SUMS.json")
    assert "eil51.tsp" in str(caught.value)
    assert "SHA-256 mismatch" in str(caught.value)


def test_missing_and_unmanifested_inputs_fail_verification(tmp_path):
    destination = tmp_path / "tsplib"
    shutil.copytree(TSPLIB, destination)
    (destination / "st70.opt.tour").unlink()
    (destination / "new-instance.tsp").write_text("EOF\n", encoding="utf-8")

    with pytest.raises(ChecksumVerificationError) as caught:
        verify_manifest(destination / "SHA256SUMS.json")
    assert "missing input: st70.opt.tour" in str(caught.value)
    assert "unmanifested input: new-instance.tsp" in str(caught.value)


def test_checksum_manifest_schema_is_strict():
    document = json.loads(CHECKSUMS.read_text(encoding="utf-8"))
    document["algorithm"] = "md5"
    with pytest.raises(ValueError, match="only sha256"):
        ChecksumManifest.from_dict(document)

    document["algorithm"] = "sha256"
    document["files"][0]["unknown"] = 1
    with pytest.raises(ValueError, match="unknown"):
        ChecksumManifest.from_dict(document)
