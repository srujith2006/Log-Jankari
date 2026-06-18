from pathlib import Path
import folium
from math import radians, cos, sin, asin, sqrt

MAP_DIR = Path("maps")
MAP_PATH = MAP_DIR / "survivor_map.html"

HOSPITALS = [
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


def choose_best_hospital(survivors, hospitals=HOSPITALS):
    if not hospitals:
        return None

    best = None
    for hospital in hospitals:
        distances = [
            haversine(s["latitude"], s["longitude"], hospital["latitude"], hospital["longitude"])
            for s in survivors
        ]
        hospital_stats = {
            "hospital": hospital,
            "max_distance_km": max(distances),
            "avg_distance_km": sum(distances) / len(distances),
            "total_distance_km": sum(distances),
        }

        if best is None:
            best = hospital_stats
            continue

        if hospital_stats["max_distance_km"] < best["max_distance_km"]:
            best = hospital_stats
        elif hospital_stats["max_distance_km"] == best["max_distance_km"]:
            if hospital_stats["total_distance_km"] < best["total_distance_km"]:
                best = hospital_stats

    return best


def generate_map(survivors):
    if not survivors:
        raise ValueError("Cannot generate a map without survivor locations")

    MAP_DIR.mkdir(exist_ok=True)

    avg_lat = sum(s["latitude"] for s in survivors) / len(survivors)
    avg_lon = sum(s["longitude"] for s in survivors) / len(survivors)

    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=13,
    )

    points = []
    survivor_group = folium.FeatureGroup(name="Survivors")

    for s in survivors:
        lat = s["latitude"]
        lon = s["longitude"]
        points.append([lat, lon])

        popup = folium.Popup(
            f"<b>Survivor ID:</b> {s.get('survivor_id', 'N/A')}<br/>"
            f"Latitude: {lat}<br/>Longitude: {lon}",
            max_width=300,
        )

        folium.Marker(
            [lat, lon],
            popup=popup,
            icon=folium.Icon(color="blue", icon="user", prefix="fa"),
        ).add_to(survivor_group)

    survivor_group.add_to(m)

    best_hospital = choose_best_hospital(survivors)
    if best_hospital:
        hospital = best_hospital["hospital"]
        hospital_popup = folium.Popup(
            f"<b>{hospital['name']}</b><br/>"
            f"Max distance: {best_hospital['max_distance_km']:.2f} km<br/>"
            f"Average distance: {best_hospital['avg_distance_km']:.2f} km",
            max_width=300,
        )

        folium.Marker(
            [hospital["latitude"], hospital["longitude"]],
            popup=hospital_popup,
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon"),
        ).add_to(m)

    if len(points) > 1:
        folium.PolyLine(points, color="green", weight=3, opacity=0.7).add_to(m)

    folium.LayerControl().add_to(m)

    m.save(str(MAP_PATH))
    return str(MAP_PATH)
