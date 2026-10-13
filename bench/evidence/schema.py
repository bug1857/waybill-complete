"""Immutable, strict schema for Waybill evidence records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Mapping

from bench.evidence._json import (
    FrozenJsonObject,
    require_bool,
    require_exact_keys,
    require_number,
    require_optional_int,
    require_optional_number,
    require_string,
)

SCHEMA_VERSION = "1.0.0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_REVISION = re.compile(r"[0-9a-f]{40,64}\Z")
_STATUSES = {
    "PROVEN_OPTIMAL_TSP",
    "EXACT_TIMEOUT_WITH_INCUMBENT",
    "HEURISTIC_FEASIBLE_TSP",
    "HEURISTIC_FEASIBLE_CVRPTW",
    "HEURISTIC_INFEASIBLE",
    "HEURISTIC_PARTIAL",
    "REFERENCE_GAP_ONLY",
}
_STOP_REASONS = {
    "optimal",
    "timeout",
    "node_cap",
    "memory_cap",
    "infeasible",
    "cancelled",
    "completed",
}
_INTERRUPTIONS = {"timeout", "node_cap", "memory_cap", "cancelled"}


def utc_timestamp(now: datetime | None = None) -> str:
    """Return an RFC 3339 UTC timestamp with deterministic microsecond precision."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("timestamp source must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def _validate_timestamp(value: str) -> None:
    if not value.endswith("Z"):
        raise ValueError("created_at_utc must use UTC and end in 'Z'")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"created_at_utc is not RFC 3339: {value!r}") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("created_at_utc must use UTC")


def validate_sha256(value: str, *, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase 64-character SHA-256")


def _validate_relative_name(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or not value or ".." in path.parts or "." in path.parts:
        raise ValueError("input_name must be a normalised relative POSIX path")


@dataclass(frozen=True, slots=True)
class RunBudget:
    """The limits under which one solver result was produced."""

    wall_time_ms: int | None = None
    max_nodes: int | None = None
    max_memory_mb: int | None = None

    def __post_init__(self) -> None:
        for field in ("wall_time_ms", "max_nodes", "max_memory_mb"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
            ):
                raise ValueError(f"budget.{field} must be a positive integer or null")

    def to_dict(self) -> dict[str, int | None]:
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_nodes": self.max_nodes,
            "wall_time_ms": self.wall_time_ms,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RunBudget":
        data = require_exact_keys(
            value,
            {"wall_time_ms", "max_nodes", "max_memory_mb"},
            location="manifest.budget",
        )
        return cls(
            wall_time_ms=require_optional_int(
                data["wall_time_ms"], location="manifest.budget.wall_time_ms"
            ),
            max_nodes=require_optional_int(
                data["max_nodes"], location="manifest.budget.max_nodes"
            ),
            max_memory_mb=require_optional_int(
                data["max_memory_mb"], location="manifest.budget.max_memory_mb"
            ),
        )


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    """Complete provenance for one solver invocation.

    All values are immutable.  In particular, ``solver_config`` is copied into
    canonical JSON at construction, preventing post-run mutation.
    """

    schema_version: str
    created_at_utc: str
    git_revision: str
    git_dirty: bool
    python_version: str
    platform: str
    input_name: str
    input_sha256: str
    matrix_hash: str
    matrix_unit: str
    solver_name: str
    solver_config: FrozenJsonObject
    budget: RunBudget
    seed: int | None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported manifest schema {self.schema_version!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )
        _validate_timestamp(self.created_at_utc)
        if not _GIT_REVISION.fullmatch(self.git_revision):
            raise ValueError("git_revision must be a lowercase 40-64 character hash")
        if type(self.git_dirty) is not bool:
            raise TypeError("git_dirty must be a boolean")
        for field in (
            "python_version",
            "platform",
            "input_name",
            "matrix_unit",
            "solver_name",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        _validate_relative_name(self.input_name)
        validate_sha256(self.input_sha256, field="input_sha256")
        validate_sha256(self.matrix_hash, field="matrix_hash")
        if not isinstance(self.solver_config, FrozenJsonObject):
            raise TypeError("solver_config must be a FrozenJsonObject")
        if not isinstance(self.budget, RunBudget):
            raise TypeError("budget must be a RunBudget")
        if self.seed is not None and (
            not isinstance(self.seed, int) or isinstance(self.seed, bool)
        ):
            raise TypeError("seed must be an integer or null")

    @classmethod
    def create(
        cls,
        *,
        created_at_utc: str,
        git_revision: str,
        git_dirty: bool,
        python_version: str,
        platform: str,
        input_name: str,
        input_sha256: str,
        matrix_hash: str,
        matrix_unit: str,
        solver_name: str,
        solver_config: Mapping[str, Any] | FrozenJsonObject | None = None,
        budget: RunBudget | None = None,
        seed: int | None = None,
        schema_version: str = SCHEMA_VERSION,
    ) -> "EvidenceManifest":
        return cls(
            schema_version=schema_version,
            created_at_utc=created_at_utc,
            git_revision=git_revision,
            git_dirty=git_dirty,
            python_version=python_version,
            platform=platform,
            input_name=input_name,
            input_sha256=input_sha256,
            matrix_hash=matrix_hash,
            matrix_unit=matrix_unit,
            solver_name=solver_name,
            solver_config=FrozenJsonObject.from_mapping(solver_config),
            budget=budget or RunBudget(),
            seed=seed,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "budget": self.budget.to_dict(),
            "created_at_utc": self.created_at_utc,
            "git_dirty": self.git_dirty,
            "git_revision": self.git_revision,
            "input_name": self.input_name,
            "input_sha256": self.input_sha256,
            "matrix_hash": self.matrix_hash,
            "matrix_unit": self.matrix_unit,
            "platform": self.platform,
            "python_version": self.python_version,
            "schema_version": self.schema_version,
            "seed": self.seed,
            "solver_config": self.solver_config.to_dict(),
            "solver_name": self.solver_name,
        }

    @classmethod
    def from_dict(cls, value: object) -> "EvidenceManifest":
        fields = {
            "schema_version",
            "created_at_utc",
            "git_revision",
            "git_dirty",
            "python_version",
            "platform",
            "input_name",
            "input_sha256",
            "matrix_hash",
            "matrix_unit",
            "solver_name",
            "solver_config",
            "budget",
            "seed",
        }
        data = require_exact_keys(value, fields, location="manifest")
        return cls.create(
            schema_version=require_string(
                data["schema_version"], location="manifest.schema_version"
            ),
            created_at_utc=require_string(
                data["created_at_utc"], location="manifest.created_at_utc"
            ),
            git_revision=require_string(
                data["git_revision"], location="manifest.git_revision"
            ),
            git_dirty=require_bool(data["git_dirty"], location="manifest.git_dirty"),
            python_version=require_string(
                data["python_version"], location="manifest.python_version"
            ),
            platform=require_string(data["platform"], location="manifest.platform"),
            input_name=require_string(
                data["input_name"], location="manifest.input_name"
            ),
            input_sha256=require_string(
                data["input_sha256"], location="manifest.input_sha256"
            ),
            matrix_hash=require_string(
                data["matrix_hash"], location="manifest.matrix_hash"
            ),
            matrix_unit=require_string(
                data["matrix_unit"], location="manifest.matrix_unit"
            ),
            solver_name=require_string(
                data["solver_name"], location="manifest.solver_name"
            ),
            solver_config=FrozenJsonObject.from_value(
                data["solver_config"], location="manifest.solver_config"
            ),
            budget=RunBudget.from_dict(data["budget"]),
            seed=require_optional_int(data["seed"], location="manifest.seed"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    """Measured output from one solver invocation."""

    problem_type: str
    status: str
    stop_reason: str
    feasible: bool
    objective_value: int | None
    objective_unit: str | None
    best_lower_bound: int | None = None
    reference_value: int | None = None
    reference_source: str | None = None
    wall_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_mb: float | None = None
    metrics: FrozenJsonObject = FrozenJsonObject("{}")

    def __post_init__(self) -> None:
        for field in ("problem_type", "status", "stop_reason"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"result.{field} must be a non-empty string")
        if self.problem_type not in {"TSP", "CVRP", "CVRPTW"}:
            raise ValueError("result.problem_type must be TSP, CVRP, or CVRPTW")
        if self.status not in _STATUSES:
            raise ValueError(f"result.status is not supported by schema v1: {self.status}")
        if self.stop_reason not in _STOP_REASONS:
            raise ValueError(
                f"result.stop_reason is not supported by schema v1: {self.stop_reason}"
            )
        if type(self.feasible) is not bool:
            raise TypeError("result.feasible must be a boolean")
        for field in ("objective_value", "best_lower_bound", "reference_value"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise ValueError(f"result.{field} must be a non-negative integer or null")
        if (self.objective_value is None) != (self.objective_unit is None):
            raise ValueError("objective_value and objective_unit must be present together")
        if self.objective_unit is not None and (
            not isinstance(self.objective_unit, str) or not self.objective_unit.strip()
        ):
            raise ValueError("objective_unit must be a non-empty string or null")
        if self.best_lower_bound is not None and self.objective_value is None:
            raise ValueError("best_lower_bound requires objective_value")
        if (
            self.best_lower_bound is not None
            and self.objective_value is not None
            and self.best_lower_bound > self.objective_value
        ):
            raise ValueError("best_lower_bound cannot exceed objective_value")
        if (self.reference_value is None) != (self.reference_source is None):
            raise ValueError("reference_value and reference_source must be present together")
        if self.reference_source is not None and (
            not isinstance(self.reference_source, str) or not self.reference_source.strip()
        ):
            raise ValueError("reference_source must be a non-empty string or null")
        for field in ("wall_time_ms", "cpu_time_ms", "peak_memory_mb"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not float("-inf") < float(value) < float("inf")
                or value < 0
            ):
                raise ValueError(f"result.{field} must be a finite non-negative number")
            if value is not None:
                object.__setattr__(self, field, float(value))
        if not isinstance(self.metrics, FrozenJsonObject):
            raise TypeError("metrics must be a FrozenJsonObject")

        self._validate_claim_discipline()

    def _validate_claim_discipline(self) -> None:
        """Make overclaimed or internally contradictory evidence unconstructable."""
        if self.status == "PROVEN_OPTIMAL_TSP":
            if self.problem_type != "TSP":
                raise ValueError("PROVEN_OPTIMAL_TSP requires problem_type=TSP")
            if self.stop_reason != "optimal":
                raise ValueError("PROVEN_OPTIMAL_TSP requires stop_reason=optimal")
            if not self.feasible or self.objective_value is None:
                raise ValueError("PROVEN_OPTIMAL_TSP requires a feasible objective")
            if self.best_lower_bound != self.objective_value:
                raise ValueError(
                    "PROVEN_OPTIMAL_TSP requires lower bound equal to objective"
                )
        elif self.stop_reason == "optimal":
            raise ValueError("stop_reason=optimal requires PROVEN_OPTIMAL_TSP")

        if self.status == "EXACT_TIMEOUT_WITH_INCUMBENT":
            if self.problem_type != "TSP":
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT requires problem_type=TSP"
                )
            if self.stop_reason not in _INTERRUPTIONS:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT requires an interruption reason"
                )
            if not self.feasible or self.objective_value is None:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT requires a feasible incumbent"
                )
            if self.best_lower_bound is None:
                raise ValueError(
                    "EXACT_TIMEOUT_WITH_INCUMBENT requires a valid lower bound"
                )
            if self.best_lower_bound == self.objective_value:
                raise ValueError(
                    "equal objective and lower bound is proven; use PROVEN_OPTIMAL_TSP"
                )

        expected_problem = {
            "HEURISTIC_FEASIBLE_TSP": "TSP",
            "HEURISTIC_FEASIBLE_CVRPTW": "CVRPTW",
        }.get(self.status)
        if expected_problem is not None:
            if self.problem_type != expected_problem:
                raise ValueError(
                    f"{self.status} requires problem_type={expected_problem}"
                )
            if not self.feasible or self.objective_value is None:
                raise ValueError(f"{self.status} requires a feasible objective")

        if self.status == "HEURISTIC_INFEASIBLE":
            if self.feasible or self.stop_reason != "infeasible":
                raise ValueError(
                    "HEURISTIC_INFEASIBLE requires feasible=false and "
                    "stop_reason=infeasible"
                )
        elif self.stop_reason == "infeasible":
            raise ValueError(
                "stop_reason=infeasible requires status=HEURISTIC_INFEASIBLE"
            )

        if self.status == "HEURISTIC_PARTIAL":
            if self.feasible:
                raise ValueError("HEURISTIC_PARTIAL requires feasible=false")
            if self.stop_reason not in _INTERRUPTIONS:
                raise ValueError(
                    "HEURISTIC_PARTIAL requires an interruption stop reason"
                )

        if not self.feasible and self.reference_value is not None:
            raise ValueError(
                "non-feasible evidence cannot carry a reference comparison"
            )

        if self.status == "REFERENCE_GAP_ONLY":
            if not self.feasible or self.objective_value is None:
                raise ValueError("REFERENCE_GAP_ONLY requires a feasible objective")
            if self.reference_value is None:
                raise ValueError("REFERENCE_GAP_ONLY requires a named reference")

    @classmethod
    def create(
        cls,
        *,
        problem_type: str,
        status: str,
        stop_reason: str,
        feasible: bool,
        objective_value: int | None,
        objective_unit: str | None,
        best_lower_bound: int | None = None,
        reference_value: int | None = None,
        reference_source: str | None = None,
        wall_time_ms: float = 0.0,
        cpu_time_ms: float = 0.0,
        peak_memory_mb: float | None = None,
        metrics: Mapping[str, Any] | FrozenJsonObject | None = None,
    ) -> "EvidenceResult":
        return cls(
            problem_type=problem_type,
            status=status,
            stop_reason=stop_reason,
            feasible=feasible,
            objective_value=objective_value,
            objective_unit=objective_unit,
            best_lower_bound=best_lower_bound,
            reference_value=reference_value,
            reference_source=reference_source,
            wall_time_ms=wall_time_ms,
            cpu_time_ms=cpu_time_ms,
            peak_memory_mb=peak_memory_mb,
            metrics=FrozenJsonObject.from_mapping(metrics),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "best_lower_bound": self.best_lower_bound,
            "cpu_time_ms": self.cpu_time_ms,
            "feasible": self.feasible,
            "metrics": self.metrics.to_dict(),
            "objective_unit": self.objective_unit,
            "objective_value": self.objective_value,
            "peak_memory_mb": self.peak_memory_mb,
            "problem_type": self.problem_type,
            "reference_source": self.reference_source,
            "reference_value": self.reference_value,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "wall_time_ms": self.wall_time_ms,
        }

    @classmethod
    def from_dict(cls, value: object) -> "EvidenceResult":
        fields = {
            "status",
            "problem_type",
            "stop_reason",
            "feasible",
            "objective_value",
            "objective_unit",
            "best_lower_bound",
            "reference_value",
            "reference_source",
            "wall_time_ms",
            "cpu_time_ms",
            "peak_memory_mb",
            "metrics",
        }
        data = require_exact_keys(value, fields, location="result")
        objective_unit = data["objective_unit"]
        reference_source = data["reference_source"]
        return cls.create(
            problem_type=require_string(
                data["problem_type"], location="result.problem_type"
            ),
            status=require_string(data["status"], location="result.status"),
            stop_reason=require_string(
                data["stop_reason"], location="result.stop_reason"
            ),
            feasible=require_bool(data["feasible"], location="result.feasible"),
            objective_value=require_optional_int(
                data["objective_value"], location="result.objective_value"
            ),
            objective_unit=(
                None
                if objective_unit is None
                else require_string(objective_unit, location="result.objective_unit")
            ),
            best_lower_bound=require_optional_int(
                data["best_lower_bound"], location="result.best_lower_bound"
            ),
            reference_value=require_optional_int(
                data["reference_value"], location="result.reference_value"
            ),
            reference_source=(
                None
                if reference_source is None
                else require_string(
                    reference_source, location="result.reference_source"
                )
            ),
            wall_time_ms=require_number(
                data["wall_time_ms"], location="result.wall_time_ms"
            ),
            cpu_time_ms=require_number(
                data["cpu_time_ms"], location="result.cpu_time_ms"
            ),
            peak_memory_mb=require_optional_number(
                data["peak_memory_mb"], location="result.peak_memory_mb"
            ),
            metrics=FrozenJsonObject.from_value(
                data["metrics"], location="result.metrics"
            ),
        )
