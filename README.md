# Kinova Gen3 robotics project

This repository contains Python tools for controlling a Kinova Gen3 arm through the Kortex API, plus a minimal ROS 2 service wrapper. It is a starting point for the team's robotics project: the current source provides saved-sequence playback and arm/gripper demos, but does not yet implement tic-tac-toe game logic, board perception, or game planning.

## Project layout

| Path | Purpose |
| --- | --- |
| `manual/run_sequence.py` | Run or list sequences already saved on the robot; the normal entry point for sequence playback. |
| `run_sequence.py` | Main-directory copy of the sequence runner, currently identical to the manual copy. It imports `utilities`, so use the manual entry point where that helper is available. |
| `manual/utilities.py` | Connection arguments, Kortex transport, login, and session cleanup. |
| `manual/demo.py` | Direct Python example that homes the arm, operates the gripper, and runs hard-coded joint movements. |
| `kinova_ws/src/kinova_gen3/` | ROS 2 Python package containing the service node, tester, and its connection helper. |
| `kinova_ws/src/kinova_gen3_interfaces/srv/` | Request/response definitions for the seven ROS 2 services. |

There are two control paths:

```text
manual Python script -> Kortex API -> robot
ROS 2 client -> kinova_gen3_node -> Kortex API -> robot
```

The manual scripts do not require ROS 2. The ROS 2 service node must be running before its tester or other service clients can control the arm. Saved-sequence playback is currently only exposed by the manual script, not by a ROS service.

## Environment and connection setup

Run the commands below in an Ubuntu/WSL shell, starting in the repository directory. Adjust the example path for your checkout:

```bash
cd ~/tictactoe_test1
```

You need Python 3 and Kinova's Kortex Python API installed in the Python environment used to run the scripts. Obtain the SDK wheel compatible with the lab robot and Python version from the team's SDK installation or Kinova distribution, then install that actual file:

```bash
python3 -m pip install /path/to/kortex_api-WHEEL-FILENAME.whl
python3 -c "from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient; print('Kortex import OK')"
```

The wheel path above is a placeholder. This repository does not bundle the SDK or pin Python, Kortex, or ROS 2 versions. Use the team's known-working environment; the ROS package metadata does not declare all runtime dependencies.

Connect the computer to the robot's network. The default address is `192.168.1.10`; the connection helpers default to username `admin` and password `admin`. Override these when the lab configuration differs. The current scripts use TCP port `10000`; the helpers also support UDP port `10001`, but the supplied entry points use TCP. When using WSL, connectivity must work from inside WSL as well as from Windows.

## Play a saved sequence

First list what is already stored on the robot. This connects and authenticates but does not request motion:

```bash
cd ~/tictactoe_test1/manual
python3 run_sequence.py --list
```

To play the default sequence named `test`, or another saved sequence:

```bash
python3 run_sequence.py
python3 run_sequence.py "another name"
python3 run_sequence.py "another name" --ip 192.168.1.10 --timeout 600
```

Before playback, the script asks you to clear the workspace, keep the E-stop ready, and type exactly `YES`. This happens before opening the robot session. Any other response cancels playback. Use a sequence whose movements have been checked for the current robot setup.

| Argument | Default | Meaning |
| --- | --- | --- |
| `sequence` | `test` | Saved sequence name; matching is case-insensitive. |
| `--list` | Off | Print available names and exit. |
| `--ip` | `192.168.1.10` | Robot address. |
| `-u`, `--username` | `admin` | Login username. |
| `-p`, `--password` | `admin` | Login password. |
| `--timeout` | `300` | Maximum number of seconds to wait for completion. |
| `-y`, `--yes` | Off | Skip the operator confirmation prompt. |

The runner reads all saved sequences, finds a unique matching name, subscribes to sequence notifications, and calls `PlaySequence`. It prints notification names while waiting. Individual events containing `TASK` are ignored for completion, so finishing one task does not incorrectly finish the entire run. A sequence-level `COMPLETED` event succeeds; a sequence-level `ABORTED` event fails.

On timeout, the runner requests `StopSequence`. Ctrl+C while waiting also requests a stop. It unsubscribes afterward, and the manual connection helper closes the session and disconnects. A software stop request is not a guarantee that motion has stopped; the script directs the operator to use the E-stop if necessary.

Exit codes: `0` = successful completion or listing, `1` = cancellation, timeout, abort, or other failure, `2` = missing or ambiguous sequence name, `130` = keyboard interruption. This script plays existing robot sequences; it does not create or upload them.

## Direct Python demo

`manual/demo.py` demonstrates Kortex calls for the saved `Home` action, gripper commands and feedback, joint motion, and a Cartesian helper. Its main routine homes the arm, closes and opens the gripper, executes multiple hard-coded six-joint poses, pauses before grabbing a block, and continues with more motion. The Cartesian helper is not enabled in the main routine.

This is a hardware motion demo, not an offline test. It starts moving without the sequence runner's `YES` prompt. Review its poses and the six-joint assumption against the actual arm and workspace before running:

```bash
cd ~/tictactoe_test1/manual
python3 demo.py --ip 192.168.1.10
```

## Build and run the ROS 2 interface

Use a ROS 2 installation with `rclpy`, `colcon`, `ament_python`, `ament_cmake`, and ROS interface generation tools available. Kortex must also be importable by the Python interpreter used by ROS. The repository does not specify a tested ROS distribution; replace `YOUR_ROS_DISTRO` below with the team's installed distribution.

```bash
source /opt/ros/YOUR_ROS_DISTRO/setup.bash
cd ~/tictactoe_test1/kinova_ws
colcon build --symlink-install
source install/setup.bash
ros2 run kinova_gen3 kinova_gen3_node --ip 192.168.1.10
```

The executable is `kinova_gen3_node`; its ROS node name is `kinova_gen3_interface`. It creates the services below and connects to the robot. It does not automatically home the arm at startup. Connection arguments use the same `--ip`, `-u`/`--username`, and `-p`/`--password` defaults as the manual scripts.

In a second terminal, source both environments before using a client:

```bash
source /opt/ros/YOUR_ROS_DISTRO/setup.bash
cd ~/tictactoe_test1/kinova_ws
source install/setup.bash
ros2 service list
ros2 service call /get_joints kinova_gen3_interfaces/srv/GetJoints '{}'
ros2 service call /get_tool kinova_gen3_interfaces/srv/GetTool '{}'
ros2 service call /get_gripper kinova_gen3_interfaces/srv/GetGripper '{}'
```

These three calls read state. Services that set a target or call `/home` request physical motion.

### Service reference

Service types below belong to `kinova_gen3_interfaces/srv`.

| Service | Type | Request | Response / behavior |
| --- | --- | --- | --- |
| `/home` | `Status` | Empty | `bool status`; executes the robot's saved `Home` action after selecting single-level servoing. |
| `/get_gripper` | `GetGripper` | Empty | `float32 value`; measured gripper position. |
| `/set_gripper` | `SetGripper` | `float32 value` | `bool status`; sends a position command (demo uses 0 for open and 1 for closed). |
| `/get_joints` | `GetJoints` | Empty | `float32[] joints`; measured joint angles in degrees. |
| `/set_joints` | `SetJoints` | `float32[] joints` | `bool status`; accepts exactly six target angles in degrees. |
| `/get_tool` | `GetTool` | Empty | `x`, `y`, `z` in meters and `theta_x`, `theta_y`, `theta_z` in degrees. |
| `/set_tool` | `SetTool` | The same six `float32` pose fields | `bool status`; sends an absolute target tool pose in the robot's Cartesian convention. |

The tester creates clients for all seven services, waits for them, and runs a scripted demonstration with homing, gripper movements, joint movements, and Cartesian movements. It also pauses before grabbing a block. Like `manual/demo.py`, it starts issuing motion commands without a `YES` prompt once services are available. Only run it after reviewing its hard-coded targets:

```bash
ros2 run kinova_gen3 kinova_gen3_tester
```

### Current implementation limitations

- The demos and `/set_joints` handler assume six joints. They must be adapted before use with a different actuator count; the manual helper only prints a length mismatch and then continues.
- ROS and manual demo action helpers wait up to 20 seconds. Both `ACTION_END` and `ACTION_ABORT` release their wait, so a returned true status does not distinguish successful motion from an abort. Timeout in these helpers does not explicitly stop motion. This differs from the saved-sequence runner.
- `/set_gripper` returns true after sending its command, without waiting for the gripper to reach the target.
- The ROS connection helper deliberately disables context-manager cleanup (`Avoiding exit`) to keep the connection alive after node construction. It lacks explicit session cleanup at shutdown. The manual connection helper does close its session normally.
- Connection options are parsed with ordinary `argparse`; arbitrary ROS-specific arguments are not handled by that parser.
- The existing package tests are lint/style checks, not hardware or motion verification. No simulator, launch file, or complete game controller is included in the current source.

## Troubleshooting and team workflow

| Symptom | Check |
| --- | --- |
| `No module named kortex_api` | Install the matching Kortex SDK in the same interpreter/environment running the script or ROS node. |
| `No module named utilities` | Run `manual/run_sequence.py`, not the main-directory copy by itself. |
| Cannot connect or log in | Confirm power, robot address, network reachability from Ubuntu/WSL, TCP port 10000, and credentials. |
| Sequence not found | Use `--list`; the sequence must already exist on the robot. Duplicate names differing only by case are rejected. |
| Playback times out | Read the robot notifications and check its state; increase `--timeout` only when the sequence legitimately needs longer. |
| ROS package or interface missing | Build `kinova_ws` and source both the ROS installation and workspace overlay in each terminal. |
| Tester keeps waiting for services | Confirm `kinova_gen3_node` is running and both terminals use compatible ROS environments and the same ROS domain. |
| `Home` cannot be found | Check that the robot has a saved joint-angle action named exactly `Home`. |

Start with sequence listing or state reads, then run a reviewed motion routine with the workspace clear. Keep custom ROS clients separate from the hardware wrapper and use the service definitions as their contract. For changes to sequence playback, keep the main and manual copies synchronized while both remain in the repository. Record the lab's working SDK/ROS versions and validated sequences as the project develops.
