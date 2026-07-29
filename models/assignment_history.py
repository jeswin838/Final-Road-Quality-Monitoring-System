from dataclasses import dataclass

@dataclass
class AssignmentHistory:
    history_id: int
    assignment_id: str
    status: str
    changed_at: str
    changed_by: str
    notes: str
