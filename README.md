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


