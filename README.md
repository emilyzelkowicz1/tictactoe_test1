Some very simple code to play with the Kinova Gen3 arm in python3 and ROS2.

The kinova_get_node node encapsulates the arm. The kinova_gen3_tester node tests it.

To play a sequence saved on the robot (the default sequence name is `test`):

```sh
cd manual
python3 run_sequence.py
```

Use `python3 run_sequence.py --list` to see the saved sequence names. Use
`python3 run_sequence.py "another name"` to select a different sequence, or
pass `--ip`, `--username`, and `--password` if the robot does not use the
defaults.


## Tic tac toe

From the repository directory, try the complete game without hardware or the Kortex SDK:

```sh
python3 manual/tic_tac_toe.py --simulate
```

For the robot, install Kinova's official Kortex Python SDK in your Python environment, then run:

```sh
python3 manual/tic_tac_toe.py --ip 192.168.1.10
```

The default uses saved **sequences**. If you create saved **actions** instead, add `--kind action`. All movements must use the selected type and the exact case-sensitive names below. The program checks that every required name exists exactly once before starting a round.

| Saved name | Movement you teach the arm |
| --- | --- |
| `getMarker` | Pick up the marker |
| `drawBoard` | Draw the grid |
| `drawx11`, `drawx12`, `drawx13` | Move to and draw X in each box of row 1 |
| `drawx21`, `drawx22`, `drawx23` | Move to and draw X in each box of row 2 |
| `drawx31`, `drawx32`, `drawx33` | Move to and draw X in each box of row 3 |
| `markerDown` | Put down the marker |
| `eraserUp` | Pick up the eraser |
| `eraseBoard` | Erase the board |
| `eraserDown` | Put down the eraser |

Each `drawxRC` movement must include moving to that box, drawing the X, and withdrawing to a position where the person can take their turn. Teach all movements so they can run in the listed order; a box movement must also work after any other box movement. Start each session with the tools put away and a blank board.

Answer `yes` to play and confirm the workspace is clear. The arm runs `getMarker`, then `drawBoard`, then chooses and draws its first X automatically. X moves first. Once the arm stops, draw your O in an empty box and enter its row and column (for example `11`). Confirm you are clear of the workspace before the next robot move.

The robot uses minimax to choose a winning move when possible and otherwise force a draw against perfect play. It tracks X and O, rejects occupied or invalid boxes, and automatically detects wins and draws. It never selects a box already marked in its recorded board. There is no camera: you must report your actual O position accurately and place only one O per turn. Each `drawxRC` sequence must be calibrated to the matching physical box.

Enter `done` at the O prompt to end early. At the end, confirm the workspace is clear for cleanup: `markerDown`, `eraserUp`, `eraseBoard`, `eraserDown`. The program then asks whether to play again; `no` exits. Each new round starts with an empty recorded board.

Keep the E-stop available during robot operation. A failed or interrupted movement stops the program without attempting further cleanup; inspect and restore the robot/tools before restarting. Sessions are reopened for each movement so time spent on human turns does not leave an expired connection. `--timeout` sets the movement timeout in seconds (default 300). `--username` and `--password` override the existing connection defaults.

Run the hardware-independent tests with:

```sh
python3 -m unittest discover -s tests -v
```

Hardware execution requires SDK installation and network access to the arm. Simulation and tests do not validate taught trajectories or physical robot behavior.

## USB camera on a tripod

A tripod is a mount; a USB camera connected to the computer is required. This supports cameras OpenCV can open, including typical Microsoft USB webcams. It has not been tested with your specific camera or physical arm.

Install camera dependencies on the computer running the game (a virtual environment is recommended):

```sh
python3 -m pip install -r manual/requirements-camera.txt
```

Keep the camera and board fixed with all nine squares visible, even lighting, dark ink on a light board, and no glare. The arm must withdraw completely from the board view after each X. Keep marks inside the squares, away from grid lines. Detection assumes one new O per human turn.

### Calibrate once

Draw a grid manually before calibration. Run this on your desktop with a display:

```sh
python3 manual/board_camera.py --calibrate
```

Click the four **outer corners of the entire nine-square playing area**, in this order: top-left, top-right, bottom-right, bottom-left. These define the rectangle enclosing the whole board, not the four intersections of the interior grid lines. Row 1 is the top row and column 1 is the left column in this selected orientation; it must match the taught robot coordinates. Press Enter to save `board-camera.json`, R to reset clicks, or Escape to cancel. For another USB camera, add `--camera-index 1`. Recalibrate if the camera, board, resolution, or framing changes. Each newly drawn robot grid must occupy the same calibrated position.

### Test camera detection without moving the arm

Start with an empty grid:

```sh
python3 manual/board_camera.py
```

Press Enter to capture a reference **before** drawing O. Draw O, move clear, then press Enter again. Check the detected coordinate and answer yes or no. Repeat with other empty boxes or enter `done`. This command never connects to the robot.

### Play with camera input

Once detection is reliable and the robot movements have been tested:

```sh
python3 manual/tic_tac_toe.py --camera --ip 192.168.1.10
```

Add `--kind action` for saved Actions. Use the same `--camera-index` as calibration if you changed it. The arm chooses and draws X. Before you draw O, the program asks for a reference image. Then draw O, clear the view, and press Enter to photograph your move. Confirm the detected box, then confirm the workspace is clear before the arm moves. Win/draw detection and cleanup work as before. Omitting `--camera` retains typed O coordinates.

The camera detects **new dark ink**, not the shape of an O. Multiple changes, changes in occupied squares, large shadows, and large lighting changes are rejected when detected. These checks cannot guarantee recognition of every obstruction or camera movement: inspect every proposed coordinate before accepting it. Rejected pictures do not change the recorded board or trigger robot movement; retry with a clear view or enter `done` to end the round. Never confirm an incorrect coordinate. No automatic motion is triggered merely by a camera image.

### Autofocus and multi-frame capture

Each reference and move capture now discards frames for one second, then checks a rolling burst of seven frames for consistent sharpness and exposure. It combines a stable burst using the per-pixel median to reduce noise. Capture retries internally for up to six seconds; if focus or the image remains unstable, it asks you to retry. Do not draw O until it prints `Reference captured`.

Comparison tolerates small stroke-edge changes from focus variation (a three-pixel neighborhood in the rectified board image). It still rejects substantial missing ink, changes in occupied boxes, and multiple new marks. These thresholds are tested on synthetic images and may need tuning for your camera. No image averaging can recover detail from a persistently out-of-focus lens. If focus continues hunting, use the camera's supported controls to focus on the board and lock manual focus. Keep checking the proposed coordinate before confirming it.
