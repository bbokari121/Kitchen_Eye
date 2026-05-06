"""YOLOv8 object detector using models/best.pt."""
import os
import cv2
from ultralytics import YOLO

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")


class YOLODetector:
    """Wraps a YOLOv8 model for inference and bounding-box rendering."""

    def __init__(self, weights=MODEL_PATH, conf=0.5):
        self.conf = conf
        self.model = YOLO(weights)

    def predict(self, frame):
        """
        Run inference on a BGR frame.

        Returns a list of dicts:
            {"bbox": [x1, y1, x2, y2], "label": str, "conf": float}
        """
        results = self.model(frame, conf=self.conf, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                label = self.model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                detections.append(
                    {"bbox": [x1, y1, x2, y2], "label": label, "conf": conf}
                )
        return detections

    def draw_boxes(self, frame, detections):
        """Draw bounding boxes onto a BGR frame and return it."""
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            text = f"{det['label']} {det['conf']:.2f}"

            # Filled label background
            (tw, th), baseline = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 128), 2)
            cv2.rectangle(
                frame,
                (x1, y1 - th - baseline - 6),
                (x1 + tw + 6, y1),
                (0, 255, 128),
                -1,
            )
            cv2.putText(
                frame,
                text,
                (x1 + 3, y1 - baseline - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
        return frame
