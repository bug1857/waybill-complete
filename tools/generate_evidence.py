"""Generate the release evidence bundle and the static demo payload."""

from __future__ import annotations

import json
import argparse
from dataclasses import replace
from pathlib import Path

from bench.evidence import EvidenceRunner, write_markdown_report
from bench.evidence.provenance import capture_git_state
from bench.generators import clustered_cvrptw_150, random_euclidean_tsp
from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem
from core.construct import ClarkeWrightSolver, NearestNeighborSolver
from core.exact import BranchAndBoundSolver, BruteForceSolver, HeldKarpSolver
from core.solver import UNLIMITED

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARTIFACTS = ROOT / "artifacts"
WEB = ROOT / "web"


def _config(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _register(runner: EvidenceRunner, report, input_path: Path, *, config: dict[str, object]) -> None:
    runner.register_solve_report(
        report,
        input_path=input_path,
        solver_config=config,
        budget=UNLIMITED,
        seed=config.get("seed") if isinstance(config.get("seed"), int) else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="require a clean committed source tree")
    args = parser.parse_args()
    if args.release and capture_git_state(ROOT).dirty:
        parser.error("release evidence requires a clean committed source tree")
    exact_path = DATA / "benchmarks" / "exact-euclidean-n10-s17.json"
    fleet_path = DATA / "benchmarks" / "clustered-cvrptw-150-v6-s240519.json"
    exact_config = _config(exact_path)
    fleet_config = _config(fleet_path)
    exact = random_euclidean_tsp(
        int(exact_config["nodes"]),
        int(exact_config["seed"]),
        float(exact_config["span"]),
        str(exact_config["name"]),
    )
    eil_path = DATA / "tsplib" / "eil51.tsp"
    eil = parse_problem(eil_path).to_instance()
    fleet = clustered_cvrptw_150(int(fleet_config["seed"]))

    runner = EvidenceRunner(
        ROOT,
        metadata={
            "purpose": "release evidence and static demo" if args.release else "development evidence and static demo",
            "scope": "exact validation, heuristic reference, and CVRPTW feasibility",
        },
    )
    exact_solver_config = {"instance_config": exact_config}
    for solver in (BruteForceSolver(), HeldKarpSolver(), BranchAndBoundSolver(), NearestNeighborSolver()):
        _, report = solver.solve(exact)
        _register(runner, report, exact_path, config={**exact_solver_config, "solver": solver.name})

    _, report = NearestNeighborSolver().solve(eil)
    report = replace(
        report,
        reference_value=PUBLISHED_OPTIMA["eil51"],
        reference_source="TSPLIB95 published optimum",
    )
    _register(
        runner,
        report,
        eil_path,
        config={"instance": "eil51", "reference": "TSPLIB95 published optimum"},
    )

    _, report = ClarkeWrightSolver().solve(fleet)
    _register(runner, report, fleet_path, config={"instance_config": fleet_config})

    if args.release and capture_git_state(ROOT).dirty:
        parser.error("source tree changed during release evidence generation")
    ARTIFACTS.mkdir(exist_ok=True)
    bundle = runner.write(ARTIFACTS / "evidence.json")
    write_markdown_report(bundle, ROOT / "report" / "results.md")
    WEB.mkdir(exist_ok=True)
    payload = (ARTIFACTS / "evidence.json").read_text(encoding="utf-8")
    (WEB / "evidence.js").write_text(
        f"window.WAYBILL_EVIDENCE = {payload};\n",
        encoding="utf-8",
    )
    print(f"wrote {ARTIFACTS / 'evidence.json'} ({bundle.content_hash})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
