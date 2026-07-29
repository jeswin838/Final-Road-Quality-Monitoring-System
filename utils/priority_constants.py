# Priority Weights (total 100%)
PRIORITY_WEIGHTS = {
    "risk": 0.40,
    "road": 0.20,
    "traffic": 0.15,
    "waiting": 0.10,
    "reports": 0.10,
    "emergency": 0.05
}

# Priority Level Thresholds
PRIORITY_THRESHOLDS = {
    "Emergency": 95,
    "Critical": 90,
    "High": 75,
    "Medium": 55,
    "Low": 0
}

# Repair Categories based on Priority Level
REPAIR_CATEGORIES = {
    "Emergency": "Immediate Repair",
    "Critical": "24 Hours",
    "High": "48 Hours",
    "Medium": "7 Days",
    "Low": "Scheduled Maintenance"
}

# Maintenance Windows based on Priority Level
MAINTENANCE_WINDOWS = {
    "Emergency": "Today",
    "Critical": "Today",
    "High": "2 Days",
    "Medium": "Next Week",
    "Low": "Scheduled"
}

# Response Time based on Priority Level
RESPONSE_TIME = {
    "Emergency": "30 minutes",
    "Critical": "4 hours",
    "High": "12 hours",
    "Medium": "2 days",
    "Low": "7 days"
}

# Estimated Repair Duration based on Priority Level
ESTIMATED_REPAIR_DAYS = {
    "Emergency": "1 Day",    # Often complex emergency work or making it safe immediately
    "Critical": "1 Day",
    "High": "4 Hours",
    "Medium": "2 Hours",
    "Low": "30 min"
}

# Escalation Levels
ESCALATION_LEVELS = {
    "Risk_95": 5,
    "Road_Closed": 4,
    "Repeated_Complaints": 3,
    "Waiting_30": 2,
    "Normal": 1
}

# Scoring Base Values for Priorities
ROAD_PRIORITY = {
    100: 100,  # Motorway
    90: 90,    # National Highway
    80: 80,    # State Highway
    70: 70,    # Primary
    60: 60,    # Secondary
    50: 50,    # Collector
    40: 40,    # Village
    20: 20,    # Residential
    10: 10     # Unknown
}

TRAFFIC_PRIORITY = {
    "Motorway": 100,
    "National Highway": 90,
    "State Highway": 90,
    "Primary/Highway": 90,
    "Primary": 80,
    "Secondary/Main Road": 70,
    "Secondary": 70,
    "Collector": 60,
    "Village Road": 40,
    "Local/Residential": 20,
    "Residential": 20,
    "Unknown": 10
}

# Component Scoring Mechanics
WAITING_BONUS_MAX_DAYS = 30
REPORT_BONUS_MAX_COUNT = 10
EMERGENCY_BONUS = 100
