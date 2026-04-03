import math
import time

from master_slave_com.event import EventType
from master_slave_com.slave import Slave


class MockDroneController(Slave):
    SLAVE_NAME: str = "CONTROLLER"

    MIN_THRUST: int = 0x0000
    MAX_THRUST: int = 0xFFFF

    DEFAULT_THRUST: int = 16000
    DEFAULT_THRUST_JUMP: int = 1500

    _POLL_INTERVAL: float = 0.05
    _POS_INTERVAL: float = 0.1   
    _RADIUS: float = 1.5        
    _SPEED: float = 0.3          

    def __init__(self, master) -> None:
        self.thrust: int = self.DEFAULT_THRUST
        self.thrust_jump: int = self.DEFAULT_THRUST_JUMP
        self._angle: float = 0.0
        self._z: float = 0.5
        super().__init__(master=master, slave_name=self.SLAVE_NAME)

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

    def _broadcast_position(self) -> None:
        x = self._RADIUS * math.cos(self._angle)
        y = self._RADIUS * math.sin(self._angle)
        vx = -self._RADIUS * self._SPEED * math.sin(self._angle)
        vy =  self._RADIUS * self._SPEED * math.cos(self._angle)
        data = {
            'x': x, 'y': y, 'z': self._z,
            'vx': vx, 'vy': vy, 'vz': 0.0,
        }
        for slave_name in self.master.slaves:
            if slave_name != self.slave_name:
                self.send_event(
                    data=data,
                    receiver=slave_name,
                    event_type=EventType.POSITION_UPDATE,
                )

    def run(self) -> None:
        self._broadcast_thrust()
        last_pos_time = time.time()

        while True:
            result = self.read_event()
            if result is not None:
                event_type, _ = result
                if event_type == EventType.INCREASE_THRUST:
                    self.thrust = min(self.thrust + self.thrust_jump, self.MAX_THRUST)
                    self._broadcast_thrust()
                elif event_type == EventType.DECREASE_THRUST:
                    self.thrust = max(self.thrust - self.thrust_jump, self.MIN_THRUST)
                    self._broadcast_thrust()

            now = time.time()
            if now - last_pos_time >= self._POS_INTERVAL:
                self._angle += self._SPEED * self._POS_INTERVAL
                self._broadcast_position()
                last_pos_time = now

            time.sleep(self._POLL_INTERVAL)
