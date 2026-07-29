import datetime
from models.hazard import Hazard
from models.worker import Worker

def append_assignment_history(hazard: Hazard, state: str, worker: Worker = None, reason: str = None):
    """Appends an event to the hazard's assignment_history."""
    if not hasattr(hazard, 'history'):
        hazard.history = []
        
    event = {
        "state": state,
        "timestamp": datetime.datetime.now().isoformat(),
        "actor": "AssignmentEngine",
        "reason": reason
    }
    
    if worker:
        event["worker_id"] = worker.worker_id
        event["team_id"] = worker.team
        
    hazard.history.append(event)

def transition_state(hazard: Hazard, new_state: str, worker: Worker = None, reason: str = None):
    """Transitions the hazard maintenance_state and logs history."""
    hazard.maintenance_state = new_state
    append_assignment_history(hazard, new_state, worker, reason)
