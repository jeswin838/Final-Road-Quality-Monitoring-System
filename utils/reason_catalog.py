"""
Reason Catalog
Stores rich deterministic templates for the Reasoning Engine.
"""

REASON_CATALOG = {
    # Safety
    "R_SEV_01": {"template": "Large road damage detected.", "priority": 1, "category": "Safety", "severity": "Critical"},
    "R_SEV_02": {"template": "Severe pothole detected.", "priority": 2, "category": "Safety", "severity": "High"},
    "R_SEV_03": {"template": "Moderate road deterioration detected.", "priority": 4, "category": "Safety", "severity": "Medium"},
    "R_SEV_04": {"template": "Minor surface damage detected.", "priority": 6, "category": "Safety", "severity": "Low"},

    # Verification
    "R_CON_01": {"template": "Very high confidence AI detection.", "priority": 5, "category": "Verification", "severity": "Medium"},
    "R_CON_02": {"template": "High confidence AI detection.", "priority": 5, "category": "Verification", "severity": "Medium"},
    "R_CON_03": {"template": "Moderate confidence detection.", "priority": 6, "category": "Verification", "severity": "Low"},
    "R_CON_04": {"template": "Verification recommended.", "priority": 4, "category": "Verification", "severity": "Medium"},

    # Citizen
    "R_REP_01": {"template": "Repeated citizen complaints detected ({count} reports).", "priority": 1, "category": "Citizen", "severity": "High"},
    "R_REP_02": {"template": "Frequently reported hazard ({count} reports).", "priority": 3, "category": "Citizen", "severity": "Medium"},
    "R_REP_03": {"template": "Multiple complaints received.", "priority": 4, "category": "Citizen", "severity": "Medium"},
    "R_REP_04": {"template": "Newly detected hazard.", "priority": 7, "category": "Citizen", "severity": "Low"},

    # Maintenance
    "R_WAT_01": {"template": "Maintenance significantly delayed (Waiting {days} days).", "priority": 2, "category": "Maintenance", "severity": "High"},
    "R_WAT_02": {"template": "Repair overdue (Waiting {days} days).", "priority": 3, "category": "Maintenance", "severity": "Medium"},
    "R_WAT_03": {"template": "Repair should be scheduled soon.", "priority": 5, "category": "Maintenance", "severity": "Low"},
    "R_WAT_04": {"template": "Recently detected.", "priority": 7, "category": "Maintenance", "severity": "Low"},

    # Traffic
    "R_TRA_01": {"template": "Heavy traffic corridor.", "priority": 2, "category": "Traffic", "severity": "High"},

    # Infrastructure
    "R_IMP_01": {"template": "Strategic transportation route.", "priority": 3, "category": "Infrastructure", "severity": "High"},
    "R_IMP_02": {"template": "Important urban road.", "priority": 4, "category": "Infrastructure", "severity": "Medium"},
    "R_IMP_03": {"template": "Local access road.", "priority": 6, "category": "Infrastructure", "severity": "Low"},

    # Risk (Landmarks)
    "R_LND_SCHOOL": {"template": "Student safety risk (Near school).", "priority": 1, "category": "Risk", "severity": "Critical"},
    "R_LND_HOSPITAL": {"template": "Emergency vehicle route (Near hospital).", "priority": 1, "category": "Risk", "severity": "Critical"},
    "R_LND_BUS": {"template": "High pedestrian activity (Near bus stop).", "priority": 3, "category": "Risk", "severity": "Medium"},
    "R_LND_RAILWAY": {"template": "Traffic interruption risk (Near railway crossing).", "priority": 2, "category": "Risk", "severity": "High"},
    "R_LND_COLLEGE": {"template": "High student traffic (Near college).", "priority": 4, "category": "Risk", "severity": "Medium"},
    "R_LND_MARKET": {"template": "Crowded commercial area (Near market).", "priority": 4, "category": "Risk", "severity": "Medium"},

    # Priority
    "R_PRI_01": {"template": "Immediate deployment required.", "priority": 1, "category": "Priority", "severity": "Critical"},
    "R_PRI_02": {"template": "Assign emergency repair crew.", "priority": 2, "category": "Priority", "severity": "High"},
    "R_PRI_03": {"template": "Repair within 24 hours.", "priority": 3, "category": "Priority", "severity": "Medium"},
    "R_PRI_04": {"template": "Include in weekly maintenance.", "priority": 5, "category": "Priority", "severity": "Low"},
    "R_PRI_05": {"template": "Routine maintenance.", "priority": 7, "category": "Priority", "severity": "Low"},
    
    # History & Clusters
    "R_HIS_01": {"template": "Hazard reported repeatedly over time.", "priority": 2, "category": "History", "severity": "High"},
    "R_CLS_01": {"template": "Repeated hazard zone detected.", "priority": 2, "category": "Infrastructure", "severity": "High"},
    
    # Operation
    "R_MNT_STATE": {"template": "Hazard is currently {state}.", "priority": 6, "category": "Operation", "severity": "Low"},
    "R_ASS_STATE": {"template": "Assignment is {state}.", "priority": 6, "category": "Assignment", "severity": "Low"}
}
