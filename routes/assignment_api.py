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

def process_create_assignment(data, session_user_id=None, session_user_name='Admin'):
    if not isinstance(data, dict):
        data = {}
    raw_id = data.get("pothole_id")
    if raw_id is None:
        raw_id = data.get("hazard_id")
    worker_name = str(data.get("worker_name") or data.get("worker_id") or "").strip()
    notes = data.get("notes", "")

    if raw_id is None or not worker_name:
        return {"error": "pothole_id (or hazard_id) and worker_name required"}, 400

    clean_id = raw_id
    hazard_source = 'AI'

    if isinstance(raw_id, str):
        if raw_id.startswith('AI-'):
            clean_id = raw_id.replace('AI-', '')
            hazard_source = 'AI'
        elif raw_id.startswith('USER-'):
            clean_id = raw_id.replace('USER-', '')
            hazard_source = 'USER'

    try:
        clean_id = int(clean_id)
    except (ValueError, TypeError):
        pass

    from app import supabase

    worker = None
    if worker_name:
        try:
            w_res = supabase.table('users').select('*').ilike('name', worker_name).eq('role', 'worker').execute()
            if not w_res.data:
                w_res = supabase.table('users').select('*').eq('id', worker_name).eq('role', 'worker').execute()
            if w_res.data:
                worker = w_res.data[0]
        except Exception:
            pass

    if not isinstance(raw_id, str) or (not raw_id.startswith('AI-') and not raw_id.startswith('USER-')):
        try:
            h_res = supabase.table('potholes').select('*').eq('id', clean_id).execute()
            if h_res.data:
                hazard_source = 'AI'
            else:
                u_res = supabase.table('user_reports').select('*').eq('id', clean_id).execute()
                if u_res.data:
                    hazard_source = 'USER'
        except Exception:
            pass

    # Prevent duplicate active assignments
    try:
        existing_res = supabase.table('assignments').select('id, status').eq('hazard_id', clean_id).order('id', desc=True).limit(1).execute()
        if existing_res.data:
            latest_status = str(existing_res.data[0].get('status', '')).lower()
            if latest_status not in ['completed', 'closed', 'rejected', 'resolved', 'fixed', 'verified']:
                return {
                    "error": "An active assignment already exists for this hazard.",
                    "id": existing_res.data[0]['id']
                }, 409
    except Exception as e:
        print("[!] Warning checking existing assignments:", e)

    insert_data = {
        'hazard_id': clean_id,
        'hazard_source': hazard_source,
        'worker_id': worker['id'] if worker else None,
        'worker_name': worker['name'] if worker else worker_name,
        'worker_email': worker['email'] if worker else None,
        'assigned_by': session_user_id,
        'assigned_by_name': session_user_name or 'Admin',
        'status': 'Assigned',
        'verification_status': 'Pending',
        'admin_notes': notes
    }

    new_id = None
    try:
        res = supabase.table('assignments').insert(insert_data).execute()
        if res.data:
            new_id = res.data[0]['id']
    except Exception as e:
        print("[!] Error inserting assignment to Supabase:", e)

    try:
        import uuid, datetime
        from models.assignment import Assignment
        asgn_uuid = str(uuid.uuid4())
        now_str = datetime.datetime.now().isoformat()
        sqlite_asgn = Assignment(
            assignment_id=asgn_uuid,
            hazard_id=str(clean_id),
            worker_id=str(worker['id'] if worker else worker_name),
            recommended_team="Default Crew",
            recommended_vehicle="Standard Vehicle",
            recommended_equipment=[],
            recommended_eta=24.0,
            recommended_distance=0.0,
            recommendation_score=100.0,
            score_breakdown={},
            recommendation_reason="Assigned by Admin",
            approved_by_admin=True,
            assigned_time=now_str,
            status="Assigned",
            priority="Medium",
            history=[]
        )
        assignment_repo.save_assignment(sqlite_asgn)
        assignment_repo.append_history(
            assignment_id=asgn_uuid,
            status="Assigned",
            changed_at=now_str,
            changed_by=session_user_name or "Admin",
            notes=notes
        )
    except Exception as e:
        print("[!] Warning saving to AssignmentRepository:", e)

    try:
        from routes.api import sync_hazard_cache, global_alerts_cache
        prefix = 'AI' if hazard_source == 'AI' else 'USER'
        master_id = f"{prefix}-{clean_id}"
        sync_hazard_cache(master_id, clean_id)
        global_alerts_cache["data"] = None
    except Exception as e:
        print("[!] Cache sync warning:", e)

    return {"id": new_id, "message": "Assigned", "hazard_id": clean_id, "worker_name": worker_name}, 201

@assignment_api.route('/api/assignments', methods=['POST'])
def create_assignment_route():
    from flask import session
    payload = request.get_json(silent=True) or {}
    resp, code = process_create_assignment(payload, session.get('user_id'), session.get('name', 'Admin'))
    return jsonify(resp), code

@assignment_api.route('/api/assignments', methods=['GET'])
def list_assignments_route():
    from routes.api import list_assignments
    return list_assignments()

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

