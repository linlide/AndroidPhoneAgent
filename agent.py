import anthropic
import pyautogui
import io
from PIL import Image, ImageGrab
import time
import base64
import pywinctl as pwc
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from constants import SYSTEM_PROMPT, TOOLS

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
        try:
            iphone_windows = [w for w in pwc.getAllWindows() if 'iPhone Mirroring' in w.title]
            if not iphone_windows:
                raise Exception("iPhone Mirroring window not found")
            
            window = iphone_windows[0]
            left, top, right, bottom = window.box

            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            screenshot = screenshot.convert('RGB')
            
            max_size = (1600, 1600)
            screenshot.thumbnail(max_size, Image.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            quality = 85
            screenshot.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr = img_byte_arr.getvalue()
            
            while len(img_byte_arr) > 5 * 1024 * 1024:
                quality = int(quality * 0.9)
                img_byte_arr = io.BytesIO()
                screenshot.save(img_byte_arr, format='JPEG', quality=quality)
                img_byte_arr = img_byte_arr.getvalue()
            
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr)
            self.update_screenshot.emit(pixmap)
            return base64.b64encode(img_byte_arr).decode("utf-8")
        except Exception as e:
            self.update_log.emit(f"Error capturing screenshot: {str(e)}")
            return None

    def move_cursor(self, direction, distance):
        if direction in ["right", "left"]:
            pyautogui.moveRel(xOffset=distance if direction == "right" else -distance, yOffset=0)
        elif direction in ["down", "up"]:
            pyautogui.moveRel(xOffset=0, yOffset=distance if direction == "down" else -distance)
        return f"Cursor moved {direction} by {distance} pixels."

    def click_cursor(self):
        pyautogui.click()
        return "Click performed successfully."

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
                "content": [
                    {
                        "type": "text",
                        "text": f"{tool_result}\nHere's the latest screenshot after running the tool for the task: {self.task_description}\nPlease analyze the image and suggest the next action."
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
                    "text": f"Here's the current screenshot for the task: {self.task_description}\nPlease analyze the image and suggest the next action."
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
        if screenshot_data is None:
            self.update_log.emit("Failed to capture screenshot. Exiting task.")
            self.task_completed.emit(False, "Screenshot capture failed")
            return
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
                        self.task_completed.emit(True, reason)
                    else:
                        self.task_completed.emit(False, reason)
                    break
                
                if tool_use.name == "move_cursor":
                    result = self.move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                elif tool_use.name == "click_cursor":
                    result = self.click_cursor()
                
                self.update_log.emit(f"Executed {tool_use.name}: {result}")
                
                new_screenshot_data = self.capture_screenshot()
                if new_screenshot_data is None:
                    self.update_log.emit("Failed to capture screenshot. Exiting task.")
                    self.task_completed.emit(False, "Screenshot capture failed")
                    return
                
                message = self.send_to_claude(new_screenshot_data, tool_use, result)
            else:
                self.update_log.emit("Claude did not request to use a tool. Continuing...")
                message = self.send_to_claude(screenshot_data)
            
            time.sleep(1)