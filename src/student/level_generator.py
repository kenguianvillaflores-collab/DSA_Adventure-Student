"""TODO: build a canonical level using the injected terrain generator."""
from src.api import LevelDefinition, LevelSpecification, TerrainGeneratorContract
import random
from src.api import GenerationFailure, Position, TerrainTopology
from src.api import to_artifact_definition, to_character_definition, to_enemy_definition
from src.student.artifact import Artifact
from src.student.character import Character
from src.student.enemy import Enemy

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class LevelGenerator:
    """Use the supplied TerrainGeneratorContract; do not instantiate a replacement."""

    def __init__(self, terrain_generator: TerrainGeneratorContract) -> None:
        self.__terrainGenerator = terrain_generator

    def generate_level(self, specification: LevelSpecification, seed: int) -> LevelDefinition:
        # Each attempt uses the next terrain seed (seed, seed + 1, ...) and its own random generator.
        for attempt in range(specification.max_attempts):
            terrain = self.__terrainGenerator.generate_terrain(
                specification.terrain_spec, seed + attempt)
            rng = random.Random(seed * 256 + attempt)

            level = self.__buildLevel(specification, seed, terrain, rng)
            if level is not None:
                return level

        raise GenerationFailure("LevelGenerator", "no acceptable level within the attempt budget")

    # ------------------------------------------------------------ main steps
    def __buildLevel(self, specification, seed, terrain, rng):
        # Each step returns None when this attempt is not good enough.
        graph = self.__makeGraph(terrain)
        if len(graph) < 2:
            return None

        if not self.__shapeIsOk(specification, graph):
            return None

        endpoints = self.__chooseEndpoints(specification, graph, rng)
        if endpoints is None:
            return None
        start, goal = endpoints

        entities = self.__placeEntities(specification, graph, start, goal, rng)
        if entities is None:
            return None
        artifacts, enemies = entities

        return LevelDefinition(
            level_id=specification.level_id,
            profile_id=specification.profile_id,
            seed=seed,
            terrain=terrain,
            start=Position(start[0], start[1]),
            exit=Position(goal[0], goal[1]),
            character=to_character_definition(Character(specification.agent_id)),
            artifacts=tuple(to_artifact_definition(a) for a in artifacts),
            enemies=tuple(to_enemy_definition(e) for e in enemies),
            patrols=(),
        )

    def __shapeIsOk(self, specification, graph):
        # Enough junctions (3+ neighbors) and not too many dead ends (1 neighbor).
        junctions = 0
        deadEnds = 0
        for cell in graph:
            neighborCount = len(graph[cell])
            if neighborCount >= 3:
                junctions = junctions + 1
            if neighborCount == 1:
                deadEnds = deadEnds + 1
        return junctions >= specification.min_branch_tiles and deadEnds <= specification.max_dead_end_tiles

    # ------------------------------------------------------------ graph
    def __makeGraph(self, terrain):
        """Map every floor cell to the list of floor cells next to it."""
        floor = set()
        for r in range(terrain.rows):
            for c in range(terrain.columns):
                if terrain.terrain_rows[r][c] == ".":
                    floor.add((r, c))

        graph = {}
        for cell in sorted(floor):
            neighbors = []
            for dr, dc in DIRECTIONS:
                other = (cell[0] + dr, cell[1] + dc)
                if other in floor:
                    neighbors.append(other)
            graph[cell] = neighbors
        return graph

    def __distances(self, graph, source, blocked=None):
        """Breadth-first search: steps from source to every reachable cell.
        `blocked` is one edge (a, b) that may not be used."""
        distance = {source: 0}
        queue = [source]
        index = 0
        while index < len(queue):
            cell = queue[index]
            index = index + 1
            for neighbor in graph[cell]:
                if neighbor in distance:
                    continue
                if blocked is not None and ((cell, neighbor) == blocked or (neighbor, cell) == blocked):
                    continue
                distance[neighbor] = distance[cell] + 1
                queue.append(neighbor)
        return distance

    def __shortestRoute(self, graph, start, goal):
        # Walk back from the goal, always stepping to a cell one step closer to the start.
        distance = self.__distances(graph, start)
        route = [goal]
        current = goal
        while current != start:
            for neighbor in graph[current]:
                if distance[neighbor] == distance[current] - 1:
                    current = neighbor
                    break
            route.append(current)
        return route

    def __hasAlternatePath(self, graph, start, goal):
        """True if the goal can still be reached after removing any one edge of the shortest route."""
        route = self.__shortestRoute(graph, start, goal)
        for i in range(len(route) - 1):
            edge = (route[i], route[i + 1])
            if goal in self.__distances(graph, start, edge):
                return True
        return False

    # ------------------------------------------------------------ endpoints
    def __chooseEndpoints(self, specification, graph, rng):
        topology = specification.terrain_spec.topology
        leavesOnly = topology in (TerrainTopology.STRAIGHT_PATH,
                                  TerrainTopology.BENT_PATH,
                                  TerrainTopology.BRANCHING_TREE)

        # Path and tree maps use dead ends as endpoints; other maps allow any cell.
        candidates = []
        for cell in graph:
            if not leavesOnly or len(graph[cell]) == 1:
                candidates.append(cell)

        # Group every allowed pair by the length of its shortest route.
        pairsByLength = {}
        for first in candidates:
            distance = self.__distances(graph, first)
            for second in candidates:
                if first < second and second in distance:
                    moves = distance[second]
                    if specification.min_route_moves <= moves <= specification.max_route_moves:
                        pairsByLength.setdefault(moves, []).append((first, second))
        if len(pairsByLength) == 0:
            return None

        # Prefer the longest routes first.
        for length in sorted(pairsByLength, reverse=True):
            pairs = pairsByLength[length]
            rng.shuffle(pairs)          # ties are decided by the seed

            for first, second in pairs:
                if specification.require_alternate_path and not self.__hasAlternatePath(graph, first, second):
                    continue
                if rng.random() < 0.5:
                    return (first, second)
                return (second, first)
        return None

    # ------------------------------------------------------------ entities
    def __placeEntities(self, specification, graph, start, goal, rng):
        artifactCells = []
        enemyCells = []
        for cell in sorted(graph):
            onEndpoint = (cell == start or cell == goal)
            if onEndpoint and not specification.allow_entities_on_endpoints:
                continue
            artifactCells.append(cell)
            if cell != start:          # enemies may never stand on the start
                enemyCells.append(cell)

        used = []

        # Enemies are placed first, then artifacts (this order keeps the seed results the same).
        enemies = []
        for index in range(specification.enemy_count):
            cell = self.__pickCell(rng, enemyCells, used, specification.allow_entity_overlap)
            if cell is None:
                return None
            penalty = rng.randint(specification.enemy_penalty_min, specification.enemy_penalty_max)
            enemies.append(Enemy(f"enemy-{index}", Position(cell[0], cell[1]), penalty))

        artifacts = []
        for index in range(specification.artifact_count):
            cell = self.__pickCell(rng, artifactCells, used, specification.allow_entity_overlap)
            if cell is None:
                return None
            value = rng.randint(specification.artifact_value_min, specification.artifact_value_max)
            artifacts.append(Artifact(f"artifact-{index}", Position(cell[0], cell[1]), value))

        return (artifacts, enemies)

    def __pickCell(self, rng, cells, used, overlapAllowed):
        # Prefer a free cell; reuse a taken one only if overlap is allowed.
        free = [cell for cell in cells if cell not in used]

        if len(free) > 0:
            choice = rng.choice(free)
        elif overlapAllowed and len(cells) > 0:
            choice = rng.choice(cells)
        else:
            return None

        used.append(choice)
        return choice
