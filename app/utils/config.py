"""Central configuration loader."""
import json
import os

_DEFAULTS = {
    "model.backend": "yolo",
    "model.weights": "models/yolo/best.pt",
    "audio.language": "en",
    "inference.confidence": 0.5,
    "inference.iou_threshold": 0.45,
}


class Config:
    def __init__(self, path: str = "config.json"):
        self._data = dict(_DEFAULTS)
        if os.path.exists(path):
            with open(path) as f:
                self._data.update(json.load(f))

    def get(self, key: str, default=None):
        return self._data.get(key, default)
