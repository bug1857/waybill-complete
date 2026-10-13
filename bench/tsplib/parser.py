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
    problem_type: str = "TSP"
    edge_weight_format: str | None = None
    explicit_weights: tuple[int, ...] | None = None
    display_coords: tuple[Coord, ...] = ()

    @property
    def is_explicit(self) -> bool:
        return self.edge_weight_type is EdgeWeightType.EXPLICIT

    def to_instance(self) -> Instance:
        """Build a single-vehicle TSP instance using this file's own convention."""
        if self.edge_weight_type is EdgeWeightType.EXPLICIT:
            if self.explicit_weights is None:
                raise ValueError("EXPLICIT problem has no decoded edge weights")
            matrix = DistanceMatrix(
                self.explicit_weights,
                self.dimension,
                Unit.TSPLIB,
            )
        else:
            fn = distance_function(self.edge_weight_type)
            matrix = DistanceMatrix.from_coords(self.coords, fn, Unit.TSPLIB)
        stops = tuple(
            Stop(id=i, coord=(self.coords or self.display_coords)[i] if self.coords or self.display_coords else None)
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
                "edge_weight_format": self.edge_weight_format or "",
                "tsplib_problem_type": self.problem_type,
                "comment": self.comment,
            },
        )


def _split_header(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, _, value = line.partition(":")
    return key.strip().upper(), value.strip()


def _decode_explicit_weights(
    *,
    path: Path | str,
    dimension: int,
    weight_format: str,
    values: list[int],
) -> tuple[int, ...]:
    """Decode a TSPLIB ``EDGE_WEIGHT_SECTION`` into a flat row-major matrix."""
    format_name = weight_format.upper()
    supported = {
        "FULL_MATRIX",
        "UPPER_ROW",
        "LOWER_ROW",
        "UPPER_DIAG_ROW",
        "LOWER_DIAG_ROW",
        "UPPER_COL",
        "LOWER_COL",
        "UPPER_DIAG_COL",
        "LOWER_DIAG_COL",
    }
    if format_name not in supported:
        raise ValueError(
            f"{path}: unsupported EDGE_WEIGHT_FORMAT {weight_format!r}"
        )

    if format_name == "FULL_MATRIX":
        positions = [
            (i, j)
            for i in range(dimension)
            for j in range(dimension)
        ]
        mirror = False
    elif format_name == "UPPER_ROW":
        positions = [
            (i, j)
            for i in range(dimension)
            for j in range(i + 1, dimension)
        ]
        mirror = True
    elif format_name == "LOWER_ROW":
        positions = [
            (i, j)
            for i in range(dimension)
            for j in range(i)
        ]
        mirror = True
    elif format_name == "UPPER_DIAG_ROW":
        positions = [
            (i, j)
            for i in range(dimension)
            for j in range(i, dimension)
        ]
        mirror = True
    elif format_name == "LOWER_DIAG_ROW":
        positions = [
            (i, j)
            for i in range(dimension)
            for j in range(i + 1)
        ]
        mirror = True
    elif format_name == "UPPER_COL":
        positions = [
            (i, j)
            for j in range(dimension)
            for i in range(j)
        ]
        mirror = True
    elif format_name == "LOWER_COL":
        positions = [
            (i, j)
            for j in range(dimension)
            for i in range(j + 1, dimension)
        ]
        mirror = True
    elif format_name == "UPPER_DIAG_COL":
        positions = [
            (i, j)
            for j in range(dimension)
            for i in range(j + 1)
        ]
        mirror = True
    else:  # LOWER_DIAG_COL
        positions = [
            (i, j)
            for j in range(dimension)
            for i in range(j, dimension)
        ]
        mirror = True

    if len(values) != len(positions):
        raise ValueError(
            f"{path}: {format_name} expected {len(positions)} edge weights, "
            f"found {len(values)}"
        )

    flat = [0] * (dimension * dimension)
    for value, (i, j) in zip(values, positions, strict=True):
        flat[i * dimension + j] = value
        if mirror:
            flat[j * dimension + i] = value
    return tuple(flat)


def parse_problem(path: Path | str) -> TsplibProblem:
    """Parse a coordinate-based or ``EXPLICIT`` TSPLIB problem file."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    name = ""
    comment = ""
    problem_type = "TSP"
    dimension: int | None = None
    ewt: EdgeWeightType | None = None
    weight_format: str | None = None
    coords: list[Coord] = []
    display_coords: list[Coord] = []
    edge_weights: list[int] = []
    section: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("NODE_COORD_SECTION"):
            section = "NODE_COORD_SECTION"
            continue
        if upper.startswith("EDGE_WEIGHT_SECTION"):
            section = "EDGE_WEIGHT_SECTION"
            continue
        if upper.startswith("DISPLAY_DATA_SECTION"):
            section = "DISPLAY_DATA_SECTION"
            continue
        if upper.startswith(("EOF", "TOUR_SECTION")):
            section = None
            continue

        if section == "NODE_COORD_SECTION":
            parts = line.split()
            if len(parts) >= 3:
                coords.append(Coord(float(parts[1]), float(parts[2])))
            continue
        if section == "DISPLAY_DATA_SECTION":
            parts = line.split()
            if len(parts) >= 3:
                display_coords.append(Coord(float(parts[1]), float(parts[2])))
            continue

        if section == "EDGE_WEIGHT_SECTION":
            for token in line.split():
                try:
                    value = int(token)
                except ValueError:
                    raise ValueError(
                        f"{path}: non-integer edge weight {token!r}"
                    ) from None
                if value < 0:
                    raise ValueError(
                        f"{path}: edge weights must be non-negative, got {value}"
                    )
                edge_weights.append(value)
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
            if dimension <= 0:
                raise ValueError(
                    f"{path}: DIMENSION must be positive, got {dimension}"
                )
        elif key == "EDGE_WEIGHT_TYPE":
            try:
                ewt = EdgeWeightType(value.upper())
            except ValueError:
                raise ValueError(f"{path}: unsupported EDGE_WEIGHT_TYPE {value!r}") from None
        elif key == "EDGE_WEIGHT_FORMAT":
            weight_format = value.upper()
        elif key == "TYPE":
            problem_type = value.upper()
            if problem_type not in {"TSP", "ATSP"}:
                raise ValueError(
                    f"{path}: only TYPE:TSP or TYPE:ATSP is supported, got {value!r}"
                )

    if ewt is None:
        raise ValueError(f"{path}: missing EDGE_WEIGHT_TYPE")

    if ewt is EdgeWeightType.EXPLICIT:
        if dimension is None:
            raise ValueError(f"{path}: EXPLICIT problems require DIMENSION")
        if weight_format is None:
            raise ValueError(
                f"{path}: EXPLICIT problems require EDGE_WEIGHT_FORMAT"
            )
        explicit_weights = _decode_explicit_weights(
            path=path,
            dimension=dimension,
            weight_format=weight_format,
            values=edge_weights,
        )
        if coords and len(coords) != dimension:
            raise ValueError(
                f"{path}: DIMENSION says {dimension} but found "
                f"{len(coords)} coordinates"
            )
    else:
        explicit_weights = None
        if not coords:
            raise ValueError(f"{path}: no NODE_COORD_SECTION found")
        if dimension is not None and dimension != len(coords):
            raise ValueError(
                f"{path}: DIMENSION says {dimension} but found "
                f"{len(coords)} coordinates"
            )
        dimension = len(coords)

    if display_coords and len(display_coords) != dimension:
        raise ValueError(f"{path}: display coordinate count disagrees with DIMENSION")
    return TsplibProblem(
        name=name or Path(path).stem,
        dimension=dimension,
        edge_weight_type=ewt,
        coords=tuple(coords),
        comment=comment,
        problem_type=problem_type,
        edge_weight_format=weight_format,
        explicit_weights=explicit_weights,
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
            if value <= 0:
                raise ValueError(
                    f"{path}: TSPLIB tour node ids must be positive or -1, "
                    f"got {value}"
                )
            nodes.append(value - 1)

    if not nodes:
        raise ValueError(f"{path}: no TOUR_SECTION found")
    if len(set(nodes)) != len(nodes):
        raise ValueError(f"{path}: tour visits a node more than once")
    return tuple(nodes)
