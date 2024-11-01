import os
import io
import base64
import pyautogui
import logging
from PIL import Image, ImageDraw
import time
import subprocess

logger = logging.getLogger(__name__)

screen_width, screen_height = pyautogui.size()

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

def capture_screenshot(device_type="android"):
    try:
        # 重启 ADB 服务器
     #   subprocess.run(['adb', 'kill-server'], check=True)
      #  time.sleep(1)
      #  subprocess.run(['adb', 'start-server'], check=True)
       # time.sleep(2)

        # 等待设备连接
        #subprocess.run(['adb', 'wait-for-device'], check=True)
        
        # 获取 UI XML
        subprocess.run(['adb', 'shell', 'uiautomator', 'dump', '/sdcard/window_dump.xml'], check=True)
        time.sleep(1)
        subprocess.run(['adb', 'pull', '/sdcard/window_dump.xml'], check=True)
        
        with open('window_dump.xml', 'r', encoding='utf-8') as f:
            ui_xml = f.read()

        # 修改截图命令，不使用 shell=True
        subprocess.run(['adb', 'shell', 'screencap', '-p', '/sdcard/screenshot.png'], check=True)
        time.sleep(1)
        subprocess.run(['adb', 'pull', '/sdcard/screenshot.png'], check=True)
        
        # 读取并编码图片
        with open('screenshot.png', 'rb') as f:
            image_data = f.read()
            screenshot_data = base64.b64encode(image_data).decode('utf-8')
            
        # 获取屏幕尺寸
        width, height = get_screen_dimensions(device_type)
        cursor_position = (width // 2, height // 2)
        
        return screenshot_data, cursor_position, ui_xml

    except Exception as e:
        logging.error(f"Error capturing screenshot: {str(e)}")
        return None, None, None

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

def get_screen_dimensions(device_type):
    try:
        # For Android devices, use adb to get screen resolution
        if device_type.lower() == "android":
            output = subprocess.check_output(['adb', 'shell', 'wm', 'size'], text=True)
            # Output format: "Physical size: 1080x1920"
            size_str = output.strip().split(': ')[1]
            width, height = map(int, size_str.split('x'))
            return width, height
        else:
            # For other device types, implement appropriate method
            raise NotImplementedError(f"Screen dimension detection not implemented for {device_type}")
    except Exception as e:
        logging.error(f"Error getting screen dimensions: {str(e)}")
        # Return default dimensions
        return 1080, 1920