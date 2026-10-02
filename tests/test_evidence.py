"""Evidence must be reproducible, immutable, strict, and tamper evident."""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from bench.evidence import (
    EvidenceBundle,
    EvidenceIntegrityError,
    EvidenceManifest,
    EvidenceRecord,
    EvidenceResult,
    EvidenceRunner,
    ReportProvenanceError,
    RunBudget,
    capture_git_state,
    render_markdown,
    verify_markdown_report,
    write_bundle,
)


REVISION = "a" * 40
INPUT_SHA = "b" * 64
MATRIX_SHA = "c" * 64
TIMESTAMP = "2026-08-30T04:00:00.000000Z"


def manifest(**overrides) -> EvidenceManifest:
    values = {
        "created_at_utc": TIMESTAMP,
        "git_revision": REVISION,
        "git_dirty": False,
        "python_version": "3.13.7",
        "platform": "TestOS-1-arm64",
        "input_name": "data/tsplib/example.tsp",
        "input_sha256": INPUT_SHA,
        "matrix_hash": MATRIX_SHA,
        "matrix_unit": "tsplib",
        "solver_name": "test-solver",
        "solver_config": {"alpha": 1, "nested": {"enabled": True}},
        "budget": RunBudget(wall_time_ms=5000, max_nodes=200),
        "seed": 1857,
    }
    values.update(overrides)
    return EvidenceManifest.create(**values)


def result(**overrides) -> EvidenceResult:
    values = {
        "problem_type": "TSP",
        "status": "PROVEN_OPTIMAL_TSP",
        "stop_reason": "optimal",
        "feasible": True,
        "objective_value": 987_654_321,
        "objective_unit": "tsplib",
        "best_lower_bound": 987_654_321,
        "wall_time_ms": 123.75,
        "cpu_time_ms": 120.5,
        "metrics": {"nodes_explored": 4321},
    }
    values.update(overrides)
    return EvidenceResult.create(**values)


def bundle(**manifest_overrides) -> EvidenceBundle:
    record = EvidenceRecord(manifest(**manifest_overrides), result())
    return EvidenceBundle.create([record], metadata={"experiment": "determinism"})


def test_serialization_is_deterministic_and_order_independent():
    config_a = {"zeta": [3, 2, 1], "alpha": {"b": False, "a": None}}
    config_b = {"alpha": {"a": None, "b": False}, "zeta": [3, 2, 1]}
    first = bundle(solver_config=config_a)
    second = bundle(solver_config=config_b)

    assert first.to_json() == second.to_json()
    assert first.content_hash == second.content_hash
    assert EvidenceBundle.from_json(first.to_json()) == first
    assert first.to_json().endswith("\n")


def test_manifest_copies_mutable_configuration():
    config = {"strategy": {"weights": [1, 2]}}
    captured = manifest(solver_config=config)
    before = captured.to_dict()
    config["strategy"]["weights"].append(999)
    assert captured.to_dict() == before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("input_sha256", "not-a-hash", "SHA-256"),
        ("matrix_hash", "0" * 63, "SHA-256"),
        ("git_revision", "dirty", "git_revision"),
        ("created_at_utc", "2026-08-30", "end in 'Z'"),
        ("input_name", "../outside.tsp", "relative POSIX"),
    ],
)
def test_manifest_schema_rejects_invalid_values(field, value, message):
    with pytest.raises((TypeError, ValueError), match=message):
        manifest(**{field: value})


def test_strict_loader_rejects_missing_and_unknown_fields():
    data = manifest().to_dict()
    data["surprise"] = True
    with pytest.raises(ValueError, match="unknown"):
        EvidenceManifest.from_dict(data)

    del data["surprise"]
    del data["seed"]
    with pytest.raises(ValueError, match="missing"):
        EvidenceManifest.from_dict(data)


def test_result_schema_rejects_overclaimed_and_contradictory_statuses():
    with pytest.raises(ValueError, match="lower bound equal"):
        result(best_lower_bound=987_654_320)
    with pytest.raises(ValueError, match="problem_type=TSP"):
        result(problem_type="CVRPTW")
    with pytest.raises(ValueError, match="stop_reason=optimal"):
        result(stop_reason="completed")
    with pytest.raises(ValueError, match="HEURISTIC_INFEASIBLE requires"):
        result(
            status="HEURISTIC_INFEASIBLE",
            stop_reason="infeasible",
            feasible=True,
            best_lower_bound=None,
        )
    partial = result(
        problem_type="CVRPTW",
        status="HEURISTIC_PARTIAL",
        stop_reason="timeout",
        feasible=False,
        best_lower_bound=None,
    )
    assert partial.feasible is False
    with pytest.raises(ValueError, match="interruption stop reason"):
        result(
            problem_type="CVRPTW",
            status="HEURISTIC_PARTIAL",
            stop_reason="completed",
            feasible=False,
            best_lower_bound=None,
        )
    with pytest.raises(ValueError, match="cannot carry a reference"):
        result(
            problem_type="CVRPTW",
            status="HEURISTIC_PARTIAL",
            stop_reason="timeout",
            feasible=False,
            best_lower_bound=None,
            reference_value=100,
            reference_source="baseline",
        )

def test_bundle_rejects_tampering_and_duplicate_keys():
    original = bundle()
    document = json.loads(original.to_json())
    document["records"][0]["result"]["metrics"]["nodes_explored"] += 1
    with pytest.raises(EvidenceIntegrityError, match="hash mismatch"):
        EvidenceBundle.from_json(json.dumps(document))

    duplicate = original.to_json().replace(
        '"metadata": {', '"metadata": {}, "metadata": {', 1
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        EvidenceBundle.from_json(duplicate)


def test_bundle_write_is_atomic_and_round_trips(tmp_path):
    destination = tmp_path / "nested" / "evidence.json"
    expected = bundle()
    returned_hash = write_bundle(expected, destination)
    assert returned_hash == expected.content_hash
    assert EvidenceBundle.read(destination) == expected
    assert list(destination.parent.glob(".evidence.json.*.tmp")) == []


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _clean_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    source = repo / "input.txt"
    source.write_text("input\n", encoding="utf-8")
    _git(repo, "add", "input.txt")
    _git(
        repo,
        "-c",
        "user.name=Evidence Test",
        "-c",
        "user.email=evidence@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    return repo


def test_git_provenance_detects_tracked_and_untracked_dirtiness(tmp_path):
    repo = _clean_git_repo(tmp_path)
    clean = capture_git_state(repo)
    assert clean.revision == _git(repo, "rev-parse", "HEAD")
    assert clean.dirty is False

    (repo / "input.txt").write_text("changed\n", encoding="utf-8")
    assert capture_git_state(repo).dirty is True

    _git(repo, "restore", "input.txt")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    assert capture_git_state(repo).dirty is True


def test_runner_registers_existing_solve_report_without_core_coupling(tmp_path):
    repo = _clean_git_repo(tmp_path)
    status = SimpleNamespace(value="PROVEN_OPTIMAL_TSP", is_feasible=True)
    report = SimpleNamespace(
        solver_name="future-held-karp",
        problem_type=SimpleNamespace(value="TSP"),
        status=status,
        stop_reason=SimpleNamespace(value="optimal"),
        objective_value=73,
        objective_units=SimpleNamespace(value="tsplib"),
        best_lower_bound=73,
        reference_value=None,
        reference_source=None,
        wall_time_ms=1.25,
        cpu_time_ms=1.0,
        peak_memory_mb=None,
        nodes_created=9,
        nodes_explored=8,
        nodes_pruned=1,
        peak_frontier=2,
        bound_time_ms=0.1,
        seed=7,
        extra={},
    )
    runner = EvidenceRunner(repo, metadata={"suite": "phase-2"})
    runner.register_solve_report(
        report,
        input_path=repo / "input.txt",
        matrix_hash="d" * 64,
        budget=RunBudget(max_nodes=10),
        created_at_utc=TIMESTAMP,
    )
    recorded = runner.bundle().records[0]
    assert recorded.manifest.solver_name == "future-held-karp"
    assert recorded.manifest.git_dirty is False
    assert recorded.result.objective_value == 73
    assert recorded.result.metrics.to_dict()["nodes_pruned"] == 1


def test_report_contains_only_bundle_results_and_explicit_provenance():
    evidence = bundle()
    markdown = render_markdown(evidence)

    # The renderer has no result/title override channel: measurements come from bundle.
    assert list(inspect.signature(render_markdown).parameters) == ["bundle"]
    assert str(evidence.records[0].result.objective_value) in markdown
    assert str(evidence.records[0].result.wall_time_ms) in markdown
    assert evidence.content_hash in markdown
    assert evidence.records[0].content_hash in markdown
    assert INPUT_SHA in markdown
    assert MATRIX_SHA in markdown
    assert REVISION in markdown
    assert "generated: do not edit" in markdown

    changed_result = result(objective_value=987_654_322, best_lower_bound=987_654_322)
    changed = EvidenceBundle.create(
        [EvidenceRecord(manifest(), changed_result)],
        metadata={"experiment": "determinism"},
    )
    changed_markdown = render_markdown(changed)
    assert "987654322" in changed_markdown
    assert "987654321" not in changed_markdown

    verify_markdown_report(evidence, markdown)
    handwritten = markdown.replace("987654321", "42", 1)
    with pytest.raises(ReportProvenanceError, match="not the exact generated rendering"):
        verify_markdown_report(evidence, handwritten)
