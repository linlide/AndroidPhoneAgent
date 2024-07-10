import os
import json
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTextEdit, QGroupBox, QStatusBar,
                             QSizePolicy, QMessageBox, QComboBox, QDoubleSpinBox, QSpinBox,
                             QFileDialog)
from PyQt5.QtGui import QIcon, QMouseEvent, QPixmap
from PyQt5.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal
import pyautogui
import base64
from agent import iPhoneMirroringAgent
from export_utils import export_conversation
from constants import (DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, 
                       DEFAULT_MAX_MESSAGES, AVAILABLE_MODELS)
import screen
from datetime import datetime

class PasswordLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEchoMode(QLineEdit.Password)

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.parent = parent

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.pixmap() and self.parent:
            pixmap_size = self.pixmap().size()
            label_size = self.size()
            x_scale = pixmap_size.width() / label_size.width()
            y_scale = pixmap_size.height() / label_size.height()

            x = int(event.x() * x_scale)
            y = int(event.y() * y_scale)
            
            self.parent.update_screenshot_cursor_position(x, y)

class AgentThread(QThread):
    update_screenshot_signal = pyqtSignal(str, tuple)
    task_completed_signal = pyqtSignal(bool, str)
    update_status_signal = pyqtSignal(str)

    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def run(self):
        self.agent.run(self.update_screenshot_signal.emit, self.task_completed_signal.emit, self.update_status_signal.emit)

class ScreenshotThread(QThread):
    screenshot_taken = pyqtSignal(str, tuple)
    screenshot_error = pyqtSignal(str)

    def run(self):
        try:
            screenshot_data, cursor_position = screen.capture_screenshot()
            self.screenshot_taken.emit(screenshot_data, cursor_position)
        except Exception as e:
            self.screenshot_error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setWindowTitle("iPhone Mirroring Agent")
        
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        
        self.setFixedSize(800, 600)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
                background-color: #e0e0e0;
                color: #888888;
            }
        """)

        self.init_ui()
        self.agent = None
        self.agent_thread = None
        self.settings_file = "settings.json"
        self.load_settings()

        self.api_key_input.textChanged.connect(self.save_settings)
        self.model_input.currentTextChanged.connect(self.save_settings)
        self.max_tokens_input.valueChanged.connect(self.save_settings)
        self.temperature_input.valueChanged.connect(self.save_settings)
        self.max_messages_input.valueChanged.connect(self.save_settings)
        self.task_input.textChanged.connect(self.save_settings)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.update_screen_cursor_position)
        self.cursor_timer.start(16)

        self.original_pixmap = None

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        self.create_input_fields()
        self.create_screenshot_group()

        self.layout.addLayout(self.left_layout, 1)
        self.layout.addLayout(self.right_layout, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_input_fields(self):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(10, 15, 10, 35)

        def add_input_field(label_text, widget):
            layout.addWidget(QLabel(label_text))
            layout.addSpacing(5)
            layout.addWidget(widget)
            layout.addSpacing(15)

        self.api_key_input = PasswordLineEdit()
        add_input_field("API Key", self.api_key_input)

        self.model_input = QComboBox()
        self.model_input.addItems(AVAILABLE_MODELS)
        self.model_input.setCurrentText(DEFAULT_MODEL)
        add_input_field("Model", self.model_input)

        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(1, 100000)
        self.max_tokens_input.setValue(DEFAULT_MAX_TOKENS)
        add_input_field("Max Tokens", self.max_tokens_input)

        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 1.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(DEFAULT_TEMPERATURE)
        add_input_field("Temperature", self.temperature_input)

        self.max_messages_input = QSpinBox()
        self.max_messages_input.setRange(1, 1000)
        self.max_messages_input.setValue(DEFAULT_MAX_MESSAGES)
        add_input_field("Max Messages", self.max_messages_input)

        self.task_input = QTextEdit()
        self.task_input.setFixedHeight(100)
        add_input_field("Task Description", self.task_input)

        layout.addSpacing(30)

        self.left_layout.addLayout(layout)

        self.button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Task")
        self.start_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_button.clicked.connect(self.start_task)
        self.button_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_button.clicked.connect(self.pause_task)
        self.pause_button.hide()
        self.button_layout.addWidget(self.pause_button)

        self.resume_button = QPushButton("Resume")
        self.resume_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.resume_button.clicked.connect(self.resume_task)
        self.resume_button.hide()
        self.button_layout.addWidget(self.resume_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        self.cancel_button.clicked.connect(self.cancel_task)
        self.cancel_button.hide()
        self.button_layout.addWidget(self.cancel_button)

        self.export_button = QPushButton("Export Conversation")
        self.export_button.setIcon(QIcon.fromTheme("document-save"))
        self.export_button.clicked.connect(self.export_conversation)
        self.export_button.hide()
        self.button_layout.addWidget(self.export_button)

        self.left_layout.addLayout(self.button_layout)

    def create_screenshot_group(self):
        self.screenshot_group = QGroupBox("Current Screenshot")
        self.screenshot_layout = QVBoxLayout()
        
        self.screenshot_label = ClickableLabel(self)
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.screenshot_layout.addWidget(self.screenshot_label)
        
        self.screenshot_buttons_layout = QHBoxLayout()
        self.screenshot_button = QPushButton("Take Screenshot")
        self.screenshot_button.clicked.connect(self.take_current_screenshot)
        self.screenshot_buttons_layout.addWidget(self.screenshot_button)
        
        self.save_screenshot_button = QPushButton("Save Screenshot")
        self.save_screenshot_button.clicked.connect(self.save_screenshot)
        self.save_screenshot_button.setDisabled(True)
        self.screenshot_buttons_layout.addWidget(self.save_screenshot_button)
        
        self.screenshot_layout.addLayout(self.screenshot_buttons_layout)
        
        self.screenshot_group.setLayout(self.screenshot_layout)
        self.right_layout.addWidget(self.screenshot_group, 1)
        
        self.screen_cursor_label = QLabel("Screen Cursor:     (    0,    0)")
        self.screenshot_cursor_label = QLabel("Screenshot Cursor: (    0,    0)")
        
        self.right_layout.addWidget(self.screen_cursor_label)
        self.right_layout.addWidget(self.screenshot_cursor_label)

    def take_current_screenshot(self):
        self.screenshot_button.setDisabled(True)
        self.save_screenshot_button.setDisabled(True)
        self.set_fields_readonly(True)
        self.status_bar.showMessage("Taking screenshot...")
        
        self.screenshot_thread = ScreenshotThread()
        self.screenshot_thread.screenshot_taken.connect(self.on_screenshot_taken)
        self.screenshot_thread.screenshot_error.connect(self.on_screenshot_error)
        self.screenshot_thread.finished.connect(self.on_screenshot_thread_finished)
        self.screenshot_thread.start()

    def on_screenshot_taken(self, screenshot_data, cursor_position):
        self.on_update_screenshot(screenshot_data, cursor_position)
        self.logger.info("Current screenshot taken")
        self.status_bar.showMessage("Screenshot updated", 3000)
        self.set_fields_readonly(False)

    def on_screenshot_error(self, error_message):
        self.logger.error(f"Error taking current screenshot: {error_message}")
        QMessageBox.warning(self, "Screenshot Error", f"Failed to take current screenshot: {error_message}")
        self.set_fields_readonly(False)

    def on_screenshot_thread_finished(self):
        self.screenshot_button.setDisabled(False)

    def save_screenshot(self):
        if self.original_pixmap:
            default_filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", default_filename, "JPEG Files (*.jpg *.jpeg)")
            
            if file_path:
                self.original_pixmap.save(file_path, "JPEG")
                self.status_bar.showMessage(f"Screenshot saved as {file_path}", 3000)
                self.logger.info(f"Screenshot saved: {file_path}")
        else:
            QMessageBox.warning(self, "No Screenshot", "There is no screenshot to save.")
            self.logger.warning("Attempted to save screenshot when none available")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
                self.api_key_input.setText(settings.get("api_key", ""))
                self.model_input.setCurrentText(settings.get("model", DEFAULT_MODEL))
                self.max_tokens_input.setValue(int(settings.get("max_tokens", DEFAULT_MAX_TOKENS)))
                self.temperature_input.setValue(float(settings.get("temperature", DEFAULT_TEMPERATURE)))
                self.max_messages_input.setValue(int(settings.get("max_messages", DEFAULT_MAX_MESSAGES)))
                self.task_input.setPlainText(settings.get("task_description", ""))
                
                pos = settings.get("window_position", None)
                if pos:
                    self.move(QPoint(pos[0], pos[1]))
            self.logger.info("Settings loaded successfully")
        else:
            self.model_input.setCurrentText(DEFAULT_MODEL)
            self.max_tokens_input.setValue(DEFAULT_MAX_TOKENS)
            self.temperature_input.setValue(DEFAULT_TEMPERATURE)
            self.max_messages_input.setValue(DEFAULT_MAX_MESSAGES)
            self.logger.info("Default settings applied")

    def save_settings(self):
        settings = {
            "api_key": self.api_key_input.text(),
            "model": self.model_input.currentText(),
            "max_tokens": self.max_tokens_input.value(),
            "temperature": self.temperature_input.value(),
            "max_messages": self.max_messages_input.value(),
            "task_description": self.task_input.toPlainText(),
            "window_position": [self.pos().x(), self.pos().y()]
        }
        with open(self.settings_file, "w") as f:
            json.dump(settings, f)
        self.logger.info("Settings saved successfully")

    def closeEvent(self, event):
        self.save_settings()
        self.logger.info("Application closed")
        super().closeEvent(event)

    def start_task(self):
        api_key = self.api_key_input.text()
        model = self.model_input.currentText()
        task_description = self.task_input.toPlainText()

        if not api_key or not task_description:
            QMessageBox.warning(self, "Missing Information", "Please enter both API key and task description.")
            self.logger.warning("Task start attempted with missing information")
            return

        max_tokens = self.max_tokens_input.value()
        temperature = self.temperature_input.value()
        max_messages = self.max_messages_input.value()

        self.agent = iPhoneMirroringAgent(
            api_key, model, max_tokens, temperature, max_messages
        )
        self.agent.task_description = task_description
        
        self.agent_thread = AgentThread(self.agent)
        self.agent_thread.update_screenshot_signal.connect(self.on_update_screenshot)
        self.agent_thread.task_completed_signal.connect(self.on_task_completed)
        self.agent_thread.update_status_signal.connect(self.update_status)
        self.agent_thread.start()
        
        self.update_button_visibility("running")
        self.status_bar.showMessage("Task started...")
        self.logger.info(f"Task started: {task_description}")

    def pause_task(self):
        if self.agent and self.agent_thread.isRunning():
            self.agent.pause()
            self.update_button_visibility("paused")
            self.status_bar.showMessage("Task paused")
            self.logger.info("Task paused")

    def resume_task(self):
        if self.agent and self.agent.isPaused():
            self.agent.resume()
            self.update_button_visibility("running")
            self.status_bar.showMessage("Task resumed...")
            self.logger.info("Task resumed")

    def cancel_task(self):
        if self.agent and self.agent_thread.isRunning():
            self.agent.cancel()
            self.status_bar.showMessage("Cancelling task...")
            self.logger.info("Task cancellation requested")

    def update_button_visibility(self, state):
        if state == "idle":
            self.start_button.show()
            self.pause_button.hide()
            self.resume_button.hide()
            self.cancel_button.hide()
            self.export_button.show()
            self.set_fields_readonly(False)
        elif state == "running":
            self.start_button.hide()
            self.pause_button.show()
            self.resume_button.hide()
            self.cancel_button.show()
            self.export_button.hide()
            self.set_fields_readonly(True)
        elif state == "paused":
            self.start_button.hide()
            self.pause_button.hide()
            self.resume_button.show()
            self.cancel_button.show()
            self.export_button.hide()
        self.logger.debug(f"Button visibility updated to state: {state}")

    def set_fields_readonly(self, disabled):
        self.api_key_input.setDisabled(disabled)
        self.model_input.setDisabled(disabled)
        self.max_tokens_input.setDisabled(disabled)
        self.temperature_input.setDisabled(disabled)
        self.max_messages_input.setDisabled(disabled)
        self.task_input.setDisabled(disabled)
        self.logger.debug(f"Input fields set to disabled: {disabled}")

    def on_update_screenshot(self, screenshot_data, cursor_position):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(screenshot_data))
        self.original_pixmap = pixmap
        self.scale_and_set_pixmap()
        self.update_screenshot_cursor_position(cursor_position[0], cursor_position[1])
        self.save_screenshot_button.setDisabled(False)
        self.logger.debug(f"Screenshot updated. Cursor position: {cursor_position}")

    def scale_and_set_pixmap(self):
        if self.original_pixmap:
            label_width = self.screenshot_label.width()
            scaled_pixmap = self.original_pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
            self.screenshot_label.setPixmap(scaled_pixmap)
            self.logger.debug("Screenshot scaled and set")

    def update_screen_cursor_position(self):
        cursor_x, cursor_y = pyautogui.position()
        self.screen_cursor_label.setText(f"Screen Cursor:     ({cursor_x:5d},{cursor_y:5d})")
        self.logger.debug(f"Screen cursor position updated: ({cursor_x}, {cursor_y})")

    def update_screenshot_cursor_position(self, x, y):
        self.screenshot_cursor_label.setText(f"Screenshot Cursor: ({x:5d},{y:5d})")
        self.logger.debug(f"Screenshot cursor position updated: ({x}, {y})")

    def on_task_completed(self, success, reason):
        self.update_button_visibility("idle")
        status = "completed successfully" if success else "failed"
        self.status_bar.showMessage(f"Task {status}")

        if not success:
            QMessageBox.warning(self, "Task Failed", f"The task failed. Reason: {reason}")
        
        self.logger.info(f"Task {status}. Reason: {reason}")

    def export_conversation(self):
        if self.agent:
            export_conversation(self, self.agent)
        else:
            QMessageBox.warning(self, "No Agent", "There is no active agent with a conversation to export.")
        self.logger.info("Conversation exported")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_and_set_pixmap()
        self.logger.debug("Window resized")

    def update_status(self, status):
        self.status_bar.showMessage(status)
        self.logger.debug(f"Status updated: {status}")