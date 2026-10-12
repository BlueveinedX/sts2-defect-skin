"""手写动画工具：用「肢体末端目标位置」描述姿势，FK + 数值 IK 解关节角，再平滑烘焙。

设计意图（对应一代骨骼的实际情况）：
  · 骨骼静止朝向已实测：Arm_R_ 世界角 -43.8°、Arm_R_2 -35.4°、Arm_R_3 -48.0°、
    Arm_L_ -147.6°、Leg_L_ -134.0°、Leg_R_ -37.3°、Neck_3(头) 30.0°、法球核心 (0,106.85)
  · 姿势里可以直接给局部旋转增量 {"rot": 度}，也可以用 IK {"ik": (x, y)} 指定末端位置
  · 关键帧之间用 smoothstep 缓动，30fps 烘焙 —— 不会出现线性折角（就是之前"抽搐"的来源）
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JSON_PATH = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"
FPS = 60   # 60fps：30fps 表现不出「3 帧爆发」这种节奏（原版攻击峰值只出现在 13% 处）

# 手臂 IK 链：末端骨骼 -> (根, 中, 末端)
CHAINS = {
    "R": ("Arm_R_", "Arm_R_2", "Arm_R_3"),
    "L": ("Arm_L_", "Arm_L_2", "Arm_L_3"),
}


def load():
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def fk(sk, local_rot, local_pos):
    """返回 {骨名: (世界位置, 世界角 度)}"""
    by = {b["name"]: b for b in sk["bones"]}
    out = {}

    def rec(name):
        if name in out:
            return out[name]
        b = by[name]
        p = b.get("parent") or ""
        lr = (b.get("rotation") or 0.0) + local_rot.get(name, 0.0)
        lp = local_pos.get(name, (b.get("x", 0.0) or 0.0, b.get("y", 0.0) or 0.0))
        if p:
            pw, pa = rec(p)
        else:
            pw, pa = (0.0, 0.0), 0.0
        a = pa + lr
        r = math.radians(pa)
        wx = pw[0] + lp[0] * math.cos(r) - lp[1] * math.sin(r)
        wy = pw[1] + lp[0] * math.sin(r) + lp[1] * math.cos(r)
        out[name] = ((wx, wy), a)
        return out[name]

    for b in sk["bones"]:
        rec(b["name"])
    return out


def solve_ik(sk, chain, target, local_rot, local_pos):
    """解析 2 骨 IK（余弦定理）。数值搜索会在粗网格上落进局部最优，解析解不会。
    可达范围是环带 [|L1-L2|, L1+L2]，超出时把目标投影回环带边界。"""
    root, mid, tip = chain
    base = dict(local_rot)
    base[root] = 0.0
    base[mid] = 0.0
    w = fk(sk, base, local_pos)
    sh, sh_world = w[root]
    L1 = math.dist(sh, w[mid][0])
    L2 = math.dist(w[mid][0], w[tip][0])
    dx, dy = target[0] - sh[0], target[1] - sh[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0, 0.0, dist
    dist_c = min(max(dist, abs(L1 - L2) + 1e-4), L1 + L2 - 1e-4)
    ang = math.degrees(math.atan2(dy, dx))
    cos_a = (L1 * L1 + dist_c * dist_c - L2 * L2) / (2 * L1 * dist_c)
    a = math.degrees(math.acos(min(1.0, max(-1.0, cos_a))))
    best = None
    for sign in (1.0, -1.0):
        r = (ang + sign * a) - sh_world
        lr = dict(base); lr[root] = r
        w2 = fk(sk, lr, local_pos)
        mp, mw = w2[mid]
        ang2 = math.degrees(math.atan2(target[1] - mp[1], target[0] - mp[0]))
        m = ang2 - mw
        lr2 = dict(lr); lr2[mid] = m
        tp, _ = fk(sk, lr2, local_pos)[tip]
        err = math.dist(tp, target)
        # 优先误差小；同误差取肘部弯曲更小的（更自然）
        score = (round(err, 2), abs(m))
        if best is None or score < best[0]:
            best = (score, r, m, err)
    return best[1], best[2], 0.0, best[3]


def expand(sk, pose, base_pos):
    """把一帧的姿势展开成 {骨: 局部旋转增量度}。
    IK 目标可以用 "frame" 指定参考骨骼（写在身体局部坐标，身体翻转时目标跟着走）。"""
    rot = {}
    for k, v in pose.items():
        if k in ("R", "L"):
            continue
        if isinstance(v, dict) and "rot" in v:
            rot[k] = v["rot"]
    world = fk(sk, rot, base_pos)
    for side, spec in pose.items():
        if side not in CHAINS:
            continue
        tgt = spec["ik"] if isinstance(spec, dict) else spec
        if isinstance(spec, dict) and spec.get("frame"):
            (px, py), pa = world[spec["frame"]]
            r0 = math.radians(pa)
            tgt = (px + tgt[0] * math.cos(r0) - tgt[1] * math.sin(r0),
                   py + tgt[0] * math.sin(r0) + tgt[1] * math.cos(r0))
        a, b, c, err = solve_ik(sk, CHAINS[side], tgt, rot, base_pos)
        rot[CHAINS[side][0]] = a
        rot[CHAINS[side][1]] = b
        rot[CHAINS[side][2]] = c
    return rot


def smoothstep(u):
    return u * u * (3 - 2 * u)


def bake(sk, keys, base_pos):
    """keys = [(t, pose), ...] -> 30fps 的 {骨: [(t, 值)]}（旋转 + 位移）"""
    rot_keys = [(t, expand(sk, p, base_pos)) for t, p in keys]
    names = set()
    for _, r in rot_keys:
        names |= set(r)
    for _, p in keys:
        for k, v in p.items():
            if isinstance(v, dict) and ("tx" in v or "ty" in v):
                names.add(k)
    dur = keys[-1][0]
    n = int(dur * FPS) + 1
    out = {}
    for nm in sorted(names):
        seq = []
        for i in range(n):
            t = i / FPS
            # 找所在区间
            k = 0
            while k < len(rot_keys) - 2 and rot_keys[k + 1][0] <= t:
                k += 1
            t0, t1 = rot_keys[k][0], rot_keys[k + 1][0]
            u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            u = smoothstep(min(1.0, max(0.0, u)))

            def val(field):
                va = rot_keys[k][1].get(nm, 0.0)
                vb = rot_keys[k + 1][1].get(nm, 0.0)
                # 位移从原始 pose 里取
                pa = keys[k][1].get(nm, {}) or {}
                pb = keys[k + 1][1].get(nm, {}) or {}
                if field != "rot":
                    va = pa.get(field, 0.0) if isinstance(pa, dict) else 0.0
                    vb = pb.get(field, 0.0) if isinstance(pb, dict) else 0.0
                return va + (vb - va) * u

            seq.append((round(t, 4), val("rot"), val("tx"), val("ty")))
        out[nm] = seq
    return out, dur


def write_anim(sk, name, baked, dur):
    a = {"bones": {}}
    for nm, seq in baked.items():
        tls = {}
        if any(abs(r) > 0.05 for _, r, _, _ in seq):
            tls["rotate"] = [{"time": t, "value": round(r, 3)} for t, r, _, _ in seq]
        if any(abs(tx) > 0.001 or abs(ty) > 0.001 for _, _, tx, ty in seq):
            tls["translate"] = [{"time": t, "x": round(tx, 3), "y": round(ty, 3)}
                                for t, _, tx, ty in seq]
        if tls:
            a["bones"][nm] = tls
    if not a["bones"]:
        return False
    sk["animations"][name] = a
    return True
