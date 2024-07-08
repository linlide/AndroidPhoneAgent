import os
import io
import base64
import pyautogui
import logging
from PIL import Image, ImageDraw
from PyQt5.QtGui import QPixmap
import time

logger = logging.getLogger(__name__)

def capture_screenshot():
    try:
        logger.info("Capturing screenshot")
        pyautogui.hotkey('command', 'shift', '3')
        
        time.sleep(5)
        
        screenshots_folder = os.path.join(os.path.expanduser("~"), "Dropbox", "Screenshots")
        screenshots = [f for f in os.listdir(screenshots_folder) if f.startswith("Screenshot")]
        screenshots.sort(key=lambda x: os.path.getmtime(os.path.join(screenshots_folder, x)))
        latest_screenshot_path = os.path.join(screenshots_folder, screenshots[-1])
        
        screenshot = Image.open(latest_screenshot_path)
        
        if screenshot.mode == 'RGBA':
            screenshot = screenshot.convert('RGB')
        
        cursor_x, cursor_y = pyautogui.position()
        
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
        
        img_byte_arr = io.BytesIO()
        quality = 95
        screenshot.save(img_byte_arr, format='JPEG', quality=quality)
        img_byte_arr = img_byte_arr.getvalue()
        
        while len(img_byte_arr) > 5 * 1024 * 1024:
            quality = int(quality * 0.9)
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr = img_byte_arr.getvalue()
        
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr)
        logger.info(f"Screenshot captured successfully. Cursor position: ({cursor_x}, {cursor_y})")
        return pixmap, base64.b64encode(img_byte_arr).decode("utf-8"), (cursor_x, cursor_y)
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