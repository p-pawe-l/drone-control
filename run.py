import argparse

from master_slave_com import Master
from control import SwarmDroneController, KeyboardReader
from visuals import DroneControllerGUI, DroneControllerCLI

parser = argparse.ArgumentParser(description="Arguments for the drone control")

if __name__ == '__main__':
    parser.add_argument('--uri', '-u', type=str, required=True, help="URI of the drone to connect to")
    parser.add_argument('--keyboard', '-k', action='store_true', help="Whether to launch the keyboard reader or not")
    parser.add_argument('--gui', '-g', action='store_true', help="Whether to launch the GUI or not")
    parser.add_argument('--cli', '-c', action='store_true', help="Whether to launch the CLI or not")
    
    args = parser.parse_args()
    
    slaves: list = [
        SwarmDroneController(uri=args.uri),
        KeyboardReader() if args.keyboard else None,
        DroneControllerGUI() if args.gui else None,
        DroneControllerCLI() if args.cli else None
    ]
    
    with Master(slaves=slaves) as master:
        pass