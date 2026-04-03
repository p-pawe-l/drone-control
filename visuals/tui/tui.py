import time

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, Footer, DataTable
from textual.containers import Center, Grid, Middle, Vertical, Horizontal
from textual.binding import Binding

from master_slave_com.slave import Slave
from master_slave_com.event import EventType
from visuals.tui.drone import DroneEntity, DroneRole


BANNER = """\
  ____                        ____            _             _
 |  _ \\ _ __ ___  _ __   ___ / ___|___  _ __ | |_ _ __ ___ | |
 | | | | '__/ _ \\| '_ \\ / _ \\ |   / _ \\| '_ \\| __| '__/ _ \\| |
 | |_| | | | (_) | | | |  __/ |__| (_) | | | | |_| | | (_) | |
 |____/|_|  \\___/|_| |_|\\___|\\____\\___/|_| |_|\\__|_|  \\___/|_|\
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
        ratio = max(0.0, min(1.0, (self._thrust - self._min) / max(self._max - self._min, 1)))
        pct = int(ratio * 100)

        h = max(self.size.height - 1, 1)
        w = max(self.size.width, 1)
        filled = int(h * ratio)

        gradient_stops = [
            (0x7D, 0xCF, 0xFF),  
            (0x7A, 0xA2, 0xF7),  
            (0xBB, 0x9A, 0xF7),  
            (0xE0, 0xAF, 0x68),  
        ]

        def lerp(a: int, b: int, t: float) -> int:
            return int(a + (b - a) * t)

        def gradient_color(level: float) -> str:
            level = max(0.0, min(1.0, level))
            span = len(gradient_stops) - 1
            idx = min(int(level * span), span - 1)
            local_t = (level * span) - idx
            c1 = gradient_stops[idx]
            c2 = gradient_stops[idx + 1]
            r = lerp(c1[0], c2[0], local_t)
            g = lerp(c1[1], c2[1], local_t)
            b = lerp(c1[2], c2[2], local_t)
            return f"#{r:02x}{g:02x}{b:02x}"

        lines = []
        for i in range(h):
            row_from_bottom = h - 1 - i
            row_level = row_from_bottom / max(h - 1, 1)
            if row_from_bottom < filled:
                color = gradient_color(row_level)
                lines.append(f"[{color}]{'█' * w}[/]")
            else:
                lines.append(f"[#3b4261]{'·' * w}[/]")

        pct_color = gradient_color(ratio)
        lines.append(f"[{pct_color}]{f'{pct:>3d}%'.center(w)}[/]")
        return "\n".join(lines)


class HorizontalBatteryBar(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._battery_pct = 0

    def update_battery(self, battery_pct: int) -> None:
        self._battery_pct = max(0, min(100, int(battery_pct)))
        self.refresh()

    def render(self) -> str:
        ratio = self._battery_pct / 100.0
        bar_w = max(self.size.width - 4, 10)
        filled = int(bar_w * ratio)

        if self._battery_pct >= 70:
            active_color = "#9ece6a"
            state = "OK"
        elif self._battery_pct >= 35:
            active_color = "#e0af68"
            state = "MID"
        else:
            active_color = "#f7768e"
            state = "LOW"

        filled_part = "█" * filled
        empty_part = "·" * (bar_w - filled)
        lines = [
            "BATTERY",
            f"[{active_color}]{filled_part}[/][#3b4261]{empty_part}[/]",
            f"[{active_color}]{self._battery_pct:>3d}%[/]  [{active_color}]{state}[/]",
        ]
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
                    yield Label("> swarm server ip:", id="ip-label")
                    yield Input(placeholder="192.168.0.1", id="ip-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def _submit(self) -> None:
        uri = self.query_one("#uri-input", Input).value.strip()
        ip_addr = self.query_one("#ip-input", Input).value.strip()
        if uri:
            screen = ControlScreen(uri=uri, ip_addr=ip_addr)
            screen.register_entity(DroneEntity(
                uri=uri, name="QUEEN", role=DroneRole.MOTHER,
                thrust=16000, max_thrust=0xFFFF, min_thrust=0,
                battery_level=85, is_connected=True,
            ))
            screen.register_entity(DroneEntity(
                uri="radio://0/80/2M/E7E7E7E701", name="KNIGHT-01", role=DroneRole.CHILD,
                thrust=14000, max_thrust=0xFFFF, min_thrust=0,
                battery_level=72, is_connected=True,
            ))
            screen.register_entity(DroneEntity(
                uri="radio://0/80/2M/E7E7E7E702", name="KNIGHT-02", role=DroneRole.CHILD,
                thrust=15000, max_thrust=0xFFFF, min_thrust=0,
                battery_level=63, is_connected=True,
            ))
            self.app.push_screen(screen)
        else:
            self.app.notify("URI cannot be empty", severity="error")


class DronePositionMap(Static):
    _RANGE = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._drones: dict[str, tuple[float, float, float, DroneRole]] = {}

    def set_entities(self, entities: list[DroneEntity]) -> None:
        for e in entities:
            self._drones[e.name] = (0.0, 0.0, 0.0, e.role)
        self.refresh()

    def update_position(self, x: float, y: float, z: float, name: str | None = None) -> None:
        if name and name in self._drones:
            _, _, _, role = self._drones[name]
            self._drones[name] = (x, y, z, role)
        elif self._drones:
            first = next(iter(self._drones))
            _, _, _, role = self._drones[first]
            self._drones[first] = (x, y, z, role)
        self.refresh()

    def render(self) -> str:
        from rich.text import Text

        w = max(self.size.width - 2, 10)
        h = max(self.size.height - 3, 5)

        inner_w = w - 2
        inner_h = h - 2

        mid_x = inner_w // 2
        mid_y = inner_h // 2

        grid: list[list[tuple[str, str | None]]] = [
            [(" ", None)] * inner_w for _ in range(inner_h)
        ]
        grid[mid_y][mid_x] = ("+", None)

        for name, (dx, dy, dz, role) in self._drones.items():
            cx = int((dx / self._RANGE + 1) / 2 * (inner_w - 1))
            cy = int((1 - (dy / self._RANGE + 1) / 2) * (inner_h - 1))
            cx = max(0, min(inner_w - 1, cx))
            cy = max(0, min(inner_h - 1, cy))
            color = "#e0af68" if role == DroneRole.MOTHER else "#737aa2"
            grid[cy][cx] = ("◆", color)
            if cx > 0:
                grid[cy][cx - 1] = ("◇", color)
            if cx < inner_w - 1:
                grid[cy][cx + 1] = ("◇", color)
            if cy > 0:
                grid[cy - 1][cx] = ("◇", color)
            if cy < inner_h - 1:
                grid[cy + 1][cx] = ("◇", color)

        top = "┌" + "─" * inner_w + "┐"
        bottom = "└" + "─" * inner_w + "┘"
        lines = [top]
        for row in grid:
            row_str = "│"
            for char, color in row:
                if color:
                    row_str += f"[{color}]{char}[/]"
                else:
                    row_str += char
            row_str += "│"
            lines.append(row_str)
        lines.append(bottom)

        if self._drones:
            first_name = next(iter(self._drones))
            x, y, z, _ = self._drones[first_name]
            lines.append(f" X:{x:+.3f}  Y:{y:+.3f}  Z:{z:+.3f} m")
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

    def __init__(self, uri: str, ip_addr: str, **kwargs):
        super().__init__(**kwargs)
        self.uri = uri
        self.ip_addr = ip_addr
        self.entities: list[DroneEntity] = []
        self._thrust_pct = 0
        self._battery_pct = 0
        self._mounted = False

    def register_entity(self, entity: DroneEntity) -> None:
        if entity not in self.entities:
            self.entities.append(entity)
            self._battery_pct = max(0, min(100, int(entity.battery_level)))
            if self.is_mounted:
                self.query_one("#status-drone-name", Static).update(f"DRONE NAME: {entity.name}")
                self.query_one("#battery-bar", HorizontalBatteryBar).update_battery(self._battery_pct)

    def compose(self) -> ComposeResult:
        yield Static("Bitzraze Drone Control TUI", id="title-bar")
        with Horizontal(id="main-area"):
            with Horizontal(id="left-panel"):
                yield VerticalThrustBar(id="thrust-bar")

                with Vertical(id="data-col"):
                    with Horizontal(id="motion-row"):
                        with Vertical(classes="data-box motion-box"):
                            yield Static("POSITION (m)", classes="table-title")
                            yield DataTable(id="pos-table", show_cursor=False)
                        with Vertical(classes="data-box motion-box"):
                            yield Static("VELOCITY (m/s)", classes="table-title")
                            yield DataTable(id="vel-table", show_cursor=False)

                    with Horizontal(id="mid-gap-row"):
                        yield HorizontalBatteryBar(id="battery-bar", classes="battery-slot")
                        yield Static("", id="mid-gap-spacer")

                    with Vertical(id="swarm-entities"):
                        with Vertical(classes="swarm-title-box"):
                            yield Static("SWARM ENTITIES", classes="swarm-section-title")

                        with Grid(id="drone-grid"):
                            for i, e in enumerate(self.entities):
                                role_cls = "drone-mother" if e.role == DroneRole.MOTHER else "drone-child"
                                icon = "◆ ♛ ◆" if e.role == DroneRole.MOTHER else "◇ ⚔ ◇"
                                box = Vertical(
                                    classes=f"drone-box {role_cls}",
                                    id=f"drone-box-{i}",
                                )
                                box.border_title = f" {icon} "
                                with box:
                                    yield Static(e.name, classes="drone-box-name")
                        
            with Vertical(id="right-panel"):
                yield Static("DRONE MAP", id="map-title")
                yield DronePositionMap(id="pos-map")
        drone_name = self.entities[0].name if self.entities else "N/A"
        with Horizontal(id="uri-bar"):
            yield Static(f"DRONE URI: {self.uri}", classes="status-part", id="status-uri")
            yield Static(f"SERVER IP: {self.ip_addr}", classes="status-part", id="status-ip")
            yield Static(f"DRONE NAME: {drone_name}", classes="status-part", id="status-drone-name")
        yield Footer()

    def on_mount(self) -> None:
        pos = self.query_one("#pos-table", DataTable)
        self._pos_cx, self._pos_cy, self._pos_cz = pos.add_columns("X", "Y", "Z")
        pos.add_row("0.000", "0.000", "0.000", key="pos")

        vel = self.query_one("#vel-table", DataTable)
        self._vel_cx, self._vel_cy, self._vel_cz = vel.add_columns("X", "Y", "Z")
        vel.add_row("0.000", "0.000", "0.000", key="vel")

        self.query_one("#battery-bar", HorizontalBatteryBar).update_battery(self._battery_pct)
        self.query_one("#pos-map", DronePositionMap).set_entities(self.entities)
        self._mounted = True

    def update_thrust(self, thrust: int, min_t: int, max_t: int) -> None:
        if not self._mounted:
            return
        self.query_one("#thrust-bar", VerticalThrustBar).update_thrust(thrust, min_t, max_t)
        ratio = (thrust - min_t) / max(max_t - min_t, 1)
        self._thrust_pct = max(0, min(100, int(ratio * 100)))

    def update_position(self, x: float, y: float, z: float) -> None:
        if not self._mounted:
            return
        t = self.query_one("#pos-table", DataTable)
        t.update_cell("pos", self._pos_cx, f"{x:.3f}")
        t.update_cell("pos", self._pos_cy, f"{y:.3f}")
        t.update_cell("pos", self._pos_cz, f"{z:.3f}")
        self.query_one("#pos-map", DronePositionMap).update_position(x, y, z)

    def update_velocity(self, x: float, y: float, z: float) -> None:
        if not self._mounted:
            return
        t = self.query_one("#vel-table", DataTable)
        t.update_cell("vel", self._vel_cx, f"{x:.3f}")
        t.update_cell("vel", self._vel_cy, f"{y:.3f}")
        t.update_cell("vel", self._vel_cz, f"{z:.3f}")

    def action_increase_thrust(self) -> None:
        self.app.increase_thrust()

    def action_decrease_thrust(self) -> None:
        self.app.decrease_thrust()

    def action_go_back(self) -> None:
        self.app.pop_screen()


class DroneControlTUI(App):
    CSS_PATH = "design.css"

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

    def _dispatch(self, event_type, data) -> None:
        screen = self._app.screen
        if not isinstance(screen, ControlScreen) or not screen._mounted:
            return
        if event_type == EventType.INCREASE_THRUST or event_type == EventType.DECREASE_THRUST:
            screen.update_thrust(data["thrust"], data["min"], data["max"])
        elif event_type == EventType.POSITION_UPDATE:
            screen.update_position(data["x"], data["y"], data["z"])
            screen.update_velocity(data["vx"], data["vy"], data["vz"])

    def run(self) -> None:
        while True:
            while True:
                result = self.read_event()
                if result is None:
                    break
                if self._app.is_running:
                    event_type, data = result
                    try:
                        self._app.call_from_thread(self._dispatch, event_type, data)
                    except Exception:
                        pass
            time.sleep(self._POLL_INTERVAL)
