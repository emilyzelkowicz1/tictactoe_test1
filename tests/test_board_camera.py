import importlib.util
from pathlib import Path
import unittest

try:
    import cv2
    import numpy as np
except ImportError:
    raise unittest.SkipTest('Install manual/requirements-camera.txt to run vision tests')

spec = importlib.util.spec_from_file_location('camera', Path(__file__).resolve().parents[1] / 'manual/board_camera.py')
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


class VisionTests(unittest.TestCase):
    def blank(self):
        image = np.full((600, 600, 3), 255, np.uint8)
        for n in (200, 400):
            cv2.line(image, (n, 0), (n, 599), (0, 0, 0), 4)
            cv2.line(image, (0, n), (599, n), (0, 0, 0), 4)
        return image

    def mark(self, image, i):
        row, col = divmod(i, 3)
        cv2.circle(image, (col * 200 + 100, row * 200 + 100), 45, (0, 0, 0), 7)

    def test_each_box(self):
        for i, cell in enumerate(camera.CELLS):
            before = self.blank()
            after = before.copy()
            self.mark(after, i)
            self.assertEqual(camera.detect_move(before, after, [''] * 9), cell)

    def test_reject_no_move_multiple_moves_and_occupied(self):
        before = self.blank()
        after = before.copy()
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, after, [''] * 9)
        self.mark(after, 0)
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, after, ['X'] + [''] * 8)
        self.mark(after, 8)
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, after, [''] * 9)

    def test_reject_hand_shadow_and_exposure(self):
        before = self.blank()
        after = before.copy()
        cv2.rectangle(after, (30, 30), (170, 170), (20, 20, 20), -1)
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, after, [''] * 9)
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, np.maximum(before.astype(int) - 50, 0).astype('uint8'), [''] * 9)

    def test_reject_shifted_existing_ink(self):
        before = self.blank()
        self.mark(before, 4)
        after = cv2.warpAffine(before, np.float32([[1, 0, 12], [0, 1, 0]]), (600, 600))
        with self.assertRaises(camera.UncertainMove):
            camera.detect_move(before, after, ['', '', '', '', 'X', '', '', '', ''])

    def test_confirmation_required_and_reference_retained(self):
        reference = self.blank()
        after = reference.copy()
        self.mark(after, 0)
        obj = camera.BoardCamera.__new__(camera.BoardCamera)
        obj.capture = lambda: after
        answers = iter(['', 'no', '', 'yes'])
        self.assertEqual(obj.human_move(reference, [''] * 9, lambda _: next(answers), lambda _: None), '11')

    def test_mild_focus_change_with_new_o(self):
        before = self.blank()
        self.mark(before, 4)
        after = before.copy()
        self.mark(after, 0)
        after = cv2.GaussianBlur(after, (9, 9), 1.8)
        board = ['', '', '', '', 'X', '', '', '', '']
        self.assertEqual(camera.detect_move(before, after, board), '11')

    def test_stable_burst_combines_noise(self):
        image = self.blank()
        rng = np.random.default_rng(42)
        frames = [np.clip(image.astype(int) + rng.integers(-2, 3, image.shape), 0, 255).astype('uint8')
                  for _ in range(7)]
        combined = camera.combine_stable_frames(frames)
        self.assertEqual(combined.shape, image.shape)
        self.assertLess(np.abs(combined.astype(int) - image).mean(), 1)

    def test_unsettled_or_blurry_burst_rejected(self):
        image = self.blank()
        blurred = cv2.GaussianBlur(image, (31, 31), 8)
        for frames in ([image] * 6 + [blurred], [blurred] * 7,
                       [image] * 6 + [np.full_like(image, 180)]):
            with self.assertRaises(camera.UncertainMove):
                camera.combine_stable_frames(frames)

    def test_failed_baseline_retries_before_drawing(self):
        obj = camera.BoardCamera.__new__(camera.BoardCamera)
        attempts = iter([camera.UncertainMove('Still focusing'), self.blank()])
        def capture():
            value = next(attempts)
            if isinstance(value, Exception):
                raise value
            return value
        obj.capture = capture
        messages = []
        reference = obj.baseline(lambda _: '', messages.append)
        self.assertEqual(reference.shape, (600, 600, 3))
        self.assertTrue(any('Do not draw O yet' in m for m in messages))

    def test_invalid_calibration(self):
        with self.assertRaises(ValueError):
            camera.validate_calibration({'corners': [[0, 0]] * 4, 'resolution': [640, 480]})
