"""Run a sequence saved on a Kinova Gen3 through the Kortex Python API."""

import argparse
import sys
import threading

from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from kortex_api.autogen.messages import Base_pb2

from utilities import DeviceConnection


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find and play a sequence saved on a Kinova Gen3."
    )
    parser.add_argument("sequence", nargs="?", default="test", help="sequence name")
    parser.add_argument("--ip", default="192.168.1.10", help="robot IP address")
    parser.add_argument("-u", "--username", default="admin")
    parser.add_argument("-p", "--password", default="admin")
    parser.add_argument(
        "--timeout", type=float, default=300.0, help="maximum run time in seconds"
    )
    parser.add_argument("--list", action="store_true", help="list sequences and exit")
    parser.add_argument("-y", "--yes", action="store_true", help="skip safety prompt")
    return parser.parse_args()

     
def sequence_event_name(notification):
    """Return the sequence event enum name without depending on its field name."""
    for field, value in notification.ListFields():
        if field.enum_type is not None:
            enum_value = field.enum_type.values_by_number.get(value)
            if enum_value is not None:
                return enum_value.name
    return "UNKNOWN_SEQUENCE_EVENT"


def run_sequence(base, sequence, timeout):
    finished = threading.Event()
    result = {"event": None}

    def on_sequence_notification(notification):
        event_name = sequence_event_name(notification)
        print("Sequence event: {}".format(event_name))

        # Kortex versions use slightly different enum prefixes.  Matching the
        # meaningful suffix keeps this compatible with those versions.
        if "COMPLETED" in event_name or "ABORTED" in event_name:
            result["event"] = event_name
            finished.set()

    notification_handle = base.OnNotificationSequenceInfoTopic(
        on_sequence_notification, Base_pb2.NotificationOptions()
    )
    try:
        print("Playing sequence {!r} ...".format(sequence.name))
        base.PlaySequence(sequence.handle)

        try:
            if not finished.wait(timeout):
                print("Timed out after {} seconds; stopping the sequence.".format(timeout))
                base.StopSequence()
                return False
        except KeyboardInterrupt:
            print("\nStopping the sequence ...", file=sys.stderr)
            base.StopSequence()
            raise

        if "ABORTED" in result["event"]:
            print("Sequence was aborted by the robot.")
            return False

        print("Sequence completed successfully.")
        return True
    finally:
        base.Unsubscribe(notification_handle)


def main():
    args = parse_args()

    # Ask before opening the robot session so it cannot time out while waiting
    # for the operator to clear the workspace.
    if not args.list and not args.yes:
        print("WARNING: the robot arm is about to move.")
        answer = input("Clear the workspace, keep the E-stop ready, then type YES: ")
        if answer.strip() != "YES":
            print("Cancelled; the robot was not moved.")
            return 1

    try:
        with DeviceConnection.createTcpConnection(args) as router:
            base = BaseClient(router)
            sequences = list(base.ReadAllSequences().sequence_list)

            if args.list:
                if not sequences:
                    print("No saved sequences were found on the robot.")
                else:
                    print("Saved sequences:")
                    for sequence in sequences:
                        print("  - {}".format(sequence.name))
                return 0

            matches = [s for s in sequences if s.name.casefold() == args.sequence.casefold()]
            if not matches:
                available = ", ".join(repr(s.name) for s in sequences) or "none"
                print(
                    "Sequence {!r} was not found. Available sequences: {}".format(
                        args.sequence, available
                    ),
                    file=sys.stderr,
                )
                return 2

            if len(matches) > 1:
                print(
                    "More than one sequence is named {!r}; refusing to guess.".format(
                        args.sequence
                    ),
                    file=sys.stderr,
                )
                return 2

            return 0 if run_sequence(base, matches[0], args.timeout) else 1
    except KeyboardInterrupt:
        print("\nInterrupted. Use the robot E-stop if motion does not stop.", file=sys.stderr)
        return 130
    except Exception as error:
        print("Could not run the sequence: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
