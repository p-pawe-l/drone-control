import enum
import typing
import dataclasses


class EventTarget(enum.Enum):
    CONTROLLER = 'controller'
    GUI = 'gui'
    CLI = 'cli'


class EventType(enum.Enum):
    INCREASE_THRUST = 'increase_thrust'
    DECREASE_THRUST = 'decrease_thrust'

    THRUST_UPDATE = 'thrust_update'


@typing.final
@dataclasses.dataclass
class Event:
    target: EventTarget
    event_type: EventType
    data: dict | None = None
