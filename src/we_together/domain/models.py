from dataclasses import dataclass, field


@dataclass
class RuntimeParticipant:
    person_id: str
    display_name: str
    scene_role: str
    activation_state: str
    activation_score: float = 0.0
    is_speaking: bool = False
    reasons: list[str] = field(default_factory=list)
