import logging
from typing import List
from models.hazard import Hazard
from services.assignment_engine import AssignmentEngine
from repositories.worker_repository import WorkerRepository

logger = logging.getLogger(__name__)

class WorkerScheduler:
    """Manages assignment queues and coordinates the Assignment Engine."""
    
    def __init__(self, worker_repo: WorkerRepository):
        self.assignment_engine = AssignmentEngine()
        
    def process_queues(self, hazards: List[Hazard]):
        """Processes hazards sequentially, assigning available workers to top-priority hazards."""
        # Ensure hazards are sorted by priority queue position
        sorted_hazards = sorted(hazards, key=lambda h: getattr(h, 'repair_queue_position', 999999))
        
        assigned_count = 0
        
        for hazard in sorted_hazards:
            # Skip if already assigned or completed
            if getattr(hazard, 'maintenance_state', 'Detected') not in ["Verified", "Prioritized"]:
                continue
                
            # Validation Gate - Only assign if verified or AI confidence is very high
            confidence = getattr(hazard, 'confidence', 0)
            is_verified = getattr(hazard, 'maintenance_state', '') == "Verified"
            
            if not is_verified and confidence < 0.85:
                logger.info(f"[SCHEDULER] Hazard {hazard.hazard_id} skipped assignment (Needs verification)")
                continue
                
            success = self.assignment_engine.assign_hazard(hazard)
            if success:
                assigned_count += 1
                
        logger.info(f"[SCHEDULER] Completed batch run. Successfully assigned {assigned_count} hazards.")
