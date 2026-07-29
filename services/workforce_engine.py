import logging
from typing import List
from models.hazard import Hazard
from repositories.worker_repository import WorkerRepository
from services.worker_scheduler import WorkerScheduler

logger = logging.getLogger(__name__)

class WorkforceEngine:
    """Facade for the Enterprise Workforce Management System (Assignment Engine)."""
    
    def __init__(self):
        self.worker_repo = WorkerRepository()
        self.scheduler = WorkerScheduler(self.worker_repo)
        
    def process(self, hazards: List[Hazard]) -> List[Hazard]:
        """
        Orchestrates the entire workforce management pipeline.
        Runs after the Priority Engine.
        """
        logger.info(f"--- Starting Workforce Management System (Phase 5) for {len(hazards)} hazards ---")
        
        # 1. Evaluate and fill queues
        self.scheduler.process_queues(hazards)
        
        # 2. Re-balance workload (placeholder for future continuous optimization)
        # self.workload_balancer.rebalance()
        
        return hazards

    # Singleton instance for easy import if needed
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
