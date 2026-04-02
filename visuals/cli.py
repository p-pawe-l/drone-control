from master_slave_com import Slave

BANNER = r"""
  ____                        ____            _             _
 |  _ \ _ __ ___  _ __   ___ / ___|___  _ __ | |_ _ __ ___ | |
 | | | | '__/ _ \| '_ \ / _ \ |   / _ \| '_ \| __| '__/ _ \| |
 | |_| | | | (_) | | | |  __/ |__| (_) | | | | |_| | | (_) | |
 |____/|_|  \___/|_| |_|\___|\____\___/|_| |_|\__|_|  \___/|_|
"""


class DroneControllerCLI(Slave):
    SLAVE_NAME: str = "CLI"

    def __init__(self, master) -> None:
        super().__init__(master=master, slave_name=self.SLAVE_NAME)

    def _starting_screen(self) -> str:
        print(BANNER)
        print("=" * 65)
        print("  Welcome to Drone Control CLI")
        print("=" * 65)
        print()

        while True:
            uri = input("  Enter drone URI: ").strip()
            if uri:
                return uri
            print("  URI cannot be empty. Please try again.")

    def run(self) -> None:
        uri = self._starting_screen()
        print(f"\n  Connecting to {uri} ...")
        # TODO: hand off URI to controller
