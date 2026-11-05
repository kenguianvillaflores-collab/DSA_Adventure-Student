import random

from src.api import (
    GenerationFailure,
    Terrain,
    TerrainGenerationSpec,
    TerrainTopology,
)


class TerrainGenerator:
    """Generate introductory straight-path terrain deterministically."""

    def __init__(self) -> None:
        # Keep no generation state here; each call uses its own seed.
        pass

    def generate_terrain(
        self, specification: TerrainGenerationSpec, seed: int
    ) -> Terrain:
        if type(specification) is not TerrainGenerationSpec:
            raise TypeError("specification must be a TerrainGenerationSpec.")
        if type(seed) is not int:
            raise TypeError("seed must be an integer.")

        if specification.topology is not TerrainTopology.STRAIGHT_PATH:
            raise GenerationFailure(
                "TerrainGenerator",
                "This implementation supports STRAIGHT_PATH only.",
            )

        # A straight path needs at least one open tile.
        minimum = max(1, specification.min_open_tiles)

        # Each orientation is paired with its maximum possible line length.
        orientations = []
        if specification.columns >= minimum:
            orientations.append(("horizontal", specification.columns))
        if specification.rows >= minimum:
            orientations.append(("vertical", specification.rows))

        if not orientations:
            raise GenerationFailure(
                "TerrainGenerator",
                "No straight path can satisfy the minimum open-tile count.",
            )

        rng = random.Random(seed)
        orientation, capacity = rng.choice(orientations)
        length = rng.randint(
            minimum,
            min(specification.max_open_tiles, capacity),
        )

        grid = [["#"] * specification.columns for _ in range(specification.rows)]

        if orientation == "horizontal":
            row = rng.randrange(specification.rows)
            start_column = rng.randrange(specification.columns - length + 1)
            for column in range(start_column, start_column + length):
                grid[row][column] = "."
        else:
            column = rng.randrange(specification.columns)
            start_row = rng.randrange(specification.rows - length + 1)
            for row in range(start_row, start_row + length):
                grid[row][column] = "."

        return Terrain(tuple("".join(row) for row in grid))