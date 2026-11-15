"""TODO: generate canonical terrain deterministically from specification and seed."""
from src.api import Terrain, TerrainGenerationSpec
import random
from src.api import GenerationFailure, TerrainTopology

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class TerrainGenerator:
    """Keep state local; identical inputs must also agree across fresh instances."""

    def __init__(self) -> None:
        # Nothing is stored between calls, so every instance gives the same answers.
        pass

    def generate_terrain(self, specification: TerrainGenerationSpec, seed: int) -> Terrain:
        rng = random.Random(seed)
        rows = specification.rows
        columns = specification.columns
        low = specification.min_open_tiles
        high = specification.max_open_tiles
        topology = specification.topology

        # Try several random draws; the first one that fits is used.
        for attempt in range(300):
            cells = self.__makeCells(rng, topology, rows, columns, low, high)

            if cells is not None:
                return self.__toTerrain(cells, rows, columns)

        raise GenerationFailure("TerrainGenerator", "no terrain fits the specification")

    # ------------------------------------------------- choose the shape
    def __makeCells(self, rng, topology, rows, columns, low, high):
        if topology == TerrainTopology.STRAIGHT_PATH:
            return self.__makeStraight(rng, rows, columns, low, high)
        if topology == TerrainTopology.BENT_PATH:
            return self.__makeBent(rng, rows, columns, low, high)
        if topology == TerrainTopology.BRANCHING_TREE:
            return self.__makeTree(rng, rows, columns, low, high)
        return self.__makeGeneral(rng, rows, columns, low, high)

    # ---------------------------------------------------------- helpers
    def __toTerrain(self, cells, rows, columns):
        # Open cells become "." and everything else becomes "#".
        lines = []
        for r in range(rows):
            line = ""
            for c in range(columns):
                if (r, c) in cells:
                    line = line + "."
                else:
                    line = line + "#"
            lines.append(line)
        return Terrain(tuple(lines))

    def __neighbors(self, cell, rows, columns):
        # The cells above, below, left and right of this cell that are inside the grid.
        result = []
        for dr, dc in DIRECTIONS:
            newRow = cell[0] + dr
            newColumn = cell[1] + dc
            if 0 <= newRow < rows and 0 <= newColumn < columns:
                result.append((newRow, newColumn))
        return result

    def __countTouching(self, cell, group, rows, columns):
        # How many neighbors of this cell are already inside the group.
        count = 0
        for neighbor in self.__neighbors(cell, rows, columns):
            if neighbor in group:
                count = count + 1
        return count

    def __pickSize(self, rng, low, high, biggest, smallest):
        # A random size between low and high, kept between smallest and biggest.
        low = max(low, smallest)
        high = min(high, biggest)
        if low > high:
            return None
        return rng.randint(low, high)

    def __findOptions(self, cells, rows, columns, avoidLoops):
        # Every empty cell next to the shape that could be added to it.
        # With avoidLoops, a cell is allowed only if it touches exactly one shape cell.
        options = []
        for cell in sorted(cells):
            for neighbor in self.__neighbors(cell, rows, columns):
                if neighbor in cells or neighbor in options:
                    continue
                if avoidLoops and self.__countTouching(neighbor, cells, rows, columns) != 1:
                    continue
                options.append(neighbor)
        return options

    # --------------------------------------------------- straight path
    def __makeStraight(self, rng, rows, columns, low, high):
        directions = []
        if columns >= 2:
            directions.append("row")
        if rows >= 2:
            directions.append("column")
        if len(directions) == 0:
            return None

        direction = rng.choice(directions)
        if direction == "row":
            length = columns
        else:
            length = rows

        size = self.__pickSize(rng, low, high, length, 2)
        if size is None:
            return None

        cells = set()
        if direction == "row":
            row = rng.randrange(rows)
            start = rng.randrange(columns - size + 1)
            for i in range(size):
                cells.add((row, start + i))
        else:
            column = rng.randrange(columns)
            start = rng.randrange(rows - size + 1)
            for i in range(size):
                cells.add((start + i, column))
        return cells

    # -------------------------------------------------------- bent path
    def __makeBent(self, rng, rows, columns, low, high):
        if rows < 2 or columns < 2:
            return None
        size = self.__pickSize(rng, low, high, rows * columns, 3)
        if size is None:
            return None

        origin = (rng.randrange(rows), rng.randrange(columns))
        self.__tries = 5000
        path = self.__extendPath(rng, [origin], size, rows, columns)
        if path is None:
            return None
        return set(path)

    def __isBent(self, path):
        # A bent path must use more than one row AND more than one column.
        rowsUsed = set()
        columnsUsed = set()
        for cell in path:
            rowsUsed.add(cell[0])
            columnsUsed.add(cell[1])
        return len(rowsUsed) > 1 and len(columnsUsed) > 1

    def __extendPath(self, rng, path, size, rows, columns):
        """Grow a path one cell at a time (backtracking when stuck)."""
        if len(path) == size:
            if self.__isBent(path):
                return path
            return None

        self.__tries = self.__tries - 1
        if self.__tries <= 0:
            return None

        tail = path[-1]
        options = self.__neighbors(tail, rows, columns)
        rng.shuffle(options)
        for cell in options:
            if cell in path:
                continue
            # The new cell may touch only the tail, otherwise the path would not be a simple line.
            if self.__countTouching(cell, path, rows, columns) != 1:
                continue

            path.append(cell)
            found = self.__extendPath(rng, path, size, rows, columns)
            if found is not None:
                return found
            path.pop()
        return None

    # ---------------------------------------------------- branching tree
    def __makeTree(self, rng, rows, columns, low, high):
        bigEnough = (rows >= 2 and columns >= 3) or (rows >= 3 and columns >= 2)
        if not bigEnough:
            return None
        size = self.__pickSize(rng, low, high, rows * columns, 4)
        if size is None:
            return None

        cells = set()
        cells.add((rng.randrange(rows), rng.randrange(columns)))

        while len(cells) < size:
            options = self.__findOptions(cells, rows, columns, True)
            if len(options) == 0:
                return None
            cells.add(rng.choice(options))

        if self.__hasJunction(cells, rows, columns):
            return cells
        return None

    def __hasJunction(self, cells, rows, columns):
        # A real tree here must have at least one junction (3 or more neighbors).
        for cell in cells:
            if self.__countTouching(cell, cells, rows, columns) >= 3:
                return True
        return False

    # ------------------------------------------------------------ general
    def __makeGeneral(self, rng, rows, columns, low, high):
        size = self.__pickSize(rng, low, high, rows * columns, 0)
        if size is None:
            return None
        if size == 0:
            return set()

        cells = set()
        if size >= 4 and rows >= 2 and columns >= 2:
            # Start with a 2x2 block so the map always contains a loop.
            r = rng.randrange(rows - 1)
            c = rng.randrange(columns - 1)
            cells.add((r, c))
            cells.add((r + 1, c))
            cells.add((r, c + 1))
            cells.add((r + 1, c + 1))
        else:
            cells.add((rng.randrange(rows), rng.randrange(columns)))

        while len(cells) < size:
            options = self.__findOptions(cells, rows, columns, False)
            if len(options) == 0:
                return None
            cells.add(rng.choice(options))
        return cells