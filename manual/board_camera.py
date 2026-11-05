"""Fixed USB-camera board calibration and conservative changed-cell detection.

Detects new dark ink, not the semantic shape of an O. Operator confirmation is
required before accepting a move. Keep camera, board, lighting and arm pose fixed.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

SIZE = 600
CELLS = tuple(f'{r}{c}' for r in range(1, 4) for c in range(1, 4))


class UncertainMove(ValueError):
    pass


def detect_move(before, after, board):
    """Return one newly marked empty cell or reject an ambiguous image pair."""
    if before.shape != after.shape or before.shape[:2] != (SIZE, SIZE):
        raise UncertainMove('Camera image dimensions changed; recalibrate.')
    if len(board) != 9:
        raise ValueError('Expected nine board cells')
    a = cv2.GaussianBlur(cv2.cvtColor(before, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    b = cv2.GaussianBlur(cv2.cvtColor(after, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    delta = a.astype(np.float32) - b.astype(np.float32)
    # Compensate for a small uniform exposure change, but reject large ones.
    exposure = float(np.median(delta))
    if abs(exposure) > 20:
        raise UncertainMove('Lighting changed too much. Restore the lighting and retry.')
    delta -= exposure
    changed = np.abs(delta) > 35
    added = (delta > 35) & (b < 160)
    removed = delta < -35
    candidates = []
    for i, cell in enumerate(CELLS):
        row, col = divmod(i, 3)
        # Ignore grid lines and a narrow border within each square.
        region = np.s_[row * 200 + 20:(row + 1) * 200 - 20,
                       col * 200 + 20:(col + 1) * 200 - 20]
        fraction = float(np.mean(changed[region]))
        ink = float(np.mean(added[region]))
        erased = float(np.mean(removed[region]))
        if erased > .008:
            raise UncertainMove('Existing ink moved or disappeared. Check alignment and occlusion.')
        if fraction > .008:
            if board[i]:
                raise UncertainMove(f'Occupied box {cell} changed. Check the board and camera.')
            if ink < .008 or ink > .22:
                raise UncertainMove('Change is too faint or too large. Clear hands and shadows.')
            candidates.append(cell)
    if len(candidates) != 1:
        raise UncertainMove(f'Expected one changed empty box; detected {len(candidates)}.')
    return candidates[0]


def validate_calibration(data):
    points = np.asarray(data['corners'], dtype=np.float32)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError('Calibration needs four finite corner coordinates')
    width, height = data['resolution']
    if width <= 0 or height <= 0 or np.any(points < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] >= height):
        raise ValueError('Calibration corners must be inside the image')
    if not cv2.isContourConvex(points) or cv2.contourArea(points) < 1000:
        raise ValueError('Corners must form a large convex board in perimeter order')
    return points


class BoardCamera:
    def __init__(self, index=0, calibration=None):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(f'Cannot open camera {index}. Check USB connection and camera permissions.')
        try:
            self.data = json.loads(Path(calibration).read_text()) if calibration else None
            if self.data:
                self.points = validate_calibration(self.data)
        except BaseException:
            self.close()
            raise

    def close(self):
        self.cap.release()

    def frame(self):
        # Drain buffered frames after the operator returns to the terminal.
        for _ in range(8):
            ok, frame = self.cap.read()
            if not ok:
                raise RuntimeError('Camera capture failed. No robot move will be selected.')
        return frame

    def capture(self):
        frame = self.frame()
        height, width = frame.shape[:2]
        if [width, height] != self.data['resolution']:
            raise RuntimeError('Camera resolution changed. Recalibrate before playing.')
        matrix = cv2.getPerspectiveTransform(self.points, np.float32([[0, 0], [599, 0], [599, 599], [0, 599]]))
        return cv2.warpPerspective(frame, matrix, (SIZE, SIZE))

    def baseline(self, read=input, write=print):
        read('Before drawing O, clear the board view and press Enter to capture the reference: ')
        reference = self.capture()
        write('Reference captured. Draw one O now, then move your hand clear.')
        return reference

    def human_move(self, reference, board, read=input, write=print):
        while True:
            if read("After drawing O and moving clear, press Enter to photograph it (or 'done'): ").strip().lower() == 'done':
                return 'done'
            try:
                cell = detect_move(reference, self.capture(), board)
            except UncertainMove as error:
                write(f'No move accepted: {error} Retry the picture, or enter done to end the round.')
                continue
            answer = read(f'Detected O in {cell}. Is that correct? (yes/no): ').strip().lower()
            if answer in ('yes', 'y'):
                return cell
            write('Detection rejected. The reference stays unchanged; clear the view and retry.')


def calibrate(camera, path):
    frame = camera.frame()
    points = []
    title = 'Click: top-left, top-right, bottom-right, bottom-left. Enter=save R=reset Esc=cancel'
    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append([x, y])
    cv2.namedWindow(title)
    cv2.setMouseCallback(title, click)
    try:
        while True:
            display = frame.copy()
            for i, point in enumerate(points):
                cv2.circle(display, tuple(point), 6, (0, 0, 255), -1)
                cv2.putText(display, str(i + 1), tuple(point), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow(title, display)
            key = cv2.waitKey(30) & 0xff
            if key == 27:
                return
            if key in (ord('r'), ord('R')):
                points.clear()
            if key in (10, 13) and len(points) == 4:
                data = {'corners': points, 'resolution': [frame.shape[1], frame.shape[0]]}
                validate_calibration(data)
                Path(path).write_text(json.dumps(data, indent=2) + '\n')
                print(f'Saved calibration to {path}')
                return
    finally:
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera-index', type=int, default=0)
    parser.add_argument('--calibration', default='board-camera.json')
    parser.add_argument('--calibrate', action='store_true')
    args = parser.parse_args()
    camera = BoardCamera(args.camera_index, None if args.calibrate else args.calibration)
    try:
        if args.calibrate:
            calibrate(camera, args.calibration)
        else:
            print('Camera-only test. Start with an empty board. No robot connection is used.')
            board = [''] * 9
            while not all(board):
                reference = camera.baseline()
                cell = camera.human_move(reference, board)
                if cell == 'done':
                    break
                board[CELLS.index(cell)] = 'O'
                print(f'Accepted O: {cell}')
    finally:
        camera.close()


if __name__ == '__main__':
    main()
