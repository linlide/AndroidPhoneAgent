## TODOs

0. Pass screen size (width, height) from screen.py to the system prompt in constants.py.
1. Use absolute cursor move instead of relative cursor move.
2. Use grounded SAM to help locate the interaction target on the screenshot.
3. Use a more sophisticated color palette for different message types.
4. Implement a chat-like layout with user messages aligned to the right and assistant messages to the left.
5. Add avatars or icons for user and assistant messages.
6. Create a fixed header with conversation details and a scrollable message area.
7. Add timestamps to each message.
8. Use icons to represent different types of content (e.g., text, image, tool use).
9. Support VLMs other than claude.

python3 paligemma_inference.py --image_path Screenshot.png --text "Describe the image" --max_new_tokens 30

python3 paligemma_inference.py --image_path Screenshot.png --text "button" --task segment --max_new_tokens 30 --output_dir ./output