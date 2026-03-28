import typing
import dataclasses


@dataclasses.dataclass
class Event:
    author: str
    receiver: str
    event_type: int
    data: dict[str, typing.Any]
    


