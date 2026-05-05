"""Reusable UI components."""


class BoundingBoxOverlay:
    """Draws detection bounding boxes over a frame."""

    def draw(self, frame, detections):
        raise NotImplementedError


class AlertBanner:
    """Displays an on-screen alert message."""

    def show(self, message: str):
        raise NotImplementedError
