"""Recorder API joining solver outputs to complete evidence provenance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from bench.evidence._json import FrozenJsonObject
from bench.evidence.bundle import EvidenceBundle, EvidenceRecord, write_bundle
from bench.evidence.provenance import capture_manifest
from bench.evidence.schema import EvidenceResult, RunBudget


def _enum_value(value: object) -> str:
    candidate = getattr(value, "value", value)
    return str(candidate)


def _budget(value: object | None) -> RunBudget:
    if value is None:
        return RunBudget()
    if isinstance(value, RunBudget):
        return value
    return RunBudget(
        wall_time_ms=getattr(value, "wall_time_ms", None),
        max_nodes=getattr(value, "max_nodes", None),
        max_memory_mb=getattr(value, "max_memory_mb", None),
    )


class EvidenceRunner:
    """Accumulates solver records and freezes them into one evidence bundle."""

    def __init__(
        self,
        repo_root: Path | str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._metadata = FrozenJsonObject.from_mapping(metadata)
        self._records: list[EvidenceRecord] = []

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def register(
        self,
        *,
        input_path: Path | str,
        matrix_hash: str,
        matrix_unit: str,
        solver_name: str,
        result: EvidenceResult,
        solver_config: Mapping[str, Any] | None = None,
        budget: RunBudget | object | None = None,
        seed: int | None = None,
        created_at_utc: str | None = None,
    ) -> EvidenceRecord:
        """Capture provenance and register one already-normalised result."""
        manifest = capture_manifest(
            repo_root=self._repo_root,
            input_path=input_path,
            matrix_hash=matrix_hash,
            matrix_unit=matrix_unit,
            solver_name=solver_name,
            solver_config=solver_config,
            budget=_budget(budget),
            seed=seed,
            created_at_utc=created_at_utc,
        )
        record = EvidenceRecord(manifest=manifest, result=result)
        self._records.append(record)
        return record

    def register_solve_report(
        self,
        report: object,
        *,
        input_path: Path | str,
        matrix_hash: str | None = None,
        matrix_unit: str | None = None,
        solver_config: Mapping[str, Any] | None = None,
        budget: RunBudget | object | None = None,
        seed: int | None = None,
        created_at_utc: str | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> EvidenceRecord:
        """Register a ``core.reporting.SolveReport`` without coupling to core.

        The adapter is intentionally duck-typed.  Future solvers can use the
        evidence package while ``bench`` remains independent of concrete solver
        implementations.
        """
        status = getattr(report, "status")
        objective_units = getattr(report, "objective_units")
        report_unit = _enum_value(objective_units)
        unit = matrix_unit or report_unit
        if unit != report_unit:
            raise ValueError(
                f"matrix_unit {unit!r} disagrees with report objective unit "
                f"{report_unit!r}"
            )
        report_matrix_hash = getattr(report, "distance_matrix_hash", None)
        if matrix_hash is None:
            matrix_hash = report_matrix_hash
        elif report_matrix_hash is not None and matrix_hash != report_matrix_hash:
            raise ValueError(
                "matrix_hash disagrees with SolveReport.distance_matrix_hash"
            )
        if matrix_hash is None:
            raise ValueError(
                "matrix_hash is required when SolveReport has no distance_matrix_hash"
            )
        report_seed = getattr(report, "seed", None)
        if seed is not None and report_seed is not None and seed != report_seed:
            raise ValueError("seed disagrees with SolveReport.seed")
        report_metrics: dict[str, Any] = {
            "bound_time_ms": getattr(report, "bound_time_ms", 0.0),
            "nodes_created": getattr(report, "nodes_created", 0),
            "nodes_explored": getattr(report, "nodes_explored", 0),
            "nodes_pruned": getattr(report, "nodes_pruned", 0),
            "peak_frontier": getattr(report, "peak_frontier", 0),
        }
        for attribute in (
            "solver_config_hash",
            "distance_matrix_hash",
            "hardware_id",
        ):
            value = getattr(report, attribute, None)
            if value is not None:
                report_metrics[f"report_{attribute}"] = value
        extra = getattr(report, "extra", None)
        if extra:
            report_metrics["report_extra"] = dict(extra)
        if metrics:
            report_metrics.update(metrics)
        result = EvidenceResult.create(
            problem_type=_enum_value(getattr(report, "problem_type")),
            status=_enum_value(status),
            stop_reason=_enum_value(getattr(report, "stop_reason")),
            feasible=bool(getattr(status, "is_feasible")),
            objective_value=getattr(report, "objective_value"),
            objective_unit=report_unit,
            best_lower_bound=getattr(report, "best_lower_bound", None),
            reference_value=getattr(report, "reference_value", None),
            reference_source=getattr(report, "reference_source", None),
            wall_time_ms=getattr(report, "wall_time_ms", 0.0),
            cpu_time_ms=getattr(report, "cpu_time_ms", 0.0),
            peak_memory_mb=getattr(report, "peak_memory_mb", None),
            metrics=report_metrics,
        )
        return self.register(
            input_path=input_path,
            matrix_hash=matrix_hash,
            matrix_unit=unit,
            solver_name=str(getattr(report, "solver_name")),
            solver_config=solver_config,
            budget=budget,
            seed=seed if seed is not None else report_seed,
            created_at_utc=created_at_utc,
            result=result,
        )

    def bundle(self) -> EvidenceBundle:
        return EvidenceBundle.create(self._records, metadata=self._metadata)

    def write(self, path: Path | str) -> EvidenceBundle:
        bundle = self.bundle()
        write_bundle(bundle, path)
        return bundle
