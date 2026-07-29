from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Reason:
    code: str
    category: str
    priority: int
    message: str
    severity: str
    confidence: float
    template: str
    arguments: dict = field(default_factory=dict)

@dataclass
class ReasonBundle:
    summary: str = ""
    citizen_message: str = ""
    engineer_message: str = ""
    supervisor_message: str = ""
    actions: List[str] = field(default_factory=list)
    recommendations: Dict[str, Any] = field(default_factory=dict)
    reasons: List[Reason] = field(default_factory=list)
    priority: str = "Low"
    generated_time: str = ""
    version: str = "1.0"
    processing_ms: float = 0.0
