import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('game', Path(__file__).resolve().parents[1] / 'manual/tic_tac_toe.py')
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)


class Arm:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def validate(self):
        self.calls.append('validate')

    def run(self, name):
        self.calls.append(name)
        if name == self.fail:
            raise RuntimeError('robot failed')


class GameTests(unittest.TestCase):
    def play(self, answers, arm=None):
        arm = arm or Arm()
        answers = iter(answers)
        game.play(arm, lambda _: next(answers), lambda _: None)
        return arm.calls

    def test_no_does_not_connect(self):
        self.assertEqual(self.play(['maybe', 'no']), [])

    def test_two_rounds_and_invalid_moves(self):
        answers = ['yes', 'yes', '44', '11', 'no', '11', '12', 'yes', 'no', 'yes',
                   'yes', 'yes', '33', 'yes', 'yes', 'no']
        cleanup = ['markerDown', 'eraserUp', 'eraseBoard', 'eraserDown']
        self.assertEqual(self.play(answers), ['validate', 'getMarker', 'drawBoard', 'drawx11', 'drawx12'] + cleanup +
                         ['getMarker', 'drawBoard', 'drawx33'] + cleanup)

    def test_done_cleans_up(self):
        self.assertEqual(self.play(['yes', 'yes', 'done', 'yes', 'no'])[-4:],
                         ['markerDown', 'eraserUp', 'eraseBoard', 'eraserDown'])

    def test_failure_stops_further_motion(self):
        arm = Arm('drawx11')
        with self.assertRaises(RuntimeError):
            self.play(['yes', 'yes', '11'], arm)
        self.assertEqual(arm.calls[-1], 'drawx11')
        self.assertNotIn('eraserUp', arm.calls)

    def test_declining_clearance_does_not_move(self):
        self.assertEqual(self.play(['yes', 'no', 'no']), ['validate'])


if __name__ == '__main__':
    unittest.main()
