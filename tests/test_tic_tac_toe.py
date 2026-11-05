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

    def test_camera_move_reaches_algorithm(self):
        class Camera:
            def baseline(self, read, write):
                return 'reference'

            def human_move(self, reference, board, read, write):
                self.last_board = board.copy()
                return '11' if board[0] == '' else 'done'
        camera = Camera()
        arm = Arm()
        answers = iter(['yes', 'yes', 'yes', 'yes', 'no'])
        game.play(arm, lambda _: next(answers), lambda _: None, camera=camera)
        self.assertEqual(camera.last_board[0], 'O')
        self.assertNotIn('drawx11', arm.calls)
        self.assertEqual(arm.calls[-4:], ['markerDown', 'eraserUp', 'eraseBoard', 'eraserDown'])

    def test_no_does_not_connect(self):
        self.assertEqual(self.play(['maybe', 'no']), [])

    def test_two_rounds_and_invalid_moves(self):
        answers = ['yes', 'yes', '44', '22', '11', 'yes', '11', 'done', 'yes',
                   'yes', 'yes', 'done', 'yes', 'no']
        calls = self.play(answers)
        self.assertEqual(calls.count('drawx22'), 2)
        self.assertEqual(calls.count('eraserDown'), 2)
        self.assertNotIn('drawx11', calls)
        self.assertEqual(calls.count('validate'), 1)

    def test_wins_and_blocks(self):
        self.assertEqual(game.choose_x(['X', 'X', '', 'O', 'O', '', '', '', '']), '13')
        self.assertEqual(game.choose_x(['O', 'O', '', '', 'X', '', '', '', 'X']), '13')

    def test_all_human_responses_never_lose_or_overlap(self):
        terminals = []
        def visit(board):
            result = game.outcome(board)
            if result:
                terminals.append(result)
                self.assertNotEqual(result, 'O')
                return
            cell = game.choose_x(board)
            i = game.CELLS.index(cell)
            self.assertEqual(board[i], '')
            next_board = list(board)
            next_board[i] = 'X'
            if game.outcome(next_board):
                visit(next_board)
                return
            for j in range(9):
                if not next_board[j]:
                    child = next_board.copy()
                    child[j] = 'O'
                    visit(child)
        visit([''] * 9)
        self.assertGreater(len(terminals), 0)
        self.assertIn('draw', terminals)
        self.assertIn('X', terminals)

    def test_done_cleans_up(self):
        self.assertEqual(self.play(['yes', 'yes', 'done', 'yes', 'no'])[-4:],
                         ['markerDown', 'eraserUp', 'eraseBoard', 'eraserDown'])

    def test_failure_stops_further_motion(self):
        arm = Arm('drawx22')
        with self.assertRaises(RuntimeError):
            self.play(['yes', 'yes', '11'], arm)
        self.assertEqual(arm.calls[-1], 'drawx22')
        self.assertNotIn('eraserUp', arm.calls)

    def test_declining_clearance_does_not_move(self):
        self.assertEqual(self.play(['yes', 'no', 'no']), ['validate'])


if __name__ == '__main__':
    unittest.main()
