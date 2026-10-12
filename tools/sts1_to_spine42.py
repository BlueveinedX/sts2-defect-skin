#!/usr/bin/env python3
"""把一代《杀戮尖塔》Defect 的 Spine 3.4 资产转成 Spine 4.2（供 Godot 4.5.1 导入）。

做两件事：
  1) atlas：3.4 文本格式 → 4.x 文本格式
       3.4:  xy: x,y  / size: w,h / orig: W,H / offset: ox,oy / rotate: true|false
       4.x:  bounds: x,y,w,h / offsets: ... / rotate: 90
       ★ 实测一代 Defect 图集 32 个区域**全部未裁剪**（orig==size 且 offset==0），
         所以不需要写 offsets，转换是纯机械的。
  2) skeleton：3.4 JSON → 4.2 JSON
       - skeleton 头改成 spine 4.2.43
       - 动画 Idle→idle_loop、Hit→hurt（二代代码硬编码这两个名字）
       - ik 补 order（4.x 需要）
       - 其余（bones/slots/skins/时间轴）先原样搬运，由 Godot 校验后按报错迭代

输出直接写到 godot-project/ 的目标路径下，随后交给 assemble.py 导入。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "ref-sts1/images/characters/defect/idle"
PROJ = HERE / "godot-project"

ANIM_RENAME = {"Idle": "idle_loop", "Hit": "hurt"}

# 我们自己的资源路径（assemble.py 里的 GROUPS 必须与此一致）
OUT_ATLAS = PROJ / "animations/characters/defect/DefectSTS1.atlas"
OUT_JSON = PROJ / "animations/characters/defect/DefectSTS1.spine-json"
OUT_PNG = PROJ / "animations/characters/defect/DefectSTS1.png"


# ------------------------------------------------------------------ atlas
PAGE_HEADER_KEYS = {"size", "format", "filter", "repeat", "pma"}


def convert_atlas(text: str, new_page: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    regions = 0
    i = 0
    page_written = False

    while i < len(lines):
        ln = lines[i]
        key = ln.split(":", 1)[0].strip() if ":" in ln else None

        # ---- 页头 ----
        if not page_written:
            if i == 0:
                # 第一行 = 原始页名，替换成我们自己的 png 名
                out.append(new_page)
                i += 1
                continue
            if key in PAGE_HEADER_KEYS:
                v = ln.split(":", 1)[1].strip()
                if key == "size":
                    # 4.x 里逗号后有空格
                    a, b = [t.strip() for t in v.split(",")]
                    out.append(f"\tsize: {a}, {b}")
                elif key == "filter":
                    a, b = ([t.strip() for t in v.split(",")] + ["Linear"])[:2]
                    out.append(f"\tfilter: {a}, {b}")
                elif key == "repeat":
                    if v.lower() != "none":
                        out.append(f"\trepeat: {v.lower()}")
                elif key == "pma":
                    if v.lower() == "true":
                        out.append("\tpma: true")
                # format 在 4.x 里由运行时自己判，丢弃
                i += 1
                continue
            page_written = True  # 到这里页头结束，开始区域

        # ---- 区域 ----
        name = ln
        attrs: dict[str, str] = {}
        i += 1
        while i < len(lines):
            a = lines[i]
            k = a.split(":", 1)[0].strip() if ":" in a else None
            if k in PAGE_HEADER_KEYS or a.startswith(("rotate", "xy", "size", "orig",
                                                      "offset", "index", "bounds", "offsets")):
                kk, vv = a.split(":", 1)
                attrs[kk.strip()] = vv.strip()
                i += 1
            else:
                break

        if "xy" in attrs:
            x, y = [t.strip() for t in attrs["xy"].split(",")]
            w, h = [t.strip() for t in attrs["size"].split(",")]
            rotated = attrs.get("rotate", "false").lower() == "true"
            # ★ 3.4 的 size 是「未旋转」尺寸；4.x 的 bounds 是页面内实际占位，
            #   旋转 90° 后占位宽高互换。实测 left_arm / left_quad 不互换会溢出页面。
            bw, bh = w, h   # ★ 实测：bounds 存「未旋转尺寸」，占位由运行时互换（互换会错位致断缝）
            out.append(name)
            out.append(f"\tbounds: {x}, {y}, {bw}, {bh}")
            if rotated:
                out.append("\trotate: 90")
            if "index" in attrs and attrs["index"] != "-1":
                out.append(f"\tindex: {attrs['index']}")
            regions += 1
        else:
            raise SystemExit(f"atlas 解析异常，区域 {name!r} 没有 xy 属性：{attrs}")

    if not page_written:
        raise SystemExit("atlas 里没找到任何区域")
    print(f"  atlas: 转换 {regions} 个区域，页名 -> {new_page}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ 贝塞尔烘焙
# ★ 实测的 spine-cpp 4.2 缺陷：translate / scale / shear 这三类时间轴里
#   只要出现贝塞尔曲线数组（"curve": [x1,y1,x2,y2]）就会 **signal 11 硬崩**；
#   而 rotate / deform / color / ik 带贝塞尔完全正常。
#   规避办法：把这三类的贝塞尔**按帧烘焙成密集的线性关键帧**，
#   既绕开崩溃，又保留原来的缓动手感（比直接改成 linear 好得多）。
BEZIER_UNSAFE = {"translate", "scale", "shear"}
BAKE_FPS = 30
BAKE_MAX_PER_SEG = 12


def _bezier_ease(u: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """单位三次贝塞尔缓动：给定归一化时间 u，求归一化进度 y。"""
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0

    def cx(t: float) -> float:
        return 3.0 * (1 - t) ** 2 * t * x1 + 3.0 * (1 - t) * t ** 2 * x2 + t ** 3

    def cy(t: float) -> float:
        return 3.0 * (1 - t) ** 2 * t * y1 + 3.0 * (1 - t) * t ** 2 * y2 + t ** 3

    lo, hi = 0.0, 1.0
    for _ in range(24):  # 二分足够精确，且不会发散
        mid = (lo + hi) / 2
        if cx(mid) < u:
            lo = mid
        else:
            hi = mid
    return cy((lo + hi) / 2)


def _kf_channels(kf: dict):
    """抽出关键帧的数值通道。返回 (类型, 数值列表)。"""
    if "color" in kf:
        h = kf["color"]
        return "hex", [int(h[i:i + 2], 16) / 255.0 for i in range(0, len(h), 2)]
    if "value" in kf:
        return "scalar", [float(kf["value"])]
    vals = [float(kf[a]) for a in ("x", "y") if a in kf]
    return ("xy" if vals else None), vals


def _set_channels(kf: dict, kind: str, vals: list) -> None:
    if kind == "hex":
        kf["color"] = "".join("%02x" % max(0, min(255, round(v * 255))) for v in vals)
    elif kind == "scalar":
        kf["value"] = round(vals[0], 6)
    else:
        if len(vals) >= 1:
            kf["x"] = round(vals[0], 6)
        if len(vals) >= 2:
            kf["y"] = round(vals[1], 6)


def bake_timeline(tl: list) -> list:
    """把一条时间轴里的贝塞尔段烘焙成密集的线性关键帧（保留缓动手感）。

    通用实现：既支持骨骼的 x/y，也支持插槽颜色时间轴的 "rrggbbaa" 十六进制。
    """
    out: list = []
    for i, kf in enumerate(tl):
        curve = kf.get("curve")
        new_kf = {k: v for k, v in kf.items() if k != "curve"}
        if curve is not None and not isinstance(curve, list):
            new_kf["curve"] = curve  # 保留 stepped
        out.append(new_kf)

        if i == len(tl) - 1 or not isinstance(curve, list) or len(curve) != 4:
            continue
        nxt = tl[i + 1]
        k0, a = _kf_channels(kf)
        k1, b = _kf_channels(nxt)
        if k0 is None or k0 != k1 or len(a) != len(b):
            continue
        t0, t1 = kf.get("time", 0.0), nxt.get("time", 0.0)
        dur = t1 - t0
        if dur <= 0 or all(abs(x - y) < 1e-9 for x, y in zip(a, b)):
            continue
        n = min(BAKE_MAX_PER_SEG, max(1, int(round(dur * BAKE_FPS))))
        x1, y1, x2, y2 = (float(v) for v in curve)
        for k in range(1, n):
            u = k / n
            e = _bezier_ease(u, x1, y1, x2, y2)
            mid: dict = {"time": round(t0 + dur * u, 5)}
            _set_channels(mid, k0, [av + (bv - av) * e for av, bv in zip(a, b)])
            out.append(mid)
    return out


def _has_bezier(tl: list) -> bool:
    return any(isinstance(f.get("curve"), list) for f in tl)


# 实测会崩：骨骼 translate/scale/shear + 插槽颜色时间轴，只要带贝塞尔数组就 signal 11
BEZIER_UNSAFE_BONE = {"translate", "scale", "shear"}
BEZIER_UNSAFE_SLOT = {"rgba", "rgb", "color", "alpha", "twoColor"}


def bake_animation(a: dict) -> tuple[int, int]:
    nb = ns = 0
    for _bone, tl_map in a.get("bones", {}).items():
        for kind in list(tl_map):
            if kind in BEZIER_UNSAFE_BONE and _has_bezier(tl_map[kind]):
                tl_map[kind] = bake_timeline(tl_map[kind])
                nb += 1
    for _slot, tl_map in a.get("slots", {}).items():
        for kind in list(tl_map):
            if kind in BEZIER_UNSAFE_SLOT and _has_bezier(tl_map[kind]):
                tl_map[kind] = bake_timeline(tl_map[kind])
                ns += 1
    return nb, ns


# 4.2 把插槽颜色时间轴的键名从 3.4 的 "color" 改成了 "rgba"
SLOT_TIMELINE_RENAME = {"color": "rgba"}


# ★ 实测：Spine 4.2 的 rotate 时间轴关键帧字段是 "value"，不是 3.4 的 "angle"。
#   用 angle 时**整个旋转时间轴被静默忽略**（不报错、不崩溃），表现为：
#   「骨骼姿势永远停在 setup pose，动画只剩位移和插槽颜色」——
#   攻击/施法看起来"没有身体动作，只有特效"就是这个原因。
def fix_rotate_field(a: dict) -> int:
    n = 0
    for _bone, tl_map in a.get("bones", {}).items():
        for f in tl_map.get("rotate", []):
            if "angle" in f:
                f["value"] = f.pop("angle")
                n += 1
    return n


def fix_slot_timelines(a: dict) -> int:
    n = 0
    slots = a.get("slots")
    if not slots:
        return 0
    for _slot, tl_map in slots.items():
        for old, new in SLOT_TIMELINE_RENAME.items():
            if old in tl_map:
                tl_map[new] = tl_map.pop(old)
                n += 1
    return n



# ------------------------------------------------------------------ 稀疏关键帧加密+平滑
# 一代原版的 Idle 里，眼球/手指这类骨骼只有 6~12 个关键帧却要跨越 13°~53°，
# 线性插值会在每个关键帧处形成"折角" → 表现出来就是"低头抬头"和"手臂颤动"。
# 修法：把这类稀疏时间轴按 60fps 重采样成密集关键帧，再做 2 次 3 点二项式平滑。
SMOOTH_MAX_KEYS = 24      # 关键帧数 ≤ 此值才处理（密集的本就平滑）
SMOOTH_FPS = 60
SMOOTH_PASSES = 2
SMOOTH_DECIMATE = 2   # 平滑后降采样倍数（60fps -> 30fps）

# 要「钉死」的骨骼时间轴：眼球镜片与胸口法球在待机时会漂移/摆动，用户要求固定。
PINNED = {
    "Eye_up": ["rotate", "translate", "scale"],
    "Eye_down": ["rotate", "translate", "scale"],
    "Hips_sphere": ["rotate", "translate", "scale"],
    "Hips_sphere_glow": ["rotate", "translate", "scale"],
}


def _eval_linear(tl: list, t: float, key: str) -> float:
    if not tl:
        return 0.0
    prev = None
    for kf in tl:
        kt = kf.get("time", 0.0)
        if kt > t:
            if prev is None:
                return float(kf.get(key, 0.0))
            span = kt - prev.get("time", 0.0)
            u = 0.0 if span <= 0 else (t - prev["time"]) / span
            if prev.get("curve") == "stepped":
                return float(prev.get(key, 0.0))
            return float(prev.get(key, 0.0)) + (float(kf.get(key, 0.0)) - float(prev.get(key, 0.0))) * u
        prev = kf
    return float(prev.get(key, 0.0))


def _smooth_series(v: list, passes: int = SMOOTH_PASSES) -> list:
    n = len(v)
    if n < 5:
        return v
    for _ in range(passes):
        out = list(v)
        for i in range(1, n - 1):
            out[i] = (v[i - 1] + 2.0 * v[i] + v[i + 1]) * 0.25
        v = out
    return v


def densify_animation(a: dict) -> int:
    """把稀疏时间轴按 60fps 加密并平滑；返回处理的条数。"""
    n_done = 0
    for _bone, tl_map in a.get("bones", {}).items():
        for kind, keys in (("rotate", ["value"]), ("translate", ["x", "y"]),
                           ("scale", ["x", "y"])):
            tl = tl_map.get(kind)
            if not tl or len(tl) > SMOOTH_MAX_KEYS:
                continue
            dur = float(tl[-1].get("time", 0.0))
            if dur <= 0.05:
                continue
            present = [k for k in keys if k in tl[0]]
            if not present:
                continue
            frames = int(dur * SMOOTH_FPS) + 1
            series = {k: _smooth_series([_eval_linear(tl, i / SMOOTH_FPS, k)
                                         for i in range(frames)]) for k in present}
            # 平滑已经在 60fps 上做完，再降到 30fps 写关键帧：
            # 平滑后的信号几乎没有 15Hz 以上成分，降采样不丢东西，体积减半。
            keep = list(range(0, frames, SMOOTH_DECIMATE))
            if keep[-1] != frames - 1:
                keep.append(frames - 1)
            new_tl = []
            for i in keep:
                kf = {"time": round(i / SMOOTH_FPS, 4)}
                for k in present:
                    kf[k] = round(series[k][i], 4)
                new_tl.append(kf)
            tl_map[kind] = new_tl
            n_done += 1
    return n_done


def pin_bones(a: dict) -> int:
    """删掉指定骨骼的局部时间轴，让这些部件死死固定在父骨骼上。"""
    n = 0
    for bone, kinds in PINNED.items():
        tl_map = a.get("bones", {}).get(bone)
        if not tl_map:
            continue
        for k in kinds:
            if k in tl_map:
                del tl_map[k]
                n += 1
        if not tl_map:
            del a["bones"][bone]
    return n

# ------------------------------------------------------------------ skeleton
def convert_skeleton(d: dict) -> dict:
    sk = dict(d)
    sk["skeleton"] = {
        "hash": d["skeleton"].get("hash", ""),
        "spine": "4.2.43",
        "width": d["skeleton"].get("width", 0),
        "height": d["skeleton"].get("height", 0),
        "images": d["skeleton"].get("images", "./images/"),
        "fps": 30,
    }

    # ik 补 order（4.x 需要；3.4 没有）
    if sk.get("ik"):
        for idx, c in enumerate(sk["ik"]):
            c.setdefault("order", idx)
        print(f"  ik: 补 order，共 {len(sk['ik'])} 条")

    # 动画改名 + 烘焙危险贝塞尔 + 修插槽时间轴键名
    anims = {}
    nb = ns = 0
    renamed = 0
    rot_fixed = 0
    pinned = 0
    densified = 0
    for name, a in d.get("animations", {}).items():
        b, s = bake_animation(a)
        nb += b; ns += s
        renamed += fix_slot_timelines(a)
        rot_fixed += fix_rotate_field(a)
        pinned += pin_bones(a)
        densified += densify_animation(a)
        anims[ANIM_RENAME.get(name, name)] = a
    sk["animations"] = anims
    print(f"  动画: {list(d.get('animations', {}))} -> {list(anims)}")
    print(f"  烘焙贝塞尔：骨骼时间轴 {nb} 条 + 插槽颜色 {ns} 条（规避 spine-cpp 4.2 崩溃）")
    print(f"  插槽时间轴 color -> rgba 重命名 {renamed} 条（4.2 改名）")
    print(f"  rotate 关键帧 angle -> value 修正 {rot_fixed} 个（4.2 改名，否则旋转被忽略）")
    print(f"  钉死漂移部件（眼球镜片/胸口法球）{pinned} 条时间轴")
    print(f"  稀疏关键帧加密+平滑 {densified} 条（治‘低头抬头/手臂颤动’）")

    # ★ 关键修正：Spine 4.2 **不再支持 3.4 的对象式 skins 格式**
    #   （{"default": {slot: {att: {...}}}}）。4.2 的 readSkin 只认 "attachments" 键，
    #   对象式会被静默读成 0 个附件 —— 表现为「骨骼动画全对，但角色完全隐形」。
    #   实测证据：转换后 33 个插槽 get_attachment() 全部为 null。
    #   必须改成数组式：[{"name": "default", "attachments": {slot: {att: {...}}}}]
    old_skins = d["skins"]
    if isinstance(old_skins, dict):
        sk["skins"] = [{"name": name, "attachments": slots}
                       for name, slots in old_skins.items()]
        print(f"  skins: 对象式 -> 4.2 数组式，{len(old_skins)} 个皮肤")
    else:
        sk["skins"] = old_skins

    slots_map = sk["skins"][0]["attachments"] if sk["skins"] else {}
    n_mesh = sum(1 for s in slots_map.values()
                 for a in s.values() if a.get("type") == "mesh")
    n_reg = sum(1 for s in slots_map.values()
                for a in s.values() if a.get("type") != "mesh")
    print(f"  附件: mesh {n_mesh} 个 / 其它 {n_reg} 个；骨骼 {len(d['bones'])} 根；插槽 {len(d['slots'])} 个")
    return sk


# ------------------------------------------------------------------ main
def main() -> int:
    atlas_text = (SRC / "skeleton.atlas").read_text(encoding="utf-8")
    skel = json.loads((SRC / "skeleton.json").read_text(encoding="utf-8"))

    print("转换 atlas → 4.x")
    new_atlas = convert_atlas(atlas_text, OUT_PNG.name)
    print("转换 skeleton → 4.2")
    new_skel = convert_skeleton(skel)

    for p in (OUT_ATLAS, OUT_JSON, OUT_PNG):
        p.parent.mkdir(parents=True, exist_ok=True)

    OUT_ATLAS.write_text(new_atlas, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(new_skel, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_PNG.write_bytes((SRC / "defect.png").read_bytes())

    print(f"\n写出：")
    for p in (OUT_ATLAS, OUT_JSON, OUT_PNG):
        print(f"  {p.relative_to(HERE)}  ({p.stat().st_size} 字节)")
    print("\n--- 新 atlas 前 20 行 ---")
    print("\n".join(new_atlas.splitlines()[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
