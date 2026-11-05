Some very simple code to play with the Kinova Gen3 arm in python and ROS2.

The kinova_get_node node encapsulates the arm. The kinova_gen3_tester node tests it.

To play a sequence saved on the robot (the default sequence name is `test`):

```sh
cd manual
python run_sequence.py
```

Use `python run_sequence.py --list` to see the saved sequence names. Use
`python run_sequence.py "another name"` to select a different sequence, or
pass `--ip`, `--username`, and `--password` if the robot does not use the
defaults.


## Tic tac toe

From the repository directory, try the complete game without hardware or the Kortex SDK:

```sh
python manual/tic_tac_toe.py --simulate
```

For the robot, install Kinova's official Kortex Python SDK in your Python environment, then run:

```sh
python manual/tic_tac_toe.py --ip 192.168.1.10
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

Answer `yes` to play and confirm the workspace is clear. The arm runs `getMarker`, then `drawBoard`. Enter a box such as `11` for the robot's first X. After the movement finishes, draw your own mark and answer whether the round is over. Answer `no` to select the robot's next box, or `yes` when someone wins or the game is a draw. You can also enter `done` at a box prompt. Confirm the workspace is clear for cleanup: `markerDown`, `eraserUp`, `eraseBoard`, `eraserDown`. The program then asks whether to play again; `no` exits.

The operator chooses every robot move and judges the result. The program rejects invalid coordinates and repeated robot moves, but cannot see the human's marks, so choose an empty box. There is no camera, automatic winner detection, or opponent AI.

Keep the E-stop available during robot operation. A failed or interrupted movement stops the program without attempting further cleanup; inspect and restore the robot/tools before restarting. Sessions are reopened for each movement so time spent on human turns does not leave an expired connection. `--timeout` sets the movement timeout in seconds (default 300). `--username` and `--password` override the existing connection defaults.

Run the hardware-independent tests with:

```sh
python -m unittest discover -s tests -v
```

Hardware execution requires SDK installation and network access to the arm. Simulation and tests do not validate taught trajectories or physical robot behavior.
