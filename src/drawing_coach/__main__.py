import os
import sys


def main() -> None:
    headless = "--headless" in sys.argv or os.environ.get("DRAWING_COACH_HEADLESS") == "1"

    if headless:
        import uvicorn
        port = int(os.environ.get("DRAWING_COACH_PORT", "8080"))
        uvicorn.run("drawing_coach.server:app", host="0.0.0.0", port=port)
    else:
        from PyQt6.QtWidgets import QApplication
        from drawing_coach.main_window import MainWindow
        app = QApplication(sys.argv)
        app.setApplicationName("Drawing Coach")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
