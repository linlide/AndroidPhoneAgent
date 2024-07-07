# iPhone Mirroring Agent

The iPhone Mirroring Agent is a Python-based tool that uses Claude AI to automate interactions with a mirrored iPhone screen. It captures screenshots, analyzes them using Claude AI, and performs simulated touch operations based on AI-generated instructions.

![iPhone Mirroring Agent Screenshot](Screenshot.png)

## Features

- Screen capture and analysis using Claude AI
- Simulated cursor movements and clicks
- Conversation logging
- Configurable AI model parameters
- User-friendly graphical interface for easy interaction and real-time feedback

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/instapal-ai/iPhoneMirroringAgent.git
   cd iPhoneMirroringAgent
   ```

2. Install the required dependencies using the provided requirements.txt file:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with the following command:

```
python iphone_mirroring_agent.py
```

This will launch the graphical user interface. Enter your Anthropic API key, configure the parameters, and provide a task description in the input fields. Click the "Start Task" button to begin the automation process.

## Configuration

The application allows you to configure the following parameters through the GUI:

- API Key: Your Anthropic API key
- Model: The Claude AI model to use (default: "claude-3-sonnet-20240320")
- Max Tokens: Maximum number of tokens in Claude's response (default: 2048)
- Temperature: Temperature for Claude's responses (0.0 to 1.0, default: 0.7)
- Max Messages: Maximum number of messages in the conversation (default: 20)
- Task Description: The task you want the agent to perform on the mirrored iPhone screen

## How It Works

1. The script captures a screenshot of the mirrored iPhone screen.
2. The screenshot is sent to Claude AI for analysis.
3. Claude AI provides instructions for the next action (move cursor, click, etc.).
4. The script executes the instructed action using PyAutoGUI.
5. This process repeats until the task is completed or the maximum number of messages is reached.
6. The GUI provides real-time updates on the task progress and displays the current screenshot.

## Limitations

- The script is designed for use with a mirrored iPhone 12 Pro screen. Other device models may require adjustments to the screen resolution and interaction parameters.
- The effectiveness of the automation depends on the quality of the mirrored display and the complexity of the task.
- The script relies on the Anthropic API, so an active internet connection is required.

## Contributing

Contributions to improve the iPhone Mirroring Agent are welcome. Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.