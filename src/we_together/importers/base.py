from dataclasses import dataclass, field


@dataclass
class ImportResult:
    raw_evidences: list = field(default_factory=list)
    identity_candidates: list = field(default_factory=list)
    event_candidates: list = field(default_factory=list)
    facet_candidates: list = field(default_factory=list)
    relation_clues: list = field(default_factory=list)
    group_clues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
