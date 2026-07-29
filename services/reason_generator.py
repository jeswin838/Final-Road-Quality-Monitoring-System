from typing import List, Dict
from models.hazard import Hazard
from models.reason import Reason
from utils.reason_rules import evaluate_all_rules
from utils.reason_catalog import REASON_CATALOG

def generate_reasons(hazard: Hazard) -> List[Reason]:
    """
    Evaluates rules, deduplicates by category/priority, sorts, and constructs Reason objects.
    """
    raw_dicts = evaluate_all_rules(hazard)
    
    # Deduplicate semantic overlaps - keeping highest priority per category
    # (Simplified approach: if multiple codes in same category, keep one with lowest priority number)
    category_map = {}
    for d in raw_dicts:
        code = d["code"]
        if code not in REASON_CATALOG:
            continue
            
        catalog_info = REASON_CATALOG[code]
        category = catalog_info["category"]
        priority = catalog_info["priority"]
        
        # If category exists, check if this code has a more urgent (lower) priority number
        if category in category_map:
            if priority < category_map[category]["catalog"]["priority"]:
                category_map[category] = {"dict": d, "catalog": catalog_info}
        else:
            category_map[category] = {"dict": d, "catalog": catalog_info}
            
    # Build Reason objects
    reasons = []
    for cat, data in category_map.items():
        code = data["dict"]["code"]
        catalog = data["catalog"]
        conf = data["dict"]["confidence"]
        args = data["dict"].get("args", {})
        
        # Format message template
        msg = catalog["template"].format(**args)
        
        r = Reason(
            code=code,
            category=catalog["category"],
            priority=catalog["priority"],
            message=msg,
            severity=catalog["severity"],
            confidence=conf,
            template=catalog["template"],
            arguments=args
        )
        reasons.append(r)
        
    # Sort by priority (lowest number = highest importance)
    reasons.sort(key=lambda x: x.priority)
    
    return reasons
