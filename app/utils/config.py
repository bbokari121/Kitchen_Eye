"""Central configuration loader."""
import json
import os

_DEFAULTS = {
    "model.backend": "yolo",
    "model.weights": "models/yolo/best.pt",
    "audio.language": "en",
    "inference.confidence": 0.5,
    "inference.iou_threshold": 0.45,
    # Device selection — set these in config.json to target specific hardware
    # e.g. Meta glasses appear as a webcam and audio device in the OS.
    # camera.device_index: OpenCV device index (0 = first/default webcam)
    # audio.input_device_index: PyAudio device index for microphone (null = OS default)
    # audio.output_device_index: reserved for future speaker routing (null = OS default)
    "camera.device_index": 0,
    "audio.input_device_index": None,
    "audio.output_device_index": None,
}


class Config:
    def __init__(self, path: str = "config.json"):
        self._data = dict(_DEFAULTS)
        if os.path.exists(path):
            with open(path) as f:
                self._data.update(json.load(f))

    def get(self, key: str, default=None):
        return self._data.get(key, default)
