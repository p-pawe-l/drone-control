import typing
import time

import cflib
from cflib.crazyflie import Crazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from master_slave_com import Slave
from master_slave_com.event import EventType

@typing.final
class SwarmDroneController(Slave):
    SLAVE_NAME: str = "CONTROLLER"
    
    DEFAULT_H: float = 0.1 # m
    DEFAULT_V: float = 1 # cm/s
    DEFAULT_FREQ: float = 2000 # Hz

    MIN_THRUST: int = 0x0000
    MAX_THRUST: int = 0xFFFF

    def __init__(self, master, uri: str, drone_vel: float | None = None, freq: float | None = None):
        cflib.crtp.init_drivers()
        self.drone: SyncCrazyflie = SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache'))
        self.drone.open_link()

        self.drone.cf.platform.send_arming_request(True)

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

        self.thrust: int = 16000
        self.thrust_jump: int = 1500

        super().__init__(master=master, slave_name=self.SLAVE_NAME)

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
        assert self.MIN_THRUST < jump < self.MAX_THRUST
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
        for slave_name in self.master.slaves:
            if slave_name != self.slave_name:
                self.send_event(
                    data=data,
                    receiver=slave_name,
                    event_type=EventType.INCREASE_THRUST,
                )

    def run(self) -> None:
        self._broadcast_thrust()
        with self.drone:
            while True:
                result = self.read_event()
                if result is not None:
                    event_type, _ = result
                    if event_type == EventType.INCREASE_THRUST:
                        self.increase_thrust()
                    elif event_type == EventType.DECREASE_THRUST:
                        self.decrease_thrust()
                time.sleep(self.timestamp)
