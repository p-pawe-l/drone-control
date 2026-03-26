import typing
import threading
import argparse
import dataclasses
import pynput
import enum
from collections import deque

import cflib
import time
from cflib.crazyflie import Crazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

PARSER = argparse.ArgumentParser(description="Swarm Drone Controller")
PARSER.add_argument("--uri", type=str, required=True, help="URI of the drone to connect to")

cflib.crtp.init_drivers()

class SwarmDroneController:
    DEFAULT_H: float = 0.1 # m
    DEFAULT_V: float = 1 # cm/s
    DEFAULT_FREQ: float = 2000 # Hz

    def __init__(self, uri: str, q: deque,
                 drone_vel: float | None = None, freq: float | None = None) -> None:
        print(f"uri: {uri}")
        self.drone: SyncCrazyflie = SyncCrazyflie("radio://0/80/2M/E7E7E7E7E7", cf=Crazyflie(rw_cache='./cache'))

        self.drone.open_link()

        response = self.drone.cf.platform.send_arming_request(True)

        self.drone.cf.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(1)
        print("conencted")
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
        # self.commander.take_off(velocity=self.drone_vel / 100)
        self.thread.start()
        self.thrust = 16000
        self.thrust_jump: int = 1500

    def set_freq(self, n_freq: float) -> None:
        assert (n_freq > 0)
        self.timestamp = (1 / n_freq)

    def set_vel(self, n_vel: float) -> None:
        assert (n_vel > 0)
        self.drone_vel = n_vel
        
    def _calc_dist(self) -> float:
        # return self.timestamp * self.drone_vel / 100
        return 0.001
        
    def _move_forward(self):
        self.commander.forward(distance_m=self._calc_dist())
        
    def _move_back(self):
        self.commander.back(distance_m=self._calc_dist())
        
    def _move_left(self):
        self.commander.left(distance_m=self._calc_dist())        

    def _move_right(self):
        self.commander.right(distance_m=self._calc_dist())

    def _move_up(self):
        print(f"self.thrust: {self.thrust}")
        self.thrust += self.thrust_jump
        self.thrust = max(self.thrust, 0x0001)
        self.thrust = min(self.thrust, 0xFFFE)
        try: 
            self.drone.cf.commander.send_setpoint(0, 0, 0, self.thrust)
        except Exception as e:
            print(f"Caught: {e}")

    def _move_down(self):
        print(f"self.thrust: {self.thrust}")
        self.thrust -= self.thrust_jump
        self.thrust = max(self.thrust, 0x0001)
        self.thrust = min(self.thrust, 0xFFFE)
        try: 
            self.drone.cf.commander.send_setpoint(0, 0, 0, self.thrust)
        except Exception as e:
            print(f"Caught: {e}")

    def move_on_key(self, key):
        if key == pynput.keyboard.KeyCode.from_char('w'):
            self._move_forward()
        elif key == pynput.keyboard.KeyCode.from_char('s'):
            self._move_back()
        elif key == pynput.keyboard.KeyCode.from_char('a'):
            self._move_left()
        elif key == pynput.keyboard.KeyCode.from_char('d'):
            self._move_right()
        elif key == pynput.keyboard.Key.space:
            self._move_up()
        elif key == pynput.keyboard.Key.shift:
            self._move_down()
        else:
            pass

    def _controller_loop(self):
        while True:
            if len(self.shared_queue) > 0:
                event: KeyboardEvent = self.shared_queue.popleft()
                if len(self.shared_queue) > 1:
                    continue
                elif event.event_type == KeyboardEventType.PRESS:
                    print("Executing movement for key: ", event.key)
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
        print(f"Key {key} released")
        self.shared_queue.append(event)

# Reads the keyboard input all the time and exectues the corresponding drone movement func
if __name__ == "__main__":
    args = PARSER.parse_args()
    
    SHARED_QUEUE: deque = deque()
    drone_controller = SwarmDroneController(uri=args.uri, q=SHARED_QUEUE)
    keyboard_reader = KeyboardReader(drone_controller=drone_controller, q=SHARED_QUEUE)
    
    keyboard_reader.thread.join()
    drone_controller.thread.join()
    
    
    
    