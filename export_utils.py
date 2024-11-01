import os
import datetime
import json
import base64
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from anthropic.types import TextBlock, ToolUseBlock
from constants import SYSTEM_PROMPT
from jinja2 import Environment, FileSystemLoader

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TextBlock):
            return {
                "type": "text",
                "text": obj.text
            }
        elif isinstance(obj, ToolUseBlock):
            return {
                "type": "tool_use",
                "id": obj.id,
                "name": obj.name,
                "input": obj.input
            }
        return super().default(obj)

def export_conversation(parent, agent):
    if not agent or not agent.conversation:
        QMessageBox.warning(parent, "No Conversation", "There is no conversation to export.")
        return

    default_folder_name = f"phone_mirroring_conversation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_path = QFileDialog.getExistingDirectory(parent, "Select Export Folder", "", QFileDialog.ShowDirsOnly)
    
    if not folder_path:
        return

    export_folder = os.path.join(folder_path, default_folder_name)
    os.makedirs(export_folder, exist_ok=True)

    try:
        parameters = {
            "Model": agent.model,
            "Max Tokens": agent.max_tokens,
            "Temperature": agent.temperature,
            "Max Messages": agent.max_messages,
            "Task Description": agent.task_description
        }

        html_content = generate_html_content(agent.conversation, export_folder, parameters)

        with open(os.path.join(export_folder, "conversation.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)

        json_file_path = os.path.join(export_folder, "conversation.json")
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(agent.conversation, json_file, cls=CustomJSONEncoder, indent=2)

        QMessageBox.information(parent, "Export Successful", f"Conversation exported to {export_folder}")
    except Exception as e:
        QMessageBox.critical(parent, "Export Failed", f"Failed to export conversation: {str(e)}")

def generate_html_content(conversation, export_folder, parameters):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('conversation_template.html')

    conversation_data = []
    screenshot_count = 0

    for message in conversation:
        content = []
        for item in message.get('content', []):
            if isinstance(item, TextBlock) or (isinstance(item, dict) and item.get('type') == 'text'):
                content.append({
                    "type": "text",
                    "text": item.text if isinstance(item, TextBlock) else item['text']
                })
            elif isinstance(item, dict) and item.get('type') == 'image':
                screenshot_filename = f"screenshot_{screenshot_count}.jpg"
                screenshot_path = os.path.join(export_folder, screenshot_filename)
                with open(screenshot_path, 'wb') as f:
                    f.write(base64.b64decode(item['source']['data']))
                content.append({"type": "image", "filename": screenshot_filename})
                screenshot_count += 1
            elif isinstance(item, ToolUseBlock):
                content.append({
                    "type": "tool_use",
                    "name": item.name,
                    "input": item.input
                })
            elif isinstance(item, dict) and item['type'] == 'tool_result':
                tool_result_content = []
                for content_item in item['content']:
                    if content_item['type'] == 'text':
                        tool_result_content.append({"type": "text", "text": content_item['text']})
                    elif content_item['type'] == 'image':
                        screenshot_filename = f"screenshot_{screenshot_count}.jpg"
                        screenshot_path = os.path.join(export_folder, screenshot_filename)
                        with open(screenshot_path, 'wb') as f:
                            f.write(base64.b64decode(content_item['source']['data']))
                        tool_result_content.append({"type": "image", "filename": screenshot_filename})
                        screenshot_count += 1
                content.append({"type": "tool_result", "content": tool_result_content})

        conversation_data.append({
            "role": message.get('role', ''),
            "content": content
        })

    html_content = template.render(
        parameters=parameters,
        system_prompt=SYSTEM_PROMPT,
        conversation=conversation_data
    )

    return html_content