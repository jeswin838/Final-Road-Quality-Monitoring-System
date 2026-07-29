import logging
from models.hazard import Hazard
from utils.risk_constants import (
    RISK_MAX_SCORE, CRITICAL_THRESHOLD, HIGH_THRESHOLD, MEDIUM_THRESHOLD,
    REPEATED_REPORT_THRESHOLD
)
from utils.risk_rules import (
    calculate_severity_score, calculate_confidence_score, calculate_report_score,
    calculate_waiting_days, calculate_age_score, calculate_road_score,
    calculate_traffic_score, generate_reason, generate_action
)

logger = logging.getLogger(__name__)

class RiskEngine:
    """Enterprise Risk Intelligence Engine to calculate hazard risks."""
    
    @staticmethod
    def calculate(hazard: Hazard) -> Hazard:
        """
        Calculates all risk scores and thresholds, enriching the Hazard object.
        Runs in O(1) per hazard, avoiding DB queries.
        """
        # Calculate Waiting Days dynamically
        hazard.waiting_days = calculate_waiting_days(hazard.created_at)
        
        # Calculate Individual Component Scores
        hazard.severity_score = calculate_severity_score(hazard.severity)
        hazard.confidence_score = calculate_confidence_score(hazard.highest_confidence if hasattr(hazard, 'highest_confidence') and hazard.highest_confidence > 0 else hazard.confidence)
        hazard.report_score = calculate_report_score(hazard.report_count)
        hazard.age_score = calculate_age_score(hazard.waiting_days)
        
        # Extract location metadata if reverse geocoded
        # If not, it defaults to 10 for unknown road importance
        road_imp = hazard.road_importance if hasattr(hazard, 'road_importance') else 10
        road_cls = hazard.road_class if hasattr(hazard, 'road_class') else "Unknown"
        
        hazard.road_score = calculate_road_score(road_imp)
        hazard.traffic_score = calculate_traffic_score(road_cls)
        
        # Total Risk Score (Sum of weights)
        raw_score = (
            hazard.severity_score +
            hazard.confidence_score +
            hazard.report_score +
            hazard.age_score +
            hazard.road_score +
            hazard.traffic_score
        )
        
        hazard.risk_breakdown = {
            "severity": hazard.severity_score,
            "confidence": hazard.confidence_score,
            "reports": hazard.report_score,
            "age": hazard.age_score,
            "road": hazard.road_score,
            "traffic": hazard.traffic_score
        }
        
        # Normalize strictly to 0-100
        hazard.risk_score = min(RISK_MAX_SCORE, max(0, raw_score))
        
        # Calculate Risk Level
        if hazard.risk_score >= CRITICAL_THRESHOLD:
            hazard.risk_level = "Critical"
        elif hazard.risk_score >= HIGH_THRESHOLD:
            hazard.risk_level = "High"
        elif hazard.risk_score >= MEDIUM_THRESHOLD:
            hazard.risk_level = "Medium"
        else:
            hazard.risk_level = "Low"
            
        # Boolean Threshold Flags
        hazard.is_repeated_location = hazard.report_count > REPEATED_REPORT_THRESHOLD
        hazard.is_high_traffic = hazard.traffic_score >= 15
        
        hazard.requires_emergency_team = (hazard.risk_level == "Critical" and hazard.is_high_traffic)
        hazard.requires_supervisor = hazard.waiting_days > 30
        hazard.requires_assignment = hazard.risk_level in ["Critical", "High"]
        
        hazard.requires_immediate_action = (hazard.risk_level == "Critical" or hazard.waiting_days > 14)
        
        # Reason and Action Generators
        hazard.risk_reason = generate_reason(hazard)
        hazard.recommended_action = generate_action(hazard)
        
        logger.info(
            f"[RISK] [SCORE] Hazard {hazard.hazard_id} | "
            f"Total: {hazard.risk_score} ({hazard.risk_level}) | "
            f"[WAIT] {hazard.waiting_days}d | "
            f"[REPORTS] {hazard.report_count} | "
            f"[ROAD] {road_cls} | "
            f"[CRITICAL] {hazard.requires_immediate_action} | "
            f"[EMERGENCY] {hazard.requires_emergency_team}"
        )
        
        return hazard
        
    @staticmethod
    def calculate_all(hazards):
        return [RiskEngine.calculate(h) for h in hazards]
