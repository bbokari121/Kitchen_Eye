"""Video file player with optional YOLO detection overlay."""
import os
import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog


class VideoPlayer:
    """
    Plays a video file frame-by-frame via a QTimer, optionally running
    a YOLODetector on each frame before passing the result to a display
    callback.

    Usage
    -----
    player = VideoPlayer(frame_callback=my_fn, detector=my_detector)
    path = player.open_file_dialog(parent=self)
    if path:
        player.start(path)
    """

    def __init__(self, frame_callback, detector=None):
        """
        Parameters
        ----------
        frame_callback : callable
            Called with an RGB numpy array for every decoded frame.
        detector : YOLODetector | None
            When provided, predict() and draw_boxes() are called before
            passing each frame to *frame_callback*.
        """
        self._frame_callback = frame_callback
        self._detector = detector
        self._cap = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._read_frame)
        self._finished_callback = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_file_dialog(self, parent=None):
        """Show an open-file dialog and return the selected path, or None."""
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Open Video File",
            os.path.expanduser("~"),
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)",
        )
        return path if path else None

    def start(self, video_path):
        """Open *video_path* and begin playback. Returns True on success."""
        self.stop()
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            self._cap = None
            return False
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        interval_ms = max(1, int(1000.0 / fps))
        self._timer.start(interval_ms)
        return True

    def stop(self):
        """Stop playback and release the video capture handle."""
        self._timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def is_playing(self):
        """Return True while the video timer is active."""
        return self._cap is not None and self._timer.isActive()

    def set_finished_callback(self, callback):
        """Register a no-argument callable invoked when the video ends."""
        self._finished_callback = callback

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _read_frame(self):
        if self._cap is None or not self._cap.isOpened():
            self._on_end()
            return

        ret, frame = self._cap.read()
        if not ret:
            self._on_end()
            return

        if self._detector is not None:
            detections = self._detector.predict(frame)
            frame = self._detector.draw_boxes(frame, detections)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._frame_callback(rgb)

    def _on_end(self):
        self.stop()
        if self._finished_callback is not None:
            self._finished_callback()
