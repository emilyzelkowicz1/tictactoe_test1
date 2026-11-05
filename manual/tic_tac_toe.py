"""Operator-directed tic-tac-toe using saved Kinova movements."""

import argparse
from collections import Counter
import math
import sys
import threading

CELLS = tuple(f"{row}{col}" for row in range(1, 4) for col in range(1, 4))
MOVEMENTS = ("getMarker", "drawBoard", *(f"drawx{cell}" for cell in CELLS),
             "markerDown", "eraserUp", "eraseBoard", "eraserDown")


class SimulatedArm:
    def validate(self):
        pass

    def run(self, name):
        print(f"[simulation] {name}")


class KinovaArm:
    """Open a fresh session per movement so human turns cannot expire it."""

    def __init__(self, args):
        self.args = args

    def catalog(self, base):
        from kortex_api.autogen.messages import Base_pb2
        if self.args.kind == "sequence":
            return list(base.ReadAllSequences().sequence_list)
        return list(base.ReadAllActions(Base_pb2.RequestedActionType()).action_list)

    def connect(self):
        from utilities import DeviceConnection
        return DeviceConnection.createTcpConnection(self.args)

    def validate(self):
        from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
        with self.connect() as router:
            counts = Counter(item.name for item in self.catalog(BaseClient(router)))
            invalid = [name for name in MOVEMENTS if counts[name] != 1]
            if invalid:
                raise RuntimeError("Expected exactly one saved movement for: " + ", ".join(invalid))

    def run(self, name):
        from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
        from kortex_api.autogen.messages import Base_pb2
        from run_sequence import run_sequence
        with self.connect() as router:
            base = BaseClient(router)
            matches = [item for item in self.catalog(base) if item.name == name]
            if len(matches) != 1:
                raise RuntimeError(f"Expected exactly one saved movement named {name!r}")
            if self.args.kind == "sequence":
                if not run_sequence(base, matches[0], self.args.timeout):
                    raise RuntimeError(f"Movement {name!r} did not complete")
                return
            done = threading.Event()
            result = []

            def on_notification(notification):
                if notification.action_event in (Base_pb2.ACTION_END, Base_pb2.ACTION_ABORT):
                    result.append(notification.action_event)
                    done.set()

            handle = base.OnNotificationActionTopic(on_notification, Base_pb2.NotificationOptions())
            try:
                print(f"Running {name} ...")
                base.ExecuteActionFromReference(matches[0].handle)
                if not done.wait(self.args.timeout):
                    raise RuntimeError(f"Movement {name!r} timed out")
                if result[0] != Base_pb2.ACTION_END:
                    raise RuntimeError(f"Movement {name!r} aborted")
            except BaseException:
                base.Stop()
                raise
            finally:
                base.Unsubscribe(handle)


def ask_yes_no(prompt, read=input, write=print):
    while True:
        answer = read(prompt).strip().lower()
        if answer in ("yes", "y"):
            return True
        if answer in ("no", "n"):
            return False
        write("Please enter yes or no.")


def play(arm, read=input, write=print):
    """The operator selects every X and declares the result; there is no AI."""
    validated = False
    while ask_yes_no("Do you want to play a round of tic tac toe? (yes/no): ", read, write):
        if not validated:
            arm.validate()
            validated = True
        write("Clear the board area before continuing; the arm will move.")
        if not ask_yes_no("Is the workspace clear and ready? (yes/no): ", read, write):
            continue
        arm.run("getMarker")
        arm.run("drawBoard")
        used = set()
        write("Boxes: 11 12 13 / 21 22 23 / 31 32 33. Enter 'done' to end the round.")
        while True:
            cell = read("Where do you want me to draw X? ").strip().lower()
            if cell == "done":
                break
            if cell not in CELLS:
                write("Enter a row and column from 1 to 3, such as 11 or 23.")
                continue
            if cell in used:
                write("I already drew X there. Choose an empty box.")
                continue
            arm.run(f"drawx{cell}")
            used.add(cell)
            write("Once the arm has stopped, draw your move. Check whether anyone won or it is a draw.")
            if ask_yes_no("Is the round over? (yes/no): ", read, write):
                break
            write("Choose a box that does not contain your mark.")
        # Do not move back into the board area until the human is clear.
        while not ask_yes_no("Ready to put the marker away and erase? Clear the workspace (yes/no): ", read, write):
            write("Waiting for the workspace to be clear.")
        for name in ("markerDown", "eraserUp", "eraseBoard", "eraserDown"):
            arm.run(name)
    write("Goodbye!")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", action="store_true", help="print movements without connecting to a robot")
    parser.add_argument("--kind", choices=("sequence", "action"), default="sequence",
                        help="type of saved robot movement (default: sequence)")
    parser.add_argument("--ip", default="192.168.1.10")
    parser.add_argument("-u", "--username", default="admin")
    parser.add_argument("-p", "--password", default="admin")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    try:
        play(SimulatedArm() if args.simulate else KinovaArm(args))
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. No automatic cleanup will run; check the arm before restarting.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Stopped: {error}. Check the arm before restarting; no further movements will run.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
