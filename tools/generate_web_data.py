"""Generate the web app's instance data from verified TSPLIB files.

The web UI must never carry hand-entered coordinates. A parallel implementation
of this project inlined them into source and had 17 of 52 wrong in one instance
-- correct for the first 35, then drifting, with the real file's tail absent
entirely. Scoring the genuine published optimal tour against that data gave
16,883 against a published 7,542.

So the TypeScript data file is a build artefact. It is generated here from the
same checksummed files in ``data/tsplib/`` that the Python test suite validates
against published optima, and it carries those checksums in its header. A test
asserts that regenerating produces an identical file, so a hand edit is caught.

    python -m tools.generate_web_data
"""

import hashlib
import sys
from pathlib import Path

from bench.tsplib.known_optima import PUBLISHED_OPTIMA
from bench.tsplib.parser import parse_problem, parse_tour
from core.eval.objective import closed_tour_cost

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tsplib"
OUT = ROOT / "reference" / "google-ui" / "src" / "data" / "instances.generated.ts"

#: Only coordinate-based instances are exported for now. EXPLICIT instances
#: (bayg29, gr17, ...) carry a matrix rather than geometry and are added once
#: the TypeScript side can represent one.
EXPORTED = ["eil51", "berlin52", "st70"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    blocks: list[str] = []
    header: list[str] = []

    for name in EXPORTED:
        tsp = DATA / f"{name}.tsp"
        tour_file = DATA / f"{name}.opt.tour"
        problem = parse_problem(tsp)
        instance = problem.to_instance()

        # Verify before exporting. A file that does not reproduce its published
        # optimum must not reach the UI.
        tour = parse_tour(tour_file)
        computed = closed_tour_cost(instance.matrix, tour)
        published = PUBLISHED_OPTIMA[name]
        if computed != published:
            sys.stderr.write(
                f"REFUSING TO EXPORT {name}: scoring its published optimal tour "
                f"gives {computed}, published is {published}.\n"
            )
            return 1

        header.append(f" *   {name:<10} n={problem.dimension:<4} "
                      f"opt={published:<8} sha256={sha256(tsp)[:16]}")

        coords = ",\n    ".join(
            f"[{c.x:g}, {c.y:g}]" for c in problem.coords
        )
        blocks.append(
            f"  {name}: {{\n"
            f"    name: {name!r},\n"
            f"    displayName: {problem.name + f' ({problem.dimension} stops)'!r},\n"
            f"    dimension: {problem.dimension},\n"
            f"    edgeWeightType: {problem.edge_weight_type.value!r},\n"
            f"    publishedOptimum: {published},\n"
            f"    source: 'TSPLIB95',\n"
            f"    coords: [\n    {coords},\n    ] as [number, number][],\n"
            f"  }},"
        )

    body = "\n".join(blocks)
    head = "\n".join(header)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f"""/**
 * GENERATED FILE -- DO NOT EDIT BY HAND.
 *
 * Produced by `python -m tools.generate_web_data` from the checksummed TSPLIB
 * files in data/tsplib/. Every instance below was verified before export: its
 * published optimal tour was scored with this project's own distance
 * implementation and matched the published optimum exactly.
 *
{head}
 *
 * Editing this file by hand will be caught by tests/test_web_data.py, which
 * regenerates it and compares.
 */

export interface TsplibInstanceData {{
  name: string;
  displayName: string;
  dimension: number;
  edgeWeightType: string;
  publishedOptimum: number;
  source: string;
  coords: [number, number][];
}}

export const TSPLIB_INSTANCES: Record<string, TsplibInstanceData> = {{
{body}
}};

export type TsplibInstanceName = keyof typeof TSPLIB_INSTANCES;
"""
    )
    sys.stdout.write(f"wrote {OUT.relative_to(ROOT)} ({len(EXPORTED)} verified instances)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
