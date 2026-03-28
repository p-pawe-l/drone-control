from __future__ import annotations
import threading
import typing
from collections import deque
import dataclasses

from master_slave_com.event import Event
if typing.TYPE_CHECKING:
    from slave import Slave

@dataclasses.dataclass
class SlaveInstance:
    write_q: deque
    read_q: deque

@typing.final
class Master(threading.Thread):    
    """Listens to slaves events and sends them to the right receiver (aka other slave)"""
    def __init__(self, slaves: typing.Optional[list[Slave]] = None) -> None:
        super().__init__(daemon=True)
        self.slaves: dict[str, SlaveInstance] = {} if slaves is None else \
        {slave.slave_name : SlaveInstance(deque(), deque()) for slave in slaves}
        self._stop_ev: threading.Event = threading.Event()
        
        self._default_timeout: float = 3.0
        
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self._stop_ev.set()
        self.join(timeout=self._default_timeout)
        
    def get_slave(self, slave_name: str) -> SlaveInstance:
        if slave_name in self.slaves:
            return self.slaves[slave_name]
        raise ValueError(f"Slave with name {slave_name} not found")

    def hire_new_slave(self, slave: Slave) -> None:
        """Hire a new slave for a master - pretty controversial, yup"""
        if slave.slave_name not in self.slaves:
            self.slaves[slave.slave_name] = SlaveInstance(deque(), deque())
        else:
            raise ValueError(f"Slave with name {slave.slave_name} already exists")

    def run(self) -> None:
        while not self._stop_ev.is_set():
            for _, slave_instance in self.slaves.items():
                if len(slave_instance.write_q) > 0:
                    fetched_event: Event = slave_instance.write_q.popleft()
                    receiver: SlaveInstance | None = self.slaves.get(fetched_event.receiver)
                    if receiver:
                        receiver.read_q.append(fetched_event)
                            
