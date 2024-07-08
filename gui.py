import os
import json
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTextEdit, QGroupBox, QStatusBar,
                             QSizePolicy, QMessageBox)
from PyQt5.QtGui import QIcon, QMouseEvent
from PyQt5.QtCore import Qt, QPoint, QTimer
import pyautogui
from agent import iPhoneMirroringAgent
from export_utils import export_conversation

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
            QLineEdit, QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                font-weight: bold;
            }
        """)

        self.init_ui()
        self.agent = None
        self.settings_file = "settings.json"
        self.load_settings()

        self.api_key_input.textChanged.connect(self.save_settings)
        self.model_input.textChanged.connect(self.save_settings)
        self.max_tokens_input.textChanged.connect(self.save_settings)
        self.temperature_input.textChanged.connect(self.save_settings)
        self.max_messages_input.textChanged.connect(self.save_settings)
        self.task_input.textChanged.connect(self.save_settings)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.update_screen_cursor_position)
        self.cursor_timer.start(16)

        self.original_pixmap = None

        self.conversation = []

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
        add_input_field("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        add_input_field("Model:", self.model_input)

        self.max_tokens_input = QLineEdit()
        add_input_field("Max Tokens:", self.max_tokens_input)

        self.temperature_input = QLineEdit()
        add_input_field("Temperature:", self.temperature_input)

        self.max_messages_input = QLineEdit()
        add_input_field("Max Messages:", self.max_messages_input)

        self.task_input = QTextEdit()
        self.task_input.setFixedHeight(100)
        add_input_field("Task Description:", self.task_input)

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
        
        self.screenshot_group.setLayout(self.screenshot_layout)
        self.right_layout.addWidget(self.screenshot_group, 1)
        
        self.screen_cursor_label = QLabel("Screen Cursor:     (    0,    0)")
        self.screenshot_cursor_label = QLabel("Screenshot Cursor: (    0,    0)")
        
        self.right_layout.addWidget(self.screen_cursor_label)
        self.right_layout.addWidget(self.screenshot_cursor_label)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
                self.api_key_input.setText(settings.get("api_key", ""))
                self.model_input.setText(settings.get("model", "claude-3-5-sonnet-20240620"))
                self.max_tokens_input.setText(str(settings.get("max_tokens", 2048)))
                self.temperature_input.setText(str(settings.get("temperature", 0.7)))
                self.max_messages_input.setText(str(settings.get("max_messages", 20)))
                self.task_input.setPlainText(settings.get("task_description", ""))
                
                pos = settings.get("window_position", None)
                if pos:
                    self.move(QPoint(pos[0], pos[1]))
            self.logger.info("Settings loaded successfully")
        else:
            self.model_input.setText("claude-3-5-sonnet-20240620")
            self.max_tokens_input.setText("2048")
            self.temperature_input.setText("0.7")
            self.max_messages_input.setText("20")
            self.logger.info("Default settings applied")

    def save_settings(self):
        settings = {
            "api_key": self.api_key_input.text(),
            "model": self.model_input.text(),
            "max_tokens": self.max_tokens_input.text(),
            "temperature": self.temperature_input.text(),
            "max_messages": self.max_messages_input.text(),
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
        model = self.model_input.text()
        task_description = self.task_input.toPlainText()

        if not api_key or not task_description:
            QMessageBox.warning(self, "Missing Information", "Please enter both API key and task description.")
            self.logger.warning("Task start attempted with missing information")
            return

        try:
            max_tokens = int(self.max_tokens_input.text())
            temperature = float(self.temperature_input.text())
            max_messages = int(self.max_messages_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for Max Tokens, Temperature, and Max Messages.")
            self.logger.warning("Task start attempted with invalid numeric inputs")
            return

        self.agent = iPhoneMirroringAgent(api_key, model, max_tokens, temperature, max_messages)
        self.agent.update_screenshot.connect(self.update_screenshot)
        self.agent.task_completed.connect(self.on_task_completed)
        self.agent.add_to_conversation.connect(self.add_to_conversation)
        self.agent.add_tool_call.connect(self.add_tool_call_to_conversation)
        self.agent.add_tool_result.connect(self.add_tool_result_to_conversation)

        self.agent.task_description = task_description
        self.conversation.clear()
        self.conversation.append(("system", f"Task: {task_description}"))
        self.agent.start()
        self.update_button_visibility("running")
        self.status_bar.showMessage("Task in progress...")
        self.logger.info(f"Task started: {task_description}")

    def pause_task(self):
        if self.agent and self.agent.isRunning():
            self.agent.pause()
            self.update_button_visibility("paused")
            self.status_bar.showMessage("Task paused")
            self.logger.info("Task paused")

    def resume_task(self):
        if self.agent and self.agent.isPaused():
            self.agent.resume()
            self.update_button_visibility("running")
            self.status_bar.showMessage("Task in progress...")
            self.logger.info("Task resumed")

    def cancel_task(self):
        if self.agent and self.agent.isRunning():
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
        elif state == "running":
            self.start_button.hide()
            self.pause_button.show()
            self.resume_button.hide()
            self.cancel_button.show()
            self.export_button.hide()
        elif state == "paused":
            self.start_button.hide()
            self.pause_button.hide()
            self.resume_button.show()
            self.cancel_button.show()
            self.export_button.hide()
        self.logger.debug(f"Button visibility updated to state: {state}")

    def update_screenshot(self, pixmap, cursor_position):
        self.original_pixmap = pixmap
        self.scale_and_set_pixmap()
        self.update_screenshot_cursor_position(cursor_position[0], cursor_position[1])
        self.conversation.append(("screenshot", pixmap))
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
        export_conversation(self, self.conversation)
        self.logger.info("Conversation exported")

    def add_to_conversation(self, item_type, content):
        self.conversation.append((item_type, content))
        self.logger.debug(f"Added to conversation: {item_type}")

    def add_tool_call_to_conversation(self, tool, input_data):
        self.add_to_conversation("tool_call", {"tool": tool, "input": input_data})
        self.logger.debug(f"Tool call added to conversation: {tool}")

    def add_tool_result_to_conversation(self, result):
        self.add_to_conversation("tool_result", result)
        self.logger.debug("Tool result added to conversation")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_and_set_pixmap()
        self.logger.debug("Window resized")