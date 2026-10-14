from dataclasses import dataclass, field
from typing import Optional, List, Any
from models.reason import ReasonBundle

@dataclass
class Hazard:
    hazard_id: str
    db_id: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    severity: str = "Unknown"
    confidence: float = 0.0
    status: str = "Detected"
    source: str = "Unknown"
    image_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    report_count: int = 1
    
    # Advanced Municipal Merge fields
    latest_report_time: str = ""
    highest_confidence: float = 0.0
    images: List[str] = field(default_factory=list)
    history: List[Any] = field(default_factory=list)
    original_reports: List[Any] = field(default_factory=list)
    
    # Placeholders for future phases / Reverse Geocoder Compatibility
    road_name: str = "Unknown Road"
    road_display_name: str = "Unknown Road"
    location_summary: str = ""
    formatted_address: str = "Location unavailable"
    google_maps_url: str = ""
    street: str = ""
    village: str = ""
    hamlet: str = ""
    neighbourhood: str = ""
    suburb: str = ""
    town: str = ""
    district: str = "Unknown"
    state: str = ""
    country: str = ""
    postal_code: str = ""
    landmark: str = "Unavailable"
    nearby_place: str = ""
    traffic_importance: str = "Unknown"
    # Risk Intelligence Engine Fields (Phase 3)
    risk_score: int = 0
    risk_level: str = "Unknown"
    severity_score: int = 0
    confidence_score: int = 0
    report_score: int = 0
    age_score: int = 0
    road_score: int = 0
    traffic_score: int = 0
    risk_breakdown: dict = field(default_factory=dict)
    risk_reason: str = ""
    recommended_action: str = ""
    waiting_days: int = 0
    
    # Store full assignment dictionary for fast O(1) reads
    assignment: dict = field(default_factory=dict)
    
    is_repeated_location: bool = False
    is_high_traffic: bool = False
    requires_immediate_action: bool = False
    requires_assignment: bool = False
    requires_supervisor: bool = False
    requires_emergency_team: bool = False
    
    # Phase 5: Reasoning Engine Fields
    reason_bundle: ReasonBundle = field(default_factory=ReasonBundle)
    
    # Phase 4: Priority Engine Fields
    priority: str = "Low"
    priority_score: int = 0
    priority_rank: int = 0
    priority_breakdown: dict = field(default_factory=dict)
    priority_history: List[Any] = field(default_factory=list)
    priority_processed_at: str = ""
    priority_reason: str = ""
    escalation_level: int = 0
    maintenance_window: str = ""
    response_time: str = ""
    estimated_repair_days: str = ""
    requires_contract_team: bool = False
    requires_senior_engineer: bool = False
    requires_municipality: bool = False
    requires_public_notice: bool = False
    requires_road_closure: bool = False
    repair_category: str = "General"
    repair_queue_position: int = 999999
    
    # Placeholders for future phases / Maintenance Workflow
    maintenance_state: str = "Detected"
    assigned_worker_id: str = ""
    assigned_worker_name: str = ""
    assigned_team: str = ""
    assignment_id: str = ""
    assignment_status: str = "Unassigned"
    assignment_time: str = ""
    accepted_at: str = ""
    
    worker: str = ""
    worker_team: str = ""
    assigned_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    verified_at: str = ""
    verification_by: str = ""
    traffic_level: str = "Unknown"
    road_class: str = "Unknown"
    road_importance: int = 40
    zone: str = ""
    cluster_id: str = ""
    reverse_geocoded: bool = False
    
    def to_dict(self) -> dict:
        """Explicit DTO mapping to prevent RecursionError and return primitive types."""
        # Serialize ReasonBundle
        reasons_list = [
            {"code": r.code, "message": r.message, "confidence": r.confidence}
            for r in getattr(self.reason_bundle, 'reasons', [])
        ]
        
        # Compute Aggregated Data for UI
        agg_conf = self.confidence
        agg_sev = self.severity
        first_rep = self.created_at
        
        if getattr(self, 'original_reports', None) and len(self.original_reports) > 0:
            import datetime
            # Avg confidence
            confs = [r.confidence for r in self.original_reports if r.confidence is not None]
            if confs:
                agg_conf = sum(confs) / len(confs)
                
            # Avg severity
            sev_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            inv_map = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
            sevs = [sev_map.get(str(r.severity).lower(), 2) for r in self.original_reports if hasattr(r, 'severity')]
            if sevs:
                avg_s = round(sum(sevs) / len(sevs))
                agg_sev = inv_map.get(avg_s, "Medium")
                
            # First Report Date
            dates = []
            for r in self.original_reports:
                if hasattr(r, 'created_at') and r.created_at:
                    try:
                        dates.append(datetime.datetime.fromisoformat(r.created_at.replace("Z", "+00:00")))
                    except:
                        pass
            if dates:
                first_rep = min(dates).isoformat()
        
        # Prefer raw assignment dict if present to guarantee fresh cache
        a_dict = getattr(self, "assignment", {}) or {}
        
        return {
            "id": self.hazard_id,
            "display_id": self.hazard_id,
            "hazard_id": self.db_id,
            "type": "Hazard",
            "source": self.source,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image_url,
            "severity": agg_sev,
            "confidence": agg_conf,
            "report_count": self.report_count,
            "created_at": self.created_at,
            "first_reported_at": first_rep,
            "last_seen": self.latest_report_time or self.created_at,
            
            "status": a_dict.get("status") or getattr(self, "status", "Pending") or "Pending",
            "maintenance_state": a_dict.get("status") or getattr(self, "maintenance_state", None) or getattr(self, "status", "Pending") or "Pending",
            "road_name": getattr(self, "road_name", "Unknown Road"),
            "street_name": getattr(self, "street", ""),
            "landmark": getattr(self, "landmark", "Unavailable"),
            "village": self.village,
            "hamlet": getattr(self, "hamlet", ""),
            "neighbourhood": getattr(self, "neighbourhood", ""),
            "suburb": getattr(self, "suburb", ""),
            "town": self.town,
            "district": self.district,
            "state": self.state,
            "country": self.country,
            "formatted_address": getattr(self, "formatted_address", "Location unavailable"),
            "road_class": getattr(self, "road_class", "Unknown"),
            "road_importance": getattr(self, "road_importance", 10),
            "traffic_importance": getattr(self, 'traffic_importance', 'Unknown'),
            "traffic_score": getattr(self, 'traffic_score', 10),
            
            "priority": self.priority,
            "priority_score": self.priority_score,
            "priority_rank": self.priority_rank,
            "priority_reason": self.priority_reason,
            "priority_breakdown": {
                "risk_score": self.risk_score,
                "waiting_days": self.waiting_days,
                "report_count": self.report_count,
                "road_importance": self.road_importance,
                "traffic_importance": getattr(self, 'traffic_importance', 'Unknown'),
                "emergency_rule": getattr(self, 'requires_emergency_team', False) or getattr(self, 'is_emergency', False),
                "critical_rule": self.priority == "Critical"
            },
            "waiting_days": self.waiting_days,
            
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_breakdown": dict(self.risk_breakdown) if self.risk_breakdown else {},
            
            "reason_bundle": reasons_list,
            
            "recommendation": {
                "team": (self.reason_bundle.recommendations.get("team", self.assigned_team) if hasattr(self.reason_bundle, 'recommendations') else self.assigned_team) or "Pending",
                "vehicle": (self.reason_bundle.recommendations.get("vehicle", "Unknown") if hasattr(self.reason_bundle, 'recommendations') else "Unknown"),
                "equipment": (self.reason_bundle.recommendations.get("equipment", []) if hasattr(self.reason_bundle, 'recommendations') else []),
                "repair_category": self.repair_category or "Unknown",
                "estimated_repair_days": self.estimated_repair_days or "Unknown",
                "response_time": self.response_time or "Unknown"
            },
            
            "workflow": {
                "state": a_dict.get("status") or self.maintenance_state or "Detected",
                "assigned_to": a_dict.get("worker_name") or self.assigned_worker_name or "Unassigned",
                "verified_at": a_dict.get("verified_at") or self.verified_at or "",
                "completed_at": a_dict.get("repair_completed_at") or a_dict.get("completed_at") or self.completed_at or ""
            },
            
            "assignment": {
                "status": a_dict.get("status") or self.assignment_status or "Unassigned",
                "worker_id": a_dict.get("worker_id") or self.assigned_worker_id or "",
                "worker_name": a_dict.get("worker_name") or self.assigned_worker_name or "",
                "time": a_dict.get("assigned_time") or self.assignment_time or "",
                "accepted_at": a_dict.get("accepted_at") or self.accepted_at or "",
                "travelling_at": a_dict.get("travelling_at", ""),
                "reached_at": a_dict.get("reached_at", ""),
                "repair_started_at": a_dict.get("repair_started_at") or a_dict.get("started_at") or self.started_at or "",
                "repair_completed_at": a_dict.get("repair_completed_at") or a_dict.get("completed_at") or self.completed_at or "",
                "verified_at": a_dict.get("verified_at") or self.verified_at or ""
            }
        }
