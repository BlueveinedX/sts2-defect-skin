# -*- coding: utf-8 -*-
"""全部 8 个动画手写。姿势用「末端目标位置」描述（IK 解算），全部控制在手臂 65 单位可达范围内。
方向由用户确认：
  attack  右臂向前直刺（活塞出拳）        cast    双手抱核心两侧蓄力、不推出
  process 被上方牵引、四肢自然下垂、微浮空后落回
  hurt    上身后仰                        die     向**后**仰倒
  idle/relaxed/low_health  全部重写（站立呼吸 / 更放松 / 低血弓身）
"""
import sys, math, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import author_anims as A

# 肩部静止：R(26.3,117.1) L(-28.1,134.7)  核心(0,106.85)  手臂全长≈65
ANIMS = {
    # ============ 待机：站立呼吸、重心微移、头缓慢扫视 ============
    # ★ 原版 idle_loop 的静止帧占比是 0.96 —— 它绝大部分时间是**几乎完全不动**的，
    #   只在个别时刻有一次明确的小动作。我原来是「全程缓慢漂移」（静止比 0.09），
    #   所以看起来像在飘而不像站着。改成：长静止 → 一次呼吸 → 长静止 → 一次扫视。
    "idle_loop": {"dur": 6.000, "keys": [
        (0.000, {}),
        (1.400, {}),                                        # 静止
        (1.650, {"Hips": {"ty": 2.6}, "Chest": {"rot": -3.0}, "Neck_3": {"rot": -3.0},
                 "Arm_R_": {"rot": -4.0}, "Arm_L_": {"rot": 4.0}}),   # 一次吸气（0.25s 完成）
        (1.950, {"Hips": {"ty": 1.6}, "Chest": {"rot": -1.8},
                 "Arm_R_": {"rot": -2.4}, "Arm_L_": {"rot": 2.4}}),   # 回落
        (2.300, {}),                                        # 归位
        (3.600, {}),                                        # 静止
        (3.900, {"Neck_3": {"rot": -5.0}, "Chest": {"rot": -1.5},
                 "Hips": {"tx": -0.8}}),                    # 一次转头扫视（0.3s 完成）
        (4.600, {"Neck_3": {"rot": 4.0}, "Chest": {"rot": -0.8},
                 "Hips": {"tx": 0.6}}),                     # 转向另一侧
        (5.000, {}),                                        # 归位
        (6.000, {}),                                        # 静止到结束
    ]},
    # ============ 非战斗待机：肩放松、呼吸更慢 ============
    # 同 idle 的结构：长静止 + 偶尔一次小动作（原版静止比 0.96）
    "relaxed_loop": {"dur": 8.000, "keys": [
        (0.000, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),
        (2.000, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),          # 静止
        (2.350, {"Hips": {"ty": 1.2}, "Chest": {"rot": -1.0}, "Neck_3": {"rot": -3.5},
                 "Arm_R_": {"rot": -9.0}, "Arm_L_": {"rot": 9.0}}),          # 一次舒展
        (3.100, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),          # 归位
        (5.400, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),          # 静止
        (5.700, {"Hips": {"tx": 0.8}, "Neck_3": {"rot": 4.0}, "Chest": {"rot": 3.5}}),  # 一次侧望
        (6.300, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),          # 归位
        (8.000, {"Hips": {"ty": -2.0}, "Chest": {"rot": 2.5},
                 "Arm_R_": {"rot": -6.0}, "Arm_L_": {"rot": 6.0}}),          # 静止到结束
    ]},
    # ============ 低血待机：弓背、一手扶核心、低头、吃力呼吸 ============
    # 原版静止比 0.93 但轨迹有 1411 —— 即「长时间弓着不动 + 偶尔一次明显的抽搐/踉跄」
    "low_health_loop": {"dur": 6.000, "keys": [
        (0.000, {"Hips": {"ty": -5.0, "rot": -3.0}, "Chest": {"rot": -9.0},
                 "Neck_3": {"rot": -12.0}, "R": {"ik": (30.0, 98.0)},
                 "Arm_L_": {"rot": 6.0}, "Arm_L_2": {"rot": 5.0}}),
        (1.700, {"Hips": {"ty": -5.0, "rot": -3.0}, "Chest": {"rot": -9.0},
                 "Neck_3": {"rot": -12.0}, "R": {"ik": (30.0, 98.0)},
                 "Arm_L_": {"rot": 6.0}, "Arm_L_2": {"rot": 5.0}}),          # 静止
        (2.000, {"Hips": {"ty": -13.0, "rot": -6.0}, "Chest": {"rot": -17.0},
                 "Neck_3": {"rot": -21.0}, "R": {"ik": (36.0, 92.0)},
                 "Arm_L_": {"rot": 13.0}, "Arm_L_2": {"rot": 11.0}}),        # ★ 一次明显踉跄（0.3s 内）
        (2.700, {"Hips": {"ty": -5.0, "rot": -3.0}, "Chest": {"rot": -9.0},
                 "Neck_3": {"rot": -12.0}, "R": {"ik": (30.0, 98.0)},
                 "Arm_L_": {"rot": 6.0}, "Arm_L_2": {"rot": 5.0}}),          # 归位
        (4.500, {"Hips": {"ty": -5.0, "rot": -3.0}, "Chest": {"rot": -9.0},
                 "Neck_3": {"rot": -12.0}, "R": {"ik": (30.0, 98.0)},
                 "Arm_L_": {"rot": 6.0}, "Arm_L_2": {"rot": 5.0}}),          # 静止
        (6.000, {"Hips": {"ty": -5.0, "rot": -3.0}, "Chest": {"rot": -9.0},
                 "Neck_3": {"rot": -12.0}, "R": {"ik": (30.0, 98.0)},
                 "Arm_L_": {"rot": 6.0}, "Arm_L_2": {"rot": 5.0}}),
    ]},
    # ============ 攻击：右臂向前直刺（活塞出拳）============
    # ★ 按游戏原版的运动结构重写（用 motion_metrics.py 量出来的）：
    #   原版 = 89% 时间几乎静止 + 极短的爆发 + 明显预备动作 + 手走弧线
    #   我原来 = 50% 时间都在匀速移动、直线、无预备 → 所以看着像纸片人
    #   现在：静止(0~0.10) → 蓄力回收到胸侧(0.17) → 弧线加速(0.20) →
    #         3 帧爆发到最远(0.23) → 跟随过冲(0.27) → 稳住(0.33) →
    #         长静止保持(0.33~0.60) → 收招(0.75~0.90) → 静止
    "attack": {"dur": 1.500, "keys": [
        (0.000, {}),
        (0.100, {}),                                        # 起手静止
        (0.170, {"Hips": {"tx": -3.0, "rot": -6.0}, "Chest": {"rot": -5.0}, "Neck_3": {"rot": 5.0},
                 "R": {"ik": (41.0, 102.0)}}),               # 预备：拳头收回胸侧
        (0.200, {"Hips": {"tx": 1.0, "rot": 0.0}, "Chest": {"rot": 0.0}, "Neck_3": {"rot": 0.0},
                 "R": {"ik": (56.0, 124.0)}}),               # 弧线中段（抬高走弧，不走直线）
        (0.230, {"Hips": {"tx": 7.0, "rot": 11.0}, "Chest": {"rot": 9.0}, "Neck_3": {"rot": -3.0},
                 "R": {"ik": (89.0, 112.0)}}),               # 3 帧爆发到最远
        (0.270, {"Hips": {"tx": 5.6, "rot": 9.0}, "Chest": {"rot": 7.0},
                 "R": {"ik": (87.0, 105.0)}}),               # 跟随过冲（手往下沉）
        (0.330, {"Hips": {"tx": 5.0, "rot": 8.0}, "Chest": {"rot": 6.0},
                 "R": {"ik": (88.0, 109.0)}}),               # 稳住
        (0.600, {"Hips": {"tx": 4.6, "rot": 7.0}, "Chest": {"rot": 5.5},
                 "R": {"ik": (87.0, 110.0)}}),               # 长静止保持（原版 89% 静止）
        (0.750, {"Hips": {"tx": 2.0, "rot": 3.0}, "Chest": {"rot": 2.0},
                 "R": {"ik": (70.0, 95.0)}}),                # 收招
        (0.900, {"R": {"ik": (76.0, 80.0)}}),
        (1.500, {}),
    ]},
    # ============ 施法：双手抱在核心两侧蓄力，不推出 ============
    # ★ 按原版节奏结构：原版 cast 峰值出现在 0.41、89% 时间静止。
    #   我原来峰值在 0.87（快结束了才动），节奏完全反了。
    #   现在：静止起手 → 中段爆发收拢到核心 → 长静止捧住核心
    "cast": {"dur": 1.233, "keys": [
        (0.000, {}),
        (0.150, {}),                                        # 起手静止
        (0.280, {"Hips": {"rot": -1.0}, "Chest": {"rot": -2.0}, "Neck_3": {"rot": -3.0},
                 "R": {"ik": (66.0, 88.0)}, "L": {"ik": (-58.0, 100.0)}}),    # 抬手中（贴近静止，主位移留给 0.41）
        (0.410, {"Hips": {"rot": 0.0, "ty": -1.5}, "Chest": {"rot": -7.0}, "Neck_3": {"rot": -11.0},
                 "R": {"ik": (32.0, 100.0)}, "L": {"ik": (-31.0, 108.0)}}),   # 爆发合抱核心
        (0.470, {"Hips": {"ty": -2.0}, "Chest": {"rot": -8.0}, "Neck_3": {"rot": -12.0},
                 "R": {"ik": (31.0, 99.0)}, "L": {"ik": (-30.0, 107.0)}}),    # 过冲
        (0.560, {"Hips": {"ty": -1.8}, "Chest": {"rot": -7.5}, "Neck_3": {"rot": -11.0},
                 "R": {"ik": (32.0, 100.0)}, "L": {"ik": (-31.0, 108.0)}}),   # 稳住
        (0.800, {"Hips": {"ty": -1.6}, "Chest": {"rot": -7.0}, "Neck_3": {"rot": -10.5},
                 "R": {"ik": (32.0, 100.0)}, "L": {"ik": (-31.0, 108.0)}}),   # 长静止蓄力
        (1.233, {"Hips": {"ty": -1.6}, "Chest": {"rot": -7.0}, "Neck_3": {"rot": -10.5},
                 "R": {"ik": (32.0, 100.0)}, "L": {"ik": (-31.0, 108.0)}}),   # 保持到结束
    ]},
    # ============ 能力牌：被上方牵引、四肢自然下垂、微浮空后落回 ============
    # 原版 process 的发力点在 0.85（最后才爆发）且轨迹 3513，所以是「先长时间静立蓄势，
    # 最后猛地被拽起来」。我原来全程匀速上浮（静止比 0.11、峰值速度 6%）。
    "process": {"dur": 1.567, "keys": [
        (0.000, {}),
        (0.550, {}),                                                        # 静立蓄势
        (0.900, {"Hips": {"ty": 6.0}, "Chest": {"rot": -2.0}, "Neck_3": {"rot": -8.0},
                 "Arm_R_": {"rot": 10.0}, "Arm_L_": {"rot": -10.0}}),       # 缓慢离地
        (1.150, {"Hips": {"ty": 14.0}, "Chest": {"rot": -3.0}, "Neck_3": {"rot": -12.0},
                 "Arm_R_": {"rot": 18.0}, "Arm_R_2": {"rot": 10.0},
                 "Arm_L_": {"rot": -18.0}, "Arm_L_2": {"rot": -10.0}}),     # 继续上升
        (1.330, {"Hips": {"ty": 34.0}, "Chest": {"rot": -8.0}, "Neck_3": {"rot": -24.0},
                 "Arm_R_": {"rot": 30.0}, "Arm_R_2": {"rot": 18.0},
                 "Arm_L_": {"rot": -30.0}, "Arm_L_2": {"rot": -18.0}}),     # ★ 0.85 处猛地拽起（峰值）
        (1.450, {"Hips": {"ty": 22.0}, "Chest": {"rot": -5.0}, "Neck_3": {"rot": -16.0},
                 "Arm_R_": {"rot": 16.0}, "Arm_L_": {"rot": -16.0}}),       # 回落
        (1.567, {}),                                                        # 落地归位
    ]},
    # ============ 受击：上身后仰 ============
    # ★ 原版 hurt 的峰值出现在 0.00 —— 挨打是**一瞬间**的事，第一帧就已经到最大位移，
    #   后面全是恢复。我原来给了 0.12s 的加速过程（占 0.333s 的 36%），所以看着软。
    "hurt": {"dur": 0.333, "keys": [
        (0.000, {}),                                                          # 第 0 帧还是静止
        (0.020, {"Hips": {"tx": -6.0, "rot": 2.0, "ty": -2.0}, "Chest": {"rot": 17.0},
                 "Neck_3": {"rot": 24.0}, "Arm_R_": {"rot": 16.0}, "Arm_R_2": {"rot": 12.0},
                 "Arm_L_": {"rot": -16.0}, "Arm_L_2": {"rot": -12.0}}),       # ★ 1~2 帧内挨完打
        (0.110, {"Hips": {"tx": -2.6, "rot": 0.8}, "Chest": {"rot": 7.0},
                 "Neck_3": {"rot": 10.0}, "Arm_R_": {"rot": 6.0}, "Arm_L_": {"rot": -6.0}}),
        (0.210, {"Hips": {"tx": 1.0, "rot": -1.0}, "Chest": {"rot": -3.0},
                 "Neck_3": {"rot": -4.0}}),                                   # 回弹过冲
        (0.333, {}),                                                          # 归位
    ]},
    # ============ 死亡：膝盖先软、往后坐倒（用户确认的方案 B）============
    # 原版 die：静止比 0.63、发力点 0.56、峰值速度 9298、轨迹 4010
    # 所以是「站住不动 → 中段膝盖一软（快）→ 停一下 → 后仰倒下 → 长静止」
    "die": {"dur": 2.233, "keys": [
        (0.000, {}),
        (0.620, {}),                                                          # 站住不动
        (0.760, {"Hips": {"ty": -18.0, "rot": 5.0}, "Chest": {"rot": 9.0}, "Neck_3": {"rot": 11.0},
                 "Leg_L_": {"rot": -30.0}, "Leg_L_2": {"rot": 26.0},
                 "Leg_R_": {"rot": 28.0}, "Leg_R_2": {"rot": -23.0},
                 "Arm_R_": {"rot": 14.0}, "Arm_L_": {"rot": -14.0}}),         # ★ 0.14s 内膝盖一软
        (0.930, {"Hips": {"ty": -26.0, "tx": -4.0, "rot": 12.0}, "Chest": {"rot": 13.0},
                 "Neck_3": {"rot": 14.0}, "Leg_L_": {"rot": -40.0}, "Leg_L_2": {"rot": 35.0},
                 "Leg_R_": {"rot": 37.0}, "Leg_R_2": {"rot": -31.0},
                 "Arm_R_": {"rot": 18.0}, "Arm_L_": {"rot": -18.0}}),
        (1.250, {"Hips": {"ty": -40.0, "tx": -12.0, "rot": 30.0}, "Chest": {"rot": 17.0},
                 "Neck_3": {"rot": 17.0}, "Leg_L_": {"rot": -52.0}, "Leg_L_2": {"rot": 46.0},
                 "Leg_R_": {"rot": 48.0}, "Leg_R_2": {"rot": -40.0},
                 "Arm_R_": {"rot": 24.0}, "Arm_L_": {"rot": -24.0}}),         # 后仰加速
        (1.450, {"Hips": {"ty": -66.0, "tx": -26.0, "rot": 62.0}, "Chest": {"rot": 20.0},
                 "Neck_3": {"rot": 19.0}, "Leg_L_": {"rot": -64.0}, "Leg_L_2": {"rot": 58.0},
                 "Leg_R_": {"rot": 60.0}, "Leg_R_2": {"rot": -50.0},
                 "Arm_R_": {"rot": 28.0}, "Arm_L_": {"rot": -28.0}}),         # ★ 峰值：瘫下去
        (1.750, {"Hips": {"ty": -74.0, "tx": -30.0, "rot": 70.0}, "Chest": {"rot": 20.0},
                 "Neck_3": {"rot": 18.0}, "Leg_L_": {"rot": -68.0}, "Leg_L_2": {"rot": 62.0},
                 "Leg_R_": {"rot": 64.0}, "Leg_R_2": {"rot": -54.0},
                 "Arm_R_": {"rot": 28.0}, "Arm_L_": {"rot": -28.0}}),
        (2.233, {"Hips": {"ty": -76.0, "tx": -31.0, "rot": 72.0}, "Chest": {"rot": 20.0},
                 "Neck_3": {"rot": 18.0}, "Leg_L_": {"rot": -69.0}, "Leg_L_2": {"rot": 63.0},
                 "Leg_R_": {"rot": 65.0}, "Leg_R_2": {"rot": -55.0},
                 "Arm_R_": {"rot": 28.0}, "Arm_L_": {"rot": -28.0}}),         # 长静止（倒地不动）
    ]},
}


# ★ 全局幅度倍率：数值表显示「节奏结构已对（静止比 8/8、发力点 6/8），
#   但动作量只有原版的 12%~53%」——即动作太小、不够脆。
#   这里统一把姿势幅度放大，IK 目标则沿「静止手位 -> 目标」方向外推。
AMP = float(__import__("os").environ.get("ANIM_AMP", "1.5"))


def amplify(anims, sk, base_pos):
    import author_anims as A
    rest = {s: A.fk(sk, {}, base_pos)[A.CHAINS[s][2]][0] for s in ("R", "L")}
    out = {}
    for name, spec in anims.items():
        keys = []
        for tt, pose in spec["keys"]:
            np_ = {}
            for k, v in pose.items():
                if k in ("R", "L") and isinstance(v, dict) and "ik" in v:
                    rx, ry = rest[k]
                    tx, ty = v["ik"]
                    nv = {"ik": (rx + (tx - rx) * AMP, ry + (ty - ry) * AMP)}
                    if v.get("frame"):
                        nv["frame"] = v["frame"]
                    np_[k] = nv
                elif isinstance(v, dict):
                    np_[k] = {kk: (vv * AMP if isinstance(vv, (int, float)) else vv)
                              for kk, vv in v.items()}
                else:
                    np_[k] = v
            keys.append((tt, np_))
        out[name] = {"dur": spec["dur"], "keys": keys}
    return out


def main():
    sk = A.load()
    # ★ 根骨骼缩放：手写动画后不再走 retarget_anims.py，但游戏里的世界尺寸靠它。
    #   实测基准：游戏原版 Defect 身体高 1828.5，一代骨架在 scale=1 时身体高 182.37。
    ROOT_SCALE = 1828.5 / 182.37
    for b in sk["bones"]:
        if b["name"] == "root":
            b["scaleX"] = b["scaleY"] = round(ROOT_SCALE, 4)
    print(f"  根骨骼缩放 = {ROOT_SCALE:.3f}")
    base_pos = {b["name"]: (b.get("x", 0.0) or 0.0, b.get("y", 0.0) or 0.0) for b in sk["bones"]}
    bad = 0
    print(f"  全局幅度倍率 AMP = {AMP}")
    for name, spec in amplify(ANIMS, sk, base_pos).items():
        for t, pose in spec["keys"]:
            # 用解算残差判断可达性（肩膀位置会随身体旋转移动，不能用静止位置估算）
            rots = {}
            for k, v in pose.items():
                if k not in ("R", "L") and isinstance(v, dict) and "rot" in v:
                    rots[k] = v["rot"]
            for side in ("R", "L"):
                if side in pose and isinstance(pose[side], dict) and not pose[side].get("frame"):
                    *_, err = A.solve_ik(sk, A.CHAINS[side], pose[side]["ik"], rots, base_pos)
                    if err > 3.0:
                        print(f"  ⚠ {name}@{t}s {side} 目标{pose[side]['ik']} 够不到，残差 {err:.1f}")
                        bad += 1
        baked, dur = A.bake(sk, spec["keys"], base_pos)
        A.write_anim(sk, name, baked, dur)
        print(f"  ✅ {name:<15} {len(baked)} 骨骼 {dur:.3f}s")
    A.JSON_PATH.write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入。超出可达范围的目标: {bad} 个")


if __name__ == "__main__":
    main()
