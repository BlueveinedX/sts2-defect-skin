# -*- coding: utf-8 -*-
"""补全图集里「被不透明像素包围的透明洞」。

一代的部件是分片装甲，网格采样到的区域内存在透明孔洞 -> 渲染时表现为
「黄色不连续、缺一块」。对静止姿态来说，把内部孔洞填掉即可补全。

安全边界：只填「不与图像边缘连通」的透明像素（即被轮廓包围的洞）；
部件之间的间隙、以及轮廓外的透明区域一律不动，所以不会把方框画出来。
"""
import sys
from collections import deque
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
DEFAULT = HERE / "godot-project/animations/characters/defect/DefectSTS1.png"


def fill(path: Path) -> None:
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    px = im.load()
    # 1) 从四边泛洪，标记「外部」透明像素
    outside = bytearray(W * H)
    dq = deque()
    for x in range(W):
        for y in (0, H - 1):
            if px[x, y][3] == 0 and not outside[y * W + x]:
                outside[y * W + x] = 1; dq.append((x, y))
    for y in range(H):
        for x in (0, W - 1):
            if px[x, y][3] == 0 and not outside[y * W + x]:
                outside[y * W + x] = 1; dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not outside[ny * W + nx] and px[nx, ny][3] == 0:
                outside[ny * W + nx] = 1; dq.append((nx, ny))
    # 2) 内部透明像素 = 洞
    holes = [(x, y) for y in range(H) for x in range(W)
             if px[x, y][3] == 0 and not outside[y * W + x]]
    print(f"  内部孔洞像素 = {len(holes)}")
    if not holes:
        return
    # 3) 迭代膨胀：洞内像素取最近的不透明邻居颜色，直到填满
    todo = set(holes)
    guard = 0
    while todo and guard < 2000:
        guard += 1
        filled = []
        for (x, y) in list(todo):
            acc = [0, 0, 0, 0]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and px[nx, ny][3] > 0:
                    r, g, b, a = px[nx, ny]
                    acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += 1
            if acc[3]:
                filled.append((x, y, acc[0] // acc[3], acc[1] // acc[3], acc[2] // acc[3]))
        if not filled:
            break
        for (x, y, r, g, b) in filled:
            px[x, y] = (r, g, b, 255)
            todo.discard((x, y))
    print(f"  已填 {len(holes) - len(todo)} / {len(holes)} 个孔洞像素（剩 {len(todo)}）")
    im.save(path)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print(f"补全孔洞: {target.name}")
    fill(target)
