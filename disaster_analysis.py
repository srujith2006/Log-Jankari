import json
import os
from math import isfinite

import requests
from dotenv import load_dotenv

from weather_service import get_weather_from_gps


load_dotenv()

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
AREA_RADIUS_METERS = 700
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def build_disaster_analysis(survivors):
    location = _average_location(survivors)
    if not location:
        return {
            "available": False,
            "summary": "No valid GPS coordinates were available for climate and area analysis.",
        }

    latitude, longitude = location
    weather = get_weather_from_gps(latitude, longitude)
    area = get_area_context(latitude, longitude)
    natural_risks = infer_natural_risks(weather, area)

    history = (
        "No verified disastrous history is available from the local project data. "
        "Current weather and map context can indicate present risk, but they cannot prove past events."
    )
    soil_area_summary = describe_area(area)

    if natural_risks:
        likely_event = "Natural-disaster conditions are possible: " + "; ".join(natural_risks) + "."
        man_made = (
            "Do not classify this as man-made yet. There are natural/climate or area indicators "
            "that should be checked by responders first."
        )
        disaster_type_prediction = (
            "Likely natural or environment-assisted risk based on the available climate and area indicators."
        )
    else:
        likely_event = (
            "No strong natural-disaster signal was detected from the available weather and area data."
        )
        man_made = (
            "If verified disaster history is also clear and field evidence shows damage or casualties, "
            "a man-made cause becomes more plausible and should be investigated."
        )
        disaster_type_prediction = (
            "Natural cause is not strongly indicated by the available data; investigate man-made causes "
            "only with field evidence."
        )

    gemini_assessment = get_gemini_disaster_assessment(
        latitude,
        longitude,
        weather,
        area,
        natural_risks,
    )
    gemini_note = None
    if gemini_assessment:
        history = gemini_assessment.get("disastrous_history") or history
        soil_area_summary = gemini_assessment.get("soil_area_summary") or soil_area_summary
        likely_event = gemini_assessment.get("climate_area_possibility") or likely_event
        man_made = gemini_assessment.get("man_made_prediction") or man_made
        disaster_type_prediction = (
            gemini_assessment.get("disaster_type_prediction")
            or disaster_type_prediction
        )
        gemini_note = gemini_assessment.get("source_note")

    return {
        "available": True,
        "latitude": latitude,
        "longitude": longitude,
        "weather": weather,
        "area": area,
        "history": history,
        "soil_area_summary": soil_area_summary,
        "likely_event": likely_event,
        "man_made": man_made,
        "disaster_type_prediction": disaster_type_prediction,
        "natural_risks": natural_risks,
        "gemini_note": gemini_note,
    }


def get_gemini_disaster_assessment(latitude, longitude, weather, area, natural_risks):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    prompt = build_gemini_prompt(latitude, longitude, weather, area, natural_risks)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    }

    result = post_gemini_request(model, api_key, payload)
    if result is None:
        payload.pop("tools", None)
        result = post_gemini_request(model, api_key, payload)

    if result is None:
        return None

    text = extract_gemini_text(result)
    if not text:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = extract_json_object(text)

    if not isinstance(parsed, dict):
        return None

    return {
        "disastrous_history": _clean_ai_text(parsed.get("disastrous_history")),
        "soil_area_summary": _clean_ai_text(parsed.get("soil_area_summary")),
        "climate_area_possibility": _clean_ai_text(parsed.get("climate_area_possibility")),
        "man_made_prediction": _clean_ai_text(parsed.get("man_made_prediction")),
        "disaster_type_prediction": _clean_ai_text(parsed.get("disaster_type_prediction")),
        "source_note": _clean_ai_text(parsed.get("source_note")),
    }


def build_gemini_prompt(latitude, longitude, weather, area, natural_risks):
    return f"""
You are helping generate a rescue PDF report. Analyze this incident location and answer exactly these three questions:
1. Any disastrous history for that place?
2. Based on climate plus area details such as soil type, road type, land use, and nearby water, what natural disaster chances might have occurred there?
3. If the first two are clear, can it be predicted as a man-made disaster?
Also provide a final short prediction: natural disaster, man-made disaster, mixed/uncertain, or insufficient evidence.

Location:
- Latitude: {latitude}
- Longitude: {longitude}

Current weather data:
{json.dumps(weather or {}, indent=2)}

Local area/map context:
{json.dumps(area or {}, indent=2)}

Rule-based risk signals already found:
{json.dumps(natural_risks or [], indent=2)}

Use web/search grounding if available. Be careful: do not invent disaster history. If history is not verified, say "No verified disastrous history found from available sources." Do not say an event is impossible. Keep each answer short enough for a PDF table.

Return only valid JSON with these keys:
{{
  "disastrous_history": "answer for question 1",
  "soil_area_summary": "soil type, road type, land use, and nearby water/terrain summary",
  "climate_area_possibility": "answer for question 2",
  "man_made_prediction": "answer for question 3",
  "disaster_type_prediction": "final short prediction: natural, man-made, mixed/uncertain, or insufficient evidence with one reason",
  "source_note": "brief note about whether Gemini used search/available context or could not verify history"
}}
"""


def post_gemini_request(model, api_key, payload):
    url = GEMINI_API_URL.format(model=model)
    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"Gemini disaster analysis unavailable: {exc}")
        return None


def extract_gemini_text(result):
    candidates = result.get("candidates", [])
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip()


def extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def get_area_context(latitude, longitude):
    query = f"""
    [out:json][timeout:8];
    (
      way(around:{AREA_RADIUS_METERS},{latitude},{longitude})["highway"];
      way(around:{AREA_RADIUS_METERS},{latitude},{longitude})["surface"];
      way(around:{AREA_RADIUS_METERS},{latitude},{longitude})["landuse"];
      way(around:{AREA_RADIUS_METERS},{latitude},{longitude})["natural"];
      way(around:{AREA_RADIUS_METERS},{latitude},{longitude})["waterway"];
    );
    out tags center 50;
    """

    context = {
        "road_types": [],
        "road_surfaces": [],
        "landuse": [],
        "natural": [],
        "waterways": [],
        "soil_inference": "Unknown from available map data",
        "source_note": "OpenStreetMap nearby tags when available",
    }

    try:
        response = requests.get(OVERPASS_URL, params={"data": query}, timeout=10)
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except Exception as exc:
        context["source_note"] = f"Area lookup unavailable: {exc}"
        return context

    for element in elements:
        tags = element.get("tags", {})
        _append_unique(context["road_types"], tags.get("highway"))
        _append_unique(context["road_surfaces"], tags.get("surface"))
        _append_unique(context["landuse"], tags.get("landuse"))
        _append_unique(context["natural"], tags.get("natural"))
        _append_unique(context["waterways"], tags.get("waterway"))

    context["soil_inference"] = infer_soil_type(context)
    return context


def infer_natural_risks(weather, area):
    risks = []

    if weather:
        rain = _number(weather.get("rain")) or 0
        precipitation = _number(weather.get("precipitation")) or 0
        wind_speed = _number(weather.get("wind_speed")) or 0
        weather_code = weather.get("weather_code")

        if weather_code in {95, 96, 99}:
            risks.append("thunderstorm conditions")
        if weather_code in {65, 80, 81, 82} or rain >= 8 or precipitation >= 8:
            risks.append("heavy rain or flash-flood conditions")
        elif weather_code in {61, 63} or rain >= 2 or precipitation >= 2:
            risks.append("rain may weaken exposed soil or roads")
        if wind_speed >= 50:
            risks.append("very high wind speed")
        elif wind_speed >= 30:
            risks.append("strong wind speed")

    soil = area.get("soil_inference", "").lower()
    landuse = set(area.get("landuse", []))
    natural = set(area.get("natural", []))
    waterways = area.get("waterways", [])
    surfaces = set(area.get("road_surfaces", []))

    if waterways or "wetland" in natural or "water" in natural:
        risks.append("nearby water or wetland increases flood risk")
    if "sandy" in soil or "loose" in soil:
        risks.append("loose/sandy soil may increase collapse or erosion risk")
    if landuse.intersection({"quarry", "construction", "industrial"}):
        risks.append("nearby industrial/construction landuse may indicate human-made hazard exposure")
    if surfaces.intersection({"unpaved", "dirt", "earth", "gravel", "sand"}):
        risks.append("unpaved or loose road surface may reduce rescue access")

    return _dedupe(risks)


def infer_soil_type(area):
    natural = set(area.get("natural", []))
    landuse = set(area.get("landuse", []))
    surfaces = set(area.get("road_surfaces", []))

    if natural.intersection({"beach", "sand", "dune"}) or "sand" in surfaces:
        return "Likely sandy or loose surface near the incident area"
    if natural.intersection({"wetland", "water"}) or area.get("waterways"):
        return "Likely water-saturated or alluvial ground nearby"
    if landuse.intersection({"farmland", "orchard", "meadow", "grass"}):
        return "Likely agricultural/topsoil or alluvial soil nearby"
    if landuse.intersection({"industrial", "construction", "quarry"}):
        return "Likely disturbed or filled ground due to human activity"
    if surfaces.intersection({"dirt", "earth", "unpaved", "gravel"}):
        return "Likely exposed earth/gravel surface near roads"
    return "Unknown from available map data"


def _average_location(survivors):
    points = []
    for survivor in survivors:
        lat = _number(survivor.get("latitude"))
        lon = _number(survivor.get("longitude"))
        if lat is None or lon is None:
            continue
        if lat == 0 and lon == 0:
            continue
        if isfinite(lat) and isfinite(lon):
            points.append((lat, lon))

    if not points:
        return None

    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_unique(values, value):
    if value and value not in values:
        values.append(value)


def _clean_ai_text(value):
    if not value:
        return None

    return " ".join(str(value).split())


def _dedupe(values):
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def describe_weather(weather):
    if not weather:
        return "Weather lookup unavailable."

    code = weather.get("weather_code")
    condition = WEATHER_CODES.get(code, f"weather code {code}")
    return (
        f"Condition: {condition}; temperature: {_display(weather.get('temperature'), 'C')}; "
        f"humidity: {_display(weather.get('humidity'), '%')}; rain: {_display(weather.get('rain'), 'mm')}; "
        f"precipitation: {_display(weather.get('precipitation'), 'mm')}; "
        f"wind: {_display(weather.get('wind_speed'), 'km/h')}; observed at: {weather.get('time') or 'N/A'}."
    )


def describe_area(area):
    return (
        f"Soil/ground inference: {area.get('soil_inference')}. "
        f"Road types: {_join(area.get('road_types'))}. "
        f"Road surfaces: {_join(area.get('road_surfaces'))}. "
        f"Land use: {_join(area.get('landuse'))}. "
        f"Natural/water features: {_join(area.get('natural') + area.get('waterways'))}. "
        f"Source note: {area.get('source_note')}."
    )


def _display(value, unit):
    if value is None:
        return "N/A"
    return f"{value} {unit}"


def _join(values):
    return ", ".join(values) if values else "not found"
