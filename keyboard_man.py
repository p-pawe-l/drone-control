import enum 
import threading
import pynput
import dataclasses
from collections import deque
import typing

class KeyboardEventType(enum.Enum):
    PRESS = 'press'
    RELEASE = 'release'

@typing.final
@dataclasses.dataclass
class KeyboardEvent:
    key: str
    event_type: KeyboardEventType

@typing.final
class KeyboardReader(threading.Thread):
    def __init__(self, shared_queue: deque) -> None:
        super().__init__(daemon=True)
        self.shared_queue: deque = shared_queue
        self._stop_event: threading.Event = threading.Event()
        
        # Timeout for joining the thread when exiting
        self._default_timeout = 3

    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._stop_event.set()
        # Give him some time to finish executing the code :p
        self.join(timeout=self.default_timeout)

    def run(self) -> None:
        with pynput.keyboard.Listener(on_press=self._on_key_press) as listener:
            self._stop_event.wait()
            listener.stop()
    
    def _on_key_press(self, key) -> None:
        """
        Function for detecting key press event
        Puts event object to the shared queue of the main thread
        """
        event = KeyboardEvent(
            key=pynput.keyboard.KeyCode.char(key) if isinstance(key, pynput.keyboard.KeyCode) else str(key),
            event_type=KeyboardEventType.PRESS
        )
        self.shared_queue.append(event)