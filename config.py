import os

from dotenv import load_dotenv


load_dotenv()


VIDEO_URL = os.getenv("VIDEO_URL", "http://192.168.1.103:8080/video")
AUDIO_URL = os.getenv("AUDIO_URL", "http://192.168.1.103:8080/audio.wav")

GPS_SERVER_PORT = int(os.getenv("GPS_SERVER_PORT", "8888"))
GPS_LATEST_URL = f"http://127.0.0.1:{GPS_SERVER_PORT}/latest"

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n-pose.pt")
PERSON_CONFIDENCE = float(os.getenv("PERSON_CONFIDENCE", "0.65"))
PERSON_IOU = float(os.getenv("PERSON_IOU", "0.45"))
MIN_PERSON_BOX_AREA = int(os.getenv("MIN_PERSON_BOX_AREA", "2500"))

SURVIVOR_FOLDER = os.getenv("SURVIVOR_FOLDER", "survivors")
