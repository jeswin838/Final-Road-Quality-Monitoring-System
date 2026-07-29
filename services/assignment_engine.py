import datetime
import time
from models.hazard import Hazard
from models.assignment_recommendation import AssignmentRecommendation, AssignmentRecommendationBundle
from repositories.worker_repository import WorkerRepository
from services.assignment_rules import (
    evaluate_and_rank_workers, 
    determine_required_vehicle, 
    determine_required_equipment,
    determine_reason
)
from utils.assignment_helpers import calculate_haversine_distance, estimate_travel_time

ENGINE_VERSION = "2.0"

class AssignmentEngine:
    def __init__(self):
        self.worker_repo = WorkerRepository()

    def generate_recommendations(self, hazard: Hazard) -> AssignmentRecommendationBundle:
        """
        Pure decision service. Does NOT save to DB.
        Generates Top 5 recommendations based on current worker state.
        """
        workers = self.worker_repo.get_all_workers()
        ranked = evaluate_and_rank_workers(hazard, workers)
        
        top_recs = []
        h_lat = getattr(hazard, 'latitude', 0.0)
        h_lng = getattr(hazard, 'longitude', 0.0)
        
        req_vehicle = determine_required_vehicle(hazard)
        req_equipment = determine_required_equipment(hazard)
        
        # Take Top 5
        for w, score, breakdown in ranked[:5]:
            dist = 0.0
            eta = 0.0
            if h_lat and h_lng and w.latitude and w.longitude:
                dist = calculate_haversine_distance(h_lat, h_lng, w.latitude, w.longitude)
                eta = estimate_travel_time(dist)
                
            reason = determine_reason(breakdown)
            
            rec = AssignmentRecommendation(
                worker_id=w.worker_id,
                worker_name=w.name,
                recommended_team=w.team,
                recommended_vehicle=req_vehicle,
                recommended_equipment=req_equipment,
                recommended_eta=round(eta, 2),
                recommended_distance=round(dist, 2),
                recommendation_score=score,
                score_breakdown=breakdown,
                recommendation_reason=reason
            )
            top_recs.append(rec)
            
        # Failsafe if empty
        if not top_recs:
            rec = AssignmentRecommendation(
                worker_id="MUNI-01",
                worker_name="Municipality Fallback Team",
                recommended_team="Municipality Team",
                recommended_vehicle="Truck",
                recommended_equipment=[],
                recommended_eta=24.0,
                recommended_distance=0.0,
                recommendation_score=0.0,
                score_breakdown={},
                recommendation_reason="No eligible internal worker available."
            )
            top_recs.append(rec)
            
        now = datetime.datetime.now().isoformat()
        
        bundle = AssignmentRecommendationBundle(
            hazard_id=hazard.hazard_id,
            recommendations=top_recs,
            engine_version=ENGINE_VERSION,
            generated_time=now
        )
        
        return bundle
