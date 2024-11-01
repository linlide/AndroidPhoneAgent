# Android Phone Agent

The Android Phone Agent is a Python-based tool that uses Claude AI to automate interactions with Android devices. Modified from the AndroidPhoneAgent project, it captures screenshots, analyzes them using Claude AI, and performs simulated touch operations based on AI-generated instructions.

![Android Phone Agent Screenshot](Screenshot.png)

## Features

- Screen capture and analysis using Claude AI
- Simulated cursor movements and clicks
- Conversation logging
- Configurable AI model parameters
- User-friendly graphical interface for easy interaction and real-time feedback
- Automatic flashing of the Android Mirroring app window when starting a task
- Compatible with any Android model connected through the Android Mirroring macOS app

## Installation

1. Clone this repository:
   ```
   git clone git@github.com:linlide/AndroidPhoneAgent.git
   cd AndroidPhoneAgent
   ```

2. Install the required dependencies using the provided requirements.txt file:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with the following command:

```
python main.py
```

This will launch the graphical user interface. Enter your Anthropic API key, configure the parameters, and provide a task description in the input fields. Click the "Start Task" button to begin the automation process.

## Configuration

The application allows you to configure the following parameters through the GUI:

- API Key: Your Anthropic API key
- Model: The Claude AI model to use (default: "claude-3-5-sonnet-20240620")
- Max Tokens: Maximum number of tokens in Claude's response (default: 2048)
- Temperature: Temperature for Claude's responses (0.0 to 1.0, default: 0.7)
- Max Messages: Maximum number of messages in the conversation (default: 20)
- Task Description: The task you want the agent to perform on the mirrored Android screen

## Project Structure

The project is organized into multiple files for better modularity and maintainability:

- `main.py`: Entry point of the application
- `gui.py`: Contains the MainWindow class and GUI-related code
- `agent.py`: Contains the AndroidPhoneAgent class for interacting with the Android mirroring and Claude API
- `constants.py`: Contains constant values like SYSTEM_PROMPT and TOOLS
- `screen.py`: Contains utility functions for screen capture, window management, and cursor operations

## How It Works

1. When the "Start Task" button is clicked, the application attempts to bring the Android Mirroring app window to the front and flash it to draw attention.
2. The script captures a screenshot of the mirrored Android screen.
3. The screenshot is sent to Claude AI for analysis.
4. Claude AI provides instructions for the next action (move cursor, click, etc.).
5. The script executes the instructed action using PyAutoGUI.
6. This process repeats until the task is completed or the maximum number of messages is reached.
7. The GUI provides real-time updates on the task progress and displays the current screenshot.

## Limitations

- The effectiveness of the automation depends on the quality of the mirrored display and the complexity of the task.
- The script relies on the Anthropic API, so an active internet connection is required.
- The window flashing feature requires the Android Mirroring app to be running and visible on the screen.
- The AI's ability to interact with the Android interface may vary depending on the specific app or task being performed.

## Contributing

Contributions to improve the Android Mirroring Agent are welcome. Please feel free to submit issues or pull requests.

## Acknowledgments

This project is modified from [iPhoneMirroringAgent](https://github.com/instapal-ai/iPhoneMirroringAgent) by instapal-ai. Special thanks to their original work and contributions.

The main modifications include:
- Added Android device support
- Enhanced ADB integration for direct device control
- Improved UI XML capture for better interaction accuracy
- Added more interaction tools (swipe, long press, key events)
- Optimized screenshot capture process

## License

This project is licensed under the MIT License. See the LICENSE file for details.