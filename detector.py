from ultralytics import YOLO
from config import PERSON_CONFIDENCE, PERSON_IOU, YOLO_MODEL

model = YOLO(YOLO_MODEL)

def detect(frame):

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        conf=PERSON_CONFIDENCE,
        iou=PERSON_IOU,
        verbose=False
    )

    return results
