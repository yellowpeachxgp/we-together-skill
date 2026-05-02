"""Multi-agent package (Phase 29)."""
from we_together.agents.person_agent import PersonAgent
from we_together.agents.turn_taking import (
    compute_turn_priority,
    next_speaker,
    orchestrate_multi_agent_turn,
)

__all__ = [
    "PersonAgent",
    "compute_turn_priority",
    "next_speaker",
    "orchestrate_multi_agent_turn",
]
