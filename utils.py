import time
import pygame
import pywinctl as pwc

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