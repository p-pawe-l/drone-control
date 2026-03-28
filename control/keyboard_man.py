import threading
import pynput
import typing
from collections import deque

from master_slave_com import Slave

@typing.final
class KeyboardReader(Slave):
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
        self.join(timeout=self._default_timeout)

    def run(self) -> None:
        with pynput.keyboard.Listener(on_press=self._on_key_press) as listener:
            self._stop_event.wait()
            listener.stop()

    def _on_key_press(self, key) -> None:
        event_type: EventType | None = None

        if key == pynput.keyboard.Key.space:
            event_type = EventType.INCREASE_THRUST
        elif key == pynput.keyboard.Key.shift:
            event_type = EventType.DECREASE_THRUST

        if event_type is not None:
            self.shared_queue.append(Event(
                target=EventTarget.CONTROLLER,
                event_type=event_type,
            ))
