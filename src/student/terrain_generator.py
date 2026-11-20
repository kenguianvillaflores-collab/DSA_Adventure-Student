"""TODO: generate canonical terrain deterministically from specification and seed."""
import random

from src.api import GenerationFailure, Terrain, TerrainGenerationSpec, TerrainTopology

DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class TerrainGenerator:
    """Keep state local; identical inputs must also agree across fresh instances."""

    def __init__(self) -> None:
        # Nothing to remember: every call makes its own random generator.
        pass

    def generate_terrain(self, specification: TerrainGenerationSpec, seed: int) -> Terrain:
        rng = random.Random(seed)
        rows, columns = specification.rows, specification.columns
        count = rng.randint(specification.min_open_tiles, specification.max_open_tiles)

        if specification.topology is TerrainTopology.STRAIGHT_PATH:
            floor = _straight_path(rows, columns, count, rng)
        elif specification.topology is TerrainTopology.BENT_PATH:
            floor = _bent_path(rows, columns, count, rng)
        elif specification.topology is TerrainTopology.BRANCHING_TREE:
            floor = _branching_tree(rows, columns, count, rng)
        else:
            floor = _general_shape(rows, columns, count, rng)

        return Terrain(tuple(
            "".join("." if (row, column) in floor else "#" for column in range(columns))
            for row in range(rows)
        ))


def _fail(reason: str) -> GenerationFailure:
    return GenerationFailure("TerrainGenerator", reason)


def _straight_path(rows, columns, count, rng):
    """One line of floor, either across a row or down a column."""
    fits_across = count <= columns
    fits_down = count <= rows
    if count < 2 or not (fits_across or fits_down):
        raise _fail("a straight path of this length does not fit the board")
    if fits_across and fits_down:
        across = rng.choice([True, False])
    else:
        across = fits_across

    if across:
        row = rng.randrange(rows)
        first = rng.randrange(columns - count + 1)
        return {(row, first + i) for i in range(count)}
    column = rng.randrange(columns)
    first = rng.randrange(rows - count + 1)
    return {(first + i, column) for i in range(count)}


def _bent_path(rows, columns, count, rng):
    """An 'L': an arm along the top or bottom row, then one turn up or down."""
    # Every way to split `count` tiles into a horizontal arm and a vertical arm.
    shapes = [(arm, count - arm) for arm in range(2, columns + 1)
              if 1 <= count - arm <= rows - 1]
    if not shapes:
        raise _fail("a bent path of this length does not fit the board")
    arm, rest = rng.choice(shapes)

    row = rng.choice([0, rows - 1])
    first = rng.randrange(columns - arm + 1)
    turn_column = rng.choice([first, first + arm - 1])   # the turn is at an end of the arm
    step = 1 if row == 0 else -1                         # away from the edge we started on

    floor = {(row, first + i) for i in range(arm)}
    floor |= {(row + step * k, turn_column) for k in range(1, rest + 1)}
    return floor


def _branching_tree(rows, columns, count, rng):
    """A 'comb': a spine along one edge with branches growing away from it.

    Branches sit two columns apart so they never touch, which means the floor
    has no loops (it is a tree). At least one branch leaves from the middle of
    the spine, so that tile has three floor neighbours (a junction).
    """
    spine = min(columns, count - 1)
    if spine < 3 or rows < 2:
        raise _fail("a branching tree of this size does not fit the board")

    branch_columns = list(range(0, spine, 2)) if spine >= 4 else [1]
    middle_columns = [c for c in branch_columns if 0 < c < spine - 1]
    longest = rows - 1
    length = {c: 0 for c in branch_columns}

    length[rng.choice(middle_columns)] += 1            # guarantees a junction
    for _ in range(count - spine - 1):                 # place the remaining tiles
        room = [c for c in branch_columns if length[c] < longest]
        if not room:
            raise _fail("a branching tree of this size does not fit the board")
        length[rng.choice(room)] += 1

    first = rng.randrange(columns - spine + 1)
    flip = rng.choice([True, False])                   # spine on the top or bottom edge
    floor = {(0, first + i) for i in range(spine)}
    for c, size in length.items():
        floor |= {(k, first + c) for k in range(1, size + 1)}
    if flip:
        floor = {(rows - 1 - row, column) for row, column in floor}
    return floor


def _general_shape(rows, columns, count, rng):
    """One connected blob, grown a random neighbouring tile at a time."""
    if count == 0:
        return set()
    floor = {(rng.randrange(rows), rng.randrange(columns))}
    while len(floor) < count:
        edge = sorted({
            (row + dr, column + dc)
            for row, column in floor
            for dr, dc in DIRECTIONS
            if 0 <= row + dr < rows and 0 <= column + dc < columns
        } - floor)
        floor.add(rng.choice(edge))
    return floor