import time

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, Footer, DataTable
from textual.containers import Center, Middle, Vertical, Horizontal
from textual.binding import Binding

from master_slave_com.slave import Slave
from master_slave_com.event import EventType


BANNER = """\
  ____                        ____            _             _
 |  _ \\ _ __ ___  _ __   ___ / ___|___  _ __ | |_ _ __ ___ | |
 | | | | '__/ _ \\| '_ \\ / _ \\ |   / _ \\| '_ \\| __| '__/ _ \\| |
 | |_| | | | (_) | | | |  __/ |__| (_) | | | | |_| | | (_) | |
 |____/|_|  \\___/|_| |_|\\___|\\____\\___/|_| |_|\\__|_|  \\___/|_|\
"""

CSS = """
Screen {
    background: #0d0d0d;
    color: #00ff41;
}

/* ── URI screen ── */

URIScreen { align: center middle; }

#banner {
    color: #00ff41;
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#subtitle {
    text-align: center;
    color: #007a1f;
    margin-bottom: 2;
}

#uri-container {
    width: 64;
    height: auto;
    border: ascii #007a1f;
    padding: 1 2;
}

#uri-label   { color: #007a1f; margin-bottom: 1; }

#error-msg { color: #ff4444; margin-bottom: 1; }

/* ── Control screen ── */

#title-bar {
    height: 3;
    border: ascii #007a1f;
    margin: 1 1 0 1;
    padding: 0 2;
    content-align: left middle;
    color: #00ff41;
    text-style: bold;
}

ControlScreen {
    layout: vertical;
    background: #0d0d0d;
}

#main-area {
    layout: horizontal;
    height: 1fr;
}

#left-panel {
    layout: horizontal;
    width: 1fr;
    border: ascii #007a1f;
    margin: 1 0 1 1;
    padding: 1;
}

#right-panel {
    width: 1fr;
    border: ascii #007a1f;
    margin: 1 1 1 1;
    padding: 1;
}

DronePositionMap {
    width: 1fr;
    height: 1fr;
    color: #00ff41;
}

#map-title {
    color: #007a1f;
    text-style: bold;
    margin-bottom: 1;
}

#data-col {
    width: 1fr;
}

#uri-bar {
    height: 3;
    border: ascii #007a1f;
    margin: 1;
    padding: 0 2;
    content-align: left middle;
}

.panel-title {
    color: #00ff41;
    text-style: bold;
    margin-bottom: 1;
}

.data-box {
    border: ascii #007a1f;
    padding: 0 1;
    height: auto;
    margin-bottom: 1;
}

.table-title {
    color: #007a1f;
    text-style: bold;
    margin-bottom: 0;
}

.control-hint { color: #007a1f; margin-bottom: 1; }

VerticalThrustBar { width: 7; height: 1fr; }

/* ── Data tables ── */

DataTable {
    background: #0d0d0d;
    color: #00ff41;
    height: auto;
}

DataTable > .datatable--header {
    background: #0d0d0d;
    color: #007a1f;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #0d0d0d;
    color: #00ff41;
}

/* ── Shared ── */

Input {
    background: #0d0d0d;
    color: #00ff41;
    border: tall #007a1f;
    margin-bottom: 1;
}
Input:focus { border: tall #00ff41; }

Button {
    background: #007a1f;
    color: #0d0d0d;
    border: none;
    text-style: bold;
    width: 100%;
    height: 1;
}
Button:hover { background: #00ff41; }
Button:focus { background: #00ff41; }

Footer { background: #007a1f; color: #0d0d0d; }
Footer > .footer--key { background: #0d0d0d; color: #00ff41; }
"""


class VerticalThrustBar(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._thrust = 0
        self._min = 0
        self._max = 0xFFFF

    def update_thrust(self, thrust: int, min_t: int, max_t: int) -> None:
        self._thrust = thrust
        self._min = min_t
        self._max = max_t
        self.refresh()

    def render(self) -> str:
        ratio = (self._thrust - self._min) / max(self._max - self._min, 1)
        pct = int(ratio * 100)
        h = max(self.size.height - 2, 1)
        filled = int(h * ratio)
        w = 5
        lines = []
        for i in range(h):
            row_from_bottom = h - 1 - i
            lines.append("█" * w if row_from_bottom < filled else "░" * w)
        lines.append(f"{pct:3d}% ")
        return "\n".join(lines)


class URIScreen(Screen):
    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Static(BANNER, id="banner")
            with Center():
                yield Static("[ crazyflie swarm controller ]", id="subtitle")
            with Center():
                with Vertical(id="uri-container"):
                    yield Label("> drone uri:", id="uri-label")
                    yield Input(placeholder="radio://0/80/2M/E7E7E7E7E7", id="uri-input")
                    yield Button("[ connect ]", id="connect-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        uri = self.query_one("#uri-input", Input).value.strip()
        if uri:
            self.app.push_screen(ControlScreen(uri=uri))
        else:
            self.app.notify("URI cannot be empty", severity="error")


class DronePositionMap(Static):
    _RANGE = 2.0  # metres shown from centre to edge

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._x = 0.0
        self._y = 0.0
        self._z = 0.0

    def update_position(self, x: float, y: float, z: float) -> None:
        self._x = x
        self._y = y
        self._z = z
        self.refresh()

    def render(self) -> str:
        w = max(self.size.width - 2, 10)
        h = max(self.size.height - 3, 5)

        # inner area inside the drawn border
        inner_w = w - 2
        inner_h = h - 2

        # map world coords → inner cell
        cx = int((self._x / self._RANGE + 1) / 2 * (inner_w - 1))
        cy = int((1 - (self._y / self._RANGE + 1) / 2) * (inner_h - 1))
        cx = max(0, min(inner_w - 1, cx))
        cy = max(0, min(inner_h - 1, cy))

        mid_x = inner_w // 2
        mid_y = inner_h // 2

        # build inner grid (spaces only, with drone and origin markers)
        grid = [[" "] * inner_w for _ in range(inner_h)]
        grid[mid_y][mid_x] = "+"
        grid[cy][cx] = "◆"

        # draw border around grid
        top    = "+" + "-" * inner_w + "+"
        bottom = "+" + "-" * inner_w + "+"
        lines  = [top]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append(bottom)
        lines.append(f" X:{self._x:+.3f}  Y:{self._y:+.3f}  Z:{self._z:+.3f} m")
        return "\n".join(lines)


class ControlScreen(Screen):
    BINDINGS = [
        Binding("up", "increase_thrust", "thrust+", priority=True),
        Binding("down", "decrease_thrust", "thrust-", priority=True),
        Binding("w", "go_forward", "forward", priority=True),
        Binding("s", "go_backward", "backward", priority=True),
        Binding("a", "go_left", "left", priority=True),
        Binding("d", "go_right", "right", priority=True),
        Binding("escape", "go_back", "disconnect"),
    ]

    def __init__(self, uri: str, **kwargs):
        super().__init__(**kwargs)
        self.uri = uri

    def compose(self) -> ComposeResult:
        yield Static("Bitzraze Drone Control TUI", id="title-bar")
        with Horizontal(id="main-area"):
            with Horizontal(id="left-panel"):
                yield VerticalThrustBar(id="thrust-bar")
                with Vertical(id="data-col"):
                    with Vertical(classes="data-box"):
                        yield Static("POSITION (m)", classes="table-title")
                        yield DataTable(id="pos-table", show_cursor=False)
                    with Vertical(classes="data-box"):
                        yield Static("VELOCITY (m/s)", classes="table-title")
                        yield DataTable(id="vel-table", show_cursor=False)
            with Vertical(id="right-panel"):
                yield Static("DRONE MAP", id="map-title")
                yield DronePositionMap(id="pos-map")
        yield Static(f"DRONE URI:  {self.uri}", id="uri-bar")
        yield Footer()

    def on_mount(self) -> None:
        pos = self.query_one("#pos-table", DataTable)
        pos.add_columns("X", "Y", "Z")
        pos.add_row("0.000", "0.000", "0.000", key="pos")

        vel = self.query_one("#vel-table", DataTable)
        vel.add_columns("X", "Y", "Z")
        vel.add_row("0.000", "0.000", "0.000", key="vel")

    def update_thrust(self, thrust: int, min_t: int, max_t: int) -> None:
        self.query_one("#thrust-bar", VerticalThrustBar).update_thrust(thrust, min_t, max_t)

    def update_position(self, x: float, y: float, z: float) -> None:
        t = self.query_one("#pos-table", DataTable)
        t.update_cell("pos", "X", f"{x:.3f}")
        t.update_cell("pos", "Y", f"{y:.3f}")
        t.update_cell("pos", "Z", f"{z:.3f}")
        self.query_one("#pos-map", DronePositionMap).update_position(x, y, z)

    def update_velocity(self, x: float, y: float, z: float) -> None:
        t = self.query_one("#vel-table", DataTable)
        t.update_cell("vel", "X", f"{x:.3f}")
        t.update_cell("vel", "Y", f"{y:.3f}")
        t.update_cell("vel", "Z", f"{z:.3f}")

    def action_increase_thrust(self) -> None:
        self.app.increase_thrust()

    def action_decrease_thrust(self) -> None:
        self.app.decrease_thrust()

    def action_go_back(self) -> None:
        self.app.pop_screen()


class DroneControlTUI(App):
    CSS = CSS

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._slave: "TUISlave | None" = None

    def on_mount(self) -> None:
        self.push_screen(URIScreen())

    def update_thrust(self, thrust: int, min_t: int, max_t: int) -> None:
        screen = self.screen
        if isinstance(screen, ControlScreen):
            screen.update_thrust(thrust, min_t, max_t)

    def update_position(self, x: float, y: float, z: float) -> None:
        screen = self.screen
        if isinstance(screen, ControlScreen):
            screen.update_position(x, y, z)

    def update_velocity(self, x: float, y: float, z: float) -> None:
        screen = self.screen
        if isinstance(screen, ControlScreen):
            screen.update_velocity(x, y, z)

    def increase_thrust(self) -> None:
        if self._slave:
            self._slave.send_event(
                data={},
                receiver="CONTROLLER",
                event_type=EventType.INCREASE_THRUST,
            )

    def decrease_thrust(self) -> None:
        if self._slave:
            self._slave.send_event(
                data={},
                receiver="CONTROLLER",
                event_type=EventType.DECREASE_THRUST,
            )


class TUISlave(Slave):
    SLAVE_NAME = "TUI"
    _POLL_INTERVAL = 0.05

    def __init__(self, master, app: DroneControlTUI):
        self._app = app
        app._slave = self
        super().__init__(master=master, slave_name=self.SLAVE_NAME)

    def run(self) -> None:
        while True:
            result = self.read_event()
            if result is not None and self._app.is_running:
                event_type, data = result
                if event_type == EventType.INCREASE_THRUST or event_type == EventType.DECREASE_THRUST:
                    self._app.call_from_thread(
                        self._app.update_thrust,
                        data["thrust"], data["min"], data["max"],
                    )
                elif event_type == EventType.POSITION_UPDATE:
                    self._app.call_from_thread(
                        self._app.update_position,
                        data["x"], data["y"], data["z"],
                    )
                    self._app.call_from_thread(
                        self._app.update_velocity,
                        data["vx"], data["vy"], data["vz"],
                    )
            time.sleep(self._POLL_INTERVAL)
