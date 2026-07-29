import math
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class OverpassService:
    SERVERS = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    RADII = [100, 250, 500, 1000, 2000, 3000, 5000]

    @classmethod
    def _query_overpass(cls, lat: float, lon: float, radius: int) -> tuple[dict, str]:
        query = f"""
        [out:json][timeout:5];
        (
          way(around:{radius},{lat},{lon})["highway"];
          node(around:{radius},{lat},{lon})["place"];
          way(around:{radius},{lat},{lon})["place"];
          relation(around:{radius},{lat},{lon})["place"];
          node(around:{radius},{lat},{lon})["boundary"];
          way(around:{radius},{lat},{lon})["boundary"];
          relation(around:{radius},{lat},{lon})["boundary"];
          node(around:{radius},{lat},{lon})["amenity"];
          way(around:{radius},{lat},{lon})["amenity"];
          relation(around:{radius},{lat},{lon})["amenity"];
          node(around:{radius},{lat},{lon})["building"];
          way(around:{radius},{lat},{lon})["building"];
          relation(around:{radius},{lat},{lon})["building"];
          node(around:{radius},{lat},{lon})["tourism"];
          way(around:{radius},{lat},{lon})["tourism"];
          relation(around:{radius},{lat},{lon})["tourism"];
          node(around:{radius},{lat},{lon})["historic"];
          way(around:{radius},{lat},{lon})["historic"];
          relation(around:{radius},{lat},{lon})["historic"];
          node(around:{radius},{lat},{lon})["railway"];
          way(around:{radius},{lat},{lon})["railway"];
          relation(around:{radius},{lat},{lon})["railway"];
          node(around:{radius},{lat},{lon})["office"];
          way(around:{radius},{lat},{lon})["office"];
          relation(around:{radius},{lat},{lon})["office"];
          node(around:{radius},{lat},{lon})["shop"];
          way(around:{radius},{lat},{lon})["shop"];
          relation(around:{radius},{lat},{lon})["shop"];
          node(around:{radius},{lat},{lon})["public_transport"];
          way(around:{radius},{lat},{lon})["public_transport"];
          relation(around:{radius},{lat},{lon})["public_transport"];
          node(around:{radius},{lat},{lon})["landuse"];
          way(around:{radius},{lat},{lon})["landuse"];
          relation(around:{radius},{lat},{lon})["landuse"];
          node(around:{radius},{lat},{lon})["natural"];
          way(around:{radius},{lat},{lon})["natural"];
          relation(around:{radius},{lat},{lon})["natural"];
          node(around:{radius},{lat},{lon})["leisure"];
          way(around:{radius},{lat},{lon})["leisure"];
          relation(around:{radius},{lat},{lon})["leisure"];
        );
        out center;
        """
        
        for server in cls.SERVERS:
            try:
                # 5-second timeout as required by user
                response = requests.post(server, data={'data': query}, timeout=5)
                if response.status_code == 200:
                    return response.json(), server
            except Exception as e:
                pass
                
        return {}, "None"

    @classmethod
    def query(cls, lat: float, lon: float) -> Dict[str, Any]:
        best_named_road = None
        best_named_road_dist = float('inf')
        best_unnamed_road = None
        best_unnamed_road_dist = float('inf')
        
        best_landmark = None
        best_landmark_dist = float('inf')
        
        best_locality = None
        best_locality_dist = float('inf')
        
        poi_tags = [
            'hospital', 'school', 'college', 'temple', 'church', 'mosque', 'fuel',
            'hotel', 'restaurant', 'bus_stop', 'bus_station', 'railway_station',
            'bank', 'mall', 'government', 'museum', 'park', 'office', 'industrial',
            'market', 'amenity', 'building', 'tourism', 'historic', 'shop', 'leisure'
        ]
        
        for radius in cls.RADII:
            data, server = cls._query_overpass(lat, lon, radius)
            elements = data.get("elements", [])
                
            for el in elements:
                elat = el.get("lat") or el.get("center", {}).get("lat")
                elon = el.get("lon") or el.get("center", {}).get("lon")
                if not elat or not elon:
                    continue
                    
                dist = haversine_distance(lat, lon, elat, elon)
                tags = el.get("tags", {})
                
                # Road
                if "highway" in tags:
                    name = (tags.get("name") or tags.get("official_name") or 
                            tags.get("ref") or tags.get("alt_name") or 
                            tags.get("loc_name") or tags.get("name:en") or 
                            tags.get("old_name"))
                    
                    if name and dist < best_named_road_dist:
                        best_named_road = {"name": name, "highway": tags.get("highway")}
                        best_named_road_dist = dist
                    elif not name and dist < best_unnamed_road_dist:
                        best_unnamed_road = {"name": "", "highway": tags.get("highway")}
                        best_unnamed_road_dist = dist
                        
                # Landmark
                is_landmark = False
                for tag in poi_tags:
                    if tag in tags or tags.get('amenity') == tag or tags.get('building') == tag:
                        is_landmark = True
                        break
                
                if is_landmark and tags.get("name") and dist < best_landmark_dist:
                    best_landmark = tags.get("name")
                    best_landmark_dist = dist
                    
                # Locality
                if "place" in tags or "boundary" in tags:
                    name = tags.get("name")
                    if name and dist < best_locality_dist:
                        place_val = tags.get("place", tags.get("boundary"))
                        best_locality = {"name": name, "place": place_val}
                        best_locality_dist = dist
                        
            # If we found a named road AND a landmark AND a locality, we can exit early.
            # Otherwise we continue up to the maximum radius.
            if best_named_road and best_landmark and best_locality:
                break

        result = {
            "highway_name": "",
            "highway_class": "",
            "road_dist": 0,
            "landmark": "",
            "landmark_dist": 0,
            "place_name": "",
            "place_type": "",
            "place_dist": 0
        }
        
        if best_named_road:
            result["highway_name"] = best_named_road.get("name", "")
            result["highway_class"] = best_named_road.get("highway", "")
            result["road_dist"] = int(best_named_road_dist)
        elif best_unnamed_road:
            result["highway_name"] = ""
            result["highway_class"] = best_unnamed_road.get("highway", "")
            result["road_dist"] = int(best_unnamed_road_dist)
            
        if best_landmark:
            result["landmark"] = best_landmark
            result["landmark_dist"] = int(best_landmark_dist)
            
        if best_locality:
            result["place_name"] = best_locality.get("name", "")
            result["place_type"] = best_locality.get("place", "")
            result["place_dist"] = int(best_locality_dist)
            
        return result
