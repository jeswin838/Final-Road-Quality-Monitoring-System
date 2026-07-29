from models.worker import Worker
from utils.assignment_constants import WORKER_STATUS, WORKER_MAX_CAPACITY

def is_worker_available(worker: Worker) -> bool:
    """Checks if a worker is currently available to take new assignments."""
    if not worker.availability:
        return False
    if worker.status in [WORKER_STATUS["OFFLINE"], WORKER_STATUS["ON_LEAVE"]]:
        return False
    return True

def has_capacity(worker: Worker) -> bool:
    """Checks if a worker has capacity for more assignments."""
    return worker.current_capacity < min(worker.maximum_capacity, WORKER_MAX_CAPACITY)

def calculate_workload_penalty(worker: Worker) -> float:
    """Calculates a workload penalty (0-100) based on current assignments."""
    max_cap = min(worker.maximum_capacity, WORKER_MAX_CAPACITY)
    if max_cap == 0:
        return 100.0
    return (worker.current_capacity / max_cap) * 100.0
