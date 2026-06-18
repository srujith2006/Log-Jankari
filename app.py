import cv2
import json
import os
import requests
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

from config import GPS_LATEST_URL, MIN_PERSON_BOX_AREA, VIDEO_URL, AUDIO_URL
from detector import detect
from voice_detector import (
    get_unprocessed_voice_locations,
    get_unmatched_voice_locations,
    mark_voice_locations_processed,
    start_voice_monitor,
    distance_meters,
    VOICE_UNKNOWN_IMAGE,
)

# Load environment variables
load_dotenv()

# MongoDB integration
try:
    from reports.connection import get_database
    MONGO_ENABLED = True
except ImportError:
    MONGO_ENABLED = False
    print("Warning: MongoDB not configured. Will save to JSON only.")

OUTPUT_VIDEO = "rescue_video.mp4"
SURVIVOR_REPORT = "reports/survivors.json"

os.makedirs("survivors", exist_ok=True)
os.makedirs("reports", exist_ok=True)

saved_ids = set()
survivor_records = {}
camera_tracks = {}
next_survivor_number = 1
last_known_gps = {
    "latitude": 0.0,
    "longitude": 0.0,
    "direction": "0"
}


def create_survivor_id():
    global next_survivor_number

    while True:
        survivor_id = f"survivor_{next_survivor_number}"
        next_survivor_number += 1

        if survivor_id not in survivor_records:
            return survivor_id


def box_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_width = max(inter_x2 - inter_x1, 0)
    inter_height = max(inter_y2 - inter_y1, 0)
    inter_area = inter_width * inter_height

    area_a = max(ax2 - ax1, 0) * max(ay2 - ay1, 0)
    area_b = max(bx2 - bx1, 0) * max(by2 - by1, 0)
    union = area_a + area_b - inter_area

    if union <= 0:
        return 0.0

    return inter_area / union


def center_distance(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    center_a = ((ax1 + ax2) / 2, (ay1 + ay2) / 2)
    center_b = ((bx1 + bx2) / 2, (by1 + by2) / 2)

    return (
        (center_a[0] - center_b[0]) ** 2
        + (center_a[1] - center_b[1]) ** 2
    ) ** 0.5


def find_matching_camera_survivor(bbox, frame_index, used_survivor_ids):
    best_id = None
    best_score = 0.0

    for survivor_id, track in camera_tracks.items():
        if survivor_id in used_survivor_ids:
            continue

        frames_since_seen = frame_index - track["last_seen"]
        if frames_since_seen > 45:
            continue

        previous_bbox = track["bbox"]
        iou = box_iou(bbox, previous_bbox)
        distance = center_distance(bbox, previous_bbox)
        width = max(bbox[2] - bbox[0], previous_bbox[2] - previous_bbox[0], 1)
        height = max(bbox[3] - bbox[1], previous_bbox[3] - previous_bbox[1], 1)
        max_reasonable_distance = max(width, height) * 0.6

        if iou >= 0.25:
            score = iou + 1.0
        elif distance <= max_reasonable_distance:
            score = 1.0 - (distance / max_reasonable_distance)
        else:
            continue

        if score > best_score:
            best_score = score
            best_id = survivor_id

    return best_id


def resolve_camera_survivor_id(track_id, bbox, frame_index, used_survivor_ids):
    if track_id is not None:
        survivor_id = f"track_{track_id}"
    else:
        survivor_id = find_matching_camera_survivor(
            bbox,
            frame_index,
            used_survivor_ids
        ) or create_survivor_id()

    camera_tracks[survivor_id] = {
        "bbox": bbox,
        "last_seen": frame_index
    }
    used_survivor_ids.add(survivor_id)
    return survivor_id


def get_latest_gps():
    global last_known_gps

    try:
        response = requests.get(
            GPS_LATEST_URL,
            timeout=1
        )
        response.raise_for_status()

        gps = response.json()
        latitude = gps.get("latitude")
        longitude = gps.get("longitude")
        direction = gps.get("direction", gps.get("bearing", "0"))

        if latitude is None or longitude is None:
            raise ValueError("GPS response missing latitude or longitude")

        latest_gps = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "direction": str(direction)
        }

        last_known_gps = latest_gps
        return latest_gps

    except Exception as exc:
        print(f"GPS fetch failed: {exc}. Using last known GPS: {last_known_gps}")
        return last_known_gps.copy()


def get_current_gps():
    gps = get_latest_gps()
    return gps["latitude"], gps["longitude"]


def find_matching_survivor(latitude, longitude, threshold_meters=10):
    for existing in survivor_records.values():
        if existing.get("voice_detected"):
            continue

        if distance_meters(latitude, longitude, existing["latitude"], existing["longitude"]) <= threshold_meters:
            return existing["survivor_id"]

    return None


def get_keypoint(keypoints, index, min_confidence=0.35):

    if keypoints is None:
        return None

    if index >= len(keypoints):
        return None

    point = keypoints[index]

    if point["confidence"] < min_confidence:
        return None

    return point


def enhance_image(image):
    """Apply blur reduction and sharpening techniques to enhance image clarity."""
    if image is None or image.size == 0:
        return image


def get_blur_score(image):
    if image is None or image.size == 0:
        return 0.0

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def has_visible_face_keypoints(keypoints, min_confidence=0.3):
    if not keypoints:
        return False

    face_keypoint_indexes = [0, 1, 2, 3, 4]
    visible_count = 0

    for index in face_keypoint_indexes:
        point = get_keypoint(keypoints, index, min_confidence=min_confidence)
        if point is not None:
            visible_count += 1

    return visible_count >= 2


def detect_face_with_cascade(image):
    if image is None or image.size == 0:
        return False

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_names = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_profileface.xml",
    ]

    for cascade_name in cascade_names:
        cascade_path = cv2.data.haarcascades + cascade_name
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(20, 20),
        )
        if len(faces) > 0:
            return True

    return False


def get_public_image_quality(image, keypoints=None):
    blur_score = get_blur_score(image)
    face_detected = (
        has_visible_face_keypoints(keypoints)
        or detect_face_with_cascade(image)
    )
    public_visible = face_detected and blur_score >= 80.0

    if not face_detected:
        quality_note = "Hidden from public: no clear face detected"
    elif blur_score < 80.0:
        quality_note = "Hidden from public: face image is too blurred"
    else:
        quality_note = "Public image approved"

    return {
        "face_detected": face_detected,
        "blur_score": round(blur_score, 2),
        "public_visible": public_visible,
        "quality_note": quality_note,
    }
    
    try:
        # 1. Bilateral filter - reduces noise while preserving edges
        enhanced = cv2.bilateralFilter(image, 9, 75, 75)
        
        # 2. Convert to float for processing
        enhanced = enhanced.astype('float32') / 255.0
        
        # 3. Unsharp mask - enhances details
        blur = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
        unsharp = enhanced + (enhanced - blur) * 1.5
        unsharp = cv2.clip(unsharp, 0, 1)
        
        # 4. Sharpen kernel for additional clarity
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        sharpened = cv2.filter2D(unsharp, -1, kernel)
        
        # 5. Convert back to uint8
        enhanced_img = (cv2.clip(sharpened, 0, 1) * 255).astype('uint8')
        
        return enhanced_img
    except Exception as exc:
        print(f"Image enhancement failed: {exc}")
        return image


def extract_pose_keypoints(result, detection_index):

    if result.keypoints is None:
        return None

    xy = result.keypoints.xy
    conf = result.keypoints.conf

    if xy is None or conf is None:
        return None

    points = []

    for point, point_conf in zip(
        xy[detection_index],
        conf[detection_index]
    ):
        points.append(
            {
                "x": float(point[0]),
                "y": float(point[1]),
                "confidence": float(point_conf)
            }
        )

    return points


def estimate_posture(x1, y1, x2, y2, keypoints=None):
    width = max(x2 - x1, 1)
    height = max(y2 - y1, 1)
    ratio = height / width

    if keypoints is None:
        if ratio >= 1.8:
            return "standing"
        if ratio >= 1.05:
            return "sitting/crouching"
        return "lying/fallen"

    left_shoulder = get_keypoint(keypoints, 5)
    right_shoulder = get_keypoint(keypoints, 6)
    left_hip = get_keypoint(keypoints, 11)
    right_hip = get_keypoint(keypoints, 12)
    left_knee = get_keypoint(keypoints, 13)
    right_knee = get_keypoint(keypoints, 14)
    left_ankle = get_keypoint(keypoints, 15)
    right_ankle = get_keypoint(keypoints, 16)

    shoulders = [p for p in [left_shoulder, right_shoulder] if p is not None]
    hips = [p for p in [left_hip, right_hip] if p is not None]
    knees = [p for p in [left_knee, right_knee] if p is not None]
    ankles = [p for p in [left_ankle, right_ankle] if p is not None]

    if shoulders and hips:
        shoulder_y = sum(p["y"] for p in shoulders) / len(shoulders)
        hip_y = sum(p["y"] for p in hips) / len(hips)
        torso_length = hip_y - shoulder_y

        if torso_length < height * 0.1:
            return "lying/fallen"

        if knees and ankles:
            knee_y = sum(p["y"] for p in knees) / len(knees)
            ankle_y = sum(p["y"] for p in ankles) / len(ankles)

            if knee_y > hip_y and ankle_y > knee_y and knee_y - hip_y > height * 0.2:
                return "standing"
            if abs(knee_y - hip_y) < height * 0.25:
                return "sitting/crouching"

        if torso_length > height * 0.35 and ratio > 1.3:
            return "standing"
        if torso_length > height * 0.22:
            return "sitting/crouching"

    if ratio >= 1.8:
        return "standing"
    if ratio >= 1.05:
        return "sitting/crouching"

    return "lying/fallen"


def save_survivor_record(record):
    """
    Save survivor record to both local JSON and MongoDB
    """
    survivor_records[record["survivor_id"]] = record

    # Save to local JSON (backup)
    survivor_data = list(survivor_records.values())
    with open(
        SURVIVOR_REPORT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            survivor_data,
            f,
            indent=4
        )

    # Save to MongoDB (primary storage)
    if MONGO_ENABLED:
        try:
            db = get_database()
            if db is not None:
                # Add timestamp if not present
                if "timestamp" not in record:
                    record["timestamp"] = datetime.now().isoformat()
                
                # Ensure identified field exists
                if "identified" not in record:
                    record["identified"] = False
                
                # Upsert: update if exists, insert if new
                db.survivors.update_one(
                    {"survivor_id": record["survivor_id"]},
                    {"$set": record},
                    upsert=True
                )
                print(f"✓ Saved to MongoDB: {record['survivor_id']}")
        except Exception as e:
            print(f"✗ Error saving to MongoDB: {e}")


def process_voice_events():
    survivors = list(survivor_records.values())
    unprocessed = get_unprocessed_voice_locations()

    if not unprocessed:
        return

    unmatched = get_unmatched_voice_locations(survivors)
    mark_voice_locations_processed(unprocessed)

    for voice_event in unmatched:
        voice_id = (
            f"voice_{voice_event['timestamp'].replace(' ', '_')}")
        voice_id = voice_id.replace(':', '-')

        if voice_id in survivor_records:
            continue

        record = {
            "survivor_id": voice_id,
            "image": VOICE_UNKNOWN_IMAGE,
            "latitude": voice_event["latitude"],
            "longitude": voice_event["longitude"],
            "direction": last_known_gps.get("direction", "0"),
            "posture": "voice detected",
            "confidence": 0.0,
            "voice_detected": True
        }

        save_survivor_record(record)
        print(f"Added unknown voice survivor record: {voice_id}")


def generate_reports():

    if not survivor_records:
        return

    process_voice_events()
    survivors = list(survivor_records.values())

    try:
        from report_generator import generate_report

        generate_report(survivors)
    except Exception as e:
        print(f"PDF report not generated: {e}")

    try:
        from map_generator import generate_map

        generate_map(survivors)
    except Exception as e:
        print(f"Map report not generated: {e}")


def main():

    video_source = int(VIDEO_URL) if str(VIDEO_URL).isdigit() else VIDEO_URL
    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():

        print(f"Cannot connect to video source: {VIDEO_URL}")
        print("Set VIDEO_URL in .env to your IP Webcam URL, or use 0 for the default webcam.")
        return

    width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    if width <= 0 or height <= 0:

        ret, frame = cap.read()

        if not ret:
            return

        height, width = frame.shape[:2]

    fps = 20

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    out = cv2.VideoWriter(
        OUTPUT_VIDEO,
        fourcc,
        fps,
        (width, height)
    )

    print("RescueCam Started...")
    print("Press ESC to Exit")

    try:
        voice_thread = threading.Thread(
            target=start_voice_monitor,
            args=(get_current_gps, AUDIO_URL),
            daemon=True
        )
        voice_thread.start()
    except Exception as exc:
        print(f"Voice monitor failed to start: {exc}")

    frame_index = 0

    while True:
        frame_index += 1

        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame")
            break

        results = detect(frame)

        annotated = frame.copy()

        if len(results) > 0:

            result = results[0]
            gps = get_latest_gps()
            used_survivor_ids = set()

            if result.boxes is not None:

                for detection_index, box in enumerate(result.boxes):

                    cls = int(box.cls[0])

                    class_name = result.names[cls]

                    if class_name != "person":
                        continue

                    confidence = float(box.conf[0])

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0]
                    )

                    box_area = max(x2 - x1, 0) * max(y2 - y1, 0)

                    if box_area < MIN_PERSON_BOX_AREA:
                        continue

                    keypoints = extract_pose_keypoints(
                        result,
                        detection_index
                    )

                    posture = estimate_posture(
                        x1,
                        y1,
                        x2,
                        y2,
                        keypoints
                    )

                    track_id = None

                    if box.id is not None:

                        track_id = int(
                            box.id[0]
                        )

                    cv2.rectangle(
                        annotated,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    label = (
                        f"Survivor {track_id} | {posture}"
                        if track_id is not None
                        else f"Survivor | {posture}"
                    )

                    cv2.putText(
                        annotated,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    gps_label = (
                        f"GPS: {gps['latitude']:.6f}, "
                        f"{gps['longitude']:.6f}"
                    )

                    cv2.putText(
                        annotated,
                        gps_label,
                        (x1, min(y2 + 22, height - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 255),
                        2
                    )

                    bbox = [x1, y1, x2, y2]
                    survivor_id = resolve_camera_survivor_id(
                        track_id,
                        bbox,
                        frame_index,
                        used_survivor_ids
                    )

                    image_path = f"survivors/survivor_{survivor_id}.jpg"
                    survivor_img = frame[y1:y2, x1:x2]
                    enhanced_img = enhance_image(survivor_img)
                    image_quality = get_public_image_quality(
                        enhanced_img,
                        keypoints=keypoints
                    )

                    if survivor_id not in saved_ids:
                        saved_ids.add(survivor_id)
                        cv2.imwrite(image_path, enhanced_img)
                        print(f"Saved Survivor {survivor_id} (enhanced)")

                    record = {
                        "survivor_id": survivor_id,
                        "image": image_path,
                        "latitude": gps["latitude"],
                        "longitude": gps["longitude"],
                        "direction": gps["direction"],
                        "posture": posture,
                        "confidence": round(confidence, 3),
                        "bbox": bbox,
                        **image_quality
                    }

                    save_survivor_record(record)

        out.write(annotated)

        cv2.imshow(
            "RescueCam",
            annotated
        )

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    out.release()

    cv2.destroyAllWindows()

    print(
        f"Video saved as "
        f"{OUTPUT_VIDEO}"
    )

    generate_reports()


if __name__ == "__main__":
    main()
