import io
import base64
import pyautogui
import time
import pygame
import pywinctl as pwc
from PIL import Image, ImageGrab, ImageDraw
from PyQt5.QtGui import QPixmap

def find_and_flash_iphone_mirroring_window():
    try:
        iphone_windows = [w for w in pwc.getAllWindows() if 'iPhone Mirroring' in w.title]
        if not iphone_windows:
            raise Exception("iPhone Mirroring window not found")
        
        window = iphone_windows[0]
        
        window.activate()
        
        left, top, right, bottom = window.box
        width = right - left
        height = bottom - top

        pygame.init()
        screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
        pygame.display.set_caption("Bounding Box")

        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{left},{top}"
        pygame.display.set_mode((width, height), pygame.NOFRAME)

        for _ in range(6):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return window

            if _ % 2 == 0:
                color = (255, 0, 0)
            else:
                color = (0, 0, 0, 0)

            screen.fill((0, 0, 0, 0))
            pygame.draw.rect(screen, color, (0, 0, width, height), 2)
            pygame.display.flip()
            time.sleep(0.5)

        pygame.quit()
        return window
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def capture_screenshot(iphone_window):
    try:
        left, top, right, bottom = iphone_window.box

        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        
        screenshot = screenshot.convert('RGB')
        
        max_size = (1600, 1600)
        screenshot.thumbnail(max_size, Image.LANCZOS)
        
        cursor_x, cursor_y = pyautogui.position()
        cursor_position = (cursor_x - left, cursor_y - top)
        
        draw = ImageDraw.Draw(screenshot)
        cursor_radius = 10
        cursor_color = "red"
        draw.ellipse([cursor_position[0] - cursor_radius, cursor_position[1] - cursor_radius,
                      cursor_position[0] + cursor_radius, cursor_position[1] + cursor_radius],
                     outline=cursor_color, width=2)
        
        line_length = 20
        draw.line([cursor_position[0] - line_length, cursor_position[1],
                   cursor_position[0] + line_length, cursor_position[1]],
                  fill=cursor_color, width=2)
        draw.line([cursor_position[0], cursor_position[1] - line_length,
                   cursor_position[0], cursor_position[1] + line_length],
                  fill=cursor_color, width=2)
        
        img_byte_arr = io.BytesIO()
        quality = 85
        screenshot.save(img_byte_arr, format='JPEG', quality=quality)
        img_byte_arr = img_byte_arr.getvalue()
        
        while len(img_byte_arr) > 5 * 1024 * 1024:
            quality = int(quality * 0.9)
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr = img_byte_arr.getvalue()
        
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr)
        return pixmap, base64.b64encode(img_byte_arr).decode("utf-8"), cursor_position
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