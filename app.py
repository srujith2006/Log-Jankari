import cv2
import json
import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

from config import (
    CAMERA_READ_FAILURE_LIMIT,
    DETECTION_FRAME_SKIP,
    GPS_LATEST_URL,
    GPS_REQUEST_TIMEOUT_SECONDS,
    MIN_PERSON_BOX_AREA,
    PROCESS_FRAME_WIDTH,
    RECORD_OUTPUT_VIDEO,
    SURVIVOR_SAVE_INTERVAL_SECONDS,
    USE_MONGO,
    VIDEO_URL,
)
from detector import detect

# Load environment variables
load_dotenv()

# MongoDB integration
try:
    from reports.connection import get_database
    MONGO_ENABLED = USE_MONGO
except ImportError:
    MONGO_ENABLED = False
    print("Warning: MongoDB not configured. Will save to JSON only.")

OUTPUT_VIDEO = "rescue_video.mp4"
SURVIVOR_REPORT = "reports/survivors.json"
http_session = requests.Session()

os.makedirs("survivors", exist_ok=True)
os.makedirs("reports", exist_ok=True)

saved_ids = set()
survivor_records = {}
camera_tracks = {}
last_record_save_times = {}
survivor_image_quality = {}
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
        response = http_session.get(
            GPS_LATEST_URL,
            timeout=GPS_REQUEST_TIMEOUT_SECONDS
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


def open_video_capture(video_source):
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1000)
    return cap


def resize_for_detection(frame):
    if PROCESS_FRAME_WIDTH <= 0:
        return frame, 1.0, 1.0

    height, width = frame.shape[:2]
    if width <= PROCESS_FRAME_WIDTH:
        return frame, 1.0, 1.0

    scale = PROCESS_FRAME_WIDTH / width
    resized_height = max(1, int(height * scale))
    resized = cv2.resize(frame, (PROCESS_FRAME_WIDTH, resized_height))
    return resized, width / PROCESS_FRAME_WIDTH, height / resized_height


def scale_bbox_to_frame(bbox, scale_x, scale_y):
    x1, y1, x2, y2 = bbox
    return [
        int(x1 * scale_x),
        int(y1 * scale_y),
        int(x2 * scale_x),
        int(y2 * scale_y),
    ]


def scale_keypoints_to_frame(keypoints, scale_x, scale_y):
    if keypoints is None:
        return None

    scaled = []
    for point in keypoints:
        scaled.append({
            **point,
            "x": point["x"] * scale_x,
            "y": point["y"] * scale_y,
        })
    return scaled


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
    """Apply light noise reduction without altering image sharpness."""
    if image is None or image.size == 0:
        return image
    
    try:
        return cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=3,
            hColor=3,
            templateWindowSize=7,
            searchWindowSize=21,
        )
    except Exception as exc:
        print(f"Image noise reduction failed: {exc}")
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


def crop_frame(frame, bbox):
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None

    return crop


def save_survivor_image(image_path, image):
    if image is None or image.size == 0:
        return False

    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    try:
        saved = cv2.imwrite(image_path, image)
    except Exception as exc:
        print(f"Survivor image save failed for {image_path}: {exc}")
        return False

    if not saved:
        print(f"Survivor image save failed for {image_path}")
        return False

    return True


def write_survivor_report():
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


def should_persist_survivor_record(survivor_id):
    now = time.monotonic()
    last_saved = last_record_save_times.get(survivor_id)

    if last_saved is None:
        last_record_save_times[survivor_id] = now
        return True

    if now - last_saved >= SURVIVOR_SAVE_INTERVAL_SECONDS:
        last_record_save_times[survivor_id] = now
        return True

    return False


def save_survivor_record(record, persist=True):
    """
    Save survivor record to both local JSON and MongoDB
    """
    if "timestamp" not in record:
        record["timestamp"] = datetime.now().isoformat()

    if "identified" not in record:
        record["identified"] = False

    survivor_records[record["survivor_id"]] = record

    if not persist:
        return

    # Save to local JSON (backup)
    write_survivor_report()

    # Save to MongoDB (primary storage)
    if MONGO_ENABLED:
        try:
            db = get_database()
            if db is not None:
                # Upsert: update if exists, insert if new
                db.survivors.update_one(
                    {"survivor_id": record["survivor_id"]},
                    {"$set": record},
                    upsert=True
                )
                print(f"✓ Saved to MongoDB: {record['survivor_id']}")
        except Exception as e:
            print(f"✗ Error saving to MongoDB: {e}")


def generate_reports():

    if not survivor_records:
        return

    survivors = list(survivor_records.values())

    try:
        from map_generator import generate_map

        map_path = generate_map(survivors)
        print(f"Map report generated: {map_path}")
    except Exception as e:
        print(f"Map report not generated: {e}")

    try:
        from report_generator import generate_report

        generate_report(survivors)
        print("PDF report generated: reports/survivor_report.pdf")
    except Exception as e:
        print(f"PDF report not generated: {e}")


def main():

    video_source = int(VIDEO_URL) if str(VIDEO_URL).isdigit() else VIDEO_URL
    cap = open_video_capture(video_source)

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

    out = None
    if RECORD_OUTPUT_VIDEO:
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

    frame_index = 0
    read_failures = 0
    last_annotated = None

    while True:
        frame_index += 1

        ret, frame = cap.read()

        if not ret:
            read_failures += 1
            print(f"Failed to read frame ({read_failures}/{CAMERA_READ_FAILURE_LIMIT})")
            if read_failures >= CAMERA_READ_FAILURE_LIMIT:
                print("Reconnecting to video source...")
                cap.release()
                time.sleep(1)
                cap = open_video_capture(video_source)
                read_failures = 0
                if not cap.isOpened():
                    print(f"Cannot reconnect to video source: {VIDEO_URL}")
                    break
            continue

        read_failures = 0

        if frame_index % DETECTION_FRAME_SKIP != 0 and last_annotated is not None:
            cv2.imshow("RescueCam", last_annotated)
            if cv2.waitKey(1) & 0xFF == 27:
                break
            continue

        detection_frame, scale_x, scale_y = resize_for_detection(frame)

        results = detect(detection_frame)

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

                    detected_bbox = list(map(
                        int,
                        box.xyxy[0]
                    ))
                    x1, y1, x2, y2 = scale_bbox_to_frame(detected_bbox, scale_x, scale_y)

                    box_area = max(x2 - x1, 0) * max(y2 - y1, 0)

                    if box_area < MIN_PERSON_BOX_AREA:
                        continue

                    keypoints = extract_pose_keypoints(
                        result,
                        detection_index
                    )
                    keypoints = scale_keypoints_to_frame(keypoints, scale_x, scale_y)

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
                    image_exists = os.path.exists(image_path)
                    image_quality = survivor_image_quality.get(survivor_id, {
                        "face_detected": False,
                        "blur_score": 0.0,
                        "public_visible": False,
                        "quality_note": "Image quality not checked yet",
                    })
                    if survivor_id not in saved_ids or not image_exists:
                        survivor_img = crop_frame(frame, bbox)
                        enhanced_img = enhance_image(survivor_img)
                        image_quality = get_public_image_quality(
                            enhanced_img,
                            keypoints=keypoints
                        )
                        if save_survivor_image(image_path, enhanced_img):
                            saved_ids.add(survivor_id)
                            survivor_image_quality[survivor_id] = image_quality
                            print(f"Saved Survivor {survivor_id} image: {image_path}")
                        else:
                            image_path = "unknown.jpg"

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

                    persist_record = should_persist_survivor_record(survivor_id)
                    save_survivor_record(record, persist=persist_record)

        if out is not None:
            out.write(annotated)

        last_annotated = annotated
        cv2.imshow(
            "RescueCam",
            annotated
        )

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    if out is not None:
        out.release()

    cv2.destroyAllWindows()

    if RECORD_OUTPUT_VIDEO:
        print(
            f"Video saved as "
            f"{OUTPUT_VIDEO}"
        )

    write_survivor_report()
    generate_reports()


if __name__ == "__main__":
    main()
