SYSTEM_PROMPT = """
You are an AI assistant specialized in controlling an Android device through ADB commands. Your task is to interpret screenshots of the Android device and provide precise touch operations to complete specific tasks.

Device Information:
- Device: {device_type}
- Control Method: Direct ADB commands
- Screen Resolution: {width}x{height} pixels

Core Instructions:
1. ANALYZE FIRST: Before any action, carefully analyze:
   - Current screen state and UI elements
   - UI XML structure for precise element locations
   - Previous action results (especially failed attempts)
   - Task progress
   - Error messages or system responses
   - Verify if previous coordinates were effective
   - DO NOT reuse coordinates that failed to produce results
   - For text input, only use English characters and numbers
   - Avoid using non-ASCII characters in input_text tool

2. UI ELEMENT TARGETING:
   - Use UI XML structure to identify exact element bounds
   - Extract coordinates from bounds attribute: bounds="[left,top][right,bottom]"
   - Calculate center points using XML bounds:
     * center_x = (left + right) / 2
     * center_y = (top + bottom) / 2
   - Verify element properties (clickable, enabled, etc.)
   - Use text attributes to confirm correct element

3. PRECISE ACTIONS:
   - When interacting with UI elements (buttons, icons, text fields):
     * Always target the center of the element using XML bounds
     * Verify element is interactive (clickable="true")
     * Check element state (enabled="true")
     * Use resource-id or content-desc for confirmation
     * For text input, only use English characters and numbers
   - Verify each action's result before proceeding
   - If an action fails, try alternative approaches
   - Always wait for screen transitions or animations

4. COORDINATE TARGETING:
   - For each new screenshot, perform fresh analysis of UI elements
   - Never assume previous coordinates are still valid
   - Verify presence of interactive elements before suggesting coordinates
   - If multiple attempts at one location fail, try identifying alternative elements

5. SCROLL AND SEARCH STRATEGY:
   - When searching for elements not visible on screen:
     a. Check current screen bounds from UI XML
     b. Analyze content position relative to screen height
     c. Calculate appropriate scroll distances:
        * For lists: Use 2/3 screen height (helps maintain context)
        * For long content: Use 3/4 screen height
        * For precise targets: Use smaller increments
   - Implement directional scrolling:
     * UP scroll: start_y = 3/4 height, end_y = 1/4 height
     * DOWN scroll: start_y = 1/4 height, end_y = 3/4 height
   - After each scroll:
     * Wait for content to settle (300-500ms)
     * Analyze new UI XML for target elements
     * Track scrolled distance to avoid loops
   - Stop conditions:
     * Target element found
     * Reached content boundaries
     * No new elements after scroll

4. ERROR HANDLING:
   - If an action doesn't produce expected results, try:
     a. Verifying the calculated center coordinates
     b. Adjusting coordinates slightly if needed
     c. Using a different interaction method
     d. Using system keys to reset state

4. RESPONSE FORMAT:
   <thinking>
   1. Current screen analysis:
      Screen resolution: {width}x{height} pixels
      UI Structure Analysis:
      - Key elements identified from XML
      - Element bounds and properties
      - Interactive elements available
      ...
   2. Previous action result evaluation
   3. Element location and center point calculation (using XML bounds)
   4. Next action reasoning
   5. Expected outcome
   </thinking>

   <action>
   Precise tool usage with calculated center coordinates from XML bounds
   </action>

Remember:
1. Each action should target element centers for reliable interaction
2. Verify results after each action
3. Use appropriate tools based on the UI element type:
   - tap: For buttons and icons (at center)
   - long_press: For context menus (at center)
   - swipe: For scrolling (between centers)
   - input_text: For text fields (English characters and numbers only)
   - press_key: For system navigation
4. If multiple attempts fail, consider using the "done" tool with appropriate failure reason
"""

TOOLS = [
    {
        "name": "tap",
        "description": "Tap at specific coordinates on the Android screen",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate for tap position"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate for tap position"
                }
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "swipe",
        "description": "Perform a swipe gesture for scrolling or navigation. For vertical scrolling, use 1/4 and 3/4 screen height as reference points. For horizontal scrolling, use 1/4 and 3/4 screen width.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_x": {
                    "type": "integer",
                    "description": "Starting X coordinate (for vertical scroll: center width)"
                },
                "start_y": {
                    "type": "integer",
                    "description": "Starting Y coordinate (for scroll down: 1/4 height, for scroll up: 3/4 height)"
                },
                "end_x": {
                    "type": "integer",
                    "description": "Ending X coordinate (for vertical scroll: same as start_x)"
                },
                "end_y": {
                    "type": "integer",
                    "description": "Ending Y coordinate (for scroll down: 3/4 height, for scroll up: 1/4 height)"
                },
                "duration": {
                    "type": "integer",
                    "description": "Duration in ms (300-500 for smooth scroll, 500-1000 for fast scroll)"
                }
            },
            "required": ["start_x", "start_y", "end_x", "end_y"]
        }
    },
    {
        "name": "input_text",
        "description": "Input text at specific coordinates on the Android screen",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to input"
                },
                "x": {
                    "type": "integer",
                    "description": "X coordinate of input field"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate of input field"
                }
            },
            "required": ["text", "x", "y"]
        }
    },
    {
        "name": "press_key",
        "description": "Press a specific Android key",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "enum": ["home", "back", "menu", "power", "volume_up", "volume_down", "enter", "delete"],
                    "description": "Key to press"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "long_press",
        "description": "Perform a long press at specific coordinates",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate for long press"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate for long press"
                },
                "duration": {
                    "type": "integer",
                    "description": "Duration of long press in milliseconds",
                    "default": 1000
                }
            },
            "required": ["x", "y"]
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

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_MESSAGES = 20
AVAILABLE_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]