import logging
from flask import Blueprint, request, jsonify
from services.verification_engine import VerificationEngine
from services.verification_validator import VerificationError

logger = logging.getLogger(__name__)
verification_api = Blueprint('verification_api', __name__, url_prefix='/api/verification')

engine = VerificationEngine()

@verification_api.route('/start', methods=['POST'])
def start_verification():
    data = request.json or {}
    task_id = data.get("task_id")
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400
        
    try:
        verif = engine.start_verification(task_id, data)
        # Exclude non-dataclass fields
        d = {k: getattr(verif, k) for k in verif.__dataclass_fields__}
        return jsonify(d), 201
    except VerificationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Error starting verification")
        return jsonify({"error": str(e)}), 500

@verification_api.route('/approve', methods=['POST'])
def approve_verification():
    data = request.json or {}
    verification_id = data.get("verification_id")
    if not verification_id:
        return jsonify({"error": "verification_id is required"}), 400
        
    try:
        verif = engine.submit_verification(verification_id, data)
        d = {k: getattr(verif, k) for k in verif.__dataclass_fields__}
        return jsonify(d), 200
    except VerificationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Error approving verification")
        return jsonify({"error": str(e)}), 500

@verification_api.route('/reject', methods=['POST'])
def reject_verification():
    data = request.json or {}
    verification_id = data.get("verification_id")
    if not verification_id:
        return jsonify({"error": "verification_id is required"}), 400
        
    try:
        # submit_verification evaluates pass/fail based on rules and provided data.
        # So we pass the data and let the engine score it. 
        # If the user explicitly wants to reject, we might need a force fail, but for now we rely on the deterministic rules.
        verif = engine.submit_verification(verification_id, data)
        d = {k: getattr(verif, k) for k in verif.__dataclass_fields__}
        return jsonify(d), 200
    except VerificationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Error rejecting verification")
        return jsonify({"error": str(e)}), 500

@verification_api.route('/<verification_id>', methods=['GET'])
def get_verification(verification_id):
    verif = engine.get_verification(verification_id)
    if not verif:
        return jsonify({"error": "Not found"}), 404
    d = {k: getattr(verif, k) for k in verif.__dataclass_fields__}
    return jsonify(d)

@verification_api.route('/', methods=['GET'])
def get_pending():
    pending = engine.get_pending()
    return jsonify([{k: getattr(v, k) for k in v.__dataclass_fields__} for v in pending])

@verification_api.route('/history/<verification_id>', methods=['GET'])
def get_history(verification_id):
    history = engine.get_history(verification_id)
    return jsonify(history)

@verification_api.route('/statistics', methods=['GET'])
def get_statistics():
    stats = engine.get_statistics()
    return jsonify(stats)
