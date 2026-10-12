"""打印一代骨架的静止姿态：每根骨骼的世界位置与「世界朝向角」。
手写动画时，要把某个肢体摆到指定方向，就用 目标角 - 静止世界角 得到局部旋转增量。
"""
import json, math, sys
from pathlib import Path

J = Path(__file__).resolve().parent.parent / "godot-project/animations/characters/defect/DefectSTS1.spine-json"
sk = json.loads(J.read_text(encoding="utf-8"))
by = {b["name"]: b for b in sk["bones"]}


def world_of(name):
    """返回 (世界位置, 世界角度) —— 逐级累加父级。"""
    chain = []
    n = name
    while n:
        chain.append(by[n])
        n = by[n].get("parent") or ""
    chain.reverse()
    x = y = 0.0
    a = 0.0
    for b in chain:
        r = math.radians(b.get("rotation", 0.0))
        lx, ly = b.get("x", 0.0) or 0.0, b.get("y", 0.0) or 0.0
        s = math.sin(math.radians(a)); c = math.cos(math.radians(a))
        x += lx * c - ly * s
        y += lx * s + ly * c
        a += b.get("rotation", 0.0)
    return (x, y), a


print(f"{'骨骼':<16}{'父级':<14}{'局部角':>8}{'世界角':>9}   世界位置")
for b in sk["bones"]:
    n = b["name"]
    (wx, wy), wa = world_of(n)
    print(f"{n:<16}{str(b.get('parent') or '-'):<14}{b.get('rotation',0.0):>8.1f}{wa:>9.1f}   ({wx:7.2f},{wy:7.2f})")
