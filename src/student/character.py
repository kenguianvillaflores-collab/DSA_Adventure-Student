"""TODO: implement your character's immutable, canonical public identity."""
from src.api import CharacterDefinition


class Character:
    """Character(agent_id); expose a read-only str agent_id property."""

    def __init__(self, agent_id: str) -> None:
        # Validate using public canonical values and retain your own state.
        if not isinstance(agent_id, str):
            raise TypeError("agent_id must be a string")
        if agent_id == "" or agent_id != agent_id.strip():
            raise ValueError("agent_id must be nonempty and trimmed")
        self._agent_id = agent_id

    @property
    def agent_id(self) -> str:
         return self._agent_id
