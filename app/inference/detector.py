# loads model and runs object detection (YOLO / FRCNN)
from app.utils.config import Config


class Detector:
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._load_model()

    def _load_model(self):
        backend = self.config.get("model.backend", "yolo")
        weights = self.config.get("model.weights")
        raise NotImplementedError(f"Load {backend} weights from {weights}")

    def predict(self, frame):
        """Return list of detections for a single frame."""
        raise NotImplementedError
