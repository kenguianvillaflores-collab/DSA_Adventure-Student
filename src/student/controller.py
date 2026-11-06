from src.api import WorldAction, WorldSnapshot


class AgentController:
    """
    Controls the agent's decisions each turn.
    Priority logic: MOVE toward exit → COLLECT → ENGAGE → EXIT when reached.
    """

    def __init__(self) -> None:
        # No special setup needed — fresh controller per run
        pass

    def choose_action(self, state: WorldSnapshot, agent_id: str) -> WorldAction:
        agent = state.agents.get(agent_id)
        if not agent:
            return WorldAction.WAIT

        my_pos = agent.position
        exit_pos = state.exit_position
        if my_pos == exit_pos:
            return WorldAction.EXIT

        def distance(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        for enemy in state.enemies.values():
            if distance(my_pos, enemy.position) == 1:
                return WorldAction.ENGAGE

        for artifact in state.artifacts.values():
            if distance(my_pos, artifact.position) == 1:
                return WorldAction.COLLECT

        directions = [
            WorldAction.MOVE_UP,
            WorldAction.MOVE_DOWN,
            WorldAction.MOVE_LEFT,
            WorldAction.MOVE_RIGHT,
        ]

        best_move = WorldAction.WAIT
        best_dist = distance(my_pos, exit_pos)

        for move in directions:
            dr, dc = 0, 0
            if move == WorldAction.MOVE_UP:
                dr = -1
            elif move == WorldAction.MOVE_DOWN:
                dr = 1
            elif move == WorldAction.MOVE_LEFT:
                dc = -1
            elif move == WorldAction.MOVE_RIGHT:
                dc = 1

            new_pos = (my_pos[0] + dr, my_pos[1] + dc)

            if (
                0 <= new_pos[0] < len(state.terrain)
                and 0 <= new_pos[1] < len(state.terrain[0])
                and state.terrain[new_pos[0]][new_pos[1]]  # True = passable
            ):
                new_dist = distance(new_pos, exit_pos)
                if new_dist < best_dist:
                    best_dist = new_dist
                    best_move = move

        return best_move