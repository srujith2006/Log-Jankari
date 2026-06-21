import os

from dotenv import load_dotenv


load_dotenv()


VIDEO_URL = os.getenv("VIDEO_URL", "http://192.168.1.103:8080/video")

GPS_SERVER_PORT = int(os.getenv("GPS_SERVER_PORT", "8888"))
GPS_LATEST_URL = f"http://127.0.0.1:{GPS_SERVER_PORT}/latest"
GPS_REQUEST_TIMEOUT_SECONDS = float(os.getenv("GPS_REQUEST_TIMEOUT_SECONDS", "0.2"))
USE_MONGO = os.getenv("USE_MONGO", "0") == "1"
RECORD_OUTPUT_VIDEO = os.getenv("RECORD_OUTPUT_VIDEO", "0") == "1"
SURVIVOR_SAVE_INTERVAL_SECONDS = float(os.getenv("SURVIVOR_SAVE_INTERVAL_SECONDS", "1.0"))
DETECTION_FRAME_SKIP = max(1, int(os.getenv("DETECTION_FRAME_SKIP", "2")))
PROCESS_FRAME_WIDTH = int(os.getenv("PROCESS_FRAME_WIDTH", "640"))
CAMERA_READ_FAILURE_LIMIT = int(os.getenv("CAMERA_READ_FAILURE_LIMIT", "20"))

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n-pose.pt")
PERSON_CONFIDENCE = float(os.getenv("PERSON_CONFIDENCE", "0.65"))
PERSON_IOU = float(os.getenv("PERSON_IOU", "0.45"))
MIN_PERSON_BOX_AREA = int(os.getenv("MIN_PERSON_BOX_AREA", "2500"))

SURVIVOR_FOLDER = os.getenv("SURVIVOR_FOLDER", "survivors")
