import sys
import os
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLE_PATH = os.path.join(os.path.dirname(__file__), "main_window.qss")

class CameraFrame(QFrame):
    """Camera container where the feed fills the frame and info box overlays it."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cameraContainer")
        self.setMinimumHeight(450)

        # Feed label — sized to fill via resizeEvent
        self.feed_label = QLabel(self)
        self.feed_label.setObjectName("cameraFeedLabel")
        self.feed_label.setAlignment(Qt.AlignCenter)

        # Info overlay — fixed size, positioned top-left
        self.info_box = QFrame(self)
        self.info_box.setObjectName("cameraInfoBox")
        self.info_box.setFixedSize(195, 58)

        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(10, 7, 10, 7)
        info_layout.setSpacing(2)
        title_lbl = QLabel("CAMERA FEED ACTIVE")
        title_lbl.setObjectName("cameraInfoTitle")
        meta_lbl = QLabel("1920x1080 @ 30fps")
        meta_lbl.setObjectName("cameraInfoMeta")
        info_layout.addWidget(title_lbl)
        info_layout.addWidget(meta_lbl)

        self.info_box.raise_()

    def resizeEvent(self, event):
        self.feed_label.setGeometry(0, 0, self.width(), self.height())
        self.info_box.move(12, 12)
        super().resizeEvent(event)


class TranscriptEntry(QFrame):
    def __init__(self, text, time_str):
        super().__init__()
        self.setObjectName("transcriptEntry")
        self.setFixedHeight(46)
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("KitchenEye")
        self.resize(1200, 900)
        self._cap = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._load_styles()
        self.init_ui()
        self._start_camera()

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
        live_text = QLabel("LIVE")
        live_text.setObjectName("liveText")
        live_layout.addWidget(live_dot)
        live_layout.addWidget(live_text)

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
        batt_text = QLabel("80%")
        batt_text.setObjectName("batteryText")
        batt_layout.addWidget(batt_icon)
        batt_layout.addWidget(batt_text)

        right_header.addWidget(live_badge)
        right_header.addWidget(battery_frame)

        header.addLayout(left_header)
        header.addLayout(right_header)
        main_layout.addLayout(header)

        main_layout.addWidget(self.get_separator())

        self._cam_frame = CameraFrame()
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

        # Add sample transcript entries
        self.scroll_vbox.addWidget(TranscriptEntry("Hot pan ahead", "10:34:12"))
        self.scroll_vbox.addWidget(TranscriptEntry("Salt to your right", "10:34:15"))
        self.scroll_vbox.addWidget(TranscriptEntry("Knife to right", "10:34:18"))
        self.scroll_vbox.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

    def _start_camera(self):
        self._cap = cv2.VideoCapture(0)
        if self._cap.isOpened():
            self._timer.start(33)  # ~30 fps
        else:
            self._camera_label.setText("No camera found")

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
        if self._cap is not None:
            self._cap.release()
        super().closeEvent(event)

    def run(self):
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())