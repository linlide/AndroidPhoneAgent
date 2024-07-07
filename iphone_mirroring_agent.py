import anthropic
import pyautogui
import io
import time
import base64
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QLineEdit, QFormLayout, QGroupBox, QStatusBar)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal

SYSTEM_PROMPT = """
You are an AI assistant specialized in guiding users through simulated touch operations on an iPhone 12 Pro screen. Your task is to interpret screen images and then provide precise movement and click instructions to complete specific tasks.

Device Information:
- Device Model: iPhone 12 Pro
- Screen Resolution: 2532 x 1170 pixels

Guiding Principles:
1. Use the provided tools to interact with the device.
2. Carefully analyze the provided screenshots, noting the current pointer position and interface elements.
3. Break down complex tasks into multiple small steps, using one tool at a time.
4. Provide step-by-step movement and click instructions, using pixel measurements and considering the specific resolution of the iPhone 12 Pro.
5. Use the "done" tool when the task is completed or cannot be completed.
6. If at any stage you find that the task cannot be completed, explain why and use the "done" tool.

Analysis and Response Process:
For each screenshot provided, you must:
1. Think step-by-step and analyze every part of the image. Provide this analysis in <thinking> tags.
2. Identify the current state of the task and any progress made.
3. Consider the available tools and which one would be most appropriate for the next step.
4. Provide your final suggestion for the next action in <action> tags.

Remember:
1. You have perfect vision and pay great attention to detail, which makes you an expert at analyzing screenshots and providing precise instructions.
2. All pixel measurements should be calculated based on the 2532 x 1170 resolution.
3. Prioritize safe and conservative actions.
4. Break down complex tasks into multiple small steps, providing only the next most appropriate step each time.
5. Assume that each new screenshot provided is the result of executing your previous instructions.
6. Always keep the initial task description in mind, ensuring that all actions are moving towards completing that task.
7. Be as precise as possible, using pixel measurements when applicable.
"""

TOOLS = [
    {
        "name": "move_cursor",
        "description": "Move the cursor in a specified direction by a certain distance",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"]
                },
                "distance": {
                    "type": "integer",
                    "description": "Distance to move in pixels"
                }
            },
            "required": ["direction", "distance"]
        }
    },
    {
        "name": "click_cursor",
        "description": "Perform a click at the current cursor position",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "done",
        "description": "Indicate that the task is completed or cannot be completed",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["completed", "failed"],
                    "description": "Whether the task was completed successfully or failed"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for completing or not completing the task"
                }
            },
            "required": ["status", "reason"]
        }
    }
]

class iPhoneMirroringAgent(QThread):
    update_log = pyqtSignal(str)
    update_screenshot = pyqtSignal(QPixmap)
    task_completed = pyqtSignal(bool, str)

    def __init__(self, api_key, model, max_tokens, temperature, max_messages):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_messages = max_messages
        self.conversation = []
        self.task_description = ""

    def capture_screenshot(self):
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr)
        self.update_screenshot.emit(pixmap)
        return base64.b64encode(img_byte_arr).decode("utf-8")

    def move_cursor(self, direction, distance):
        if direction in ["right", "left"]:
            pyautogui.moveRel(xOffset=distance if direction == "right" else -distance, yOffset=0)
        elif direction in ["down", "up"]:
            pyautogui.moveRel(xOffset=0, yOffset=distance if direction == "down" else -distance)
        return {"result": f"Cursor moved {direction} by {distance} pixels."}

    def click_cursor(self):
        pyautogui.click()
        return {"result": "Click performed successfully."}

    def send_to_claude(self, screenshot_data, tool_use=None, tool_result=None):
        if len(self.conversation) >= self.max_messages:
            error_message = f"Conversation exceeded maximum length of {self.max_messages} messages. Exiting task as failed."
            self.update_log.emit(error_message)
            self.task_completed.emit(False, error_message)
            return None

        content = []
        
        if tool_use and tool_result:
            content.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": tool_result,
            })
        
        content.extend([
            {
                "type": "text",
                "text": f"Here's the current screenshot for the task: {self.task_description}\nPlease analyze the image and suggest the next action."
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_data
                }
            }
        ])
        
        self.conversation.append({
            "role": "user",
            "content": content
        })
        self.update_log.emit(f"User: Sent screenshot for analysis")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=self.conversation
        )

        return response

    def run(self):
        screenshot_data = self.capture_screenshot()
        message = self.send_to_claude(screenshot_data)
        
        while True:
            self.update_log.emit("Claude's response:")
            for block in message.content:
                if block.type == "text":
                    self.update_log.emit(block.text)
            
            self.conversation.append({
                "role": "assistant",
                "content": message.content
            })
            
            if message.stop_reason == "tool_use":
                tool_use = next(block for block in message.content if block.type == "tool_use")
                
                if tool_use.name == "done":
                    status = tool_use.input["status"]
                    reason = tool_use.input["reason"]
                    if status == "completed":
                        self.update_log.emit(f"Task completed successfully. Reason: {reason}")
                        self.task_completed.emit(True, reason)
                    else:
                        self.update_log.emit(f"Task failed. Reason: {reason}")
                        self.task_completed.emit(False, reason)
                    break
                
                if tool_use.name == "move_cursor":
                    result = self.move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                elif tool_use.name == "click_cursor":
                    result = self.click_cursor()
                
                self.update_log.emit(f"Executed {tool_use.name}: {result}")
                
                new_screenshot_data = self.capture_screenshot()
                
                message = self.send_to_claude(new_screenshot_data, tool_use, result)
            else:
                self.update_log.emit("Claude did not request to use a tool. Continuing...")
                message = self.send_to_claude(screenshot_data)
            
            time.sleep(1)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iPhone Mirroring Agent")
        self.setGeometry(100, 100, 800, 600)
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

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        self.input_group = QGroupBox("Configuration")
        self.form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.model_input = QLineEdit("claude-3-sonnet-20240320")
        self.max_tokens_input = QLineEdit("2048")
        self.temperature_input = QLineEdit("0.7")
        self.max_messages_input = QLineEdit("20")
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

        self.log_group = QGroupBox("Log")
        self.log_layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_layout.addWidget(self.log_display)
        self.log_group.setLayout(self.log_layout)
        self.left_layout.addWidget(self.log_group)

        self.screenshot_group = QGroupBox("Current Screenshot")
        self.screenshot_layout = QVBoxLayout()
        self.screenshot_label = QLabel()
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_label.setFixedSize(200, 433)
        self.screenshot_layout.addWidget(self.screenshot_label)
        self.screenshot_group.setLayout(self.screenshot_layout)
        self.right_layout.addWidget(self.screenshot_group)

        self.layout.addLayout(self.left_layout, 1)
        self.layout.addLayout(self.right_layout, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.agent = None

    def start_task(self):
        api_key = self.api_key_input.text()
        model = self.model_input.text()
        max_tokens = int(self.max_tokens_input.text())
        temperature = float(self.temperature_input.text())
        max_messages = int(self.max_messages_input.text())
        task_description = self.task_input.text()

        if api_key and task_description:
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

    def update_screenshot(self, pixmap):
        scaled_pixmap = pixmap.scaled(self.screenshot_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.screenshot_label.setPixmap(scaled_pixmap)

    def on_task_completed(self, success, reason):
        self.start_button.setEnabled(True)
        status = "completed successfully" if success else "failed"
        self.update_log(f"Task {status}. Reason: {reason}")
        self.status_bar.showMessage(f"Task {status}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()