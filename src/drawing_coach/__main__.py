import sys


def main() -> None:
    import logging

    from drawing_coach.logging_config import setup_logging

    setup_logging()

    from drawing_coach._version import __version__

    logging.getLogger("drawing_coach").info("Drawing Coach v%s starting", __version__)

    from PyQt6.QtWidgets import QApplication

    from drawing_coach.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Drawing Coach")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
