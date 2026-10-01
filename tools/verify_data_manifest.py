"""Verify every immutable benchmark input against its committed checksum."""

from __future__ import annotations

import argparse
from pathlib import Path

from bench.data_manifest import verify_manifest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "tsplib" / "SHA256SUMS.json"
BENCHMARK_MANIFEST = PROJECT_ROOT / "data" / "benchmarks" / "SHA256SUMS.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="*", type=Path)
    parser.add_argument("--root", type=Path)
    arguments = parser.parse_args(argv)
    manifests = arguments.manifest or [DEFAULT_MANIFEST, BENCHMARK_MANIFEST]
    total = 0
    for manifest_path in manifests:
        is_benchmark_config = manifest_path.resolve() == BENCHMARK_MANIFEST.resolve()
        manifest = verify_manifest(
            manifest_path,
            arguments.root,
            input_suffixes=(".json",) if is_benchmark_config else (".tsp", ".opt.tour"),
        )
        total += len(manifest.files)
    print(f"verified {total} benchmark inputs against SHA-256 manifests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
