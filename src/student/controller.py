from src.api import Position, WorldAction, WorldActionType, WorldSnapshot

MOVES = {
    WorldActionType.MOVE_NORTH: (-1, 0),
    WorldActionType.MOVE_SOUTH: (1, 0),
    WorldActionType.MOVE_WEST: (0, -1),
    WorldActionType.MOVE_EAST: (0, 1),
}


class AgentController:
    """A new controller is constructed for each run; arrival still needs EXIT."""

    def __init__(self) -> None:
        self._actions = []          # the actions we still plan to take

    def choose_action(self, state: WorldSnapshot, agent_id: str) -> WorldAction:
        if not self._actions:
            self._actions = find_best_actions(state)

        if self._actions:
            return self._actions.pop(0)

        # No way to finish was found: do something legal instead of crashing.
        if WorldActionType.WAIT in state.allowed_actions:
            return WorldAction.wait()
        return WorldAction(WorldActionType.EXIT)


def patrol_tiles(level, turn):
    """The tiles patrol enemies stand on at this turn."""
    tiles = []
    for patrol in level.patrols:
        place = patrol.positions[(patrol.initial_phase + turn) % patrol.period]
        tiles.append((place.row, place.column))
    return tiles


def legal_choices(state, enemies, situation, turn):
    """Every legal action from a situation at a given turn.

    Each choice is (action, new_row, new_column, new_collected, new_defeated, extra_cost).
    """
    row, column, collected, defeated, _ = situation
    level = state.level
    allowed = state.allowed_actions
    choices = []

    # Tiles we cannot walk onto: enemies not yet cleared, and patrols right now.
    blocked = patrol_tiles(level, turn)
    for enemy in enemies:
        if enemy.enemy_id not in defeated:
            blocked.append((enemy.position.row, enemy.position.column))

    # Walking.
    for kind, (d_row, d_col) in MOVES.items():
        tile = (row + d_row, column + d_col)
        if kind in allowed and state.is_traversable(Position(*tile)) and tile not in blocked:
            choices.append((WorldAction(kind), tile[0], tile[1], collected, defeated, 0))

    # Waiting (only useful when patrols move around).
    if level.patrols and WorldActionType.WAIT in allowed:
        choices.append((WorldAction.wait(), row, column, collected, defeated, 0))

    # Collecting an artifact on our tile.
    if WorldActionType.COLLECT in allowed:
        for artifact in level.artifacts:
            here = (artifact.position.row, artifact.position.column) == (row, column)
            if here and artifact.artifact_id not in collected:
                action = WorldAction(WorldActionType.COLLECT, target_id=artifact.artifact_id)
                new_collected = tuple(sorted(collected + (artifact.artifact_id,)))
                choices.append((action, row, column, new_collected, defeated, 0))

    # Engaging an enemy on a neighbouring tile (costs its penalty).
    if WorldActionType.ENGAGE in allowed:
        for enemy in enemies:
            distance = abs(enemy.position.row - row) + abs(enemy.position.column - column)
            if distance == 1 and enemy.enemy_id not in defeated:
                action = WorldAction(WorldActionType.ENGAGE, target_id=enemy.enemy_id)
                new_defeated = tuple(sorted(defeated + (enemy.enemy_id,)))
                choices.append((action, row, column, collected, new_defeated, enemy.encounter_penalty))

    return choices


def is_safe(state, tile, new_turn):
    """After a non-EXIT action: is the run still alive and inside its limits?"""
    if new_turn >= state.max_turns:
        return False                                  # no turn left for EXIT
    if state.deadline_turn is not None and new_turn >= state.deadline_turn:
        return False                                  # too late
    return tile not in patrol_tiles(state.level, new_turn)   # a patrol hits us


def points(state, collected, final_cost):
    """The workbench's points: base + artifact values - rate * extra cost."""
    reward = sum(a.value for a in state.level.artifacts if a.artifact_id in collected)
    excess = max(0, final_cost - state.baseline_cost)
    if excess >= state.zero_score_excess:
        return 0
    return max(0, state.base_points + reward - state.deduction_rate * excess)


def find_best_actions(state):
    """Return the list of actions of the best route (empty if there is none)."""
    level = state.level
    exit_tile = (level.exit.row, level.exit.column)
    patrol_ids = [patrol.enemy_id for patrol in level.patrols]
    enemies = [e for e in level.enemies if e.enemy_id not in patrol_ids]

    # Cost so far = turns used + penalties already paid.
    paid = sum(e.encounter_penalty for e in enemies if e.enemy_id in state.defeated_enemy_ids)
    # A situation is (row, column, collected, defeated, turn). The turn only matters
    # when patrols move, so without patrols we store 0 to keep the search small.
    has_patrols = len(level.patrols) > 0
    start = (state.agent_position.row, state.agent_position.column,
             state.collected_artifact_ids, state.defeated_enemy_ids,
             state.turn if has_patrols else 0)
    start_cost = state.turn + paid

    cheapest = {start: start_cost}      # situation -> lowest cost found so far
    came_from = {}                      # situation -> (previous situation, action)
    to_explore = [(start_cost, state.turn, start)]  # (cost, real turn, situation)
    best_finish = None                  # (points, -cost, situation)

    while to_explore:
        item = min(to_explore)          # the cheapest situation
        to_explore.remove(item)
        cost, turn, situation = item
        row, column, collected, defeated, _ = situation

        # On the exit: EXIT is one more action, and then the run is over.
        if (row, column) == exit_tile and WorldActionType.EXIT in state.allowed_actions:
            finish = (points(state, collected, cost + 1), -(cost + 1), situation)
            if best_finish is None or finish[:2] > best_finish[:2]:
                best_finish = finish

        for action, new_row, new_col, new_collected, new_defeated, extra in \
                legal_choices(state, enemies, situation, turn):
            if not is_safe(state, (new_row, new_col), turn + 1):
                continue
            new_situation = (new_row, new_col, new_collected, new_defeated,
                             turn + 1 if has_patrols else 0)
            new_cost = cost + 1 + extra
            if new_situation not in cheapest or new_cost < cheapest[new_situation]:
                if new_situation in cheapest:
                    to_explore = [x for x in to_explore if x[2] != new_situation]
                cheapest[new_situation] = new_cost
                came_from[new_situation] = (situation, action)
                to_explore.append((new_cost, turn + 1, new_situation))

    if best_finish is None:
        return []

    # Walk backwards from the best finish to the start to get the actions.
    actions = [WorldAction(WorldActionType.EXIT)]
    situation = best_finish[2]
    while situation in came_from:
        situation, action = came_from[situation]
        actions.append(action)
    actions.reverse()
    return actions