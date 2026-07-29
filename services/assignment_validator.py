from models.worker import Worker

def is_worker_eligible(worker: Worker) -> bool:
    if (worker.status or "").lower() in ["inactive", "vacation", "suspended"]:
        return False
        
    if not worker.available:
        return False
        
    if worker.current_workload >= worker.max_daily_tasks:
        return False
        
    # Check working hours if present, skipped for now to keep simple logic
    
    return True
