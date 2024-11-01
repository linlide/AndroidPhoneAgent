import anthropic
import time
import logging
import subprocess
import base64
from constants import SYSTEM_PROMPT, TOOLS
from screen import capture_screenshot, move_cursor, click_cursor, get_screen_dimensions
from anthropic.types import (
    MessageParam,
    TextBlockParam,
    ImageBlockParam,
    ToolResultBlockParam,
    ToolUseBlock
)

class PhoneMirroringAgent:
    def __init__(self, api_key, model, max_tokens, temperature, max_messages, device_type="android"):
        self.logger = logging.getLogger(__name__)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_messages = max_messages
        self.conversation: list[MessageParam] = []
        self.task_description = ""
        self.cursor_position = (0, 0)
        self._is_paused = False
        self._is_cancelled = False
        self.update_status = None
        self.device_type = device_type
        
        # 默认分辨率
        width = 1080
        height = 1920
        
        # 获取初始截图以确定屏幕分辨率
        screenshot_data, cursor_position, ui_xml = capture_screenshot(device_type)
        if screenshot_data:
            width, height = get_screen_dimensions(device_type)
        
        # 设置系统提示
        self.system_prompt = SYSTEM_PROMPT.format(
            device_type=device_type.capitalize(),
            width=width,
            height=height
        )
        
        self.logger.info(f"PhoneMirroringAgent initialized for {device_type} device with resolution {width}x{height}")

    def capture_screenshot(self):
        try:
            screenshot_data, cursor_position, ui_xml = capture_screenshot(self.device_type)
            self.cursor_position = cursor_position
            self.logger.debug(f"Screenshot captured. Cursor position: {cursor_position}")
            return screenshot_data, cursor_position, ui_xml
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {str(e)}")
            return None, None, None

    def send_to_claude(self, screenshot_data, cursor_position, ui_xml=None, tool_results=None):
        if len(self.conversation) >= self.max_messages:
            error_message = f"Conversation exceeded maximum length of {self.max_messages} messages. Exiting task as failed."
            self.task_completed(False, error_message)
            self.logger.warning(error_message)
            return None

        # 验证图片数据格式
        try:
            # 检查base64数据是否有效
            base64.b64decode(screenshot_data)
        except Exception as e:
            self.logger.error(f"Invalid base64 image data: {str(e)}")
            return None

        content = []
        
        if tool_results:
            content.extend(tool_results)
            screenshot_message = f"Here's the latest screenshot after running the tool(s) for the task: {self.task_description}"
        else:
            screenshot_message = f"Here's the initial screenshot for the task: {self.task_description}"

        # 确保图片格式正确
        content.extend([
            TextBlockParam(
                type="text",
                text=f"{screenshot_message}\nPlease analyze the image and UI structure to suggest the next action."
            ),
            ImageBlockParam(
                type="image",
                source={
                    "type": "base64",
                    "media_type": "image/png",  # 改为 image/png
                    "data": screenshot_data
                }
            )
        ])
        
        if ui_xml:
            content.append(TextBlockParam(
                type="text",
                text=f"UI XML Structure:\n{ui_xml}"
            ))

        message = MessageParam(role="user", content=content)
        
        self.conversation.append(message)
        self.logger.info(f"Sent {'tool results and ' if tool_results else ''}screenshot for analysis. Cursor position: {cursor_position}")

        try:
            # Log request parameters
            request_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self.system_prompt,
                "tools": TOOLS,
                "messages": self.conversation
            }
           # self.logger.info(f"Sending request to Claude with parameters: {request_params}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                tools=TOOLS,
                messages=self.conversation
            )
            self.logger.info("Received response from Claude")
            return response
        except Exception as e:
            self.logger.error(f"Error communicating with Claude: {str(e)}")
            return None

    def run(self, task_completed, update_status):
        self.task_completed = task_completed
        self.update_status = update_status

        self.logger.info(f"Starting task: {self.task_description}")
        self.update_status("Capturing initial screenshot...")
        screenshot_data, cursor_position, ui_xml = self.capture_screenshot()
        if screenshot_data is None:
            self.task_completed(False, "Screenshot capture failed")
            self.logger.error("Failed to capture screenshot. Exiting task.")
            return
        self.update_status("Analyzing initial screenshot...")
        message = self.send_to_claude(screenshot_data, cursor_position, ui_xml)
        
        while not self._is_cancelled:
            while self._is_paused:
                time.sleep(0.1)
                if self._is_cancelled:
                    break
            
            if self._is_cancelled:
                break

            if message is None:
                self.task_completed(False, "Failed to communicate with Claude")
                self.logger.error("Failed to communicate with Claude")
                return

            self.logger.info("Claude's response received")
            self.logger.info(f"Claude's response content: {message.content}")
            self.update_status("Received response from Claude, processing...")
            
            self.conversation.append(MessageParam(
                role="assistant",
                content=message.content
            ))
            
            if message.stop_reason == "tool_use":
                tool_uses = [block for block in message.content if isinstance(block, ToolUseBlock)]
                tool_results = []
                for tool_use in tool_uses:
                    if tool_use.name == "done":
                        status = tool_use.input["status"]
                        reason = tool_use.input["reason"]
                        if status == "completed":
                            self.task_completed(True, reason)
                        else:
                            self.task_completed(False, reason)
                        self.logger.info(f"Task {status}. Reason: {reason}")
                        return
                    
                    try:
                        self.update_status(f"Executing {tool_use.name}...")
                        if tool_use.name == "move_cursor":
                            result = move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                        elif tool_use.name == "click_cursor":
                            result = click_cursor()
                        elif tool_use.name == "tap":
                            try:
                                # Execute tap command
                                process = subprocess.run([
                                    'adb', 'shell', 'input', 'tap',
                                    str(tool_use.input["x"]), str(tool_use.input["y"])
                                ], capture_output=True, text=True, check=True)
                                
                                # Check if there was any error output
                                if process.stderr:
                                    raise Exception(f"ADB error: {process.stderr}")
                                    
                                # Verify the command executed
                                if process.returncode == 0:
                                    result = f"Successfully tapped at coordinates ({tool_use.input['x']}, {tool_use.input['y']})"
                                    # Add small delay to ensure tap is registered
                                    time.sleep(0.5)
                                else:
                                    raise Exception(f"ADB command failed with return code {process.returncode}")
                                
                            except subprocess.CalledProcessError as e:
                                raise Exception(f"Failed to execute tap command: {str(e)}")
                            except Exception as e:
                                raise Exception(f"Error during tap operation: {str(e)}")
                        elif tool_use.name == "swipe":
                            result = subprocess.check_output([
                                'adb', 'shell', 'input', 'swipe',
                                str(tool_use.input["start_x"]), str(tool_use.input["start_y"]),
                                str(tool_use.input["end_x"]), str(tool_use.input["end_y"]),
                                str(tool_use.input.get("duration", 300))
                            ], text=True)
                            result = f"Swiped from ({tool_use.input['start_x']}, {tool_use.input['start_y']}) to ({tool_use.input['end_x']}, {tool_use.input['end_y']})"
                        elif tool_use.name == "input_text":
                            result = subprocess.check_output([
                                'adb', 'shell', 'input', 'text',
                                tool_use.input["text"].replace(' ', '%s')
                            ], text=True)
                            result = f"Input text: {tool_use.input['text']}"
                        elif tool_use.name == "press_key":
                            key_mapping = {
                                "home": "KEYCODE_HOME",
                                "back": "KEYCODE_BACK",
                                "menu": "KEYCODE_MENU",
                                "power": "KEYCODE_POWER",
                                "volume_up": "KEYCODE_VOLUME_UP",
                                "volume_down": "KEYCODE_VOLUME_DOWN",
                                "enter": "KEYCODE_ENTER",
                                "delete": "KEYCODE_DEL"
                            }
                            android_key = key_mapping[tool_use.input["key"]]
                            result = subprocess.check_output([
                                'adb', 'shell', 'input', 'keyevent',
                                android_key
                            ], text=True)
                            result = f"Pressed key: {tool_use.input['key']}"
                        elif tool_use.name == "long_press":
                            duration = tool_use.input.get("duration", 1000)
                            result = subprocess.check_output([
                                'adb', 'shell', 'input', 'swipe',
                                str(tool_use.input["x"]), str(tool_use.input["y"]),
                                str(tool_use.input["x"]), str(tool_use.input["y"]),
                                str(duration)
                            ], text=True)
                            result = f"Long pressed at ({tool_use.input['x']}, {tool_use.input['y']}) for {duration}ms"
                        else:
                            raise ValueError(f"Unknown tool: {tool_use.name}")
                        
                        tool_results.append(ToolResultBlockParam(
                            type="tool_result",
                            tool_use_id=tool_use.id,
                            content=[TextBlockParam(type="text", text=f"{result}")]
                        ))
                        
                        self.logger.info(f"Executed {tool_use.name}: {result}")
                    except Exception as e:
                        self.task_completed(False, f"Error executing {tool_use.name}")
                        self.logger.error(f"Error executing {tool_use.name}: {str(e)}")
                        return
                
                self.update_status("Capturing new screenshot after action...")
                new_screenshot_data, new_cursor_position, new_ui_xml = self.capture_screenshot()
                if new_screenshot_data is None:
                    self.task_completed(False, "Screenshot capture failed")
                    self.logger.error("Failed to capture screenshot after tool execution. Exiting task.")
                    return
                
                self.update_status("Analyzing new screenshot...")
                message = self.send_to_claude(new_screenshot_data, new_cursor_position, new_ui_xml, tool_results)
            else:
                self.logger.info("Claude did not request to use any tools. Continuing...")
                self.update_status("Analyzing current state...")
                message = self.send_to_claude(screenshot_data, cursor_position, ui_xml, None)
            
            time.sleep(1)

        if self._is_cancelled:
            self.task_completed(False, "Task cancelled by user")
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