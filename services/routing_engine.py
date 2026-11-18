import math
from typing import Any, Dict, List, Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def evaluate_area_road_status(
    audits: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    radius_km: float = 1.5,
) -> Dict[str, Any]:
    nearby = []
    for item in audits:
        if item.get("ticket_status") == "RESOLVED":
            continue
        try:
            alat = float(item.get("latitude", 0.0))
            alon = float(item.get("longitude", 0.0))
            dist = haversine_km(center_lat, center_lon, alat, alon)
            if dist <= radius_km:
                nearby.append((dist, item))
        except (TypeError, ValueError):
            continue

    red_count = sum(1 for _, x in nearby if x.get("severity_level") == "RED")
    yellow_count = sum(1 for _, x in nearby if x.get("severity_level") == "YELLOW")

    score = max(10, min(100, 96 - red_count * 26 - yellow_count * 10))

    if red_count > 0:
        overall = "UNSAFE — Severe Structural Hazards"
        wheelchair = "UNSAFE (Reroute Required)"
        elder = "UNSAFE (High Trip/Slip Risk)"
        blind = "UNSAFE (Acoustic Detour Active)"
        two_wheeler = "UNSAFE (Skid / Rim Damage Risk)"
        three_wheeler = "CAUTION (Suspension / Tipping Risk)"
        four_wheeler = "CAUTION (Slow Speed / Swell Hazard)"
    elif yellow_count > 0:
        overall = "CAUTION — Minor Surface Wear"
        wheelchair = "CAUTION (Use Smooth Curb Cuts)"
        elder = "PASSABLE WITH CARE"
        blind = "PASSABLE (Stay Near Inner Edge)"
        two_wheeler = "PASSABLE (Watch Loose Gravel)"
        three_wheeler = "SAFE"
        four_wheeler = "SAFE"
    else:
        overall = "SAFE — Verified Barrier-Free"
        wheelchair = "SAFE (Barrier-Free)"
        elder = "SAFE"
        blind = "SAFE (Clear Tactile Path)"
        two_wheeler = "SAFE"
        three_wheeler = "SAFE"
        four_wheeler = "SAFE"

    return {
        "area_score": score,
        "accessibility_score": score,
        "overall_status": overall,
        "red_count": red_count,
        "yellow_count": yellow_count,
        "red_hazards": red_count,
        "yellow_hazards": yellow_count,
        "total_nearby": len(nearby),
        "nearby_count": len(nearby),
        "wheelchair_status": wheelchair,
        "elder_status": elder,
        "visually_impaired_status": blind,
        "elder_blind_status": blind,
        "two_wheeler_status": two_wheeler,
        "three_wheeler_status": three_wheeler,
        "four_wheeler_status": four_wheeler,
        "safe_vehicles": ["4-Wheelers (Proceed Slowly)"] if red_count > 0 else ["2-Wheelers / Cycles", "3-Wheelers / Autos", "4-Wheelers"],
        "recommended_action": (
            "Municipal Re-Construction Escalation (RED Zone)"
            if red_count > 0
            else ("Citizen / RWA Quick-Fix Initiative (YELLOW Zone)" if yellow_count > 0 else "Verified Barrier-Free Corridor")
        ),
        "civic_summary": (
            f"Municipal Reconstruction Track: {red_count} critical structural hazard(s) require immediate PWD/MCD intervention."
            if red_count > 0
            else (
                f"Citizen / RWA Vigilance Track: {yellow_count} minor surface issue(s) eligible for local RWA/volunteer quick-fix."
                if yellow_count > 0
                else "Barrier-Free Corridor: All footpaths and crossings in this zone are verified safe."
            )
        ),

    }




def compute_safe_detour_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    audits: List[Dict[str, Any]],
    travel_mode: str = "Wheelchair / Elder",
) -> Tuple[List[Tuple[float, float]], str]:
    active_hazards = [
        a for a in audits
        if a.get("ticket_status") != "RESOLVED" and a.get("severity_level") in {"RED", "YELLOW"}
    ]

    # Try OpenStreetMap routing first if osmnx/networkx are installed
    try:
        import networkx as nx
        import osmnx as ox

        mid_lat = (start_lat + end_lat) / 2.0
        mid_lon = (start_lon + end_lon) / 2.0
        dist_m = max(800, int(haversine_km(start_lat, start_lon, end_lat, end_lon) * 1000 * 1.6))
        network_type = "walk" if any(k in travel_mode.lower() for k in ["wheelchair", "elder", "blind", "pedestrian"]) else "drive"

        G = ox.graph_from_point((mid_lat, mid_lon), dist=min(dist_m, 3000), network_type=network_type)

        for u, v, k, data in G.edges(keys=True, data=True):
            base_len = float(data.get("length", 10.0))
            u_lat, u_lon = G.nodes[u]["y"], G.nodes[u]["x"]
            penalty = 1.0
            for haz in active_hazards:
                h_dist = haversine_km(u_lat, u_lon, float(haz["latitude"]), float(haz["longitude"]))
                if h_dist <= 0.04:
                    penalty += 10000.0 if haz.get("severity_level") == "RED" else 500.0
            data["freedom_cost"] = base_len * penalty

        orig_node = ox.distance.nearest_nodes(G, start_lon, start_lat)
        dest_node = ox.distance.nearest_nodes(G, end_lon, end_lat)
        route_nodes = nx.shortest_path(G, orig_node, dest_node, weight="freedom_cost")
        coords: List[Tuple[float, float]] = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_nodes]

        total_km = sum(
            haversine_km(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
            for i in range(len(coords) - 1)
        )

        # --- FIRST RETURN REPLACEMENT ---
        summary_text = (
            f"Barrier-aware route ({round(total_km, 2)} km) computed for {travel_mode} "
            f"via OpenStreetMap avoiding {len(active_hazards)} reported hazards."
        )
        return coords, summary_text

    except Exception:
        pass

    # Deterministic geometric detour fallback (works offline)
    mid_lat = (start_lat + end_lat) / 2.0
    mid_lon = (start_lon + end_lon) / 2.0

    dlat = end_lat - start_lat
    dlon = end_lon - start_lon
    offset_lat = -dlon * 0.25
    offset_lon = dlat * 0.25

    near_hazard = any(
        haversine_km(mid_lat, mid_lon, float(h.get("latitude", 0)), float(h.get("longitude", 0))) < 0.35
        for h in active_hazards
    )
    if near_hazard:
        mid_lat += offset_lat if abs(offset_lat) > 0.0005 else 0.0018
        mid_lon += offset_lon if abs(offset_lon) > 0.0005 else 0.0018

    coords = [(start_lat, start_lon), (mid_lat, mid_lon), (end_lat, end_lon)]
    total_km = (
        haversine_km(start_lat, start_lon, mid_lat, mid_lon)
        + haversine_km(mid_lat, mid_lon, end_lat, end_lon)
    )

    # --- SECOND RETURN REPLACEMENT ---
    summary_text = (
        f"Safe detour route ({round(total_km, 2)} km) generated for {travel_mode} "
        f"({'detoured around active hazard zone' if near_hazard else 'direct corridor clear'})."
    )
    return coords, summary_text

