import os
import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox

def export_conversation(parent, conversation):
    if not conversation:
        QMessageBox.warning(parent, "No Conversation", "There is no conversation to export.")
        return

    default_folder_name = f"iphone_mirroring_conversation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_path = QFileDialog.getExistingDirectory(parent, "Select Export Folder", "", QFileDialog.ShowDirsOnly)
    
    if not folder_path:
        return

    export_folder = os.path.join(folder_path, default_folder_name)
    os.makedirs(export_folder, exist_ok=True)

    try:
        html_content = generate_html_content(conversation, export_folder)

        with open(os.path.join(export_folder, "conversation.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)

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
            .log { background-color: #f4f4f4; padding: 10px; margin-bottom: 10px; }
            .screenshot { max-width: 100%; height: auto; margin-bottom: 10px; }
            .tool-call, .tool-result { background-color: #e6f3ff; padding: 10px; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>iPhone Mirroring Agent Conversation</h1>
    """

    for index, (item_type, content) in enumerate(conversation):
        if item_type == "system":
            html_content += f"<h2>{content}</h2>"
        elif item_type == "log":
            html_content += f"<div class='log'>{content}</div>"
        elif item_type == "screenshot":
            screenshot_filename = f"screenshot_{index}.jpg"
            screenshot_path = os.path.join(export_folder, screenshot_filename)
            content.save(screenshot_path)
            html_content += f"<img src='{screenshot_filename}' alt='Screenshot {index}' class='screenshot'>"
        elif item_type == "tool_call":
            html_content += f"""
            <div class='tool-call'>
                <strong>Tool Call:</strong><br>
                Tool: {content['tool']}<br>
                Input: {content['input']}
            </div>
            """
        elif item_type == "tool_result":
            html_content += f"<div class='tool-result'><strong>Tool Result:</strong><br>{content}</div>"

    html_content += """
    </body>
    </html>
    """

    return html_content