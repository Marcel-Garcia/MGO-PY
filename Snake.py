
# file: snake.py (Windows)
import msvcrt, time, random, os

W, H = 40, 20
snake = [(W//2, H//2)]
dir = (1, 0)
food = (random.randint(1, W-2), random.randint(1, H-2))

def draw():
    os.system('cls')
    grid = [[' ']*W for _ in range(H)]
    for x, y in snake: grid[y][x] = 'O'
    fx, fy = food; grid[fy][fx] = '*'
    print("+" + "-"*(W-2) + "+")
    for row in grid: print("|" + "".join(row[1:-1]) + "|")
    print("+" + "-"*(W-2) + "+")

while True:
    if msvcrt.kbhit():
        k = msvcrt.getch().lower()
        if k == b'w': dir = (0, -1)
        if k == b's': dir = (0,  1)
        if k == b'a': dir = (-1, 0)
        if k == b'd': dir = (1,  0)
        if k == b'q': break
    hx, hy = snake[0]
    nx, ny = hx + dir[0], hy + dir[1]
    snake.insert(0, (nx, ny))
    if (nx, ny) == food:
        food = (random.randint(1, W-2), random.randint(1, H-2))
    else:
        snake.pop()
    if nx <= 0 or nx >= W-1 or ny <= 0 or ny >= H-1 or (nx, ny) in snake[1:]:
        break
    draw(); time.sleep(0.08)
print("Game Over")
