# starts the app, connects everything together, entry point
import torch
import sys
import os

# macOS: rename process so dock/taskbar shows "KitchenEye" not "Python"
if sys.platform == "darwin":
    try:
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        if bundle:
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info:
                info["CFBundleName"] = "KitchenEye"
    except ImportError:
        pass  # pyobjc not installed — title still works, dock label stays Python

# Add parent directory to path so 'app' module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from app.ui.main_window import MainWindow

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KitchenEye")
    app.setApplicationDisplayName("KitchenEye")
    app.setWindowIcon(QIcon(os.path.join(ASSETS_DIR, "logo.png")))
    window = MainWindow()
    window.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()