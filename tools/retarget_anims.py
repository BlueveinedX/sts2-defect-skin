#!/usr/bin/env python3
"""把二代原版 Defect 的动画重定向到一代骨架上。

原理（关键）：
  · Spine 的时间轴值是**相对 setup 的偏移量**（已实测，translate/rotate/scale 都是）。
  · 两代骨架的骨骼朝向完全不同，所以不能直接搬局部旋转。
    正确做法是搬**世界空间旋转增量**：
        Δg(t) = worldRot_g(t) − worldRot_g(setup)        # 二代骨骼在世界的转动量
        想要   worldDelta_s(t) = Δg(t)
        而     worldDelta_s(t) = worldDelta_parent(t) + localΔ_s(t)
        ⇒      localΔ_s(t) = Δg(t) − worldDelta_parent(t)
    按层级自上而下计算即可（未映射的骨骼 localΔ=0，跟随父级刚性运动）。
  · 位移按 SIZE_RATIO 换算（二代骨骼单位比一代大 ~11 倍），再给 root 一个
    等比例的缩放，视觉幅度就与二代一致。

输入： game-defect/anims.json（由 godot-project/dump_anims.gd 导出）
输出： 直接改写 godot-project/animations/characters/defect/DefectSTS1.spine-json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GAME = HERE / "game-defect/anims.json"
S1 = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"

# 二代骨骼 → 一代骨骼。多个二代骨骼映射到同一个一代骨骼时，旋转增量相加。
# 依据是解剖学对位（见 game-defect/anims.json 的骨骼层级）。
BONE_MAP: dict[str, str] = {
    # ★ 严格一对一。子级的世界角增量**已经包含**祖先的旋转，所以绝对不能
    #   把父子同时加到一个目标骨骼上（那会把旋转重复计算，姿势就会变形）。
    #   这里每段只取一个代表性骨骼。
    "hips":         "Hips",        # 骨盆（其世界增量已含 COG 的运动）
    "torso_upper":  "Chest",       # 脊椎顶端（已含 torso / torso_twist 的旋转）
    "neck":         "Neck_",
    "head":         "Neck_3",
    "arm_upper_l":  "Arm_L_",
    "arm_lower_l":  "Arm_L_2",
    "hand_l":       "Arm_L_3",
    "arm_upper_r":  "Arm_R_",
    "arm_lower_r":  "Arm_R_2",
    "hand_r":       "Arm_R_3",
    "leg_upper_l":  "Leg_L_",
    "leg_lower_l":  "Leg_L_2",
    "foot_l":       "Leg_L_4",
    "leg_upper_r":  "Leg_R_",
    "leg_lower_r":  "Leg_R_2",
    "foot_r":       "Leg_R_4",
}

# 要生成的一代动画名（idle_loop / hurt 用一代原版，不覆盖）
TARGETS = ["attack", "cast", "die", "process", "relaxed_loop", "low_health_loop"]

# ★ 腿骨不参与重定向（die 除外）。
# 一代的腿是「分片装甲」（大腿/小腿/脚是独立贴图块），一代 Idle 里腿几乎不动、
# 甲片严丝合缝；把二代的腿部动作搬过来会让甲片分开、露出缝（左小腿尤其明显，
# 因为它的原图本身就比右边窄近一半：26×58 vs 43×59）。
# 排除后既修掉「缺一块」，又让站姿更贴近一代原版。
# 身体仍会随 Hips 位移/旋转运动，视觉上腿是跟着身体走的。
LEG_BONES = {"Leg_L_", "Leg_L_2", "Leg_L_4", "Leg_R_", "Leg_R_2", "Leg_R_4"}
# 旋转增量放大系数：>1 更夸张，<1 更含蓄
ROT_GAIN = 1.0
# ★ 低通平滑：二代原版动作里带约 10Hz 的机械微颤（源数据实测 arm_upper_r 在
#   5.2/5.9/6.6 之间反复），经重定向后会被放大成肉眼可见的"抽搐"。
#   这里做 SMOOTH_PASS 次 3 点二项式平滑（[1,2,1]/4），压掉高频、保留真实动作。
SMOOTH_PASS = 2


def smooth(series: list[float], passes: int = SMOOTH_PASS) -> list[float]:
    v = list(series)
    n = len(v)
    if n < 5:
        return v
    for _ in range(passes):
        out = list(v)
        for i in range(1, n - 1):
            out[i] = (v[i - 1] + 2.0 * v[i] + v[i + 1]) * 0.25
        # 首尾保持端点
        v = out
    return v
# 位移保留比例（相对视觉等幅）
TRANS_GAIN = 1.0


# ------------------------------------------------------------------ 工具
def build_world(bones: list[dict], local_rot: dict, local_xy: dict) -> dict:
    """按层级算世界旋转（度）。local_rot 是绝对局部角。"""
    by = {b["name"]: b for b in bones}
    out: dict[str, float] = {}

    def calc(name: str) -> float:
        if name in out:
            return out[name]
        b = by[name]
        r = local_rot.get(name, 0.0)
        p = b.get("parent") or ""
        out[name] = r + (calc(p) if p in by else 0.0)
        return out[name]

    for b in bones:
        calc(b["name"])
    return out


def sts1_hierarchy(sk: dict) -> list[str]:
    by = {b["name"]: b for b in sk["bones"]}
    order: list[str] = []
    seen: set[str] = set()

    def visit(n: str) -> None:
        if n in seen or n not in by:
            return
        p = by[n].get("parent")
        if p:
            visit(p)
        seen.add(n)
        order.append(n)

    for b in sk["bones"]:
        visit(b["name"])
    return order


# ------------------------------------------------------------------ 主流程
def main() -> int:
    g = json.loads(GAME.read_text(encoding="utf-8"))
    sk = json.loads(S1.read_text(encoding="utf-8"))

    g_bones = g["bones"]
    g_by = {b["name"]: b for b in g_bones}

    # 二代 setup 世界角
    g_setup_rot = build_world(g_bones, {b["name"]: b["rotation"] for b in g_bones}, {})

    # 尺寸比例 ★ 必须用「实测身体高度」，不能用骨架声明的 bbox ——
    # 二代 defect.skel 的 bbox(2339) 被停在远处(x≈3748)的特效骨骼撑大了，
    # 按它缩放会让角色偏大约 30%，在商店这类近景里尤其明显。
    GAME_BODY_H = 1828.5   # 实测：游戏原版 Defect 在 setup pose 下的身体高度
    S1_BODY_H = 182.37     # 实测：一代骨架在 root scale=1 时的身体高度
    ratio = GAME_BODY_H / S1_BODY_H
    print(f"尺寸比例 SIZE_RATIO = {ratio:.3f}  (二代身体 {GAME_BODY_H} / 一代身体 {S1_BODY_H})")

    # 反向索引：一代骨骼 → 贡献它的二代骨骼列表
    rev: dict[str, str] = {}
    for gb, sname in BONE_MAP.items():
        if gb not in g_by:
            print(f"  ⚠ 二代骨骼 {gb!r} 不存在，跳过")
            continue
        rev[sname] = gb

    order = sts1_hierarchy(sk)
    sk_by = {b["name"]: b for b in sk["bones"]}
    anims: dict[str, dict] = {}
    covered: set[str] = set()

    # ★ 关键：游戏的「静止姿势」不是 bind pose —— 所有动画都把骨架摆在离 bind 约
    #   (−107, −38) 的一个中性位上。所以参考基准必须取 idle_loop 第 0 帧，
    #   否则每个动画都会带上一个恒定偏置（角色会一直歪着）。
    REF_ANIM = "idle_loop"

    def world_rot_series(anim: str) -> dict[str, list[float]]:
        rec = g["animations"][anim]["bones"]
        n = g["animations"][anim]["count"]
        acc: dict[str, list[float]] = {}
        for b in g_bones:
            nm = b["name"]
            p = b.get("parent") or ""
            base = acc.get(p, [0.0] * n)
            lr = rec[nm]["rot"] if nm in rec else [b["rotation"]] * n
            acc[nm] = [base[i] + lr[i] for i in range(n)]
        return acc

    ref_world = world_rot_series(REF_ANIM)
    ref_rec = g["animations"][REF_ANIM]["bones"]
    ref_rot = {nm: ref_world[nm][0] for nm in ref_world}
    # 游戏骨盆在世界空间的位置（COG 的父级旋转为 0，所以 local 即 world 偏移）
    def hips_world_xy(rec, i):
        return (rec["COG"]["x"][i] + rec["hips"]["x"][i],
                rec["COG"]["y"][i] + rec["hips"]["y"][i])
    ref_hips = hips_world_xy(ref_rec, 0)
    print(f"参考基准 = {REF_ANIM}@0: hips世界=({ref_hips[0]:.1f}, {ref_hips[1]:.1f})")

    for anim in TARGETS:
        if anim not in g["animations"]:
            print(f"  ⚠ 二代没有动画 {anim}，跳过")
            continue
        src = g["animations"][anim]
        rec = src["bones"]
        n = src["count"]
        times = rec["root"]["t"]

        # 每条二代骨骼的「世界旋转增量」序列
        delta: dict[str, list[float]] = {}

        # 逐帧重建二代世界角（父角逐帧累加）
        g_world: dict[str, list[float]] = {b["name"]: [0.0] * n for b in g_bones}

        def gworld(name: str) -> list[float]:
            return g_world[name]

        for b in g_bones:
            nm = b["name"]
            p = b.get("parent") or ""
            base = gworld(p) if p in g_world else [0.0] * n
            lr = rec[nm]["rot"] if nm in rec else [b["rotation"]] * n
            g_world[nm] = [base[i] + lr[i] for i in range(n)]

        for gb in g_by:
            delta[gb] = [g_world[gb][i] - ref_rot[gb] for i in range(n)]

        # 一代侧自上而下
        world_delta: dict[str, list[float]] = {}
        bone_tls: dict[str, dict] = {}

        for sname in order:
            p = sk_by[sname].get("parent") or ""
            pwd = world_delta.get(p, [0.0] * n)
            gsrc = rev.get(sname)
            if sname in LEG_BONES and anim != "die":
                gsrc = None          # 腿保持一代站姿；die 例外（要倒下）
            if gsrc:
                # 目标世界增量 = 该源骨骼的世界角增量（一对一，不累加祖先）
                tgt = smooth([delta[gsrc][i] * ROT_GAIN for i in range(n)])
                local = [tgt[i] - pwd[i] for i in range(n)]
                world_delta[sname] = tgt
                # 去掉全零时间轴
                if any(abs(v) > 0.05 for v in local):
                    bone_tls[sname] = {
                        "rotate": [{"time": round(times[i], 4), "value": round(local[i], 4)}
                                   for i in range(n)]
                    }
                    covered.add(sname)
            else:
                world_delta[sname] = pwd  # 未映射：刚性跟随

        # 位移：游戏「骨盆世界位置」相对静止姿势的差 → 一代 Hips（按比例缩小）
        if "COG" in rec and "hips" in rec:
            xs, ys = [], []
            for i in range(n):
                hx, hy = hips_world_xy(rec, i)
                xs.append((hx - ref_hips[0]) / ratio * TRANS_GAIN)
                ys.append((hy - ref_hips[1]) / ratio * TRANS_GAIN)
            xs, ys = smooth(xs), smooth(ys)
            if any(abs(v) > 0.05 for v in xs + ys):
                tls = bone_tls.setdefault("Hips", {})
                tls["translate"] = [{"time": round(times[i], 4),
                                     "x": round(xs[i], 3), "y": round(ys[i], 3)}
                                    for i in range(n)]

        anims[anim] = {"bones": bone_tls}
        print(f"  {anim:<16} {n:>4} 帧  影响骨骼 {len(bone_tls):>2} 根  时长 {src['duration']:.3f}")

    for a, data in anims.items():
        sk["animations"][a] = data

    # root 缩放：让整体尺寸与二代 Defect 对齐
    for b in sk["bones"]:
        if b["name"] == "root":
            b["scaleX"] = round(ratio, 4)
            b["scaleY"] = round(ratio, 4)
    # 声明 bbox 只影响编辑器取景，不影响玩法；按实测身体高度重算即可
    w0 = float(sk["skeleton"].get("width") or 229.0)
    sk["skeleton"]["width"] = round(w0 * ratio, 2)
    sk["skeleton"]["height"] = round(S1_BODY_H * ratio, 2)
    sk["skeleton"]["x"] = round(-sk["skeleton"]["width"] * 0.5, 2)
    sk["skeleton"]["y"] = round(-sk["skeleton"]["height"] * 0.08, 2)

    S1.write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写入 {S1.relative_to(HERE)}")
    print(f"总动画: {sorted(sk['animations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
