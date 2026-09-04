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
from core.distance.explicit import EdgeWeightFormat, build_matrix_data
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
    edge_weight_format: EdgeWeightFormat | None = None
    edge_weights: tuple[int, ...] = ()
    display_coords: tuple[Coord, ...] = ()

    @property
    def is_explicit(self) -> bool:
        return self.edge_weight_type is EdgeWeightType.EXPLICIT

    def to_instance(self) -> Instance:
        """Build a single-vehicle TSP instance using this file's own convention.

        For EXPLICIT instances the distances come from the file's matrix. Any
        coordinates present are DISPLAY_DATA and are attached to the stops for
        drawing only -- they are never used to compute a distance.
        """
        if self.is_explicit:
            data = build_matrix_data(
                self.edge_weights, self.edge_weight_format, self.dimension
            )
            matrix = DistanceMatrix(data, self.dimension, Unit.TSPLIB)
            coords_for_display = (
                self.display_coords
                if self.display_coords
                else (None,) * self.dimension
            )
            stops = tuple(
                Stop(id=i, coord=coords_for_display[i])
                for i in range(self.dimension)
            )
            return Instance.single_vehicle_tsp(
                name=self.name,
                stops=stops,
                matrix=matrix,
                depot_index=0,
                metadata={
                    "source": "TSPLIB95",
                    "edge_weight_type": self.edge_weight_type.value,
                    "edge_weight_format": self.edge_weight_format.value,
                    "comment": self.comment,
                    "coords_are_display_only": "true",
                },
            )

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
    """Parse a ``.tsp`` file.

    Handles coordinate instances (``NODE_COORD_SECTION``) and explicit-matrix
    instances (``EDGE_WEIGHT_SECTION``). A file declaring EXPLICIT weights that
    also carries display coordinates keeps the two strictly apart: the matrix
    supplies every distance, and the coordinates are used only for drawing.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    name = ""
    comment = ""
    dimension: int | None = None
    ewt: EdgeWeightType | None = None
    ewf: EdgeWeightFormat | None = None

    coords: list[Coord] = []
    display_coords: list[Coord] = []
    weights: list[int] = []

    section: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("NODE_COORD_SECTION"):
            section = "coords"
            continue
        if upper.startswith("DISPLAY_DATA_SECTION"):
            section = "display"
            continue
        if upper.startswith("EDGE_WEIGHT_SECTION"):
            section = "weights"
            continue
        if upper.startswith(("EOF", "TOUR_SECTION", "DEPOT_SECTION", "DEMAND_SECTION")):
            section = None
            continue

        if section == "coords":
            parts = line.split()
            if len(parts) >= 3:
                coords.append(Coord(float(parts[1]), float(parts[2])))
            continue
        if section == "display":
            parts = line.split()
            if len(parts) >= 3:
                display_coords.append(Coord(float(parts[1]), float(parts[2])))
            continue
        if section == "weights":
            for token in line.split():
                try:
                    weights.append(int(float(token)))
                except ValueError:
                    continue
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
                raise ValueError(f"{path}: unsupported EDGE_WEIGHT_TYPE {value!r}") from None
        elif key == "EDGE_WEIGHT_FORMAT":
            try:
                ewf = EdgeWeightFormat(value.upper())
            except ValueError:
                raise ValueError(
                    f"{path}: unsupported EDGE_WEIGHT_FORMAT {value!r}. "
                    f"Row-wise layouts are supported; column-wise are not."
                ) from None
        elif key == "TYPE" and value.upper() not in {"TSP", "ATT"}:
            raise ValueError(f"{path}: only TYPE:TSP is supported, got {value!r}")

    if ewt is None:
        raise ValueError(f"{path}: missing EDGE_WEIGHT_TYPE")

    if ewt is EdgeWeightType.EXPLICIT:
        if ewf is None:
            raise ValueError(f"{path}: EXPLICIT weights require EDGE_WEIGHT_FORMAT")
        if not weights:
            raise ValueError(
                f"{path}: declares EXPLICIT weights but has no EDGE_WEIGHT_SECTION. "
                f"Its coordinates, if any, are DISPLAY_DATA and must not be used "
                f"to compute distances."
            )
        if dimension is None:
            raise ValueError(f"{path}: EXPLICIT weights require DIMENSION")
        return TsplibProblem(
            name=name or Path(path).stem,
            dimension=dimension,
            edge_weight_type=ewt,
            coords=(),
            comment=comment,
            edge_weight_format=ewf,
            edge_weights=tuple(weights),
            display_coords=tuple(display_coords),
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
        display_coords=tuple(display_coords),
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
