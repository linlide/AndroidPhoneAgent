import os
import io
import base64
import pyautogui
import logging
from PIL import Image, ImageDraw
import time

logger = logging.getLogger(__name__)

def draw_cursor(screenshot, cursor_x, cursor_y):
    draw = ImageDraw.Draw(screenshot)
    cursor_radius = 10
    cursor_color = "red"
    draw.ellipse([cursor_x - cursor_radius, cursor_y - cursor_radius,
                  cursor_x + cursor_radius, cursor_y + cursor_radius],
                 outline=cursor_color, width=2)
    
    line_length = 20
    draw.line([cursor_x - line_length, cursor_y,
               cursor_x + line_length, cursor_y],
              fill=cursor_color, width=2)
    draw.line([cursor_x, cursor_y - line_length,
               cursor_x, cursor_y + line_length],
              fill=cursor_color, width=2)
    
    return screenshot

def compress_image(image, max_size=5*1024*1024, initial_quality=95):
    img_byte_arr = io.BytesIO()
    quality = initial_quality
    image.save(img_byte_arr, format='JPEG', quality=quality)
    img_byte_arr = img_byte_arr.getvalue()
    
    while len(img_byte_arr) > max_size:
        quality = int(quality * 0.9)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=quality)
        img_byte_arr = img_byte_arr.getvalue()
    
    return img_byte_arr

def capture_screenshot():
    try:
        logger.info("Capturing screenshot")
        screenshots_folder = os.path.join(os.path.expanduser("~"), "Dropbox", "Screenshots")
        
        initial_screenshots = set(f for f in os.listdir(screenshots_folder) if f.startswith("Screenshot"))
        
        pyautogui.hotkey('command', 'shift', '3')
        
        max_attempts = 3
        attempt = 0
        new_screenshot_path = None
        
        while attempt < max_attempts:
            time.sleep(2)
            current_screenshots = set(f for f in os.listdir(screenshots_folder) if f.startswith("Screenshot"))
            new_screenshots = current_screenshots - initial_screenshots
            
            if new_screenshots:
                new_screenshot = max(new_screenshots, key=lambda x: os.path.getmtime(os.path.join(screenshots_folder, x)))
                new_screenshot_path = os.path.join(screenshots_folder, new_screenshot)
                logger.info(f"New screenshot found: {new_screenshot_path}")
                break
            
            attempt += 1
            logger.info(f"No new screenshot found. Attempt {attempt} of {max_attempts}")
        
        if not new_screenshot_path:
            logger.warning("No new screenshot found after multiple attempts. Taking a new screenshot.")
            return capture_screenshot()
        
        screenshot = Image.open(new_screenshot_path)
        
        if screenshot.mode == 'RGBA':
            screenshot = screenshot.convert('RGB')
        
        cursor_x, cursor_y = pyautogui.position()
        
        screenshot = draw_cursor(screenshot, cursor_x, cursor_y)
        
        img_byte_arr = compress_image(screenshot)
        
        base64_screenshot = base64.b64encode(img_byte_arr).decode('utf-8')
        
        logger.info(f"Screenshot captured successfully. Cursor position: ({cursor_x}, {cursor_y})")
        return base64_screenshot, (cursor_x, cursor_y)
    except Exception as e:
        logger.error(f"Error capturing screenshot: {str(e)}")
        raise Exception(f"Error capturing screenshot: {str(e)}")

def move_cursor(direction, distance):
    try:
        if direction in ["right", "left"]:
            pyautogui.moveRel(xOffset=distance if direction == "right" else -distance, yOffset=0)
        elif direction in ["down", "up"]:
            pyautogui.moveRel(xOffset=0, yOffset=distance if direction == "down" else -distance)
        logger.info(f"Cursor moved {direction} by {distance} pixels")
        return f"Cursor moved {direction} by {distance} pixels."
    except Exception as e:
        logger.error(f"Error moving cursor: {str(e)}")
        raise Exception(f"Error moving cursor: {str(e)}")

def click_cursor():
    try:
        pyautogui.click()
        logger.info("Click performed successfully")
        return "Click performed successfully."
    except Exception as e:
        logger.error(f"Error performing click: {str(e)}")
        raise Exception(f"Error performing click: {str(e)}")