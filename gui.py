import pygame 
import threading

from api import SwarmDroneController

class DroneControllerGUI(threading.Thread):
    FPS: int = 60 
    
    def __init__(self, controller: SwarmDroneController, width=800, height=600):
        super().__init__(daemon=True)
        self.controller = controller
        
        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode((width, height))
        self.screen.fill((0xFF, 0xFF, 0xFF))
        
        pygame.display.set_caption("Drone Controller GUI")
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.running: bool = True
        
        self.thread_timeout: int = 3

    def _run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    
                    elif event.key == pygame.K_SPACE:
                        self.controller.increase_thrust()
                    elif event.key == pygame.K_LSHIFT:
                        self.controller.decrease_thrust()
                        
                        
            pygame.display.flip()  
            self.clock.tick(self.FPS) 

        pygame.quit()
        
    def __enter__(self):
        self.start()
        self._run()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.join(timeout=self.thread_timeout)
        