import sys
from PyQt5.QtWidgets import QApplication
from gui import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Exiting gracefully...")
        window.save_settings()
        app.quit()
        sys.exit(0)

if __name__ == "__main__":
    main()