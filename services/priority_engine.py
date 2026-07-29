import datetime
import logging
from typing import List
from models.hazard import Hazard
from config import Config
from utils.priority_constants import (
    PRIORITY_WEIGHTS, PRIORITY_THRESHOLDS, REPAIR_CATEGORIES,
    ESTIMATED_REPAIR_DAYS
)
from utils.priority_rules import (
    calculate_road_priority, calculate_traffic_priority,
    calculate_waiting_priority, calculate_report_priority,
    calculate_emergency_priority, determine_escalation_level,
    generate_priority_reason
)

logger = logging.getLogger(__name__)

class PriorityEngine:
    """Enterprise Priority Engine to determine maintenance queues."""
    
    @staticmethod
    def calculate(hazard: Hazard) -> Hazard:
        """Calculates Priority Score, Flags, and Operational Metadata."""
        
        # Component Scores (No getattr)
        r_score = hazard.risk_score or 0
        road_imp = hazard.road_importance or 10
        road_cls = hazard.road_class or "Unknown"
        waiting = hazard.waiting_days or 0
        reports = hazard.report_count or 1
        
        p_risk = r_score * PRIORITY_WEIGHTS["risk"]
        p_road = calculate_road_priority(road_imp) * PRIORITY_WEIGHTS["road"]
        p_traffic = calculate_traffic_priority(road_cls) * PRIORITY_WEIGHTS["traffic"]
        p_wait = calculate_waiting_priority(waiting) * PRIORITY_WEIGHTS["waiting"]
        p_rep = calculate_report_priority(reports) * PRIORITY_WEIGHTS["reports"]
        p_emg = calculate_emergency_priority(hazard) * PRIORITY_WEIGHTS["emergency"]
        
        raw_score = p_risk + p_road + p_traffic + p_wait + p_rep + p_emg
        
        hazard.priority_breakdown = {
            "risk": round(p_risk, 2),
            "road": round(p_road, 2),
            "traffic": round(p_traffic, 2),
            "waiting": round(p_wait, 2),
            "reports": round(p_rep, 2),
            "emergency": round(p_emg, 2)
        }
        
        hazard.priority_score = int(min(100, max(0, raw_score)))
        
        # Priority Level
        if hazard.priority_score >= PRIORITY_THRESHOLDS["Emergency"]:
            hazard.priority = "Emergency"
        elif hazard.priority_score >= PRIORITY_THRESHOLDS["Critical"]:
            hazard.priority = "Critical"
        elif hazard.priority_score >= PRIORITY_THRESHOLDS["High"]:
            hazard.priority = "High"
        elif hazard.priority_score >= PRIORITY_THRESHOLDS["Medium"]:
            hazard.priority = "Medium"
        else:
            hazard.priority = "Low"
            
        hazard.priority_processed_at = datetime.datetime.now().isoformat()
        
        # Metadata Assignment
        hazard.repair_category = REPAIR_CATEGORIES.get(hazard.priority, "Scheduled Maintenance")
        
        # Escalation & Reason (Needs repair_category for reason)
        hazard.escalation_level = determine_escalation_level(hazard)
        hazard.priority_reason = generate_priority_reason(hazard)
        
        if not hazard.priority_history or (hazard.priority_history and hazard.priority_history[-1].get("priority") != hazard.priority):
            hazard.priority_history.append({
                "priority": hazard.priority,
                "score": hazard.priority_score,
                "reason": hazard.priority_reason,
                "timestamp": hazard.priority_processed_at
            })
        
        # Maintenance Window (Timestamp generation from Config)
        now = datetime.datetime.now()
        if hazard.priority == "Emergency":
            hazard.maintenance_window = (now + datetime.timedelta(hours=getattr(Config, 'EMERGENCY_REPAIR_HOURS', 4))).isoformat()
            hazard.response_time = f"{getattr(Config, 'EMERGENCY_REPAIR_HOURS', 4)} hours"
        elif hazard.priority == "Critical":
            hazard.maintenance_window = (now + datetime.timedelta(hours=getattr(Config, 'CRITICAL_REPAIR_HOURS', 8))).isoformat()
            hazard.response_time = f"{getattr(Config, 'CRITICAL_REPAIR_HOURS', 8)} hours"
        elif hazard.priority == "High":
            hazard.maintenance_window = (now + datetime.timedelta(days=getattr(Config, 'HIGH_REPAIR_DAYS', 2))).isoformat()
            hazard.response_time = f"{getattr(Config, 'HIGH_REPAIR_DAYS', 2)} days"
        elif hazard.priority == "Medium":
            hazard.maintenance_window = (now + datetime.timedelta(days=getattr(Config, 'MEDIUM_REPAIR_DAYS', 7))).isoformat()
            hazard.response_time = f"{getattr(Config, 'MEDIUM_REPAIR_DAYS', 7)} days"
        else:
            hazard.maintenance_window = (now + datetime.timedelta(days=getattr(Config, 'LOW_REPAIR_DAYS', 30))).isoformat()
            hazard.response_time = f"{getattr(Config, 'LOW_REPAIR_DAYS', 30)} days"
            
        hazard.estimated_repair_days = ESTIMATED_REPAIR_DAYS.get(hazard.priority, "30 min")
        
        # Booleans
        hazard.requires_road_closure = (hazard.priority == "Emergency" and road_imp >= 80)
        hazard.requires_public_notice = (hazard.priority == "Emergency" or hazard.requires_road_closure or reports >= 20)
        
        hazard.requires_senior_engineer = (hazard.priority == "Emergency" or hazard.escalation_level >= 4)
        hazard.requires_municipality = (road_imp >= 80 or getattr(hazard, 'zone', '') == "Municipal")
        hazard.requires_contract_team = (hazard.priority in ["Emergency", "Critical"])
        
        return hazard
        
    @staticmethod
    def calculate_all(hazards: List[Hazard]) -> List[Hazard]:
        """Calculates priorities and ranks hazards in a single O(N log N) sort."""
        for h in hazards:
            try:
                PriorityEngine.calculate(h)
            except Exception as e:
                logger.exception(f"Error calculating priority for hazard {h.hazard_id}: {e}")
            
        # Sort highest priority score first
        # Resolve ties with waiting_days, then report_count, risk_score, created_at
        hazards.sort(
            key=lambda h: (
                h.priority_score or 0,
                h.waiting_days or 0,
                h.report_count or 1,
                h.risk_score or 0,
                h.created_at or ""
            ),
            reverse=True
        )
        
        # Assign rank and queue position (Keep separate logically even if equal)
        for i, h in enumerate(hazards):
            rank = i + 1
            h.priority_rank = rank
            h.repair_queue_position = rank
            
            logger.info(
                f"\n[PRIORITY]\n"
                f"Hazard {h.hazard_id}\n"
                f"Priority : {h.priority}\n"
                f"Score    : {h.priority_score}\n"
                f"Rank     : {h.priority_rank}\n"
                f"Queue    : {h.repair_queue_position}\n"
                f"Due      : {h.maintenance_window}\n"
                f"Road     : {getattr(h, 'road_class', 'Unknown')} ({getattr(h, 'road_name', '')})\n"
                f"Reason   : {h.priority_reason}"
            )
            
        return hazards
