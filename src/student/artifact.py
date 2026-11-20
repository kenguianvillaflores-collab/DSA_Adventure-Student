"""TODO: implement initial artifact data; introductory gameplay has no artifacts."""
from src.api import ArtifactDefinition, Position


class Artifact:
    """Expose read-only canonical identity, position, and nonnegative value."""

    def __init__(self, artifact_id: str, position: Position, value: int) -> None:
        ArtifactDefinition(artifact_id, position, value)
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
