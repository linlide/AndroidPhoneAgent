import os
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QLineEdit, QFormLayout, QGroupBox, QStatusBar,
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
        self.setWindowTitle("iPhone Mirroring Agent")
        
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        
        self.setFixedSize(800, 600)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
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

        self.create_input_group()
        self.create_log_group()
        self.create_screenshot_group()

        self.layout.addLayout(self.left_layout, 1)
        self.layout.addLayout(self.right_layout, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_input_group(self):
        self.input_group = QGroupBox("Configuration")
        self.form_layout = QFormLayout()
        self.api_key_input = PasswordLineEdit()
        self.model_input = QLineEdit()
        self.max_tokens_input = QLineEdit()
        self.temperature_input = QLineEdit()
        self.max_messages_input = QLineEdit()
        self.task_input = QLineEdit()

        self.form_layout.addRow("API Key:", self.api_key_input)
        self.form_layout.addRow("Model:", self.model_input)
        self.form_layout.addRow("Max Tokens:", self.max_tokens_input)
        self.form_layout.addRow("Temperature:", self.temperature_input)
        self.form_layout.addRow("Max Messages:", self.max_messages_input)
        self.form_layout.addRow("Task Description:", self.task_input)
        self.input_group.setLayout(self.form_layout)

        self.left_layout.addWidget(self.input_group)

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

    def create_log_group(self):
        self.log_group = QGroupBox("Log")
        self.log_layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_layout.addWidget(self.log_display)
        self.log_group.setLayout(self.log_layout)
        self.left_layout.addWidget(self.log_group)

    def create_screenshot_group(self):
        self.screenshot_group = QGroupBox("Current Screenshot")
        self.screenshot_layout = QVBoxLayout()
        
        self.screenshot_label = ClickableLabel(self)
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.screenshot_layout.addWidget(self.screenshot_label)
        
        self.screen_cursor_label = QLabel("Screen Cursor:     (    0,    0)")
        self.screenshot_cursor_label = QLabel("Screenshot Cursor: (    0,    0)")
        
        self.screenshot_layout.addWidget(self.screen_cursor_label)
        self.screenshot_layout.addWidget(self.screenshot_cursor_label)
        
        self.screenshot_group.setLayout(self.screenshot_layout)
        self.right_layout.addWidget(self.screenshot_group, 1)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
                self.api_key_input.setText(settings.get("api_key", ""))
                self.model_input.setText(settings.get("model", "claude-3-5-sonnet-20240620"))
                self.max_tokens_input.setText(str(settings.get("max_tokens", 2048)))
                self.temperature_input.setText(str(settings.get("temperature", 0.7)))
                self.max_messages_input.setText(str(settings.get("max_messages", 20)))
                self.task_input.setText(settings.get("task_description", ""))
                
                pos = settings.get("window_position", None)
                if pos:
                    self.move(QPoint(pos[0], pos[1]))
        else:
            self.model_input.setText("claude-3-5-sonnet-20240620")
            self.max_tokens_input.setText("2048")
            self.temperature_input.setText("0.7")
            self.max_messages_input.setText("20")

    def save_settings(self):
        settings = {
            "api_key": self.api_key_input.text(),
            "model": self.model_input.text(),
            "max_tokens": self.max_tokens_input.text(),
            "temperature": self.temperature_input.text(),
            "max_messages": self.max_messages_input.text(),
            "task_description": self.task_input.text(),
            "window_position": [self.pos().x(), self.pos().y()]
        }
        with open(self.settings_file, "w") as f:
            json.dump(settings, f)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def start_task(self):
        api_key = self.api_key_input.text()
        model = self.model_input.text()
        task_description = self.task_input.text()

        if not api_key or not task_description:
            QMessageBox.warning(self, "Missing Information", "Please enter both API key and task description.")
            return

        try:
            max_tokens = int(self.max_tokens_input.text())
            temperature = float(self.temperature_input.text())
            max_messages = int(self.max_messages_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for Max Tokens, Temperature, and Max Messages.")
            return

        self.agent = iPhoneMirroringAgent(api_key, model, max_tokens, temperature, max_messages)
        self.agent.update_log.connect(self.update_log)
        self.agent.update_screenshot.connect(self.update_screenshot)
        self.agent.task_completed.connect(self.on_task_completed)
        self.agent.add_to_conversation.connect(self.add_to_conversation)
        self.agent.add_tool_call.connect(self.add_tool_call_to_conversation)
        self.agent.add_tool_result.connect(self.add_tool_result_to_conversation)

        self.agent.task_description = task_description
        self.log_display.clear()
        self.conversation.clear()
        self.update_log(f"Starting task: {task_description}")
        self.conversation.append(("system", f"Task: {task_description}"))
        self.agent.start()
        self.update_button_visibility("running")
        self.status_bar.showMessage("Task in progress...")

    def pause_task(self):
        if self.agent and self.agent.isRunning():
            self.agent.pause()
            self.update_log("Task paused.")
            self.update_button_visibility("paused")
            self.status_bar.showMessage("Task paused")

    def resume_task(self):
        if self.agent and self.agent.isPaused():
            self.agent.resume()
            self.update_log("Task resumed.")
            self.update_button_visibility("running")
            self.status_bar.showMessage("Task in progress...")

    def cancel_task(self):
        if self.agent and self.agent.isRunning():
            self.agent.cancel()
            self.update_log("Task cancellation requested.")
            self.status_bar.showMessage("Cancelling task...")

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

    def update_log(self, message):
        self.log_display.append(message)
        self.conversation.append(("log", message))

    def update_screenshot(self, pixmap, cursor_position):
        self.original_pixmap = pixmap
        self.scale_and_set_pixmap()
        self.update_screenshot_cursor_position(cursor_position[0], cursor_position[1])
        self.conversation.append(("screenshot", pixmap))

    def scale_and_set_pixmap(self):
        if self.original_pixmap:
            label_width = self.screenshot_label.width()
            scaled_pixmap = self.original_pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
            self.screenshot_label.setPixmap(scaled_pixmap)

    def update_screen_cursor_position(self):
        cursor_x, cursor_y = pyautogui.position()
        self.screen_cursor_label.setText(f"Screen Cursor:     ({cursor_x:5d},{cursor_y:5d})")

    def update_screenshot_cursor_position(self, x, y):
        self.screenshot_cursor_label.setText(f"Screenshot Cursor: ({x:5d},{y:5d})")

    def on_task_completed(self, success, reason):
        self.update_button_visibility("idle")
        status = "completed successfully" if success else "failed"
        self.update_log(f"Task {status}. Reason: {reason}")
        self.status_bar.showMessage(f"Task {status}")

        if not success:
            QMessageBox.warning(self, "Task Failed", f"The task failed. Reason: {reason}")

    def export_conversation(self):
        export_conversation(self, self.conversation)

    def add_to_conversation(self, item_type, content):
        self.conversation.append((item_type, content))

    def add_tool_call_to_conversation(self, tool, input_data):
        self.add_to_conversation("tool_call", {"tool": tool, "input": input_data})

    def add_tool_result_to_conversation(self, result):
        self.add_to_conversation("tool_result", result)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_and_set_pixmap()