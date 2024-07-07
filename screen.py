import io
import base64
import pyautogui
from PIL import ImageGrab, ImageDraw
from PyQt5.QtGui import QPixmap

def capture_screenshot():
    try:
        screenshot = ImageGrab.grab()
        
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
        return pixmap, base64.b64encode(img_byte_arr).decode("utf-8"), (cursor_x, cursor_y)
    except Exception as e:
        raise Exception(f"Error capturing screenshot: {str(e)}")

def move_cursor(direction, distance):
    if direction in ["right", "left"]:
        pyautogui.moveRel(xOffset=distance if direction == "right" else -distance, yOffset=0)
    elif direction in ["down", "up"]:
        pyautogui.moveRel(xOffset=0, yOffset=distance if direction == "down" else -distance)
    return f"Cursor moved {direction} by {distance} pixels."

def click_cursor():
    pyautogui.click()
    return "Click performed successfully."