import typing
import threading
import argparse
import dataclasses
import pynput
import enum
from collections import deque

from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

PARSER = argparse.ArgumentParser(description="Swarm Drone Controller")
PARSER.add_argument("--uri", type=str, required=True, help="URI of the drone to connect to")


class SwarmDroneController:
    DEFAULT_H: float = 0.0 # m
    DEFAULT_V: float = 50 # cm/s
    DEFAULT_FREQ: float = 100 # Hz

    def __init__(self, uri: str, q: deque,
                 drone_vel: float | None = None, freq: float | None = None) -> None:
        self.drone: SyncCrazyflie = SyncCrazyflie(uri)
        self.commander: MotionCommander = MotionCommander(
            crazyflie=self.drone,
            default_height=self.DEFAULT_H
        )
        if drone_vel is not None: assert (drone_vel > 0)
        # Same vel in all directions for now but can be changed in the future
        self.drone_vel: float = self.DEFAULT_V if drone_vel is None else drone_vel
        self.drone_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
        if freq is not None: assert (freq > 0)
        self.timestamp: float = (1 / (self.DEFAULT_FREQ if freq is None else freq))
        self.shared_queue: deque = q
        
        self.thread: threading.Thread = threading.Thread(
            target=self._controller_loop,
            daemon=True
        )
        self.thread.start()

    def set_freq(self, n_freq: float) -> None:
        assert (n_freq > 0)
        self.timestamp = (1 / n_freq)

    def set_vel(self, n_vel: float) -> None:
        assert (n_vel > 0)
        self.drone_vel = n_vel
        
    def _calc_dist(self) -> float:
        return self.timestamp * self.drone_vel
        
    def _move_forward(self):
        self.commander.forward(distance_m=self._calc_dist())
        
    def _move_back(self):
        self.commander.back(distance_m=self._calc_dist())
        
    def _move_left(self):
        self.commander.left(distance_m=self._calc_dist())        

    def _move_right(self):
        self.commander.right(distance_m=self._calc_dist())

    def _move_up(self):
        self.commander.up(distance_m=self._calc_dist())
        
    def _move_down(self):
        self.commander.down(distance_m=self._calc_dist()) 
        
    def move_on_key(self, key) -> None:
        match key:
            case pynput.keyboard.KeyCode.from_char('w'):
                self._move_forward()
            case pynput.keyboard.KeyCode.from_char('s'):
                self._move_back()
            case pynput.keyboard.KeyCode.from_char('a'): 
                self._move_left()
            case pynput.keyboard.KeyCode.from_char('d'):
                self._move_right()
            case pynput.keyboard.Key.space:
                self._move_up()
            case pynput.keyboard.Key.shift:
                self._move_down()
            case _:
                pass
            
    def _controller_loop(self):
        while True:
            if len(self.shared_queue) > 0:
                event: KeyboardEvent = self.shared_queue.popleft()
                if event.event_type == KeyboardEventType.PRESS:
                    self.move_on_key(event.key)

        
class KeyboardEventType(enum.Enum):
    PRESS = 'press'
    RELEASE = 'release'


@dataclasses.dataclass
class KeyboardEvent:
    key: pynput.keyboard.Key | pynput.keyboard.KeyCode
    event_type: KeyboardEventType


class KeyboardReader:
    def __init__(self, drone_controller: SwarmDroneController, q: deque) -> None:
        self.drone_controller = drone_controller
        
        self.pressed_keys: set = set()
        self.thread: threading.Thread = threading.Thread(
            target=self._keyboard_loop,
            daemon=True
        )
        self.thread.start()
        self.shared_queue: deque = q
    
    def _keyboard_loop(self):
        with pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as listener:
            listener.join()
    
    def _on_press(self, key) -> None:
        event = KeyboardEvent(
            key=key,
            event_type=KeyboardEventType.PRESS
        )
        print(f"Key {key} pressed")
        self.shared_queue.append(event)
    
    def _on_release(self, key) -> None:
        event = KeyboardEvent(
            key=key,
            event_type=KeyboardEventType.RELEASE
        )
        self.shared_queue.append(event)

# Reads the keyboard input all the time and exectues the corresponding drone movement func
if __name__ == "__main__":
    args = PARSER.parse_args()
    
    SHARED_QUEUE: deque = deque()
    drone_controller = SwarmDroneController(uri=args.uri, q=SHARED_QUEUE)
    keyboard_reader = KeyboardReader(drone_controller=drone_controller, q=SHARED_QUEUE)
    
    keyboard_reader.thread.join()
    drone_controller.thread.join()
    
    
    
    