"""
Workflow History Service — Phase 7b (Enterprise Hardening)
Orchestrates append-only history + structured event emission.
All writes share one SQLite connection for atomicity.
"""
import logging
from typing import Optional
from repositories.history_repository import HistoryRepository
from repositories.maintenance_repository import MaintenanceRepository
from models.workflow_event import WorkflowEvent
from utils.workflow_constants import STATE_EVENT_MAP, EVENT_SOURCE, EVENT_VERSION

logger = logging.getLogger(__name__)


class WorkflowHistoryService:
    def __init__(self):
        self.history_repo = HistoryRepository()
        self.maint_repo = MaintenanceRepository()

    def record_transition(
        self,
        task_id: str,
        previous_state: Optional[str],
        new_state: str,
        changed_by: str,
        changed_time: str,
        actor_type: str = "System",
        remarks: str = "",
        gps_lat: Optional[float] = None,
        gps_lon: Optional[float] = None,
        gps_accuracy: Optional[float] = None,
        photo_before: Optional[str] = None,
        photo_after: Optional[str] = None,
        verification_photo: Optional[str] = None,
        device: Optional[str] = None,
        device_type: Optional[str] = None,
        conn=None,                        # shared SQLite connection for transactions
    ) -> None:
        history_id = self.history_repo.append(
            task_id=task_id,
            previous_state=previous_state,
            new_state=new_state,
            changed_by=changed_by,
            changed_time=changed_time,
            actor_type=actor_type,
            remarks=remarks,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            gps_accuracy=gps_accuracy,
            photo_before=photo_before,
            photo_after=photo_after,
            verification_photo=verification_photo,
            device=device,
            device_type=device_type,
            conn=conn,
        )
        logger.info(
            f"[HISTORY] Task {task_id}: {previous_state} -> {new_state} "
            f"by {changed_by} ({actor_type}) at {changed_time} | history_id={history_id}"
        )

        # Emit structured event
        event_type = STATE_EVENT_MAP.get(new_state)
        if event_type:
            event = WorkflowEvent(
                event_id=None,
                task_id=task_id,
                event_type=event_type,
                event_time=changed_time,
                payload=None,
            )
            # Attach source/version dynamically
            event.event_source = EVENT_SOURCE    # type: ignore[attr-defined]
            event.event_version = EVENT_VERSION  # type: ignore[attr-defined]
            self.maint_repo.save_event(event, conn=conn)
            logger.info(f"[EVENT] {event_type} emitted for task {task_id}")

    def get_history(self, task_id: str) -> list:
        return self.history_repo.get_history(task_id)
