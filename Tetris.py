
# Tetris in the Windows Terminal (VS Code friendly)
# No external libraries. Uses msvcrt for input and ASCII for rendering.
# Author: M365 Copilot
#
# Controls:
#   A / Left Arrow  = Move left
#   D / Right Arrow = Move right
#   S / Down Arrow  = Soft drop (+1 per cell)
#   W / Up Arrow    = Rotate clockwise
#   SPACE           = Hard drop (+2 per cell)
#   P               = Pause/Resume
#   Q               = Quit
#
# Notes:
# - This version uses a simple rotation + basic wall-kick (try offsets).
# - Scoring: line clears (1:100, 2:300, 3:500, 4:800) * (level+1),
#            soft drop +1 per cell, hard drop +2 per cell.
# - Level increases every 10 cleared lines; gravity speeds up each level.
#
# Windows only (uses msvcrt). For macOS/Linux, replace input with curses.

import msvcrt
import time
import os
import random

WIDTH = 10
HEIGHT = 20

# 7-bag shapes, defined as rotation states with block offsets in a 4x4 bounding box.
# Coordinates are (x, y) offsets relative to the piece's top-left (x, y).
SHAPES = {
    'I': [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    'O': [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    'T': [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

# Characters for each shape (keep ASCII simple)
TILE_CHAR = {
    'I': 'I',
    'O': 'O',
    'T': 'T',
    'S': 'S',
    'Z': 'Z',
    'J': 'J',
    'L': 'L',
}

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


def new_bag():
    bag = list(SHAPES.keys())
    random.shuffle(bag)
    return bag


class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.rot = 0
        # Start near top center. Use 4x4 box anchor.
        self.x = WIDTH // 2 - 2
        self.y = -1  # allow spawn above visible grid

    def tiles(self, x=None, y=None, rot=None):
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        if rot is None:
            rot = self.rot
        return [(x + dx, y + dy) for (dx, dy) in SHAPES[self.shape][rot]]


def empty_grid():
    return [[' ' for _ in range(WIDTH)] for __ in range(HEIGHT)]


def collides(grid, piece, x=None, y=None, rot=None):
    for px, py in piece.tiles(x, y, rot):
        # Outside left/right or below bottom is a collision.
        if px < 0 or px >= WIDTH or py >= HEIGHT:
            return True
        # Above the top is ok during spawn; only consider collisions with existing cells if visible.
        if py >= 0 and grid[py][px] != ' ':
            return True
    return False


def try_move(piece, grid, dx, dy):
    nx, ny = piece.x + dx, piece.y + dy
    if not collides(grid, piece, nx, ny, piece.rot):
        piece.x, piece.y = nx, ny
        return True
    return False


def try_rotate(piece, grid):
    new_rot = (piece.rot + 1) % 4
    # Basic wall-kick offsets to try after rotation
    kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
    for kx, ky in kicks:
        nx, ny = piece.x + kx, piece.y + ky
        if not collides(grid, piece, nx, ny, new_rot):
            piece.x, piece.y, piece.rot = nx, ny, new_rot
            return True
    return False


def lock_piece(grid, piece):
    # Place piece blocks into the grid
    for px, py in piece.tiles():
        if py < 0:
            # Locked above top => game over condition
            return False
        grid[py][px] = TILE_CHAR[piece.shape]
    return True


def clear_lines(grid):
    cleared = 0
    new_rows = []
    for y in range(HEIGHT):
        if all(grid[y][x] != ' ' for x in range(WIDTH)):
            cleared += 1
        else:
            new_rows.append(grid[y])
    # Add empty rows at the top
    while len(new_rows) < HEIGHT:
        new_rows.insert(0, [' ' for _ in range(WIDTH)])
    # Copy back
    for y in range(HEIGHT):
        grid[y] = new_rows[y]
    return cleared


def ghost_position(grid, piece):
    # Compute how far the piece would fall
    gx, gy = piece.x, piece.y
    while not collides(grid, piece, gx, gy + 1, piece.rot):
        gy += 1
    return gx, gy


def draw(grid, piece, score, level, lines, next_shape, paused):
    # Create a copy buffer with current piece overlaid
    buffer = [row[:] for row in grid]
    # Draw ghost
    gx, gy = ghost_position(grid, piece)
    for px, py in piece.tiles(gx, gy, piece.rot):
        if 0 <= py < HEIGHT:
            if buffer[py][px] == ' ':
                buffer[py][px] = '.'
    # Draw active piece
    for px, py in piece.tiles():
        if 0 <= py < HEIGHT:
            buffer[py][px] = TILE_CHAR[piece.shape]

    # Render
    os.system('cls')
    print(
        "TETRIS (ASCII) | Score: {}  Level: {}  Lines: {}  Next: {}  {}".format(
            score,
            level,
            lines,
            next_shape if next_shape else '-',
            '[PAUSED]' if paused else ''
        )
    )
    print("+" + "-" * WIDTH + "+")
    for y in range(HEIGHT):
        print("|" + "".join(buffer[y]) + "|")
    print("+" + "-" * WIDTH + "+")
    print("Controls: A/← Left  D/→ Right  S/↓ Soft drop  W/↑ Rotate  SPACE Hard drop  P Pause  Q Quit")


def gravity_interval(level):
    # Faster each level; clamp to minimum
    return max(0.05, 0.80 * (0.85 ** level))


def get_key():
    """Non-blocking key reader. Returns a string key or None."""
    if not msvcrt.kbhit():
        return None
    k = msvcrt.getch()
    # Arrow keys produce a two-byte sequence: b'\xe0' then code
    if k == b'\xe0':
        kk = msvcrt.getch()
        codes = {
            b'H': 'UP',
            b'P': 'DOWN',
            b'K': 'LEFT',
            b'M': 'RIGHT',
        }
        return codes.get(kk, None)
    # Handle space, letters
    if k == b' ':
        return 'SPACE'
    try:
        kc = k.decode().lower()
    except Exception:
        return None
    return kc


def main():
    random.seed()
    grid = empty_grid()
    bag = new_bag()
    next_shape = None

    def take_shape():
        nonlocal bag
        if not bag:
            bag = new_bag()
        return bag.pop()

    # Initialize first piece
    current = Piece(take_shape())
    next_shape = take_shape()

    score = 0
    lines_cleared_total = 0
    level = 0
    paused = False

    last_fall = time.time()

    # Game loop
    while True:
        # Draw
        draw(grid, current, score, level, lines_cleared_total, next_shape, paused)

        # Input
        key = get_key()
        if key:
            if key == 'q':
                break
            if key == 'p':
                paused = not paused
            if paused:
                time.sleep(0.05)
                continue

            if key in ('a', 'left'):
                try_move(current, grid, -1, 0)
            elif key in ('d', 'right'):
                try_move(current, grid, 1, 0)
            elif key in ('s', 'down'):
                moved = try_move(current, grid, 0, 1)
                if moved:
                    score += 1  # soft drop point
            elif key in ('w', 'up'):
                try_rotate(current, grid)
            elif key == 'SPACE':
                # Hard drop
                drop_distance = 0
                while try_move(current, grid, 0, 1):
                    drop_distance += 1
                score += drop_distance * 2  # hard drop points
                # Lock and proceed
                if not lock_piece(grid, current):
                    # Game over
                    draw(grid, current, score, level, lines_cleared_total, next_shape, paused)
                    print("\nGame Over! Final score:", score)
                    break
                # Clear lines
                cleared = clear_lines(grid)
                if cleared > 0:
                    score += LINE_SCORES.get(cleared, 0) * (level + 1)
                    lines_cleared_total += cleared
                    # Level up every 10 lines
                    while lines_cleared_total >= (level + 1) * 10:
                        level += 1
                # New piece
                current = Piece(next_shape)
                next_shape = take_shape()
                # Reset timer
                last_fall = time.time()

        # Gravity
        if not paused and (time.time() - last_fall) >= gravity_interval(level):
            last_fall = time.time()
            if not try_move(current, grid, 0, 1):
                # Lock
                if not lock_piece(grid, current):
                    draw(grid, current, score, level, lines_cleared_total, next_shape, paused)
                    print("\nGame Over! Final score:", score)
                    break
                # Clear lines
                cleared = clear_lines(grid)
                if cleared > 0:
                    score += LINE_SCORES.get(cleared, 0) * (level + 1)
                    lines_cleared_total += cleared
                    while lines_cleared_total >= (level + 1) * 10:
                        level += 1
                # New piece
                current = Piece(next_shape)
                next_shape = take_shape()

        time.sleep(0.01)  # small delay to reduce CPU usage


if __name__ == "__main__":
    main()
