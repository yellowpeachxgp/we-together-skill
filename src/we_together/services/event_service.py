from dataclasses import dataclass


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    event_type: str
    source_type: str
    timestamp: str
    summary: str
