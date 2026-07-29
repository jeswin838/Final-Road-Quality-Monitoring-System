import logging
import requests
from config import Config
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PhotonService:
    @classmethod
    def query(cls, lat: float, lon: float) -> Dict[str, str]:
        """Query Photon API and extract useful metadata."""
        url = Config.PHOTON_URL
        params = {
            'lat': lat,
            'lon': lon,
            'limit': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    return {
                        "street": props.get("street") or props.get("name") or "",
                        "village": props.get("village") or "",
                        "neighbourhood": props.get("neighbourhood") or "",
                        "suburb": props.get("suburb") or "",
                        "town": props.get("town") or "",
                        "city": props.get("city") or "",
                        "district": props.get("district") or props.get("county") or "",
                        "state": props.get("state") or "",
                        "country": props.get("country") or ""
                    }
        except Exception as e:
            logger.warning(f"[PHOTON] Failed to query {lat}, {lon}: {e}")
            
        return {}
