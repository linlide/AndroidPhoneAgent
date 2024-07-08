import sys
import logging
from PyQt5.QtWidgets import QApplication
from gui import MainWindow

def setup_logging():
    logging.basicConfig(
        filename='iphone_mirroring_agent.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        logger.info("Ctrl+C detected. Exiting gracefully...")
        window.save_settings()
        app.quit()
        sys.exit(0)

if __name__ == "__main__":
    main()