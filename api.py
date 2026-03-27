import threading
import argparse
from collections import deque

import cflib
import time
from cflib.crazyflie import Crazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from events import Event, EventTarget, EventType


PARSER = argparse.ArgumentParser(description="Swarm Drone Controller")
PARSER.add_argument("--uri", type=str, required=True, help="URI of the drone to connect to")
PARSER.add_argument("--gui", action='store_true', help="Whether to launch the GUI")


class SwarmDroneController:
    DEFAULT_H: float = 0.1 # m
    DEFAULT_V: float = 1 # cm/s
    DEFAULT_FREQ: float = 2000 # Hz

    MIN_THRUST: int = 0x0000
    MAX_THRUST: int = 0xFFFF

    def __init__(self, uri: str, input_queue: deque, slave_queues: dict[EventTarget, deque],
                 drone_vel: float | None = None, freq: float | None = None) -> None:
        cflib.crtp.init_drivers()
        self.drone: SyncCrazyflie = SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache'))
        self.drone.open_link()

        response = self.drone.cf.platform.send_arming_request(True)

        self.drone.cf.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(1)
        print("connected")
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

        self.input_queue: deque = input_queue
        self.slave_queues: dict[EventTarget, deque] = slave_queues

        self.thrust: int = 16000
        self.thrust_jump: int = 1500

        self.thread: threading.Thread = threading.Thread(
            target=self._controller_loop,
            daemon=True
        )
        self.thread.start()

        # Broadcast initial state to all slaves
        self._broadcast_thrust()

    def set_freq(self, n_freq: float) -> None:
        assert (n_freq > 0)
        self.timestamp = (1 / n_freq)

    def set_vel(self, n_vel: float) -> None:
        assert (n_vel > 0)
        self.drone_vel = n_vel

    def _calc_dist(self) -> float:
        # TODO: add actual distance calculation xd
        # return self.timestamp * self.drone_vel / 100
        return 0.001

    # TODO something need to be done with this _move* functions
    def _move_forward(self):
        self.commander.forward(distance_m=self._calc_dist())

    def _move_back(self):
        self.commander.back(distance_m=self._calc_dist())

    def _move_left(self):
        self.commander.left(distance_m=self._calc_dist())

    def _move_right(self):
        self.commander.right(distance_m=self._calc_dist())

    def SET_THRUST_JUMP(self, jump: int) -> None:
        assert 0x0000 < jump < 0xFFFF
        self.thrust_jump = jump

    def SET_THRUST(self, thrust: int) -> None:
        self.thrust = max(min(thrust, self.MAX_THRUST), self.MIN_THRUST)

        try:
            self.drone.cf.commander.send_setpoint(0, 0, 0, self.thrust)
        except Exception as e:
            print(f"Error occured: {e}")

    def increase_thrust(self) -> None:
        new_thrust = min(self.thrust + self.thrust_jump, self.MAX_THRUST)
        self.SET_THRUST(new_thrust)
        self._broadcast_thrust()

    def decrease_thrust(self) -> None:
        new_thrust = max(self.thrust - self.thrust_jump, self.MIN_THRUST)
        self.SET_THRUST(new_thrust)
        self._broadcast_thrust()

    def _broadcast_thrust(self) -> None:
        data = {
            'thrust': self.thrust,
            'min': self.MIN_THRUST,
            'max': self.MAX_THRUST,
        }
        for target, queue in self.slave_queues.items():
            queue.append(Event(
                target=target,
                event_type=EventType.THRUST_UPDATE,
                data=data,
            ))

    def _controller_loop(self):
        while True:
            if len(self.input_queue) > 0:
                event: Event = self.input_queue.popleft()
                if len(self.input_queue) > 1:
                    continue

                if event.event_type == EventType.INCREASE_THRUST:
                    self.increase_thrust()
                elif event.event_type == EventType.DECREASE_THRUST:
                    self.decrease_thrust()
