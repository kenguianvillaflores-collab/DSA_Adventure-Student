"""TODO: build a canonical level using the injected terrain generator."""

import random
from collections import deque

from src.api import (
    GenerationFailure, LevelDefinition, LevelSpecification, Position, TerrainGeneratorContract,
    TerrainTopology, to_artifact_definition, to_character_definition, to_enemy_definition,
)
from src.student.artifact import Artifact
from src.student.character import Character
from src.student.enemy import Enemy

DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
MAX_SEED = 2 ** 31 - 1


class LevelGenerator:
    """Use the supplied TerrainGeneratorContract; do not instantiate a replacement."""

    def __init__(self, terrain_generator: TerrainGeneratorContract) -> None:
        self._terrain_generator = terrain_generator

    def generate_level(self, specification: LevelSpecification, seed: int) -> LevelDefinition:
        rng = random.Random(seed)

        for attempt in range(specification.max_attempts):
            # A new terrain seed for each attempt; the level keeps the original seed.
            try:
                terrain = self._terrain_generator.generate_terrain(
                    specification.terrain_spec, (seed + attempt) % (MAX_SEED + 1))
            except GenerationFailure:
                continue

            floor = _floor_tiles(terrain)
            if not _shape_is_allowed(floor, specification):
                continue
            endpoints = _choose_endpoints(floor, specification, rng)
            if endpoints is None:
                continue
            start, exit_tile = endpoints

            placed = _place_entities(floor, start, exit_tile, specification, rng)
            if placed is None:
                continue
            artifact_tiles, enemy_tiles = placed

            artifacts = tuple(
                to_artifact_definition(Artifact(
                    f"artifact-{i}", Position(row, column),
                    rng.randint(specification.artifact_value_min, specification.artifact_value_max)))
                for i, (row, column) in enumerate(artifact_tiles))
            enemies = tuple(
                to_enemy_definition(Enemy(
                    f"enemy-{i}", Position(row, column),
                    rng.randint(specification.enemy_penalty_min, specification.enemy_penalty_max)))
                for i, (row, column) in enumerate(enemy_tiles))

            return LevelDefinition(
                level_id=specification.level_id,
                profile_id=specification.profile_id,
                seed=seed,
                terrain=terrain,
                start=Position(*start),
                exit=Position(*exit_tile),
                character=to_character_definition(Character(specification.agent_id)),
                artifacts=artifacts,
                enemies=enemies,
            )

        raise GenerationFailure("LevelGenerator", "no acceptable level within max_attempts")


# ---------- small helpers: the floor as a set of (row, column) tiles ----------

def _floor_tiles(terrain):
    return {(row, column)
            for row, symbols in enumerate(terrain.terrain_rows)
            for column, symbol in enumerate(symbols) if symbol == "."}


def _neighbours(tile, floor):
    row, column = tile
    return [(row + dr, column + dc) for dr, dc in DIRECTIONS if (row + dr, column + dc) in floor]


def _find_path(start, goal, floor, skip=None):
    """Shortest list of tiles from start to goal (or None). `skip` removes one edge."""
    came_from = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            path = []
            while here is not None:
                path.append(here)
                here = came_from[here]
            return path[::-1]
        for nxt in _neighbours(here, floor):
            if nxt not in came_from and frozenset((here, nxt)) != skip:
                came_from[nxt] = here
                queue.append(nxt)
    return None


def _has_alternate_path(path, floor):
    """True if blocking some single edge of the shortest path still leaves a route."""
    start, goal = path[0], path[-1]
    return any(_find_path(start, goal, floor, skip=frozenset(edge)) is not None
               for edge in zip(path, path[1:]))


# ---------- the steps of one attempt ----------

def _shape_is_allowed(floor, spec):
    junctions = sum(len(_neighbours(tile, floor)) >= 3 for tile in floor)
    dead_ends = sum(len(_neighbours(tile, floor)) == 1 for tile in floor)
    return junctions >= spec.min_branch_tiles and dead_ends <= spec.max_dead_end_tiles


def _choose_endpoints(floor, spec, rng):
    candidates = sorted(floor)
    if spec.terrain_spec.topology is not TerrainTopology.GENERAL:
        # Paths and trees must start and finish at a dead end (a leaf).
        candidates = [t for t in candidates if len(_neighbours(t, floor)) == 1]

    pairs = [(a, b) for a in candidates for b in candidates if a != b]
    rng.shuffle(pairs)
    for start, exit_tile in pairs:
        path = _find_path(start, exit_tile, floor)
        moves = len(path) - 1
        if not spec.min_route_moves <= moves <= spec.max_route_moves:
            continue
        if spec.require_alternate_path and not _has_alternate_path(path, floor):
            continue
        return start, exit_tile
    return None


def _place_entities(floor, start, exit_tile, spec, rng):
    """Pick tiles for the artifacts, then the enemies. Returns None if there is no room."""
    tiles = sorted(floor)
    artifact_ok = [t for t in tiles
                   if spec.allow_entities_on_endpoints or t not in (start, exit_tile)]
    enemy_ok = [t for t in artifact_ok if t != start]      # an enemy never stands on the start
    used = set()

    def pick(count, allowed):
        chosen = []
        for _ in range(count):
            free = allowed if spec.allow_entity_overlap else [t for t in allowed if t not in used]
            if not free:
                return None
            tile = rng.choice(free)
            chosen.append(tile)
            used.add(tile)
        return chosen

    artifact_tiles = pick(spec.artifact_count, artifact_ok)
    enemy_tiles = pick(spec.enemy_count, enemy_ok)
    if artifact_tiles is None or enemy_tiles is None:
        return None
    return artifact_tiles, enemy_tiles