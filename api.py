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
PARSER.add_argument("--gui", action='store_true', help="Whether to launch the GUI")

cflib.crtp.init_drivers()

class SwarmDroneController:
    DEFAULT_H: float = 0.1 # m
    DEFAULT_V: float = 1 # cm/s
    DEFAULT_FREQ: float = 2000 # Hz
    
    MIN_THRUST: int = 0x0000
    MAX_THRUST: int = 0xFFFF
    
    def __init__(self, uri: str, q: deque, drone_vel: float | None = None, freq: float | None = None) -> None:
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

    @property
    def drone_thrust(self) -> int:
        return self.thrust
    
    def SET_THRUST_JUMP(self, jump: int) -> None:
        assert 0x0000 < jump < 0xFFFF
        self.thrust_jump = jump
    
    def SET_THRUST(self, thrust: int) -> None:
        self.thrust = min(thrust, self.MAX_THRUST)
        self.thrust = max(thrust, self.MIN_THRUST)
        
        try:
            self.drone.cf.commander.send_setpoint(0, 0, 0, self.thrust)
        except Exception as e:
            print(f"Error occured: {e}")
        
    def increase_thrust(self) -> None:
        new_thrust = min(self.thrust + self.thrust_jump, self.MAX_THRUST)
        
        self.SET_THRUST(new_thrust)

    def decrease_thrust(self) -> None:
        new_thrust = max(self.thrust - self.thrust_jump, self.MIN_THRUST)
        
        self.SET_THRUST(new_thrust)

    def move_on_key(self, key):
        # TODO - implement movement in all 4 directions
        # if key == pynput.keyboard.KeyCode.from_char('w'):
        #     self._move_forward()
        # elif key == pynput.keyboard.KeyCode.from_char('s'):
        #     self._move_back()
        # elif key == pynput.keyboard.KeyCode.from_char('a'):
        #     self._move_left()
        # elif key == pynput.keyboard.KeyCode.from_char('d'):
        #     self._move_right()
        
        # Only works up and down for no :p
        if key == pynput.keyboard.Key.space:
            self.increase_thrust()
        elif key == pynput.keyboard.Key.shift:
            self.decrease_thrust()
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

# Reads the keyboard input all the time and exectues the corresponding drone movement func
if __name__ == "__main__":
    args = PARSER.parse_args()
    
    SHARED_QUEUE: deque = deque()
    drone_controller = SwarmDroneController(uri=args.uri, q=SHARED_QUEUE)
    keyboard_reader = KeyboardReader(drone_controller=drone_controller, q=SHARED_QUEUE)
    
    keyboard_reader.thread.join()
    drone_controller.thread.join()
    
    
    
    