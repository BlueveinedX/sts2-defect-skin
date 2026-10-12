# -*- coding: utf-8 -*-
"""运动质量量化：把「动作像不像人做的」变成可比较的数字，并与游戏原版动画对齐。
我不具备审美判断，但可以量出「原版是怎么动的」，然后要求自己的动画达到同样的数值。
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))

HAND = {"mine": "Arm_R_3", "game": "hand_r"}
SHOULDER = {"mine": "Arm_R_", "game": "arm_upper_r"}


# ---------------------------------------------------------------- 取世界坐标
def frames_mine(anim: str, fps: int = 60):
    import author_anims as A
    sk = A.load()
    bp = {b["name"]: (b.get("x", 0.0) or 0.0, b.get("y", 0.0) or 0.0) for b in sk["bones"]}
    tl = sk["animations"][anim].get("bones", {})
    dur = 0.0
    for tls in tl.values():
        for k in tls.values():
            if k:
                dur = max(dur, k[-1]["time"])
    n = int(dur * fps) + 1
    out = []
    for i in range(n):
        t = i / fps
        rot = {}
        for bn, tls in tl.items():
            rl = tls.get("rotate")
            if rl:
                v = 0.0
                for j, kf in enumerate(rl):
                    if kf["time"] >= t or j == len(rl) - 1:
                        if j == 0:
                            v = kf["value"]
                        else:
                            p = rl[j - 1]
                            u = 0.0 if kf["time"] <= p["time"] else (t - p["time"]) / (kf["time"] - p["time"])
                            v = p["value"] + (kf["value"] - p["value"]) * min(1.0, max(0.0, u))
                        break
                rot[bn] = v
            tl2 = tls.get("translate")
            if tl2:
                for ax, key in (("tx", "x"), ("ty", "y")):
                    v = 0.0
                    for j, kf in enumerate(tl2):
                        if kf["time"] >= t or j == len(tl2) - 1:
                            if j == 0:
                                v = kf[key]
                            else:
                                p = tl2[j - 1]
                                u = 0.0 if kf["time"] <= p["time"] else (t - p["time"]) / (kf["time"] - p["time"])
                                v = p[key] + (kf[key] - p[key]) * min(1.0, max(0.0, u))
                            break
                    if ax == "tx":
                        bp = dict(bp); bp[bn] = (v, bp[bn][1])
                    else:
                        bp = dict(bp); bp[bn] = (bp[bn][0], v)
        out.append(A.fk(sk, rot, bp))
    return out, dur


def frames_game(anim: str):
    g = json.load(open(HERE / "game-defect/anims.json"))
    rest = {b["name"]: b for b in g["bones"]}
    rec = g["animations"][anim]
    cnt = rec["count"]
    out = []
    for i in range(cnt):
        cache = {}

        def rec_world(name):
            if name in cache:
                return cache[name]
            b = rest[name]
            p = b.get("parent") or ""
            lr = b.get("rotation", 0.0) + rec["bones"].get(name, {}).get("rot", [0.0] * cnt)[i]
            lx = rec["bones"].get(name, {}).get("x", [b.get("x", 0.0)] * cnt)[i]
            ly = rec["bones"].get(name, {}).get("y", [b.get("y", 0.0)] * cnt)[i]
            if p:
                pw, pa = rec_world(p)
            else:
                pw, pa = (0.0, 0.0), 0.0
            r = math.radians(pa)
            wx = pw[0] + lx * math.cos(r) - ly * math.sin(r)
            wy = pw[1] + lx * math.sin(r) + ly * math.cos(r)
            cache[name] = ((wx, wy), pa + lr)
            return cache[name]

        for b in g["bones"]:
            rec_world(b["name"])
        out.append(cache)
    return out, rec["duration"]


# ---------------------------------------------------------------- 指标
def metrics(frames, bone: str):
    pts = [f[bone][0] for f in frames]
    n = len(pts)
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(n - 1)]
    total = sum(seg)
    speeds = [d * 60.0 for d in seg]                      # 单位/秒
    peak = max(speeds) if speeds else 0.0
    # 轨迹折角：方向变化率
    turns = []
    for i in range(1, n - 1):
        a = (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        b = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        na, nb = math.hypot(*a), math.hypot(*b)
        if na < 1e-6 or nb < 1e-6:
            continue
        c = max(-1.0, min(1.0, (a[0] * b[0] + a[1] * b[1]) / (na * nb)))
        turns.append(math.degrees(math.acos(c)))
    # 速度变化（ jerk 的连续版本）
    ds = [abs(speeds[i + 1] - speeds[i]) for i in range(len(speeds) - 1)]
    disp = math.dist(pts[0], pts[-1])
    # 预备动作：★ 不能拿「起点->终点」当方向 —— 首尾都回到静止姿势时净位移为 0，
    # 方向未定义会算成 0（那是指标 bug，不是动画缺陷）。
    # 正确做法：找出位移最大的那一段当「主动作」，量它开始之前的反向蓄力。
    if n >= 3:
        k = max(range(n - 1), key=lambda i: math.dist(pts[i], pts[i + 1]))
        dx, dy = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
        d = math.hypot(dx, dy)
        if d > 1e-6:
            ux, uy = dx / d, dy / d
            proj = [(p[0] - pts[0][0]) * ux + (p[1] - pts[0][1]) * uy for p in pts[:k + 1]]
            anticip = max(0.0, -min(proj))
        else:
            anticip = 0.0
    else:
        anticip = 0.0
    peak_at = speeds.index(peak) / max(1, len(speeds) - 1) if speeds else 0.0
    return {
        "轨迹总长": total,
        "净位移": disp,
        "绕行比(总长/净位移)": total / disp if disp > 1e-6 else 0.0,
        "方向转角总量(度)": sum(turns),
        "折角数(>20度/帧)": sum(1 for t in turns if t > 20),
        "峰值速度": peak,
        "峰值出现位置(0-1)": peak_at,
        "速度变化均值/峰值": (sum(ds) / len(ds) / peak) if peak > 1e-6 and ds else 0.0,
        "静止帧占比": (sum(1 for s in speeds if s < peak * 0.15) / len(speeds)) if speeds else 0.0,
        "预备动作幅度": anticip,
        "预备/净位移": anticip / disp if disp > 1e-6 else 0.0,
    }


def report(anim: str, scale_mine: float = 10.026):
    gm, gd = frames_game(anim)
    mm, md = frames_mine(anim)
    a = metrics(gm, HAND["game"])
    b = metrics(mm, HAND["mine"])
    # 我的手写动画量的是「骨架单位」，原版是「世界单位」，需乘上 root 缩放才能比
    for k in ["轨迹总长", "净位移", "峰值速度", "预备动作幅度"]:
        b[k] = b[k] * scale_mine
    print(f"\n===== {anim}：右手 =====")
    print(f"{'指标':<22}{'游戏原版':>14}{'我的手写':>14}   判定")
    for k in a:
        va, vb = a[k], b[k]
        diff = abs(va - vb) / (abs(va) + 1e-9)
        flag = "✅" if diff < 0.45 else ("⚠" if diff < 1.2 else "❌")
        print(f"{k:<22}{va:>14.2f}{vb:>14.2f}   {flag} 差{diff*100:>5.0f}%")
    return a, b, gm, mm


if __name__ == "__main__":
    for anim in (sys.argv[1:] or ["attack"]):
        report(anim)
