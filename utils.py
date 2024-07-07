import time
import pygame
from AppKit import NSWorkspace, NSScreen, NSApplicationActivateIgnoringOtherApps
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

def find_and_flash_iphone_mirroring_window():
    iphone_window = None
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    
    for window in window_list:
        window_name = window.get('kCGWindowName', '').lower()
        if 'iphone' in window_name and 'mirroring' in window_name:
            iphone_window = window
            break

    if iphone_window:
        # Get window coordinates
        left = iphone_window['kCGWindowBounds']['X']
        top = iphone_window['kCGWindowBounds']['Y']
        width = iphone_window['kCGWindowBounds']['Width']
        height = iphone_window['kCGWindowBounds']['Height']

        # Convert coordinates to account for Retina displays
        screen = NSScreen.mainScreen()
        scale_factor = screen.backingScaleFactor()
        left *= scale_factor
        top *= scale_factor
        width *= scale_factor
        height *= scale_factor

        # Flip Y-coordinate (macOS uses bottom-left origin)
        screen_height = NSScreen.mainScreen().frame().size.height * scale_factor
        top = screen_height - top - height

        # Initialize Pygame
        pygame.init()
        screen = pygame.display.set_mode((int(width), int(height)), pygame.NOFRAME)
        pygame.display.set_caption("Bounding Box")

        # Set the window position
        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{int(left)},{int(top)}"
        pygame.display.set_mode((int(width), int(height)), pygame.NOFRAME)

        # Flash the bounding box
        for _ in range(6):  # Flash 3 times (3 on, 3 off)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            if _ % 2 == 0:
                color = (255, 0, 0)  # Red
            else:
                color = (0, 0, 0, 0)  # Transparent

            screen.fill((0, 0, 0, 0))  # Transparent background
            pygame.draw.rect(screen, color, (0, 0, width, height), 2)
            pygame.display.flip()
            time.sleep(0.5)

        pygame.quit()
    else:
        print("iPhone Mirroring window not found.")

def bring_window_to_front(window_name):
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    for app in running_apps:
        if window_name.lower() in app.localizedName().lower():
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            return True
    return False