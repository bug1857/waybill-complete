"""Render human-readable reports solely from validated evidence bundles."""

from __future__ import annotations

import json
from pathlib import Path

from bench.evidence.bundle import EvidenceBundle, atomic_write_text


class ReportProvenanceError(ValueError):
    """Raised when a report is not the exact rendering of its claimed bundle."""


def _cell(value: object) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _json_cell(value: object) -> str:
    return _cell(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def render_markdown(bundle: EvidenceBundle) -> str:
    """Render every result and provenance field directly from ``bundle``.

    This function intentionally takes no title, summary, or result overrides.
    Fixed text provides labels only; every reported measurement and provenance
    value originates in the validated bundle.
    """
    lines = [
        "<!-- generated: do not edit; source is the evidence bundle -->",
        f"<!-- waybill-evidence-sha256: {bundle.content_hash} -->",
        "# Waybill evidence report",
        "",
        "This report is generated from a schema-validated, content-hashed evidence bundle.",
        "",
        f"Bundle schema: `{bundle.schema_version}`  ",
        f"Bundle SHA-256: `{bundle.content_hash}`",
        "",
        "## Solver results",
        "",
        "| Input | Problem | Solver | Status | Stop reason | Feasible | Objective | Lower bound | Reference | Wall time (ms) | Record SHA-256 |",
        "|---|---|---|---|---|:---:|---:|---:|---|---:|---|",
    ]
    for record in bundle.records:
        manifest = record.manifest
        result = record.result
        objective = (
            "—"
            if result.objective_value is None
            else f"{result.objective_value} {result.objective_unit}"
        )
        reference = (
            "—"
            if result.reference_value is None
            else f"{result.reference_value} {result.objective_unit} ({result.reference_source})"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(manifest.input_name),
                    _cell(result.problem_type),
                    _cell(manifest.solver_name),
                    _cell(result.status),
                    _cell(result.stop_reason),
                    "yes" if result.feasible else "no",
                    _cell(objective),
                    _cell(result.best_lower_bound),
                    _cell(reference),
                    _cell(result.wall_time_ms),
                    f"`{record.content_hash}`",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Provenance",
            "",
            "| Record | Timestamp (UTC) | Git revision | Dirty | Python | Platform | Input SHA-256 | Matrix SHA-256 | Matrix unit | Seed | Budget | Solver configuration | Metrics |",
            "|---|---|---|:---:|---|---|---|---|---|---:|---|---|---|",
        ]
    )
    for record in bundle.records:
        manifest = record.manifest
        result = record.result
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{record.content_hash}`",
                    _cell(manifest.created_at_utc),
                    f"`{manifest.git_revision}`",
                    "yes" if manifest.git_dirty else "no",
                    _cell(manifest.python_version),
                    _cell(manifest.platform),
                    f"`{manifest.input_sha256}`",
                    f"`{manifest.matrix_hash}`",
                    _cell(manifest.matrix_unit),
                    _cell(manifest.seed),
                    _json_cell(manifest.budget.to_dict()),
                    _json_cell(manifest.solver_config.to_dict()),
                    _json_cell(result.metrics.to_dict()),
                )
            )
            + " |"
        )

    if bundle.metadata:
        lines.extend(
            [
                "",
                "## Bundle metadata",
                "",
                "```json",
                json.dumps(
                    bundle.metadata.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                "```",
            ]
        )
    lines.extend(("", "_Generated from the bundle identified above; manual edits are not evidence._", ""))
    return "\n".join(lines)


def write_markdown_report(bundle: EvidenceBundle, path: Path | str) -> None:
    atomic_write_text(path, render_markdown(bundle))


def verify_markdown_report(bundle: EvidenceBundle, text: str) -> None:
    """Reject manual changes, including handwritten result numbers."""
    if text != render_markdown(bundle):
        raise ReportProvenanceError(
            "Markdown is not the exact generated rendering of evidence bundle "
            f"{bundle.content_hash}"
        )
