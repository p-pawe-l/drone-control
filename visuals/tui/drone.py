import dataclasses
import enum 
import typing


@typing.final
class DroneRole(enum.Enum):
    MOTHER = "mother"
    CHILD = "child"


@typing.final
@dataclasses.dataclass
class DroneEntity:
    uri: str
    name: str 
    role: DroneRole
    thrust: int
    max_thrust: int
    min_thrust: int
    battery_level: int 
    is_connected: bool
    
    @property
    def thrust_percentage(self) -> float:
        span = max(self.max_thrust - self.min_thrust, 1)
        pct = (self.thrust - self.min_thrust) / span * 100
        return max(0.0, min(100.0, pct))