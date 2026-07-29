from flask import Blueprint, request, jsonify, session
from flask_bcrypt import Bcrypt
from datetime import datetime

worker_api = Blueprint("worker_api", __name__, url_prefix="/api/worker")
bcrypt = Bcrypt()

def get_supabase():
    from app import supabase
    return supabase

# -----------------------------------------------------------------------------
# ADMIN WORKER MANAGEMENT - CRUD
# -----------------------------------------------------------------------------
@worker_api.route("/admin/manage", methods=["GET"])
def get_workers():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    supabase = get_supabase()
    try:
        res = supabase.table("users").select("*").eq("role", "worker").order("created_at", desc=True).execute()
        workers = res.data or []
        for w in workers:
            w.pop("password", None)
        return jsonify(workers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@worker_api.route("/admin/manage", methods=["POST"])
def add_worker():
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    team_name = data.get("team")
    designation = data.get("designation")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"error": "Name, Email and Password are required"}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    supabase = get_supabase()
    try:
        res = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": password_hash,
            "role": "worker",
            "phone": phone,
            "team_name": team_name,
            "designation": designation,
            "worker_status": "Available"
        }).execute()
        return jsonify({"success": True, "message": "Worker added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@worker_api.route("/admin/manage/<int:worker_id>", methods=["PUT"])
def edit_worker(worker_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    team_name = data.get("team")
    designation = data.get("designation")
    status = data.get("status")

    supabase = get_supabase()
    try:
        supabase.table("users").update({
            "name": name,
            "email": email,
            "phone": phone,
            "team_name": team_name,
            "designation": designation,
            "worker_status": status
        }).eq("id", worker_id).execute()
        return jsonify({"success": True, "message": "Worker updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@worker_api.route("/admin/manage/<int:worker_id>", methods=["DELETE"])
def delete_worker(worker_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    # The prompt requested: "When Admin disables a Worker, Update worker_status = Inactive. Do not delete existing work history."
    # So we will interpret "delete" as disabling. 
    supabase = get_supabase()
    try:
        supabase.table("users").update({
            "worker_status": "Inactive"
        }).eq("id", worker_id).execute()
        return jsonify({"success": True, "message": "Worker marked as Inactive"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@worker_api.route("/admin/manage/<int:worker_id>/reset-password", methods=["PUT"])
def reset_password(worker_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    new_password = data.get("new_password")
    if not new_password:
        return jsonify({"error": "New password is required"}), 400
        
    password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    
    supabase = get_supabase()
    try:
        supabase.table("users").update({
            "password": password_hash
        }).eq("id", worker_id).execute()
        return jsonify({"success": True, "message": "Password reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# WORKER PROFILE & STATUS
# -----------------------------------------------------------------------------
@worker_api.route("/profile", methods=["GET"])
def get_profile():
    if session.get("role") != "worker":
        return jsonify({"error": "Unauthorized"}), 403
        
    worker_id = session.get("user_id")
    supabase = get_supabase()
    try:
        res = supabase.table("users").select("*").eq("id", worker_id).execute()
        worker = res.data[0] if res.data else None
        
        if not worker:
            return jsonify({"error": "Worker not found"}), 404
            
        worker.pop("password", None)
        return jsonify(worker)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@worker_api.route("/status", methods=["PUT"])
def update_status():
    if session.get("role") != "worker":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    new_status = data.get("status")
    valid_statuses = ["Available", "Busy", "Offline", "On Leave", "Inactive"]
    
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400
        
    worker_id = session.get("user_id")
    
    supabase = get_supabase()
    try:
        supabase.table("users").update({
            "worker_status": new_status
        }).eq("id", worker_id).execute()
        return jsonify({"success": True, "message": "Status updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
