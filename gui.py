import os
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QLineEdit, QFormLayout, QGroupBox, QStatusBar,
                             QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint
from agent import iPhoneMirroringAgent
from utils import bring_window_to_front, find_and_flash_iphone_mirroring_window

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
        self.api_key_input = QLineEdit()
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

        self.start_button = QPushButton("Start Task")
        self.start_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_button.clicked.connect(self.start_task)
        self.left_layout.addWidget(self.start_button)

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
        
        self.screenshot_label = QLabel()
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_layout.addWidget(self.screenshot_label)
        
        # Add a stretching spacer to push the cursor position label to the bottom
        self.screenshot_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.cursor_position_label = QLabel("Cursor Position: N/A")
        self.cursor_position_label.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.screenshot_layout.addWidget(self.cursor_position_label)
        
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
        max_tokens = int(self.max_tokens_input.text())
        temperature = float(self.temperature_input.text())
        max_messages = int(self.max_messages_input.text())
        task_description = self.task_input.text()

        if api_key and task_description:
            if bring_window_to_front("iPhone Mirroring"):
                find_and_flash_iphone_mirroring_window()
            else:
                self.update_log("iPhone Mirroring app not found or couldn't be brought to front.")

            self.agent = iPhoneMirroringAgent(api_key, model, max_tokens, temperature, max_messages)
            self.agent.update_log.connect(self.update_log)
            self.agent.update_screenshot.connect(self.update_screenshot)
            self.agent.task_completed.connect(self.on_task_completed)

            self.agent.task_description = task_description
            self.log_display.clear()
            self.update_log(f"Starting task: {task_description}")
            self.agent.start()
            self.start_button.setEnabled(False)
            self.status_bar.showMessage("Task in progress...")
        else:
            self.update_log("Please enter both API key and task description.")

    def update_log(self, message):
        self.log_display.append(message)

    def update_screenshot(self, pixmap, cursor_position):
        label_width = self.screenshot_label.width()
        scaled_pixmap = pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
        self.screenshot_label.setPixmap(scaled_pixmap)
        self.cursor_position_label.setText(f"Cursor Position: ({cursor_position[0]:.2f}, {cursor_position[1]:.2f})")
        
        # Ensure the cursor position label is visible
        self.cursor_position_label.show()

    def on_task_completed(self, success, reason):
        self.start_button.setEnabled(True)
        status = "completed successfully" if success else "failed"
        self.update_log(f"Task {status}. Reason: {reason}")
        self.status_bar.showMessage(f"Task {status}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'screenshot_label') and self.screenshot_label.pixmap():
            self.update_screenshot(self.screenshot_label.pixmap().copy(), self.agent.cursor_position if self.agent else (0, 0))