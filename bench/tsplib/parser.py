"""TSPLIB file parsing.

Lives in ``bench/`` rather than ``core/`` because it reads files, and ``core/``
touches no disk. The distance *formulas* it relies on are pure and live in
``core/distance/conventions.py``.

Real TSPLIB files are inconsistent about header punctuation -- ``NAME: berlin52``
and ``NAME : eil51`` both occur in the official archive, sometimes within the same
directory -- so the header parser is deliberately permissive about whitespace
around the colon while remaining strict about the keywords themselves.
"""

from dataclasses import dataclass
from pathlib import Path

from core.distance.conventions import EdgeWeightType, distance_function
from core.distance.matrix import DistanceMatrix
from core.model.geometry import Coord
from core.model.instance import Instance
from core.model.stop import Stop
from core.model.units import Unit


@dataclass(frozen=True, slots=True)
class TsplibProblem:
    name: str
    dimension: int
    edge_weight_type: EdgeWeightType
    coords: tuple[Coord, ...]
    comment: str = ""

    def to_instance(self) -> Instance:
        """Build a single-vehicle TSP instance using this file's own convention."""
        fn = distance_function(self.edge_weight_type)
        matrix = DistanceMatrix.from_coords(self.coords, fn, Unit.TSPLIB)
        stops = tuple(
            Stop(id=i, coord=c) for i, c in enumerate(self.coords)
        )
        return Instance.single_vehicle_tsp(
            name=self.name,
            stops=stops,
            matrix=matrix,
            depot_index=0,
            metadata={
                "source": "TSPLIB95",
                "edge_weight_type": self.edge_weight_type.value,
                "comment": self.comment,
            },
        )


def _split_header(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, _, value = line.partition(":")
    return key.strip().upper(), value.strip()


def parse_problem(path: Path | str) -> TsplibProblem:
    """Parse a ``.tsp`` file with a ``NODE_COORD_SECTION``."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    name = ""
    comment = ""
    dimension: int | None = None
    ewt: EdgeWeightType | None = None
    coords: list[Coord] = []
    in_coords = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith("NODE_COORD_SECTION"):
            in_coords = True
            continue
        if upper.startswith(("EOF", "DISPLAY_DATA_SECTION", "TOUR_SECTION")):
            in_coords = False
            continue

        if in_coords:
            parts = line.split()
            if len(parts) < 3:
                continue
            coords.append(Coord(float(parts[1]), float(parts[2])))
            continue

        header = _split_header(line)
        if header is None:
            continue
        key, value = header
        if key == "NAME":
            name = value
        elif key == "COMMENT":
            comment = value
        elif key == "DIMENSION":
            dimension = int(value)
        elif key == "EDGE_WEIGHT_TYPE":
            try:
                ewt = EdgeWeightType(value.upper())
            except ValueError:
                raise ValueError(
                    f"{path}: unsupported EDGE_WEIGHT_TYPE {value!r}"
                ) from None
        elif key == "TYPE" and value.upper() not in {"TSP", "ATT"}:
            raise ValueError(f"{path}: only TYPE:TSP is supported, got {value!r}")

    if ewt is None:
        raise ValueError(f"{path}: missing EDGE_WEIGHT_TYPE")
    if ewt is EdgeWeightType.EXPLICIT:
        raise ValueError(
            f"{path}: EXPLICIT edge weights are not supported yet; this loader "
            f"handles coordinate-based conventions"
        )
    if not coords:
        raise ValueError(f"{path}: no NODE_COORD_SECTION found")
    if dimension is not None and dimension != len(coords):
        raise ValueError(
            f"{path}: DIMENSION says {dimension} but found {len(coords)} coordinates"
        )

    return TsplibProblem(
        name=name or Path(path).stem,
        dimension=len(coords),
        edge_weight_type=ewt,
        coords=tuple(coords),
        comment=comment,
    )


def parse_tour(path: Path | str) -> tuple[int, ...]:
    """Parse a ``.opt.tour`` file into zero-based node indices.

    TSPLIB tour files are one-based and terminated by ``-1``; the returned tuple
    is zero-based to match :class:`~core.model.instance.Instance` indexing. Off-by-one
    here would silently produce a wrong tour cost, so the conversion is done in
    exactly one place.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    nodes: list[int] = []
    in_tour = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("TOUR_SECTION"):
            in_tour = True
            continue
        if upper.startswith("EOF"):
            break
        if not in_tour:
            continue
        for token in line.split():
            try:
                value = int(token)
            except ValueError:
                continue
            if value == -1:
                in_tour = False
                break
            nodes.append(value - 1)

    if not nodes:
        raise ValueError(f"{path}: no TOUR_SECTION found")
    if len(set(nodes)) != len(nodes):
        raise ValueError(f"{path}: tour visits a node more than once")
    return tuple(nodes)
