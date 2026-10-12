# -*- coding: utf-8 -*-
"""全面向一代靠拢：不再自创关节姿势。

一代 Defect 的骨架只有 Idle / Hit 两个动画，攻击表现是**身体平移 + 特效**。
所以这里所有动作都基于一代原版 Idle：
  · 基础层 = 一代 Idle 的原始曲线，截断到目标时长（保留它自然的呼吸起伏）
  · 动作层 = 只对 Hips 加整体平移/起伏，不动任何关节
`hurt` 直接用一代 Hit 原版。
"""
import copy, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JSON = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"

HURT_SRC = "hurt"           # sts1_to_spine42 已把一代 Hit 转成 hurt
IDLE_SRC = "idle_loop"      # 一代 Idle

# 目标动画 -> (时长, Hips 平移关键帧 [时间, tx, ty, rot])
# tx/ty 单位是骨架单位（骨架高约 180）；rot 是度
TARGETS = {
    # 攻击：照一代做法，身体向前一冲再收回
    "attack": (1.500, [(0.00, 0, 0, 0), (0.18, -2.0, 0, -2.0),
                       (0.32, 9.0, 1.0, 3.0), (0.55, 8.0, 0.6, 2.4),
                       (0.85, 2.0, 0, 0.6), (1.50, 0, 0, 0)]),
    # 施法：向后一沉再回正（能量在核心聚集）
    "cast": (1.233, [(0.00, 0, 0, 0), (0.25, -1.5, -1.5, 1.5),
                     (0.55, -1.0, -2.5, 2.0), (0.90, -0.5, -1.5, 1.0),
                     (1.233, 0, 0, 0)]),
    # 能力牌：被上方牵引而整体浮起，再落回
    "process": (1.567, [(0.00, 0, 0, 0), (0.45, 0, 3.0, -1.0),
                        (0.95, 0, 11.0, -2.5), (1.25, 0, 9.0, -2.0),
                        (1.567, 0, 0, 0)]),
    # 低血 / 非战斗待机：**直接沿用一代 Idle 自己的 Hips 曲线**（含上下起伏），
    # 只加一个恒定偏移。之前我自写了几乎压平的 Hips -> 腿看着不动，
    # 而战斗里 idle_loop 的腿会跟着 Hips 起伏一起动。用户要求直接迁移过来。
    "relaxed_loop": (8.000, None, (0.0, -2.0, 1.5)),
    "low_health_loop": (6.000, None, (0.0, -5.5, -3.0)),
    # 死亡：整体向下沉、并向后倾（膝盖一软往后坐倒的观感，仍然只动 Hips）
    # TODO: 下一步改成切到一代 corpse.png 尸体贴图
    "die": (2.233, [(0.00, 0, 0, 0), (0.45, 0, -8.0, 4.0), (1.10, -3.0, -24.0, 13.0),
                    (1.70, -6.0, -38.0, 22.0), (2.233, -8.0, -45.0, 27.0)]),
}


def fit(tl: list, dur: float, key_names: list, src_dur: float) -> list:
    """把一代 Idle 的曲线铺到目标时长。
    目标比源短 -> 截断；目标比源长 -> **平铺重复**
    （一代 Idle 是循环动画，首尾值接得上，所以平铺不会跳变）。
    之前我用"截断后就保持"，结果是后半段完全静止 —— 商店里表现为"一会动一会不动"。"""
    if dur <= src_dur + 1e-6:
        return truncate(tl, dur, key_names)
    out = []
    k = 0
    while k * src_dur < dur - 1e-6:
        off = k * src_dur
        for kf in tl:
            tt = kf.get("time", 0.0) + off
            if tt > dur + 1e-6:
                break
            e = copy.deepcopy(kf)
            e["time"] = round(tt, 4)
            out.append(e)
        k += 1
    if out and out[-1].get("time", 0.0) < dur - 1e-6:
        e = copy.deepcopy(out[-1]); e["time"] = round(dur, 4); e.pop("curve", None)
        out.append(e)
    return out


def truncate(tl: list, dur: float, key_names: list) -> list:
    """把一代 Idle 的时间轴截断到 dur（保留曲线形状，末尾补一帧以防跳变）。"""
    out = [k for k in tl if k.get("time", 0.0) <= dur + 1e-6]
    if not out:
        return [{**{n: k.get(n, 0.0) for n in key_names}, "time": 0.0} for k in [tl[0]]]
    last = out[-1]
    if last.get("time", 0.0) < dur - 1e-6:
        e = copy.deepcopy(last)
        e["time"] = round(dur, 4)
        e.pop("curve", None)     # 末帧用线性，避免停在曲线中途
        out.append(e)
    return out


ROOT_SCALE = 1828.5 / 182.37      # 与 make_hand_anims.py 同一基准：游戏原版身体高 / 一代骨架身体高


def main() -> int:
    d = json.loads(JSON.read_text(encoding="utf-8"))
    # ★ 根骨骼缩放必须在这里设：游戏里的世界尺寸靠它，漏了角色就只有 1/10 大
    for b in d["bones"]:
        if b["name"] == "root":
            b["scaleX"] = b["scaleY"] = round(ROOT_SCALE, 4)
    print(f"  根骨骼缩放 = {ROOT_SCALE:.3f}")
    if IDLE_SRC not in d["animations"]:
        print(f"❌ 骨架里没有 {IDLE_SRC}"); return 1
    idle = d["animations"][IDLE_SRC]
    IDLE_DUR = max((k.get("time", 0.0) for tls in idle.get("bones", {}).values()
                    for tl in tls.values() for k in tl), default=6.6666)
    print(f"  一代 Idle 时长 = {IDLE_DUR:.3f}s（更长的目标会自动平铺重复）")
    hurt = d["animations"].get(HURT_SRC)

    for name, spec in TARGETS.items():
        dur = spec[0]; hips = spec[1]; off = spec[2] if len(spec) > 2 else (0.0, 0.0, 0.0)
        new_bones = {}
        # 基础层：一代 Idle 的每条时间轴截断到目标时长
        for bn, tls in idle.get("bones", {}).items():
            nb = {}
            for kind, tl in tls.items():
                keys = list(tl[0].keys())
                nb[kind] = fit(tl, dur, keys, IDLE_DUR)
            if nb:
                new_bones[bn] = nb
        # 动作层
        hb = new_bones.setdefault("Hips", {})
        if hips is None:
            # 沿用一代 Idle 自己的 Hips 曲线（已平铺到目标时长），加恒定偏移
            ox, oy, orot = off
            for kf in hb.get("translate", []):
                kf["x"] = round(kf.get("x", 0.0) + ox, 4)
                kf["y"] = round(kf.get("y", 0.0) + oy, 4)
            for kf in hb.get("rotate", []):
                kf["value"] = round(kf.get("value", 0.0) + orot, 4)
            if not hb.get("translate"):
                hb["translate"] = [{"time": 0.0, "x": ox, "y": oy}, {"time": dur, "x": ox, "y": oy}]
        else:
            hb["translate"] = [{"time": t, "x": tx, "y": ty} for (t, tx, ty, _r) in hips]
            hb["rotate"] = [{"time": t, "value": r} for (t, _x, _y, r) in hips]
        d["animations"][name] = {"bones": new_bones}
        print(f"  ✅ {name:<16} {dur:.3f}s  基础层 {len(new_bones)-1} 根 + Hips 平移")

    # hurt：一代 Hit 原版（sts1_to_spine42 已转好），只去掉多余时长
    if hurt is not None:
        print(f"  ✅ hurt             一代 Hit 原版（{hurt.get('bones') and len(hurt['bones'])} 根骨骼）")

    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入 {JSON.name}：8 个动画")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
