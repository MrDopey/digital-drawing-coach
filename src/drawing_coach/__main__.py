import sys


def main() -> None:
    from PyQt6.QtWidgets import QApplication
    from drawing_coach.main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName("Drawing Coach")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
