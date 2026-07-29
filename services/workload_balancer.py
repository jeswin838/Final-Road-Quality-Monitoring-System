from typing import List
from models.worker import Worker
from utils.workload_rules import is_worker_available, has_capacity

def filter_eligible_workers(workers: List[Worker], required_team: str = None) -> List[Worker]:
    """Filters workers based on availability, capacity, and required team."""
    eligible = []
    for w in workers:
        if not is_worker_available(w):
            continue
            
        if not has_capacity(w):
            continue
            
        # Simplified team matching for mock implementation
        if required_team:
            if required_team == "EMERGENCY" and "EMG" not in w.team:
                continue
            if required_team == "HIGHWAY" and "HWY" not in w.team:
                continue
            if required_team == "MUNICIPALITY" and "MUN" not in w.team:
                continue
                
        eligible.append(w)
        
    return eligible
