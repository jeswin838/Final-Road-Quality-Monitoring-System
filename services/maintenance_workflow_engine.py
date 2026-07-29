"""
Maintenance Workflow Engine — Phase 7b (Enterprise Hardening)
Single public facade for all workflow state transitions.
Pipeline: Validator → StateMachine → TaskService (transactional) → Timeline
"""
import datetime
import logging
from typing import Optional

from models.maintenance_task import MaintenanceTask
from models.timeline_item import TimelineItem, MaintenanceTimeline
from services.state_machine import validate_transition, IllegalTransitionError
from services.workflow_validator import (
    run_all_validations, WorkflowValidationError, ConcurrentModificationError
)
from services.task_service import TaskService
from services.workflow_history_service import WorkflowHistoryService

logger = logging.getLogger(__name__)


class MaintenanceWorkflowEngine:
    """Facade: the only public entry point for all workflow transitions."""

    def __init__(self):
        self.task_svc = TaskService()
        self.history_svc = WorkflowHistoryService()

    # ── Task Creation ──────────────────────────────────────────────────────────
    def create_task(
        self,
        hazard_id: str,
        assignment_id: Optional[str] = None,
        created_by: str = "System",
    ) -> MaintenanceTask:
        task = self.task_svc.get_or_create_task(hazard_id, assignment_id, created_by)
        logger.info(f"[WORKFLOW] Task {task.task_id} created for hazard {hazard_id}")
        return task

    # ── State Transition ───────────────────────────────────────────────────────
    def transition(
        self,
        task_id: str,
        new_state: str,
        changed_by: str = "System",
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
    ) -> MaintenanceTask:
        """
        Validated, transactional state transition.
        Raises IllegalTransitionError, WorkflowValidationError, or ConcurrentModificationError.
        """
        task = self.task_svc.get_task(task_id)
        if task is None:
            raise WorkflowValidationError(f"[WORKFLOW] Task {task_id} not found.")

        previous_state = task.current_state
        captured_version = task.row_version   # capture BEFORE any mutation

        # 1. Business rule guards
        run_all_validations(task, new_state)

        # 2. State machine graph guard
        validate_transition(previous_state, new_state)

        # 3. Transactional update (task + history + event in one commit)
        task = self.task_svc.apply_state_transition(
            task=task,
            new_state=new_state,
            changed_by=changed_by,
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
            expected_version=captured_version,
        )

        logger.info(
            f"[WORKFLOW] [TRANSITION] Task {task_id}: "
            f"'{previous_state}' -> '{new_state}' by {changed_by} ({actor_type})"
        )
        return task

    # ── Read Helpers ───────────────────────────────────────────────────────────
    def get_task(self, task_id: str) -> Optional[MaintenanceTask]:
        return self.task_svc.get_task(task_id)

    def get_history(self, task_id: str) -> list:
        return self.history_svc.get_history(task_id)

    def get_kanban(self) -> dict:
        return self.task_svc.get_kanban()

    def get_metrics(self, task_id: str) -> dict:
        task = self.task_svc.get_task(task_id)
        if not task:
            return {}
        return self.task_svc.get_metrics(task)

    def get_timeline(self, task_id: str) -> MaintenanceTimeline:
        """
        Returns a structured MaintenanceTimeline built from the append-only history.
        Ready for the Timeline page — no raw dicts needed.
        """
        task = self.task_svc.get_task(task_id)
        raw_history = self.history_svc.get_history(task_id)

        items = []
        for h in raw_history:
            item = TimelineItem(
                timestamp=h.get("changed_time", ""),
                state=h.get("new_state", ""),
                actor=h.get("changed_by", ""),
                actor_type=h.get("actor_type", "System"),
                message=f"Transitioned to '{h.get('new_state', '')}'",
                image=h.get("photo_after") or h.get("verification_photo"),
                gps_lat=h.get("gps_lat"),
                gps_lon=h.get("gps_lon"),
                device=h.get("device"),
                remarks=h.get("remarks"),
            )
            items.append(item)

        total_duration = task.total_duration if task else None
        return MaintenanceTimeline(task_id=task_id, items=items, total_duration=total_duration)
