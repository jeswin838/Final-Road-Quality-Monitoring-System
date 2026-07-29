from dataclasses import dataclass
from typing import Optional


@dataclass
class MaintenanceTask:
    task_id:                str
    hazard_id:              str
    assignment_id:          Optional[str] = None
    maintenance_task_id:    Optional[str] = None
    current_state:          str = "Detected"
    workflow_version:       str = "1.0"
    row_version:            int = 1
    reopen_count:           int = 0
    last_reopened_at:       Optional[str] = None
    created_time:           Optional[str] = None
    updated_time:           Optional[str] = None
    created_by:             Optional[str] = None
    last_modified_by:       Optional[str] = None
    closed_time:            Optional[str] = None
    assigned_at:            Optional[str] = None
    accepted_at:            Optional[str] = None
    travel_started_at:      Optional[str] = None
    arrived_at:             Optional[str] = None
    inspection_started_at:  Optional[str] = None
    repair_started_at:      Optional[str] = None
    temporary_completed_at: Optional[str] = None
    repair_completed_at:    Optional[str] = None
    verification_started_at:Optional[str] = None
    verified_at:            Optional[str] = None
    closed_at:              Optional[str] = None

    # ── Computed metrics (not persisted, calculated on-the-fly) ───────────────
    @property
    def travel_duration(self) -> Optional[float]:
        return self._diff_minutes(self.travel_started_at, self.arrived_at)

    @property
    def inspection_duration(self) -> Optional[float]:
        return self._diff_minutes(self.inspection_started_at, self.repair_started_at)

    @property
    def repair_duration(self) -> Optional[float]:
        return self._diff_minutes(self.repair_started_at, self.repair_completed_at)

    @property
    def verification_duration(self) -> Optional[float]:
        return self._diff_minutes(self.verification_started_at, self.verified_at)

    @property
    def total_duration(self) -> Optional[float]:
        return self._diff_minutes(self.created_time, self.closed_at)

    @staticmethod
    def _diff_minutes(start: Optional[str], end: Optional[str]) -> Optional[float]:
        if not start or not end:
            return None
        from datetime import datetime
        try:
            fmt = "%Y-%m-%dT%H:%M:%S.%f"
            s = datetime.fromisoformat(start)
            e = datetime.fromisoformat(end)
            return round((e - s).total_seconds() / 60, 2)
        except Exception:
            return None
