"""TODO: implement your character's immutable, canonical public identity."""
from src.api import CharacterDefinition


class Character:
    """Character(agent_id); expose a read-only str agent_id property."""

    def __init__(self, agent_id: str) -> None:
        #CharacterDefinition raises an error if the id is not a non-empty,
        # already-trimmed string, so we get the validation for free.
        CharacterDefinition(agent_id)
        self._agent_id = agent_id

    @property
    def agent_id(self) -> str:
        return self._agent_id
