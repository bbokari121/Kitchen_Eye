import sys
import os
import json
import cv2
import psutil
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from app.audio.voice_assistant import VoiceAssistantController
from app.utils.config import Config

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLE_PATH = os.path.join(os.path.dirname(__file__), "main_window.qss")

class CameraFrame(QFrame):
    """Camera container where the feed fills the frame."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cameraContainer")
        self.setMinimumHeight(450)
        self.setCursor(Qt.PointingHandCursor)

        # Feed label — sized to fill via resizeEvent
        self.feed_label = QLabel(self)
        self.feed_label.setObjectName("cameraFeedLabel")
        self.feed_label.setAlignment(Qt.AlignCenter)

    def resizeEvent(self, event):
        self.feed_label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class TranscriptEntry(QFrame):
    replay = pyqtSignal(str)

    def __init__(self, text, time_str):
        super().__init__()
        self._text = text
        self.setObjectName("transcriptEntry")
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        dot = QLabel("●")
        dot.setObjectName("entryDot")
        
        msg = QLabel(text)
        msg.setObjectName("entryMessage")
        
        time_lbl = QLabel(time_str)
        time_lbl.setObjectName("entryTime")
        
        layout.addWidget(dot)
        layout.addWidget(msg)
        layout.addStretch()
        layout.addWidget(time_lbl)

    def mousePressEvent(self, event):
        self.replay.emit(self._text)
        super().mousePressEvent(event)

class MainWindow(QWidget):
    _transcript_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("KitchenEye")
        self.resize(1200, 900)
        self._cap = None
        self._camera_on = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        
        # Initialize audio components
        self.config = Config()
        self.voice_assistant = VoiceAssistantController(
            self.config,
            on_command_detected=self._transcript_ready.emit,
        )

        self._transcript_ready.connect(self._add_transcript_entry)

        self._load_styles()
        self.init_ui()
        self._set_camera_state(False)
        self.voice_assistant.start()

        # Battery refresh every 30 s
        self._battery_timer = QTimer(self)
        self._battery_timer.timeout.connect(self._update_battery)
        self._battery_timer.start(30_000)
        self._update_battery()  # populate immediately

    def get_separator(self):
        line = QFrame()
        line.setObjectName("separatorLine")
        return line

    def _load_styles(self):
        if os.path.exists(STYLE_PATH):
            with open(STYLE_PATH, "r", encoding="utf-8") as style_file:
                self.setStyleSheet(style_file.read())

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        header = QHBoxLayout()
        header.setSpacing(12)
        
        logo = QLabel()
        logo.setFixedSize(60, 60)
        logo.setAlignment(Qt.AlignCenter)
        _logo_px = QPixmap(os.path.join(ASSETS_DIR, "logo.png"))
        if not _logo_px.isNull():
            logo.setPixmap(_logo_px.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        title = QLabel("KitchenEye")
        title.setObjectName("titleLabel")

        left_header = QHBoxLayout()
        left_header.addWidget(logo)
        left_header.addWidget(title)
        left_header.addStretch()

        right_header = QHBoxLayout()
        right_header.setSpacing(10)
        
        live_badge = QFrame()
        live_badge.setObjectName("liveBadge")
        live_badge.setMinimumWidth(128)
        live_badge.setFixedHeight(38)
        live_layout = QHBoxLayout(live_badge)
        live_layout.setContentsMargins(18, 4, 18, 4)
        live_layout.setSpacing(7)

        live_dot = QLabel("●")
        live_dot.setObjectName("liveDot")
        self.live_text = QLabel("LIVE")
        self.live_text.setObjectName("liveText")
        live_layout.addWidget(live_dot)
        live_layout.addWidget(self.live_text)

        battery_frame = QFrame()
        battery_frame.setObjectName("batteryFrame")
        battery_frame.setMinimumWidth(132)
        battery_frame.setFixedHeight(38)
        batt_layout = QHBoxLayout(battery_frame)
        batt_layout.setContentsMargins(18, 4, 18, 4)
        batt_layout.setSpacing(6)

        batt_icon = QLabel()
        batt_icon.setObjectName("batteryIcon")
        _batt_px = QPixmap(os.path.join(ASSETS_DIR, "battery_icon.png"))
        if not _batt_px.isNull():
            batt_icon.setPixmap(_batt_px.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self._batt_text = QLabel("--")
        self._batt_text.setObjectName("batteryText")
        batt_layout.addWidget(batt_icon)
        batt_layout.addWidget(self._batt_text)

        right_header.addWidget(live_badge)
        right_header.addWidget(battery_frame)

        header.addLayout(left_header)
        header.addLayout(right_header)
        main_layout.addLayout(header)

        main_layout.addWidget(self.get_separator())

        self._cam_frame = CameraFrame()
        self._cam_frame.clicked.connect(self._toggle_camera)
        self._camera_label = self._cam_frame.feed_label
        main_layout.addWidget(self._cam_frame)

        main_layout.addWidget(self.get_separator())

        transcript_header = QHBoxLayout()
        t_dot = QLabel("●")
        t_dot.setObjectName("transcriptDot")
        t_title = QLabel("VOICE ASSISTANT TRANSCRIPT")
        t_title.setObjectName("transcriptTitle")
        
        transcript_header.addWidget(t_dot)
        transcript_header.addWidget(t_title)
        transcript_header.addStretch()
        main_layout.addLayout(transcript_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("transcriptScrollArea")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("transcriptScrollContent")
        self.scroll_vbox = QVBoxLayout(self.scroll_content)
        self.scroll_vbox.setContentsMargins(0, 0, 10, 0)
        self.scroll_vbox.setSpacing(10)

        self.scroll_vbox.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

    def _update_battery(self):
        batt = psutil.sensors_battery()
        if batt is not None:
            pct = int(batt.percent)
            charging = batt.power_plugged
            label = f"{pct}%"
        else:
            label = "N/A"
        self._batt_text.setText(label)

    def _add_transcript_entry(self, text):
        current_time = datetime.now().strftime("%H:%M:%S")
        entry = TranscriptEntry(text, current_time)
        entry.replay.connect(self.voice_assistant.replay)
        self.scroll_vbox.insertWidget(0, entry)

    def _start_camera(self):
        device = self.config.get("camera.device_index", 0)
        self._cap = cv2.VideoCapture(device)
        if self._cap.isOpened():
            frame_size = None
            ret, frame = self._cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                frame_size = (w, h)
            self._log_camera_startup(
                detected=True,
                device_index=device,
                width=(frame_size[0] if frame_size else None),
                height=(frame_size[1] if frame_size else None),
                fps=None,
            )
            self._timer.start(33)  # ~30 fps
            self._camera_on = True
            self.live_text.setText("LIVE")
            self._camera_label.clear()
        else:
            self._log_camera_startup(
                detected=False,
                device_index=device,
                width=None,
                height=None,
                fps=None,
            )
            self._set_camera_state(False)
            self._camera_label.setText("No camera found")

    def _stop_camera(self):
        self._timer.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._camera_on = False
        self.live_text.setText("NOT LIVE")
        self._show_camera_off_state()

    def _toggle_camera(self):
        if self._camera_on:
            self._stop_camera()
        else:
            self._start_camera()

    def _set_camera_state(self, enabled):
        if enabled:
            self._start_camera()
        else:
            self._stop_camera()

    def _show_camera_off_state(self):
        self._camera_label.setPixmap(self._build_camera_off_placeholder())

    def _log_camera_startup(self, detected, device_index, width, height, fps):
        payload = {
            "camera_start": {
                "detected": detected,
                "device_index": device_index,
                "resolution": {
                    "width": width,
                    "height": height,
                },
                "fps": fps,
            }
        }
        print(json.dumps(payload), flush=True)

    def _build_camera_off_placeholder(self):
        width = max(self._camera_label.width(), 600)
        height = max(self._camera_label.height(), 300)

        pix = QPixmap(width, height)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        eye_w = min(width * 0.16, 140)
        eye_h = eye_w * 0.6
        center_x = width / 2
        center_y = height / 2 - 30

        stroke = QPen(QColor("#8EA6B8"))
        stroke.setWidth(6)
        painter.setPen(stroke)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(center_x - eye_w / 2), int(center_y - eye_h / 2), int(eye_w), int(eye_h))
        painter.drawEllipse(int(center_x - eye_h / 6), int(center_y - eye_h / 6), int(eye_h / 3), int(eye_h / 3))

        slash = QPen(QColor("#8EA6B8"))
        slash.setWidth(7)
        painter.setPen(slash)
        painter.drawLine(
            int(center_x - eye_w / 2 - 12),
            int(center_y + eye_h / 2 + 12),
            int(center_x + eye_w / 2 + 12),
            int(center_y - eye_h / 2 - 12),
        )

        painter.setPen(QColor("#C7D6E2"))
        text_rect_y = int(center_y + eye_h / 2 + 28)
        painter.drawText(
            0,
            text_rect_y,
            width,
            40,
            Qt.AlignHCenter | Qt.AlignVCenter,
            "Tap to turn on webcam",
        )

        painter.end()
        return pix

    def _update_frame(self):
        if self._cap is None or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        self._camera_label.setPixmap(
            pixmap.scaled(
                self._camera_label.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
        )

    def closeEvent(self, event):
        self._timer.stop()
        self.voice_assistant.stop()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._camera_on:
            self._show_camera_off_state()

    def run(self):
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())