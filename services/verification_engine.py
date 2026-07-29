import uuid
import datetime
import logging
import sqlite3
import os
from typing import Optional, Dict, Any

from models.verification import Verification
from repositories.verification_repository import VerificationRepository
from services.verification_validator import VerificationValidator, VerificationError
from services.verification_scorer import VerificationScorer
from services.verification_rules import VerificationRules
from services.hazard_registry_sync import HazardRegistrySync
from services.maintenance_workflow_engine import MaintenanceWorkflowEngine
from utils.workflow_constants import STATE_REPAIR_VERIFIED, STATE_REPAIR_STARTED, STATE_VERIFICATION_PENDING
from utils.verification_constants import (
    VERIFICATION_STATUS_PENDING, VERIFICATION_STATUS_VERIFIED, VERIFICATION_STATUS_REJECTED,
    VERIFICATION_RESULT_PASS, VERIFICATION_RESULT_FAIL,
    TAG_VERIFY_PASS, TAG_VERIFY_FAIL, TAG_VERIFY_SCORE, TAG_VERIFY_HISTORY
)

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local_db.sqlite')

class VerificationEngine:
    def __init__(self):
        self.repo = VerificationRepository()
        self.validator = VerificationValidator()
        self.scorer = VerificationScorer()
        self.rules = VerificationRules()
        self.sync = HazardRegistrySync()
        self.workflow_engine = MaintenanceWorkflowEngine()

    def start_verification(self, task_id: str, context: Dict[str, Any]) -> Verification:
        task = self.workflow_engine.get_task(task_id)
        if not task:
            raise VerificationError(f"Task {task_id} not found.")

        self.validator.validate_workflow_state(task)
        self.validator.validate_not_duplicate(task_id)

        verif = Verification(
            verification_id=str(uuid.uuid4()),
            task_id=task.task_id,
            hazard_id=task.hazard_id,
            assignment_id=task.assignment_id,
            verified_by=context.get("verified_by"),
            engineer_name=context.get("engineer_name"),
            engineer_department=context.get("engineer_department"),
            verification_status=VERIFICATION_STATUS_PENDING,
            before_photo=context.get("before_photo"),
            after_photo=context.get("after_photo"),
            verification_photo=context.get("verification_photo"),
            gps_lat=context.get("gps_lat"),
            gps_lon=context.get("gps_lon"),
            gps_accuracy=context.get("gps_accuracy"),
            remarks=context.get("remarks")
        )

        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("BEGIN")
            self.repo.save(verif, conn=conn)
            self.repo.append_history(
                verification_id=verif.verification_id,
                task_id=task.task_id,
                event_type="VERIFICATION_STARTED",
                changed_by=verif.verified_by or "System",
                previous_status=None,
                new_status=VERIFICATION_STATUS_PENDING,
                conn=conn
            )
            
            # Transition workflow to Verification Pending if it's currently Repair Completed
            if task.current_state != STATE_VERIFICATION_PENDING:
                # We need to transition using workflow engine, but that manages its own transactions.
                # It's better to commit our verification first, then transition workflow to avoid nested transaction issues across services.
                pass
                
            conn.commit()
            logger.info(f"[VERIFY] Started verification {verif.verification_id} for task {task_id}")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # Update workflow engine state (this manages its own db connection)
        if task.current_state != STATE_VERIFICATION_PENDING:
            self.workflow_engine.transition(
                task_id=task.task_id,
                new_state=STATE_VERIFICATION_PENDING,
                changed_by=verif.verified_by or "System",
                actor_type="Verification Engineer"
            )

        return verif

    def submit_verification(self, verification_id: str, context: Dict[str, Any] = None) -> Verification:
        verif = self.repo.get_by_id(verification_id)
        if not verif:
            raise VerificationError(f"Verification {verification_id} not found.")
            
        if verif.verification_result is not None:
            raise VerificationError(f"Verification {verification_id} is already completed.")

        if context:
            # Update verification context with any new data provided
            for k, v in context.items():
                if hasattr(verif, k) and v is not None:
                    setattr(verif, k, v)

        # Validate mandatory fields
        self.validator.validate_mandatory_fields(verif)

        # Score
        score, grade, breakdown = self.scorer.score(verif)
        verif.verification_score = score
        verif.verification_grade = grade
        logger.info(f"{TAG_VERIFY_SCORE} Verification {verification_id} scored {score} ({grade})")

        # Rules
        result = self.rules.evaluate_pass_fail(score, breakdown)
        verif.verification_result = result
        verif.verification_reason = self.rules.generate_reason(result, breakdown)
        verif.recommendation = self.rules.generate_recommendation(result, score)
        
        now_str = datetime.datetime.now().isoformat()
        verif.verified_time = now_str
        # simplified duration for now
        verif.verification_duration = 0.0 

        prev_status = verif.verification_status
        
        if result == VERIFICATION_RESULT_PASS:
            verif.verification_status = VERIFICATION_STATUS_VERIFIED
            logger.info(f"{TAG_VERIFY_PASS} Verification {verification_id} PASSED.")
        else:
            verif.verification_status = VERIFICATION_STATUS_REJECTED
            logger.info(f"{TAG_VERIFY_FAIL} Verification {verification_id} FAILED: {verif.verification_reason}")

        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("BEGIN")
            self.repo.save(verif, conn=conn)
            self.repo.append_history(
                verification_id=verif.verification_id,
                task_id=verif.task_id,
                event_type="VERIFICATION_SUBMITTED",
                changed_by=verif.verified_by or "System",
                previous_status=prev_status,
                new_status=verif.verification_status,
                remarks=verif.verification_reason,
                gps_lat=verif.gps_lat,
                gps_lon=verif.gps_lon,
                photo=verif.verification_photo,
                conn=conn
            )
            if result == VERIFICATION_RESULT_PASS:
                self.sync.sync_on_pass(verif.hazard_id, verif.verified_by or "System", now_str, conn=conn)
            else:
                self.sync.sync_on_fail(verif.hazard_id, conn=conn)
                
            conn.commit()
            logger.info(f"{TAG_VERIFY_HISTORY} History appended and hazard registry synced.")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # Update Workflow engine
        if result == VERIFICATION_RESULT_PASS:
            self.workflow_engine.transition(
                task_id=verif.task_id,
                new_state=STATE_REPAIR_VERIFIED,
                changed_by=verif.verified_by or "System",
                actor_type="Verification Engineer",
                remarks=verif.verification_reason
            )
        else:
            # Inspection Failed -> Repair Started
            self.workflow_engine.transition(
                task_id=verif.task_id,
                new_state=STATE_REPAIR_STARTED, # Workflow engine now has Inspection Failed, maybe transition there first, but spec says Repair Started
                changed_by=verif.verified_by or "System",
                actor_type="Verification Engineer",
                remarks=verif.verification_reason
            )
            
        return verif

    def get_verification(self, verification_id: str) -> Optional[Verification]:
        return self.repo.get_by_id(verification_id)
        
    def get_pending(self):
        return self.repo.get_pending()
        
    def get_history(self, verification_id: str):
        return self.repo.get_history(verification_id)
        
    def get_statistics(self):
        return self.repo.get_statistics()
