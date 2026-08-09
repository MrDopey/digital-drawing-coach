import sys


def main() -> None:
    import logging

    from drawing_coach.logging_config import setup_logging

    setup_logging()

    from drawing_coach._version import __version__

    logging.getLogger("drawing_coach").info("Drawing Coach v%s starting", __version__)

    from PyQt6.QtWidgets import QApplication

    from drawing_coach.main_window import MainWindow
    from drawing_coach.session_picker_dialog import SessionPickerDialog

    app = QApplication(sys.argv)
    app.setApplicationName("Drawing Coach")

    # Installed before the session picker so a stall inside its nested exec()
    # loop is caught too. No-op unless DRAWING_COACH_PERF_WATCHDOG is set.
    from drawing_coach import perf

    perf.install_watchdog()
    app.aboutToQuit.connect(perf.log_summary)

    action, session_dir = SessionPickerDialog.choose_session()
    if action == "quit":
        sys.exit(0)

    window = MainWindow(session_dir=session_dir, start_new=(action == "new"))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
