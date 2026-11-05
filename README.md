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
