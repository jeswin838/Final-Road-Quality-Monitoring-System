import logging
import datetime
import time
import hashlib
from typing import List
from models.hazard import Hazard
from models.reason import Reason, ReasonBundle
from services.action_generator import generate_recommended_actions
from services.recommendation_engine import generate_recommendations
from services.summary_builder import (
    build_summary, build_citizen_message, 
    build_engineer_message, build_supervisor_message
)
from utils.reason_constants import REASON_VERSION

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """Enterprise Reasoning Engine to deterministically explain Hazards."""
    
    @staticmethod
    def process(hazard: Hazard) -> Hazard:
        """Enriches a single hazard with a complete ReasonBundle."""
        start_time = time.time()
        try:
            priority = getattr(hazard, 'priority', 'Low')
            priority_clean = str(priority).lower().strip()
            
            # --- Wait Days Calculation ---
            now = datetime.datetime.now(datetime.timezone.utc)
            
            def parse_date(date_str):
                if not date_str:
                    return datetime.datetime.now(datetime.timezone.utc)
                clean = date_str.replace("Z", "+00:00")
                try:
                    dt = datetime.datetime.fromisoformat(clean)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    return dt
                except Exception:
                    try:
                        dt = datetime.datetime.strptime(clean.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        return dt.replace(tzinfo=datetime.timezone.utc)
                    except Exception:
                        return datetime.datetime.now(datetime.timezone.utc)

            first_rep = getattr(hazard, 'first_reported_at', None)
            if not first_rep:
                dates = []
                for r in getattr(hazard, 'original_reports', []):
                    d_str = getattr(r, 'created_at', None) or getattr(r, 'first_reported_at', None)
                    if d_str:
                        dates.append(parse_date(d_str))
                if dates:
                    first_date = min(dates)
                else:
                    first_date = parse_date(hazard.created_at)
            else:
                first_date = parse_date(first_rep)
                
            wait_days = max(0, (now - first_date).days)
            
            # --- Deterministic Choice Helper ---
            hazard_id = hazard.hazard_id or hazard.cluster_id or "unknown"
            
            def get_choice(category: str, options: list) -> str:
                seed_str = f"{hazard_id}_{category}"
                hash_val = int(hashlib.md5(seed_str.encode('utf-8')).hexdigest(), 16)
                idx = hash_val % len(options)
                return options[idx]
                
            # --- Category 1: Severity ---
            sev = str(getattr(hazard, 'severity', 'Low')).lower().strip()
            sev_options = {
                "low": [
                    "Minor surface deterioration detected. Suitable for planned routine maintenance.",
                    "Superficial road distress observed. Poses negligible immediate risk to traffic.",
                    "Initial stage pavement wearing identified. Recommended for standard monitoring."
                ],
                "medium": [
                    "Moderate structural wear observed on the roadway pavement.",
                    "Pavement degradation has reached intermediate levels, requiring scheduling.",
                    "Noticeable localized surface deformities detected. Normal priority for repair crews."
                ],
                "high": [
                    "Significant road distress identified, with potential to deteriorate rapidly.",
                    "Substantial pavement damage present. Intervention is required to prevent vehicle damage.",
                    "High-impact surface anomalies detected. Remediation should be scheduled promptly."
                ],
                "critical": [
                    "Severe pavement failure detected with immediate safety implications.",
                    "Critical structural defect observed. Immediate intervention is recommended to reduce accident risk.",
                    "Dangerous roadway damage detected. Requires rapid deployment to preserve traffic safety."
                ],
                "emergency": [
                    "Catastrophic roadway structural collapse or severe hazard zone identified.",
                    "Extreme pavement hazard presenting immediate, high-probability danger to life and property.",
                    "Severe hazard demanding emergency closure or immediate barricading/repair."
                ]
            }
            sev_key = sev if sev in sev_options else "low"
            msg_sev = get_choice("severity", sev_options[sev_key])
            
            # --- Category 2: AI Confidence ---
            conf = getattr(hazard, 'confidence', 0.0)
            conf_pct = conf * 100.0 if conf <= 1.0 else conf
            
            if conf_pct >= 95:
                conf_list = [
                    f"AI detection confidence is extremely high ({conf_pct:.1f}%), confirming visual telemetry.",
                    f"Computer vision analysis confirms the hazard with near-absolute certainty ({conf_pct:.1f}% confidence).",
                    f"Automated inspection system reports maximum confidence ({conf_pct:.1f}%) in this detection."
                ]
            elif conf_pct >= 90:
                conf_list = [
                    f"High confidence AI detection ({conf_pct:.1f}%) suggests a clear structural defect.",
                    f"Vision system reports high certainty ({conf_pct:.1f}%), minimizing likelihood of false positive.",
                    f"Strong AI verification model match ({conf_pct:.1f}%) indicates validated anomaly."
                ]
            elif conf_pct >= 80:
                conf_list = [
                    f"Reliable AI confidence level ({conf_pct:.1f}%) is aligned with typical pavement anomalies.",
                    f"Neural network reports a solid classification match of {conf_pct:.1f}%.",
                    f"Visual analysis model flags the location with a confident {conf_pct:.1f}% rating."
                ]
            elif conf_pct >= 70:
                conf_list = [
                    f"Moderate AI detection confidence ({conf_pct:.1f}%). Secondary verification is recommended.",
                    f"Model classification certainty stands at {conf_pct:.1f}%. Field verification advised.",
                    f"Vision telemetry confidence is moderate ({conf_pct:.1f}%), suggesting optional ground check."
                ]
            elif conf_pct >= 60:
                conf_list = [
                    f"Borderline AI model confidence ({conf_pct:.1f}%). Field crew verification is recommended.",
                    f"Computer vision engine reports limited confidence ({conf_pct:.1f}%). On-site confirmation advised.",
                    f"Model classification confidence is {conf_pct:.1f}%, warranting secondary inspection."
                ]
            else:
                conf_list = [
                    f"Low detection confidence ({conf_pct:.1f}%). Inspection team must perform physical validation.",
                    f"Computer vision classification certainty is low ({conf_pct:.1f}%). High chance of false anomaly; validation required.",
                    f"Visual processing model reports sub-standard confidence ({conf_pct:.1f}%). On-site inspection should confirm detection."
                ]
            msg_conf = get_choice("confidence", conf_list)
            
            # --- Category 3: Report Count ---
            count = getattr(hazard, 'report_count', 1)
            if count <= 1:
                count_list = [
                    "Initial citizen report registered for this location.",
                    "Single complaint recorded. Ground-truth validation pending.",
                    "First public notification received concerning this road section."
                ]
            elif count <= 5:
                count_list = [
                    f"Multiple independent public reports ({count}) corroborate this roadway defect.",
                    f"A cluster of {count} citizen notifications indicates growing local awareness.",
                    f"Road Operations Center received {count} separate reports from motorists."
                ]
            elif count <= 20:
                count_list = [
                    f"Repeated citizen complaints ({count} reports) verify sustained local impact.",
                    f"Growing public reporting volume ({count} complaints) indicates escalating neighborhood concern.",
                    f"A total of {count} community alerts have flagged this location."
                ]
            elif count <= 50:
                count_list = [
                    f"High community reporting activity ({count} reports) indicates substantial road obstruction.",
                    f"The defect has generated sustained public concern with {count} reports filed.",
                    f"A total of {count} citizen notifications highlight this as a high-visibility concern."
                ]
            elif count <= 100:
                count_list = [
                    f"Extreme reporting volume ({count} reports) suggests significant neighborhood disruption.",
                    f"Over {count} citizen reports indicate this issue has heavily impacted local motorists.",
                    f"Significant public outcry ({count} separate tickets) logged at this intersection."
                ]
            else:
                count_list = [
                    f"Exceptionally high reporting volume ({count}) indicates prolonged community impact and safety issues.",
                    f"Widespread public reporting ({count} complaints) signals severe municipal road system issues.",
                    f"Massive reporting activity ({count} files) indicates critical public concern requiring administrative attention."
                ]
            msg_count = get_choice("report_count", count_list)
            
            # --- Category 4: Waiting Time ---
            if wait_days <= 1:
                wait_list = [
                    "Recently detected hazard. Dispatch cycle is within acceptable timeline.",
                    "Fresh defect log. Standard response queue rules apply.",
                    "Newly reported condition. Currently under standard processing times."
                ]
            elif wait_days <= 7:
                wait_list = [
                    f"The hazard has remained unresolved for {wait_days} days despite citizen logs.",
                    f"Defect backlog age is {wait_days} days. Crew scheduling is pending.",
                    f"Issue has been active for {wait_days} days. Standard mitigation threshold reached."
                ]
            elif wait_days <= 30:
                wait_list = [
                    f"Maintenance response appears delayed ({wait_days} days since initial report).",
                    f"Hazard has been active for {wait_days} days. Elevating ticket priority.",
                    f"Aging defect active for {wait_days} days. Recommended for scheduling push."
                ]
            elif wait_days <= 90:
                wait_list = [
                    f"Long-term unresolved infrastructure issue ({wait_days} days active).",
                    f"Critical backlog delay: hazard has sat for {wait_days} days without repair.",
                    f"Substantial resolution delay of {wait_days} days. Supervisor review advised."
                ]
            else:
                wait_list = [
                    f"Severe administrative escalation recommended ({wait_days} days unresolved).",
                    f"Unacceptable backlog age ({wait_days} days). Requires emergency allocation of public works resource.",
                    f"Prolonged backlog item outstanding for {wait_days} days. Formal audit review recommended."
                ]
            msg_wait = get_choice("waiting_time", wait_list)
            
            # --- Category 5: Risk Score ---
            score = getattr(hazard, 'risk_score', 0)
            if score <= 25:
                score_list = [
                    f"Low municipal hazard risk profile (Risk Score: {score}).",
                    f"Negligible operational impact (Risk Score: {score}).",
                    f"Overall risk index is minimal ({score}/100)."
                ]
            elif score <= 50:
                score_list = [
                    f"Minor operational impact requiring planned intervention (Risk Score: {score}).",
                    f"Moderate overall risk profile ({score}/100) suitable for standard maintenance workflows.",
                    f"Intermediate priority hazard score of {score} logged."
                ]
            elif score <= 75:
                score_list = [
                    f"Significant operational risk index of {score}/100. Routine crew deployment recommended.",
                    f"Moderate to high operational risk profile ({score}) requiring scheduled repair.",
                    f"Pavement defect risk has reached elevated index ({score}), recommending dispatch focus."
                ]
            elif score <= 90:
                score_list = [
                    f"High overall operational risk ({score}/100). Remediation should be accelerated.",
                    f"Elevated safety risk score ({score}) suggests urgent allocation in dispatch queue.",
                    f"Substantial threat level ({score}/100) to standard road safety and vehicle integrity."
                ]
            else:
                score_list = [
                    f"Overall operational risk is extremely high ({score}/100), posing immediate threats.",
                    f"Maximal safety risk profile ({score}/100) logged. Extreme structural danger.",
                    f"Severe threat matrix ({score}/100) demands immediate physical intervention."
                ]
            msg_score = get_choice("risk_score", score_list)
            
            # --- Category 6: Assignment Status ---
            assign_status = "Unassigned"
            assign_dict = getattr(hazard, 'assignment', None)
            if assign_dict and isinstance(assign_dict, dict):
                assign_status = assign_dict.get('status', 'Unassigned')
            elif hasattr(hazard, 'assignment_status') and hazard.assignment_status:
                assign_status = hazard.assignment_status
                
            assign_status_clean = str(assign_status).lower().strip()
            if "completed" in assign_status_clean or "done" in assign_status_clean:
                assign_list = [
                    "Physical repair completed; awaiting supervisor verification.",
                    "Remediation works finished on site. Pending closing inspection.",
                    "Patching completed. Work order is in verification stage."
                ]
            elif "started" in assign_status_clean or "progress" in assign_status_clean:
                assign_list = [
                    "Repair activities are actively in progress on-site.",
                    "On-site remediation and patching are currently underway.",
                    "Maintenance crew has initiated physical repair works."
                ]
            elif "travel" in assign_status_clean or "route" in assign_status_clean:
                assign_list = [
                    "Response team is currently en route to the location.",
                    "Assigned maintenance vehicle is travelling to the coordinate.",
                    "Crew is currently in transit to begin remediation."
                ]
            elif "assigned" in assign_status_clean or "allocated" in assign_status_clean:
                assign_list = [
                    "A maintenance crew has been allocated and assigned to this ticket.",
                    "Repair team is scheduled for deployment to this site.",
                    "Workforce crew assigned. Scheduling window confirmed."
                ]
            else:
                assign_list = [
                    "No crew has been allocated to this hazard yet.",
                    "Currently waiting in the maintenance dispatch queue.",
                    "Crew assignment is currently pending."
                ]
            msg_assign = get_choice("assignment", assign_list)
            
            # --- Category 7: Verification Status ---
            status_str = str(getattr(hazard, 'status', 'Pending')).lower().strip()
            if "verified" in status_str:
                ver_list = [
                    "Hazard detection verified by authorized municipal inspector.",
                    "Quality review verified; defect presence officially confirmed.",
                    "Incident report validated through inspection process."
                ]
            elif "rejected" in status_str:
                ver_list = [
                    "Report rejected by audit review; flagged as false detection.",
                    "Incident review rejected the hazard marker. Work ticket dismissed.",
                    "Ground check confirmed no hazard present; status marked Rejected."
                ]
            else:
                ver_list = [
                    "Verification is pending; currently awaiting physical inspection.",
                    "Status remains pending municipal inspector validation.",
                    "Field verification cycle is open for this report."
                ]
            msg_ver = get_choice("verification", ver_list)
            
            # --- Category 8: Priority ---
            if "emergency" in priority_clean:
                pri_list = [
                    "Emergency deployment required. Intercept location immediately.",
                    "Deploy emergency crew for immediate barricading and temporary patching.",
                    "Immediate tactical closure and correction required to prevent road accidents."
                ]
            elif "critical" in priority_clean:
                pri_list = [
                    "Immediate operational intervention recommended to secure pavement integrity.",
                    "Critical dispatch priority. Deploy field crew as an priority work order.",
                    "Action recommended within 12-24 hours to secure safe vehicle traversal."
                ]
            elif "high" in priority_clean:
                pri_list = [
                    "Accelerated remediation schedule advised within 48 hours.",
                    "High priority dispatch. Allocate crew within next shift cycles.",
                    "Remediation recommended on next priority crew run."
                ]
            elif "medium" in priority_clean:
                pri_list = [
                    "Planned repair is recommended in the current monthly cycle.",
                    "Standard priority work order. Schedule remediation within next 14 business days.",
                    "Queue for standard dispatch workflow. Address during local zone repair sweeps."
                ]
            else:
                pri_list = [
                    "Routine schedule recommended. Remediation will occur in normal maintenance cycle.",
                    "Low priority work order. Monitor for deterioration during weekly sweeps.",
                    "Schedule for routine patching. No immediate tactical action required."
                ]
            msg_pri = get_choice("priority", pri_list)
            
            # --- Assemble Dynamic Bullets ---
            if "emergency" in priority_clean:
                bullet_count = 8
            elif "critical" in priority_clean:
                bullet_count = 7
            elif "high" in priority_clean:
                bullet_count = 6
            elif "medium" in priority_clean:
                bullet_count = 5
            else:
                bullet_count = 4
                
            all_bullets = [msg_sev, msg_conf, msg_count, msg_wait, msg_score, msg_assign, msg_ver, msg_pri]
            selected_bullets = all_bullets[:bullet_count]
            
            # --- Convert to Reason Objects ---
            categories = [
                ("severity", "Operational Severity", 10),
                ("confidence", "AI Telemetry Confidence", 20),
                ("report_count", "Public Report Analytics", 30),
                ("waiting_time", "Operational Backlog Time", 40),
                ("risk_score", "Systemic Risk Index", 50),
                ("assignment", "Crew Allocation Status", 60),
                ("verification", "Audit Verification Status", 70),
                ("priority", "Operational Action Recommendation", 80)
            ]
            
            reason_list = []
            for i in range(bullet_count):
                cat_name, cat_desc, cat_priority = categories[i]
                msg = selected_bullets[i]
                r = Reason(
                    code=f"R_{cat_name.upper()}_01",
                    category=cat_desc,
                    priority=cat_priority,
                    message=msg,
                    severity=hazard.severity,
                    confidence=hazard.confidence,
                    template=msg,
                    arguments={}
                )
                reason_list.append(r)
            
            # Generators
            actions = generate_recommended_actions(hazard)
            recommendations = generate_recommendations(hazard)
            
            # Summaries and Messages
            summary = build_summary(hazard, reason_list)
            citizen_message = build_citizen_message(priority)
            engineer_message = build_engineer_message(hazard, reason_list, actions)
            supervisor_message = build_supervisor_message(hazard, reason_list)
            
            generated_at = datetime.datetime.now().isoformat()
            processing_ms = round((time.time() - start_time) * 1000, 3)
            
            # Construct ReasonBundle
            hazard.reason_bundle = ReasonBundle(
                summary=summary,
                citizen_message=citizen_message,
                engineer_message=engineer_message,
                supervisor_message=supervisor_message,
                actions=actions,
                recommendations=recommendations,
                reasons=reason_list,
                priority=priority,
                generated_time=generated_at,
                version=REASON_VERSION,
                processing_ms=processing_ms
            )
            
            logger.info(
                f"[ReasoningEngine] {hazard.hazard_id} | "
                f"Severity={hazard.severity} | "
                f"Confidence={hazard.confidence:.2f} | "
                f"Reports={hazard.report_count} | "
                f"Waiting={wait_days} | "
                f"Priority={hazard.priority} | "
                f"Generated={len(hazard.reason_bundle.reasons)} reasons"
            )
            
        except Exception as e:
            logger.exception(f"[ReasoningEngine] Failed to generate reasons for {hazard.hazard_id}: {e}")
            
        return hazard
        
    @staticmethod
    def process_all(hazards: List[Hazard]) -> List[Hazard]:
        """Processes a batch of hazards."""
        for h in hazards:
            ReasoningEngine.process(h)
        return hazards
