import cv2
from config import VIDEO_URL
from detector import detect

OUTPUT_VIDEO = "objDet_output.mp4"


def main():
    cap = cv2.VideoCapture(VIDEO_URL)

    if not cap.isOpened():
        print("Cannot connect to IP Webcam")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    ret, frame = cap.read()
    if not ret:
        print("Failed to read first frame")
        cap.release()
        return

    if width <= 0 or height <= 0:
        height, width = frame.shape[:2]

    fps = 20
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(
        OUTPUT_VIDEO,
        fourcc,
        fps,
        (width, height)
    )

    try:
        while True:
            results = detect(frame)
            annotated = results[0].plot()

            out.write(annotated)
            cv2.imshow("RescueCam", annotated)

            if cv2.waitKey(1) & 0xFF == 27:
                break

            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

    print(f"Video saved as {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
