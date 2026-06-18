import time
import json
import numpy as np
import requests
from math import radians, cos, sin, asin, sqrt

VOICE_LOCATIONS_FILE = "voice_locations.json"
VOICE_UNKNOWN_IMAGE = "unknown.jpg"
VOICE_PROXIMITY_METERS = 25


def save_voice_location(latitude, longitude):
    try:
        with open(VOICE_LOCATIONS_FILE, "r", encoding="utf-8") as f:
            locations = json.load(f)
    except Exception:
        locations = []

    locations.append({
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "processed": False
    })

    with open(VOICE_LOCATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(locations, f, indent=4)

    print("Voice location saved")


def load_voice_locations():
    try:
        with open(VOICE_LOCATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_voice_locations(locations):
    with open(VOICE_LOCATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(locations, f, indent=4)


def distance_meters(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371000 * c


def get_unprocessed_voice_locations():
    return [
        location for location in load_voice_locations()
        if not location.get("processed", False)
    ]


def mark_voice_locations_processed(locations):
    all_locations = load_voice_locations()
    for entry in all_locations:
        for processed in locations:
            if (
                entry.get("timestamp") == processed.get("timestamp") and
                entry.get("latitude") == processed.get("latitude") and
                entry.get("longitude") == processed.get("longitude")
            ):
                entry["processed"] = True
    save_voice_locations(all_locations)


def voice_near_survivor(voice_location, survivors, threshold_m=VOICE_PROXIMITY_METERS):
    for s in survivors:
        dist = distance_meters(
            voice_location["latitude"],
            voice_location["longitude"],
            s["latitude"],
            s["longitude"]
        )
        if dist <= threshold_m:
            return True
    return False


def get_unmatched_voice_locations(survivors, threshold_m=VOICE_PROXIMITY_METERS):
    unprocessed = get_unprocessed_voice_locations()
    return [
        voice for voice in unprocessed
        if not voice_near_survivor(voice, survivors, threshold_m)
    ]


def detect_voice(audio):
    if audio is None or audio.size == 0:
        return False

    waveform = np.abs(audio.flatten())
    peak = float(np.max(waveform))
    rms = float(np.sqrt(np.mean(waveform ** 2)))

    THRESHOLD_PEAK = 0.05
    THRESHOLD_RMS = 0.008

    return peak > THRESHOLD_PEAK or rms > THRESHOLD_RMS


def stream_audio_from_camera(audio_url, chunk_size=32000):
    """Stream audio from IP camera and yield audio chunks."""
    try:
        response = requests.get(audio_url, stream=True, timeout=10)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield np.frombuffer(chunk, dtype=np.float32)
    except Exception as exc:
        print(f"Audio stream error: {exc}")
        return


def start_voice_monitor(get_current_gps, audio_url):
    """Monitor audio stream from IP camera and detect voice."""
    print("Voice monitoring started from IP camera...")

    try:
        audio_stream = stream_audio_from_camera(audio_url)
        for audio_chunk in audio_stream:
            try:
                if detect_voice(audio_chunk):
                    lat, lon = get_current_gps()
                    print("VOICE DETECTED!")
                    print("Location:", lat, lon)
                    save_voice_location(lat, lon)

            except Exception as exc:
                print(f"Voice detection error: {exc}")
                continue

    except Exception as exc:
        print(f"Audio stream disabled or failed: {exc}")
        time.sleep(5)
