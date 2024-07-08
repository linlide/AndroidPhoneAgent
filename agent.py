import anthropic
import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from constants import SYSTEM_PROMPT, TOOLS
from screen import capture_screenshot, move_cursor, click_cursor

class iPhoneMirroringAgent(QThread):
    update_screenshot = pyqtSignal(QPixmap, tuple)
    task_completed = pyqtSignal(bool, str)
    add_to_conversation = pyqtSignal(str, object)
    add_tool_call = pyqtSignal(str, object)
    add_tool_result = pyqtSignal(str)

    def __init__(self, api_key, model, max_tokens, temperature, max_messages):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_messages = max_messages
        self.conversation = []
        self.task_description = ""
        self.cursor_position = (0, 0)
        self._is_paused = False
        self._is_cancelled = False
        self.logger.info("iPhoneMirroringAgent initialized")

    def capture_screenshot(self):
        try:
            pixmap, screenshot_data, self.cursor_position = capture_screenshot()
            self.update_screenshot.emit(pixmap, self.cursor_position)
            self.add_to_conversation.emit("screenshot", pixmap)
            self.logger.debug(f"Screenshot captured. Cursor position: {self.cursor_position}")
            return screenshot_data, self.cursor_position
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {str(e)}")
            return None, None

    def send_to_claude(self, screenshot_data, cursor_position, tool_use=None, tool_result=None):
        if len(self.conversation) >= self.max_messages:
            error_message = f"Conversation exceeded maximum length of {self.max_messages} messages. Exiting task as failed."
            self.task_completed.emit(False, error_message)
            self.logger.warning(error_message)
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
            self.add_tool_result.emit(tool_result)
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
        self.add_to_conversation.emit("log", f"User: Sent screenshot for analysis. Cursor position: {cursor_position}")
        self.logger.info(f"Sent screenshot for analysis. Cursor position: {cursor_position}")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.conversation
            )
            self.logger.debug("Received response from Claude")
            return response
        except Exception as e:
            self.logger.error(f"Error communicating with Claude: {str(e)}")
            return None

    def run(self):
        self.logger.info(f"Starting task: {self.task_description}")
        screenshot_data, cursor_position = self.capture_screenshot()
        if screenshot_data is None:
            self.task_completed.emit(False, "Screenshot capture failed")
            self.logger.error("Failed to capture screenshot. Exiting task.")
            return
        message = self.send_to_claude(screenshot_data, cursor_position)
        
        while not self._is_cancelled:
            while self._is_paused:
                time.sleep(0.1)
                if self._is_cancelled:
                    break
            
            if self._is_cancelled:
                break

            if message is None:
                self.task_completed.emit(False, "Failed to communicate with Claude")
                self.logger.error("Failed to communicate with Claude")
                return

            self.logger.info("Claude's response received")
            for block in message.content:
                if block.type == "text":
                    self.add_to_conversation.emit("log", f"Claude: {block.text}")
            
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
                    self.logger.info(f"Task {status}. Reason: {reason}")
                    break
                
                try:
                    self.add_tool_call.emit(tool_use.name, tool_use.input)
                    if tool_use.name == "move_cursor":
                        result = move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                    elif tool_use.name == "click_cursor":
                        result = click_cursor()
                    else:
                        raise ValueError(f"Unknown tool: {tool_use.name}")
                    
                    self.add_to_conversation.emit("log", f"Executed {tool_use.name}: {result}")
                    self.logger.info(f"Executed {tool_use.name}: {result}")
                except Exception as e:
                    self.task_completed.emit(False, f"Error executing {tool_use.name}")
                    self.logger.error(f"Error executing {tool_use.name}: {str(e)}")
                    return
                
                new_screenshot_data, new_cursor_position = self.capture_screenshot()
                if new_screenshot_data is None:
                    self.task_completed.emit(False, "Screenshot capture failed")
                    self.logger.error("Failed to capture screenshot after tool execution. Exiting task.")
                    return
                
                message = self.send_to_claude(new_screenshot_data, new_cursor_position, tool_use, result)
            else:
                self.add_to_conversation.emit("log", "Claude did not request to use a tool. Continuing...")
                self.logger.info("Claude did not request to use a tool. Continuing...")
                message = self.send_to_claude(screenshot_data, cursor_position)
            
            time.sleep(1)

        if self._is_cancelled:
            self.task_completed.emit(False, "Task cancelled by user")
            self.logger.info("Task cancelled by user")

    def pause(self):
        self._is_paused = True
        self.logger.info("Task paused")

    def resume(self):
        self._is_paused = False
        self.logger.info("Task resumed")

    def cancel(self):
        self._is_cancelled = True
        self.logger.info("Task cancellation requested")

    def isPaused(self):
        return self._is_paused

    def isCancelled(self):
        return self._is_cancelled