"""
Workflow API — Phase 7
All new routes. Never modifies existing APIs.
"""
from flask import Blueprint, jsonify, request

from services.maintenance_workflow_engine import MaintenanceWorkflowEngine
from services.state_machine import IllegalTransitionError
from services.workflow_validator import WorkflowValidationError
from utils.workflow_constants import (
    STATE_VERIFIED, STATE_PENDING_ASSIGNMENT,
    STATE_ASSIGNMENT_APPROVED, STATE_ASSIGNED,
    STATE_WORKER_ACCEPTED, STATE_TRAVELLING, STATE_ARRIVED,
    STATE_INSPECTION_STARTED, STATE_REPAIR_STARTED,
    STATE_REPAIR_COMPLETED, STATE_VERIFICATION_PENDING,
    STATE_REPAIR_VERIFIED, STATE_CLOSED, STATE_REOPENED,
    STATE_ESCALATED, STATE_CANCELLED,
)

workflow_api = Blueprint('workflow_api', __name__)
engine = MaintenanceWorkflowEngine()


def _transition_route(new_state: str):
    """Generic handler for transition POST routes."""
    data = request.json or {}
    task_id = data.get("task_id")
    if not task_id:
        return jsonify({"error": "task_id required"}), 400

    try:
        task = engine.transition(
            task_id=task_id,
            new_state=new_state,
            changed_by=data.get("changed_by", "API"),
            remarks=data.get("remarks", ""),
            gps_lat=data.get("gps_lat"),
            gps_lon=data.get("gps_lon"),
            photo_before=data.get("photo_before"),
            photo_after=data.get("photo_after"),
            verification_photo=data.get("verification_photo"),
            device=data.get("device"),
        )
        return jsonify({"task": task.__dict__}), 200
    except (IllegalTransitionError, WorkflowValidationError) as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


# ── Task Management ────────────────────────────────────────────────────────────
@workflow_api.route('/api/workflow/task', methods=['POST'])
def create_task():
    data = request.json or {}
    hazard_id = data.get("hazard_id")
    if not hazard_id:
        return jsonify({"error": "hazard_id required"}), 400
    task = engine.create_task(
        hazard_id=hazard_id,
        assignment_id=data.get("assignment_id"),
        created_by=data.get("created_by", "API"),
    )
    return jsonify({"task": task.__dict__}), 201


@workflow_api.route('/api/workflow/task/<task_id>', methods=['GET'])
def get_task(task_id):
    task = engine.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"task": task.__dict__}), 200


@workflow_api.route('/api/workflow/history/<task_id>', methods=['GET'])
def get_history(task_id):
    history = engine.get_history(task_id)
    return jsonify({"history": history}), 200


@workflow_api.route('/api/workflow/kanban', methods=['GET'])
def get_kanban():
    board = engine.get_kanban()
    return jsonify({"kanban": board}), 200


# ── Worker Actions ─────────────────────────────────────────────────────────────
@workflow_api.route('/api/workflow/accept',          methods=['POST'])
def accept():          return _transition_route(STATE_WORKER_ACCEPTED)

@workflow_api.route('/api/workflow/travel',          methods=['POST'])
def travel():          return _transition_route(STATE_TRAVELLING)

@workflow_api.route('/api/workflow/arrive',          methods=['POST'])
def arrive():          return _transition_route(STATE_ARRIVED)

@workflow_api.route('/api/workflow/start-inspection', methods=['POST'])
def start_inspection(): return _transition_route(STATE_INSPECTION_STARTED)

@workflow_api.route('/api/workflow/start-repair',    methods=['POST'])
def start_repair():    return _transition_route(STATE_REPAIR_STARTED)

@workflow_api.route('/api/workflow/complete-repair', methods=['POST'])
def complete_repair(): return _transition_route(STATE_REPAIR_COMPLETED)

@workflow_api.route('/api/workflow/request-verification', methods=['POST'])
def request_verification(): return _transition_route(STATE_VERIFICATION_PENDING)


# ── Admin Actions ──────────────────────────────────────────────────────────────
@workflow_api.route('/api/workflow/verify',   methods=['POST'])
def verify():   return _transition_route(STATE_REPAIR_VERIFIED)

@workflow_api.route('/api/workflow/close',    methods=['POST'])
def close():    return _transition_route(STATE_CLOSED)

@workflow_api.route('/api/workflow/reopen',   methods=['POST'])
def reopen():   return _transition_route(STATE_REOPENED)

@workflow_api.route('/api/workflow/escalate', methods=['POST'])
def escalate(): return _transition_route(STATE_ESCALATED)

@workflow_api.route('/api/workflow/cancel',   methods=['POST'])
def cancel():   return _transition_route(STATE_CANCELLED)
