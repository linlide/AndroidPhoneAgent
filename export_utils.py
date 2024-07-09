import os
import datetime
import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock

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
        elif isinstance(obj, dict) and obj.get('type') == 'image':
            return {
                "type": "image",
                "source": {
                    "type": obj['source']['type'],
                    "data": "..."
                }
            }
        return super().default(obj)

def export_conversation(parent, agent):
    if not agent or not agent.conversation:
        QMessageBox.warning(parent, "No Conversation", "There is no conversation to export.")
        return

    default_folder_name = f"iphone_mirroring_conversation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_path = QFileDialog.getExistingDirectory(parent, "Select Export Folder", "", QFileDialog.ShowDirsOnly)
    
    if not folder_path:
        return

    export_folder = os.path.join(folder_path, default_folder_name)
    os.makedirs(export_folder, exist_ok=True)

    try:
        html_content = generate_html_content(agent.conversation, export_folder)

        with open(os.path.join(export_folder, "conversation.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Export conversation as JSON with custom encoder
        json_file_path = os.path.join(export_folder, "conversation.json")
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(agent.conversation, json_file, cls=CustomJSONEncoder, indent=2)

        QMessageBox.information(parent, "Export Successful", f"Conversation exported to {export_folder}")
    except Exception as e:
        QMessageBox.critical(parent, "Export Failed", f"Failed to export conversation: {str(e)}")

def generate_html_content(conversation, export_folder):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>iPhone Mirroring Agent Conversation</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
            h1 { color: #333; }
            .user, .assistant { padding: 10px; margin-bottom: 10px; }
            .user { background-color: #f4f4f4; }
            .assistant { background-color: #e6f3ff; }
            .screenshot { max-width: 100%; height: auto; margin-bottom: 10px; }
            .tool-use { background-color: #fff0e6; padding: 10px; margin-bottom: 10px; }
            .tool-result { background-color: #e6ffe6; padding: 10px; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>iPhone Mirroring Agent Conversation</h1>
    """

    for index, message in enumerate(conversation):
        role = message.get('role', '')
        content = message.get('content', [])

        if role == 'user':
            html_content += f"<div class='user'><strong>User:</strong><br>"
        elif role == 'assistant':
            html_content += f"<div class='assistant'><strong>Assistant:</strong><br>"

        for item in content:
            if isinstance(item, TextBlock):
                html_content += f"{item.text}<br>"
            elif isinstance(item, dict) and item['type'] == 'image':
                screenshot_filename = f"screenshot_{index}.jpg"
                screenshot_path = os.path.join(export_folder, screenshot_filename)
                with open(screenshot_path, 'wb') as f:
                    f.write(item['source']['data'].encode('utf-8'))
                html_content += f"<img src='{screenshot_filename}' alt='Screenshot {index}' class='screenshot'>"
            elif isinstance(item, ToolUseBlock):
                html_content += f"""
                <div class='tool-use'>
                    <strong>Tool Use:</strong><br>
                    Tool: {item.name}<br>
                    Input: {json.dumps(item.input)}
                </div>
                """
            elif isinstance(item, dict) and item['type'] == 'tool_result':
                html_content += f"""
                <div class='tool-result'>
                    <strong>Tool Result:</strong><br>
                """
                for content_item in item['content']:
                    if content_item['type'] == 'text':
                        html_content += f"{content_item['text']}<br>"
                    elif content_item['type'] == 'image':
                        screenshot_filename = f"tool_result_screenshot_{index}.jpg"
                        screenshot_path = os.path.join(export_folder, screenshot_filename)
                        with open(screenshot_path, 'wb') as f:
                            f.write(content_item['source']['data'].encode('utf-8'))
                        html_content += f"<img src='{screenshot_filename}' alt='Tool Result Screenshot {index}' class='screenshot'>"
                html_content += "</div>"

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    return html_content