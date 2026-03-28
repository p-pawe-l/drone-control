from __future__ import annotations
import abc
import threading
import typing

if typing.TYPE_CHECKING:
    from master import Master
from event import Event


class Slave(abc.ABC, threading.Thread):
    """Worker for master"""
    def __init__(self, master: Master, slave_name: str) -> None:
        super().__init__(daemon=True)
        self.slave_name: str = slave_name
        self.master: Master = master
        
        self.start()
        
    def __eq__(self, other: object) -> bool:
        return self.slave_name == other.slave_name
        
    @abc.abstractmethod
    def run(self):
        """What this slave is going to do ?"""
        pass
        
    def send_event(self, data: dict, receiver: str, event_type: str) -> None:
        self.master.get_slave(self.slave_name).write_q.append(Event(
            author=self.slave_name,
            receiver=receiver,
            event_type=event_type,
            data=data
        ))
        
    def read_event(self) -> tuple[str, dict]:
        if len(self.master.get_slave(self.slave_name).read_q) > 0:
            event: Event = self.master.get_slave(self.slave_name).read_q.popleft()
            return (event.event_type, event.data)
            
        
    