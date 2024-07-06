# iPhone Mirroring Agent

The iPhone Mirroring Agent is a Python-based tool that uses Claude AI to automate interactions with a mirrored iPhone screen. It captures screenshots, analyzes them using Claude AI, and performs simulated touch operations based on AI-generated instructions.

## Features

- Screen capture and analysis using Claude AI
- Simulated cursor movements and clicks
- Conversation logging
- Configurable AI model parameters

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/instapal-ai/iPhoneMirroringAgent.git
   cd iPhoneMirroringAgent
   ```

2. Install the required dependencies:
   ```
   pip install anthropic pyautogui
   ```

3. Set up your Anthropic API key as an environment variable:
   ```
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

## Usage

Run the script with the following command:

```
python iphone_mirroring_agent.py --api_key YOUR_API_KEY
```

You can also specify additional parameters:

```
python iphone_mirroring_agent.py --api_key YOUR_API_KEY --model MODEL_NAME --max_tokens MAX_TOKENS --temperature TEMPERATURE --max_messages MAX_MESSAGES
```

## Configuration

The script accepts the following command-line arguments:

- `--api_key`: (Required) Your Anthropic API key
- `--model`: (Optional) The Claude AI model to use (default: "claude-3-sonnet-20240320")
- `--max_tokens`: (Optional) Maximum number of tokens in Claude's response (default: 2048)
- `--temperature`: (Optional) Temperature for Claude's responses (0.0 to 1.0, default: 0.7)
- `--max_messages`: (Optional) Maximum number of messages in the conversation (default: 20)

## How It Works

1. The script captures a screenshot of the mirrored iPhone screen.
2. The screenshot is sent to Claude AI for analysis.
3. Claude AI provides instructions for the next action (move cursor, click, etc.).
4. The script executes the instructed action using PyAutoGUI.
5. This process repeats until the task is completed or the maximum number of messages is reached.

## Limitations

- The script is designed for use with a mirrored iPhone 12 Pro screen. Other device models may require adjustments to the screen resolution and interaction parameters.
- The effectiveness of the automation depends on the quality of the mirrored display and the complexity of the task.
- The script relies on the Anthropic API, so an active internet connection is required.

## Contributing

Contributions to improve the iPhone Mirroring Agent are welcome. Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.