from dataclasses import dataclass, field
from typing import List

@dataclass
class Worker:
    worker_id: str
    employee_code: str
    name: str
    team: str
    department: str
    designation: str
    phone: str
    email: str
    zone: str
    district: str
    skills: List[str] = field(default_factory=list)
    is_on_leave: bool = False
    is_online: bool = True
    is_emergency_team: bool = False
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    shift: str = "Morning"
    latitude: float = 0.0
    longitude: float = 0.0
    active_tasks: int = 0
    completed_tasks: int = 0
    experience_years: int = 0
    max_daily_tasks: int = 5
    today_tasks: int = 0
    current_workload: int = 0
    vehicle: str = ""
    equipment: List[str] = field(default_factory=list)
    status: str = "Active"
    last_assignment: str = ""
    performance_score: float = 0.0
    average_completion_time: float = 0.0
    password_hash: str = ""
    created_at: str = ""
    updated_at: str = ""
