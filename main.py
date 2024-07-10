import sys
import logging
from PyQt5.QtWidgets import QApplication
from gui import MainWindow

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    3
    file_handler = logging.FileHandler('iphone_mirroring_agent.log')
    file_handler.setLevel(logging.INFO)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

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