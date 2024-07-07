import anthropic
import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from constants import SYSTEM_PROMPT, TOOLS
from screen import capture_screenshot, move_cursor, click_cursor

class iPhoneMirroringAgent(QThread):
    update_log = pyqtSignal(str)
    update_screenshot = pyqtSignal(QPixmap, tuple)
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
        self.cursor_position = (0, 0)

    def capture_screenshot(self):
        try:
            pixmap, screenshot_data, self.cursor_position = capture_screenshot()
            self.update_screenshot.emit(pixmap, self.cursor_position)
            return screenshot_data, self.cursor_position
        except Exception as e:
            self.update_log.emit(f"Error capturing screenshot: {str(e)}")
            return None, None

    def send_to_claude(self, screenshot_data, cursor_position, tool_use=None, tool_result=None):
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
                "content": [
                    {
                        "type": "text",
                        "text": f"{tool_result}\nHere's the latest screenshot after running the tool for the task: {self.task_description}\nCurrent cursor position: {cursor_position}\nPlease analyze the image and suggest the next action."
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": screenshot_data
                        }
                    }
                ]
            })
        else:
            content.extend([
                {
                    "type": "text",
                    "text": f"Here's the current screenshot for the task: {self.task_description}\nCurrent cursor position: {cursor_position}\nPlease analyze the image and suggest the next action."
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": screenshot_data
                    }
                }
            ])
        
        self.conversation.append({
            "role": "user",
            "content": content
        })
        self.update_log.emit(f"User: Sent screenshot for analysis. Cursor position: {cursor_position}")

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
        screenshot_data, cursor_position = self.capture_screenshot()
        if screenshot_data is None:
            self.update_log.emit("Failed to capture screenshot. Exiting task.")
            self.task_completed.emit(False, "Screenshot capture failed")
            return
        message = self.send_to_claude(screenshot_data, cursor_position)
        
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
                        self.task_completed.emit(True, reason)
                    else:
                        self.task_completed.emit(False, reason)
                    break
                
                if tool_use.name == "move_cursor":
                    result = move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                elif tool_use.name == "click_cursor":
                    result = click_cursor()
                
                self.update_log.emit(f"Executed {tool_use.name}: {result}")
                
                new_screenshot_data, new_cursor_position = self.capture_screenshot()
                if new_screenshot_data is None:
                    self.update_log.emit("Failed to capture screenshot. Exiting task.")
                    self.task_completed.emit(False, "Screenshot capture failed")
                    return
                
                message = self.send_to_claude(new_screenshot_data, new_cursor_position, tool_use, result)
            else:
                self.update_log.emit("Claude did not request to use a tool. Continuing...")
                message = self.send_to_claude(screenshot_data, cursor_position)
            
            time.sleep(1)