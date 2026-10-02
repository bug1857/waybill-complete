"""Command-line entry point for evidence recording, validation, and rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from bench.data_manifest import verify_manifest
from bench.evidence.bundle import EvidenceBundle
from bench.evidence.report import write_markdown_report
from bench.evidence.runner import EvidenceRunner
from bench.evidence.schema import EvidenceResult, RunBudget


def _json_object(text: str) -> Mapping[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return value


def _record(arguments: argparse.Namespace) -> int:
    objective_unit = arguments.objective_unit
    if objective_unit is None and arguments.objective is not None:
        objective_unit = arguments.matrix_unit
    result = EvidenceResult.create(
        problem_type=arguments.problem_type,
        status=arguments.status,
        stop_reason=arguments.stop_reason,
        feasible=arguments.feasible,
        objective_value=arguments.objective,
        objective_unit=objective_unit,
        best_lower_bound=arguments.lower_bound,
        reference_value=arguments.reference_value,
        reference_source=arguments.reference_source,
        wall_time_ms=arguments.wall_time_ms,
        cpu_time_ms=arguments.cpu_time_ms,
        peak_memory_mb=arguments.peak_memory_mb,
        metrics=arguments.metrics,
    )
    runner = EvidenceRunner(arguments.repo_root, metadata=arguments.bundle_metadata)
    runner.register(
        input_path=arguments.input,
        matrix_hash=arguments.matrix_hash,
        matrix_unit=arguments.matrix_unit,
        solver_name=arguments.solver,
        solver_config=arguments.solver_config,
        budget=RunBudget(
            wall_time_ms=arguments.budget_wall_time_ms,
            max_nodes=arguments.budget_max_nodes,
            max_memory_mb=arguments.budget_max_memory_mb,
        ),
        seed=arguments.seed,
        result=result,
    )
    bundle = runner.write(arguments.output)
    print(f"wrote {arguments.output} ({bundle.content_hash})")
    return 0


def _validate(arguments: argparse.Namespace) -> int:
    bundle = EvidenceBundle.read(arguments.bundle)
    print(
        f"valid: {arguments.bundle} "
        f"({len(bundle.records)} records, {bundle.content_hash})"
    )
    return 0


def _render(arguments: argparse.Namespace) -> int:
    bundle = EvidenceBundle.read(arguments.bundle)
    write_markdown_report(bundle, arguments.output)
    print(f"wrote {arguments.output} from {bundle.content_hash}")
    return 0


def _verify_data(arguments: argparse.Namespace) -> int:
    manifest = verify_manifest(arguments.manifest, arguments.root)
    print(f"verified {len(manifest.files)} benchmark inputs")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bench.evidence",
        description="Create, validate, and render Waybill evidence bundles.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser(
        "record", help="record one externally produced solver result"
    )
    record.add_argument("--repo-root", type=Path, default=Path.cwd())
    record.add_argument("--input", type=Path, required=True)
    record.add_argument("--matrix-hash", required=True)
    record.add_argument("--matrix-unit", required=True)
    record.add_argument(
        "--objective-unit",
        help="defaults to --matrix-unit; omit only when objective is absent",
    )
    record.add_argument("--solver", required=True)
    record.add_argument(
        "--problem-type", choices=("TSP", "CVRP", "CVRPTW"), required=True
    )
    record.add_argument("--status", required=True)
    record.add_argument("--stop-reason", required=True)
    record.add_argument("--objective", type=int)
    record.add_argument("--lower-bound", type=int)
    record.add_argument("--reference-value", type=int)
    record.add_argument("--reference-source")
    record.add_argument("--wall-time-ms", type=float, default=0.0)
    record.add_argument("--cpu-time-ms", type=float, default=0.0)
    record.add_argument("--peak-memory-mb", type=float)
    record.add_argument("--seed", type=int)
    record.add_argument("--feasible", action=argparse.BooleanOptionalAction, default=True)
    record.add_argument("--solver-config", type=_json_object, default={})
    record.add_argument("--metrics", type=_json_object, default={})
    record.add_argument("--bundle-metadata", type=_json_object, default={})
    record.add_argument("--budget-wall-time-ms", type=int)
    record.add_argument("--budget-max-nodes", type=int)
    record.add_argument("--budget-max-memory-mb", type=int)
    record.add_argument("--output", type=Path, required=True)
    record.set_defaults(handler=_record)

    validate = subparsers.add_parser(
        "validate", help="validate a bundle schema and content hash"
    )
    validate.add_argument("bundle", type=Path)
    validate.set_defaults(handler=_validate)

    render = subparsers.add_parser(
        "render", help="generate Markdown exclusively from a valid bundle"
    )
    render.add_argument("bundle", type=Path)
    render.add_argument("--output", type=Path, required=True)
    render.set_defaults(handler=_render)

    verify_data = subparsers.add_parser(
        "verify-data", help="verify benchmark input checksums"
    )
    verify_data.add_argument(
        "--manifest", type=Path, default=Path("data/tsplib/SHA256SUMS.json")
    )
    verify_data.add_argument("--root", type=Path)
    verify_data.set_defaults(handler=_verify_data)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":  # pragma: no cover - exercised through CLI invocation
    raise SystemExit(main())
