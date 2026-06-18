import json
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parent
SURVIVORS_JSON = PROJECT_ROOT / "reports" / "survivors.json"
MIN_PUBLIC_BLUR_SCORE = 80.0


def get_blur_score(image):
    if image is None or image.size == 0:
        return 0.0

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def detect_face(image):
    if image is None or image.size == 0:
        return False

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_names = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_profileface.xml",
    ]

    for cascade_name in cascade_names:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_name)
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(20, 20),
        )
        if len(faces) > 0:
            return True

    return False


def quality_note(face_detected, blur_score):
    if not face_detected:
        return "Hidden from public: no clear face detected"
    if blur_score < MIN_PUBLIC_BLUR_SCORE:
        return "Hidden from public: face image is too blurred"
    return "Public image approved"


def main():
    with SURVIVORS_JSON.open("r", encoding="utf-8") as f:
        survivors = json.load(f)

    for survivor in survivors:
        image_path = survivor.get("image")
        full_path = PROJECT_ROOT / image_path if image_path else None

        image = cv2.imread(str(full_path)) if full_path and full_path.exists() else None
        blur_score = round(get_blur_score(image), 2)
        face_detected = detect_face(image)
        public_visible = face_detected and blur_score >= MIN_PUBLIC_BLUR_SCORE

        survivor["face_detected"] = face_detected
        survivor["blur_score"] = blur_score
        survivor["public_visible"] = public_visible
        survivor["quality_note"] = quality_note(face_detected, blur_score)

        print(
            f"{survivor.get('survivor_id')}: "
            f"face={face_detected}, blur={blur_score}, public={public_visible}"
        )

    with SURVIVORS_JSON.open("w", encoding="utf-8") as f:
        json.dump(survivors, f, indent=4)

    try:
        from reports.connection import get_database

        db = get_database()
        for survivor in survivors:
            survivor_id = survivor.get("survivor_id")
            if not survivor_id:
                continue

            db.survivors.update_one(
                {"survivor_id": survivor_id},
                {
                    "$set": {
                        "face_detected": survivor.get("face_detected"),
                        "blur_score": survivor.get("blur_score"),
                        "public_visible": survivor.get("public_visible"),
                        "quality_note": survivor.get("quality_note"),
                    }
                },
            )
        print("MongoDB survivor image quality metadata synced.")
    except Exception as exc:
        print(f"MongoDB sync skipped: {exc}")


if __name__ == "__main__":
    main()
