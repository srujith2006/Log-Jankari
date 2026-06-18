from pathlib import Path
import json
import folium
import requests
from math import radians, cos, sin, asin, sqrt

MAP_DIR = Path("maps")
MAP_PATH = MAP_DIR / "survivor_map.html"
HOSPITALS_FILE = Path("hospitals.json")
USER_AGENT = "myVerse/1.0"

DEFAULT_HOSPITALS = [
    {
        "name": "Lifeline Hospital",
        "latitude": 17.0950,
        "longitude": 82.0720,
    },
    {
        "name": "Vijaya Hospital",
        "latitude": 17.0820,
        "longitude": 82.0560,
    },
    {
        "name": "City Care Hospital",
        "latitude": 17.0885,
        "longitude": 82.0630,
    },
]


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371 * c


def load_local_hospitals():
    if not HOSPITALS_FILE.exists():
        return []

    try:
        with open(HOSPITALS_FILE, "r", encoding="utf-8") as f:
            hospitals = json.load(f)
    except Exception:
        return []

    valid = []
    for hospital in hospitals:
        if not all(k in hospital for k in ("name", "latitude", "longitude")):
            continue
        try:
            valid.append({
                "name": hospital["name"],
                "latitude": float(hospital["latitude"]),
                "longitude": float(hospital["longitude"]),
            })
        except Exception:
            continue

    return valid


def search_nearby_hospitals(latitude, longitude, limit=12):
    try:
        params = {
            "format": "json",
            "q": "hospital",
            "limit": limit,
            "lat": latitude,
            "lon": longitude,
            "addressdetails": 0,
        }
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json()

        hospitals = []
        for result in results:
            try:
                hospitals.append({
                    "name": result.get("display_name", "Hospital"),
                    "latitude": float(result["lat"]),
                    "longitude": float(result["lon"]),
                })
            except Exception:
                continue
        return hospitals
    except Exception:
        return []


def get_hospitals(survivors):
    hospitals = load_local_hospitals()
    if hospitals:
        return hospitals

    if not survivors:
        return DEFAULT_HOSPITALS

    center_lat = sum(s["latitude"] for s in survivors) / len(survivors)
    center_lon = sum(s["longitude"] for s in survivors) / len(survivors)
    nearby = search_nearby_hospitals(center_lat, center_lon)
    return nearby or DEFAULT_HOSPITALS


def choose_best_hospital(survivors, hospitals=None):
    if hospitals is None:
        hospitals = get_hospitals(survivors)

    if not hospitals or not survivors:
        return None

    best = None
    for hospital in hospitals:
        distances = [
            haversine(s["latitude"], s["longitude"], hospital["latitude"], hospital["longitude"])
            for s in survivors
        ]
        stats = {
            "hospital": hospital,
            "max_distance_km": max(distances),
            "avg_distance_km": sum(distances) / len(distances),
            "total_distance_km": sum(distances),
        }

        if best is None or stats["max_distance_km"] < best["max_distance_km"] or (
            stats["max_distance_km"] == best["max_distance_km"] and stats["total_distance_km"] < best["total_distance_km"]
        ):
            best = stats

    return best


def generate_map(survivors):
    if not survivors:
        raise ValueError("Cannot generate a map without survivor locations")

    MAP_DIR.mkdir(exist_ok=True)

    avg_lat = sum(s["latitude"] for s in survivors) / len(survivors)
    avg_lon = sum(s["longitude"] for s in survivors) / len(survivors)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
    points = []
    survivor_group = folium.FeatureGroup(name="Survivors")
    voice_group = folium.FeatureGroup(name="Voice-Only Detections")

    for s in survivors:
        lat = s["latitude"]
        lon = s["longitude"]
        voice_only = s.get("voice_detected", False)
        popup_text = (
            f"<b>Survivor ID:</b> {s.get('survivor_id', 'N/A')}<br/>"
            f"Latitude: {lat}<br/>Longitude: {lon}<br/>"
            f"Posture: {s.get('posture', 'N/A')}"
        )

        if voice_only:
            popup_text += "<br/><b>Note:</b> voice-only detection"
            marker_group = voice_group
            icon = folium.Icon(color="orange", icon="microphone", prefix="fa")
        else:
            marker_group = survivor_group
            icon = folium.Icon(color="blue", icon="user", prefix="fa")
            points.append([lat, lon])

        folium.Marker([lat, lon], popup=folium.Popup(popup_text, max_width=300), icon=icon).add_to(marker_group)

    survivor_group.add_to(m)
    voice_group.add_to(m)

    confirmed_survivors = [s for s in survivors if not s.get("voice_detected")]
    best_hospital = choose_best_hospital(confirmed_survivors)
    if best_hospital:
        hospital = best_hospital["hospital"]
        folium.Marker(
            [hospital["latitude"], hospital["longitude"]],
            popup=folium.Popup(
                f"<b>{hospital['name']}</b><br/>"
                f"Max distance: {best_hospital['max_distance_km']:.2f} km<br/>"
                f"Average distance: {best_hospital['avg_distance_km']:.2f} km",
                max_width=300,
            ),
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon"),
        ).add_to(m)

    if len(points) > 1:
        folium.PolyLine(points, color="green", weight=3, opacity=0.7).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(str(MAP_PATH))
    return str(MAP_PATH)
