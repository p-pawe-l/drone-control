import pygame 
import threading

from api import SwarmDroneController

class DroneControllerGUI(threading.Thread):
    FPS: int = 60 
    WINDOW_TITLE: str = "Drone Controller GUI"
    FONT_SIZE: int = 36
    
    def __init__(self, controller: SwarmDroneController, width=800, height=600):
        super().__init__(daemon=True)
        self.controller: SwarmDroneController = controller
        
        pygame.init()
        self._screen: pygame.Surface = pygame.display.set_mode((width, height))
        self._bg_color: tuple[int, int, int] = (0xFF, 0xFF, 0xFF)
        
        pygame.display.set_caption(self.WINDOW_TITLE)
        self._clock: pygame.time.Clock = pygame.time.Clock()
        self._running: bool = True
        
        self._thread_timeout: int = 3
        
        # Thrust text info
        self._font = pygame.font.SysFont(None, self.FONT_SIZE)
        self.text_color: tuple[int, int, int] = (0x00, 0x00, 0x00)
        
        # Thrust bar info
        self.thrust_bar_color: tuple[int, int, int] = (0x00, 0xFF, 0x00)
        self.thrust_bar_height: int = 450
        self.thrust_bar_width: int = 50
        
        self.fill_bar_padding: int = 5
        
        self.thrust_bar_x_pos: int = self._screen.get_width() - 100
        self.thrust_bar_y_pos: int = self._screen.get_height() - self.thrust_bar_height - 50

    def _calc_thrust_ratio(self) -> float:
        thrust_now: int = int(self.controller.drone_thrust)
        delta: int = max(self.controller.MAX_THRUST - self.controller.MIN_THRUST, 1)

        thrust_ratio = (thrust_now - self.controller.MIN_THRUST) / delta
        return thrust_ratio
    
    def _draw_thrust_bar(self):
        outer_rect: pygame.Rect = pygame.Rect(self.thrust_bar_x_pos, self.thrust_bar_y_pos, self.thrust_bar_width, self.thrust_bar_height)

        inner_width: int = self.thrust_bar_width - 2 * self.fill_bar_padding
        inner_height: int = self.thrust_bar_height - 2 * self.fill_bar_padding
        
        thrust_ratio: float = self._calc_thrust_ratio()
        fill_height: int = int(inner_height * thrust_ratio)
        fill_top: int = self.thrust_bar_y_pos + self.fill_bar_padding + (inner_height - fill_height)
        fill_rect = pygame.Rect(self.thrust_bar_x_pos + self.fill_bar_padding, fill_top, inner_width, fill_height)

        pygame.draw.rect(self._screen, self._bg_color, outer_rect)
        if fill_height > 0:
            pygame.draw.rect(self._screen, self.thrust_bar_color, fill_rect)
        pygame.draw.rect(self._screen, (0x00, 0x00, 0x00), outer_rect, width=self.fill_bar_padding)
        
    def _draw_thrust_text(self):
        thrust_text = f"Thrust: {self.controller.drone_thrust:.2f}"
        text_surface = self._font.render(thrust_text, True, self.text_color)
        text_rect = text_surface.get_rect()
        text_rect.topleft = (self.thrust_bar_x_pos - 10, self.thrust_bar_y_pos - 50)
        self._screen.blit(text_surface, text_rect)

    def _run(self):
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    
                    elif event.key == pygame.K_SPACE:
                        self.controller.increase_thrust()
                    elif event.key == pygame.K_LSHIFT:
                        self.controller.decrease_thrust()

            self._screen.fill(self._bg_color)

            self._draw_thrust_bar()
            self._draw_thrust_text()
               
            pygame.display.flip()  
            self._clock.tick(self.FPS) 
        
    def __enter__(self):
        self.start()
        self._run()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        pygame.quit()
        self.join(timeout=self._thread_timeout)
        