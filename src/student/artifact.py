"""TODO: implement initial artifact data; introductory gameplay has no artifacts."""
from src.api import ArtifactDefinition, Position


class Artifact:
    """Expose read-only canonical identity, position, and nonnegative value."""

    def __init__(self, artifact_id: str, position: Position, value: int) -> None:
        if not isinstance(artifact_id, str):
            raise TypeError("artifact_id must be a string")
        if artifact_id == "" or artifact_id != artifact_id.strip():
            raise ValueError("artifact_id must be nonempty and trimmed")
        if not isinstance(position, Position):
            raise TypeError("position must be a Position")
        # bool is a kind of int in Python, so reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("value must be an int")
        if value < 0:
            raise ValueError("value must not be negative")
        self._artifact_id = artifact_id
        self._position = position
        self._value = value

    @property
    def artifact_id(self) -> str:
        return self._artifact_id

    @property
    def position(self) -> Position:
        return self._position

    @property
    def value(self) -> int:
        return self._value
