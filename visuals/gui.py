import pygame
import typing

from master_slave_com import EventType
from master_slave_com import Slave
from control import SwarmDroneController


class DroneControllerGUI(Slave):
    SLAVE_NAME: str = "GUI"
    WINDOW_TITLE: str = "Drone Controller GUI"
    FPS: int = 60
    FONT_SIZE: int = 36

    def __init__(self, master, width=800, height=600):
        # Set all attrs before super().__init__() since Slave calls self.start()
        self._thrust: int | None = None
        self._min_thrust: int | None = None
        self._max_thrust: int | None = None

        pygame.init()
        self._screen: pygame.Surface = pygame.display.set_mode((width, height))
        self._bg_color: tuple[int, int, int] = (0xFF, 0xFF, 0xFF)

        pygame.display.set_caption(self.WINDOW_TITLE)
        self._clock: pygame.time.Clock = pygame.time.Clock()
        self._running: bool = True

        self._font = pygame.font.SysFont(None, self.FONT_SIZE)
        self.text_color: tuple[int, int, int] = (0x00, 0x00, 0x00)

        self.thrust_bar_color: tuple[int, int, int] = (0x00, 0xFF, 0x00)
        self.thrust_bar_height: int = 450
        self.thrust_bar_width: int = 50

        self.fill_bar_padding: int = 5

        self.thrust_bar_x_pos: int = 50
        self.thrust_bar_y_pos: int = self._screen.get_height() - self.thrust_bar_height - 50

        super().__init__(master=master, slave_name=self.SLAVE_NAME)

    def run(self) -> None:
        # Slave thread — no-op since pygame loop runs on the main thread via loop()
        pass

    def _process_state_events(self):
        result = self.read_event()
        while result is not None:
            _, data = result
            self._thrust = data.get('thrust', self._thrust)
            self._min_thrust = data.get('min', self._min_thrust)
            self._max_thrust = data.get('max', self._max_thrust)
            result = self.read_event()

    def _send_command(self, ev_t: EventType, **data: dict[str, typing.Any]):
        self.send_event(
            data=data,
            receiver=SwarmDroneController.SLAVE_NAME,
            event_type=ev_t,
        )

    def _calc_thrust_ratio(self) -> float:
        delta: int = max(self._max_thrust - self._min_thrust, 1)
        return (self._thrust - self._min_thrust) / delta

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
        thrust_text = f"Thrust: {self._thrust:.2f}"
        text_surface = self._font.render(thrust_text, True, self.text_color)
        text_rect = text_surface.get_rect()
        text_rect.topleft = (self.thrust_bar_x_pos, self.thrust_bar_y_pos - 50)
        self._screen.blit(text_surface, text_rect)

    def loop(self):
        """Blocking pygame loop — call from main thread."""
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    elif event.key == pygame.K_SPACE:
                        self._send_command(EventType.INCREASE_THRUST)
                    elif event.key == pygame.K_LSHIFT:
                        self._send_command(EventType.DECREASE_THRUST)

            self._process_state_events()

            self._screen.fill(self._bg_color)
            if self._thrust is not None:
                self._draw_thrust_bar()
                self._draw_thrust_text()

            pygame.display.flip()
            self._clock.tick(self.FPS)

        pygame.quit()
