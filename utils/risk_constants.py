# Risk Scoring Configuration

RISK_MAX_SCORE = 100

# Severity Weights (max 35)
SEVERITY_WEIGHTS = {
    "critical": 35,
    "high": 28,
    "medium": 18,
    "low": 8,
    "unknown": 0
}

# Confidence Weights (max 20)
def get_confidence_weight(confidence: float) -> int:
    conf = confidence * 100 if confidence <= 1.0 else confidence
    if conf >= 95: return 20
    if conf >= 90: return 18
    if conf >= 80: return 15
    if conf >= 70: return 10
    return 5

# Report Count Weights (max 35)
def get_report_weight(count: int) -> int:
    if count >= 10: return 35
    if count >= 6: return 25
    if count >= 3: return 18
    if count >= 2: return 10
    return 5

# Age Weights (max 35)
def get_age_weight(waiting_days: int) -> int:
    if waiting_days >= 30: return 35
    if waiting_days >= 15: return 25
    if waiting_days >= 8: return 18
    if waiting_days >= 3: return 12
    return 5

# Road Importance Weights (max 25)
ROAD_WEIGHTS = {
    100: 25, # Motorway
    90: 22,  # National Highway
    80: 21,  # State Highway
    70: 20,  # Primary
    60: 15,  # Secondary
    40: 10,  # Village Road
    20: 5,   # Residential
    10: 2    # Unknown
}

# Traffic Weights based on Road Class for now (Phase 8 will upgrade this) (max 20)
TRAFFIC_WEIGHTS = {
    "Motorway": 20,
    "National Highway": 18,
    "State Highway": 18,
    "Primary/Highway": 18,
    "Primary": 15,
    "Secondary/Main Road": 10,
    "Secondary": 10,
    "Village Road": 8,
    "Local/Residential": 5,
    "Residential": 5,
    "Unknown": 2
}

# Risk Level Thresholds
CRITICAL_THRESHOLD = 90
HIGH_THRESHOLD = 75
MEDIUM_THRESHOLD = 55
LOW_THRESHOLD = 0

# Configuration Options
REPEATED_REPORT_THRESHOLD = 5
