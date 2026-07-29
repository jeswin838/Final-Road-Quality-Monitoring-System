from flask import Blueprint, jsonify, request
from models.hazard import Hazard # Mocking this for the GET route if we dynamically generate
from repositories.assignment_repository import AssignmentRepository
from repositories.worker_repository import WorkerRepository
from services.assignment_engine import AssignmentEngine
from services.approval_service import ApprovalService

assignment_api = Blueprint('assignment_api', __name__)
assignment_repo = AssignmentRepository()
worker_repo = WorkerRepository()
engine = AssignmentEngine()
approval_service = ApprovalService()

@assignment_api.route('/api/assignments/recommended', methods=['POST'])
def get_recommended():
    # Expecting hazard dict in body to generate recommendations on the fly
    data = request.json
    h = Hazard(
        hazard_id=data.get('hazard_id', 'Unknown'),
        latitude=data.get('latitude', 0.0),
        longitude=data.get('longitude', 0.0),
        priority=data.get('priority', 'Low')
    )
    h.road_class = data.get('road_class', '')
    h.zone = data.get('zone', '')
    h.district = data.get('district', '')
    h.location_summary = data.get('location_summary', '')
    
    bundle = engine.generate_recommendations(h)
    
    # Convert dataclasses to dict
    bundle_dict = {
        "hazard_id": bundle.hazard_id,
        "engine_version": bundle.engine_version,
        "generated_time": bundle.generated_time,
        "recommendations": [r.__dict__ for r in bundle.recommendations]
    }
    
    return jsonify(bundle_dict), 200

@assignment_api.route('/api/workers', methods=['GET'])
def get_workers():
    workers = worker_repo.get_all_workers()
    return jsonify({"workers": [w.__dict__ for w in workers]}), 200

@assignment_api.route('/api/assignments/history', methods=['GET'])
def get_history():
    assignment_id = request.args.get('assignment_id')
    if not assignment_id:
        return jsonify({"error": "assignment_id required"}), 400
    history = assignment_repo.get_history(assignment_id)
    return jsonify({"history": [h.__dict__ for h in history]}), 200

@assignment_api.route('/api/assignments/approve', methods=['POST'])
def approve_assignment():
    data = request.json
    hazard_id = data.get("hazard_id")
    recommendation = data.get("recommendation")
    admin_id = data.get("admin_id", "Admin")
    
    if not hazard_id or not recommendation:
        return jsonify({"error": "hazard_id and recommendation payload required"}), 400
        
    assignment = approval_service.approve_recommendation(hazard_id, recommendation, admin_id)
        
    return jsonify({"message": "Assignment approved", "assignment": assignment.__dict__}), 200
