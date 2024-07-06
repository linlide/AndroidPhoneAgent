import anthropic
import pyautogui
import io
import time
import base64
import argparse
from datetime import datetime
import sys

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

class iPhoneMirroringAgent:
    def __init__(self, api_key, model, max_tokens, temperature, max_messages):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_messages = max_messages
        self.conversation = []
        self.task_description = ""
        self.log_file = None

    def capture_screenshot(self):
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
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
            print(error_message)
            self.append_to_log({
                "role": "error",
                "content": [{"type": "text", "text": error_message}]
            })
            sys.exit(1)

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
        self.append_to_log(self.conversation[-1])

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=self.conversation
        )

        return response

    def initialize_log(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"conversation_{timestamp}.md"
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"# Conversation Log\n\n")
            f.write(f"Task Description: {self.task_description}\n\n")
            f.write(f"Model: {self.model}\n\n")
            f.write(f"Max Tokens: {self.max_tokens}\n\n")
            f.write(f"Temperature: {self.temperature}\n\n")
            f.write(f"Max Messages: {self.max_messages}\n\n")

    def append_to_log(self, message):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"## {message['role'].capitalize()}\n\n")
            for content in message['content']:
                if content['type'] == 'text':
                    f.write(f"{content['text']}\n\n")
                elif content['type'] == 'image':
                    f.write(f"[Screenshot]\n\n")
                elif content['type'] == 'tool_result':
                    f.write(f"Tool Result: {content['content']}\n\n")
            f.write("---\n\n")

    def run_task(self):
        self.task_description = input("Enter the task description: ")
        self.initialize_log()
        print(f"Conversation log will be saved to {self.log_file}")
        
        screenshot_data = self.capture_screenshot()
        message = self.send_to_claude(screenshot_data)
        
        while True:
            print("Claude's response:")
            for block in message.content:
                if block.type == "text":
                    print(block.text)
            
            self.conversation.append({
                "role": "assistant",
                "content": message.content
            })
            self.append_to_log(self.conversation[-1])
            
            if message.stop_reason == "tool_use":
                tool_use = next(block for block in message.content if block.type == "tool_use")
                
                if tool_use.name == "done":
                    status = tool_use.input["status"]
                    reason = tool_use.input["reason"]
                    if status == "completed":
                        print(f"Task completed successfully. Reason: {reason}")
                    else:
                        print(f"Task failed. Reason: {reason}")
                    break
                
                if tool_use.name == "move_cursor":
                    result = self.move_cursor(tool_use.input["direction"], tool_use.input["distance"])
                elif tool_use.name == "click_cursor":
                    result = self.click_cursor()
                
                print(f"Executed {tool_use.name}: {result}")
                
                new_screenshot_data = self.capture_screenshot()
                
                message = self.send_to_claude(new_screenshot_data, tool_use, result)
            else:
                print("Claude did not request to use a tool. Continuing...")
                message = self.send_to_claude(screenshot_data)
            
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Run the iPhone Mirroring Agent with Claude AI")
    parser.add_argument("--api_key", required=True, help="Anthropic API key")
    parser.add_argument("--model", default="claude-3-sonnet-20240320", help="Model name to use for Claude")
    parser.add_argument("--max_tokens", type=int, default=2048, help="Maximum number of tokens in Claude's response")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for Claude's responses (0.0 to 1.0)")
    parser.add_argument("--max_messages", type=int, default=20, help="Maximum number of messages in the conversation")
    args = parser.parse_args()

    agent = iPhoneMirroringAgent(args.api_key, args.model, args.max_tokens, args.temperature, args.max_messages)
    agent.run_task()

if __name__ == "__main__":
    main()