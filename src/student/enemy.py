"""TODO: implement initial enemy data; introductory gameplay has no enemies."""
from src.api import EnemyDefinition, Position


class Enemy:
    """Expose read-only identity, position, and nonnegative encounter penalty."""

    def __init__(self, enemy_id: str, position: Position, encounter_penalty: int) -> None:
        if not isinstance(enemy_id, str):
            raise TypeError("enemy_id must be a string")

        if not isinstance(position, Position):
            raise TypeError("position must be a Position")

        if isinstance(encounter_penalty, bool) or not isinstance(encounter_penalty, int):
            raise TypeError("encounter_penalty must be an integer")

        if encounter_penalty < 0:
            raise ValueError("encounter_penalty cannot be negative")

        self._enemy_id = enemy_id
        self._position = position
        self._encounter_penalty = encounter_penalty

    @property
    def enemy_id(self) -> str:
        return self._enemy_id

    @property
    def position(self) -> Position:
        return self._position

    @property
    def encounter_penalty(self) -> int:
        return self._encounter_penalty