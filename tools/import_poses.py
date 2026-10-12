# -*- coding: utf-8 -*-
"""把姿势编辑器导出的 poses_export.json 接回管线。

编辑器导出格式：
  {"fps":60, "animations": {"attack": {"dur":1.5, "keys":[{"t":0.0, "pose":{"Arm_R_":{"rot":30}}}, ...]}}}
author_anims.bake 需要：
  keys = [(t, pose), ...]，pose = {骨骼: {"rot"/"tx"/"ty"}}

本脚本负责衔接：补首尾关键帧（0 秒与时长处）、按 60fps + smoothstep 烘焙、
写入与 make_hand_anims.py 完全相同的骨架 JSON。
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import author_anims as A

POSES = HERE / "godot-project/poses_export.json"
ROOT_SCALE = 1828.5 / 182.37          # 与 make_hand_anims.py 同一基准


def main() -> int:
    if not POSES.exists():
        print(f"❌ 找不到 {POSES}，请先在姿势编辑器里点「导出」")
        return 1
    d = json.loads(POSES.read_text(encoding="utf-8"))
    anims = d.get("animations", {})
    if not anims:
        print("❌ 导出文件里没有任何动画")
        return 1
    sk = A.load()
    for b in sk["bones"]:
        if b["name"] == "root":
            b["scaleX"] = b["scaleY"] = round(ROOT_SCALE, 4)
    base_pos = {b["name"]: (b.get("x", 0.0) or 0.0, b.get("y", 0.0) or 0.0) for b in sk["bones"]}

    done = 0
    for name, spec in anims.items():
        ks = sorted(spec.get("keys", []), key=lambda k: k["t"])
        if not ks:
            print(f"  ⚠ {name}: 没有关键帧，跳过")
            continue
        dur = float(spec.get("dur") or ks[-1]["t"] or 1.0)
        keys = [(float(k["t"]), k["pose"]) for k in ks]
        # 首尾补齐：Spine 里未 key 的属性会沿用残留值，所以两端要显式给出姿势
        if keys[0][0] > 0.0:
            keys.insert(0, (0.0, {}))
        if keys[-1][0] < dur - 1e-4:
            keys.append((dur, keys[-1][1]))
        baked, baked_dur = A.bake(sk, keys, base_pos)
        A.write_anim(sk, name, baked, baked_dur)
        print(f"  ✅ {name:<16} 关键帧 {len(ks):>2} -> 烘焙 {len(baked)} 根骨骼  {baked_dur:.3f}s")
        done += 1
    if not done:
        print("❌ 没有任何动画被写入")
        return 1
    A.JSON_PATH.write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入 {A.JSON_PATH.name}（{done} 个动画来自姿势编辑器）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
