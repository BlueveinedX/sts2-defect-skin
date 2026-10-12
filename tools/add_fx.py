#!/usr/bin/env python3
"""补齐二代特有的特效部件（程序化生成贴图 + 扩图集 + 加插槽/附件 + 加透明度时间轴）。

为什么能用「插槽透明度」实现显隐：
  实测 Spine 4.2 的插槽 rgba 时间轴是**绝对值**语义
  （setup 色 `ffffff00` + 时间轴 `ff000080` → 结果正是 (1,0,0,0.5)）。
  所以把特效插槽的 setup alpha 设为 0（不可见），只在需要时用 rgba 时间轴把 alpha 打上去即可。
  —— 比用 attachment 时间轴可靠（实测 attachment 时间轴在 4.2 里没生效）。

覆盖了二代 Defect 出现过的特效部件族：
  glowie*（法球光晕）、blender_*（手部拖影/锥光）、binder_bolt（小电弧）、
  blip_star（星闪）、flare（爆闪）、deathspark（放射火花）
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent.parent
RIG = HERE / "godot-project/animations/characters/defect"
ATLAS = RIG / "DefectSTS1.atlas"
PNG = RIG / "DefectSTS1.png"
JSON = RIG / "DefectSTS1.spine-json"

# 一代 Defect 的配色：青蓝 + 白
CYAN = (0, 226, 255)
PALE = (186, 245, 255)
WHITE = (255, 255, 255)


# ------------------------------------------------------------------ 贴图生成
def radial(size: int, color, power: float = 2.2, core: float = 0.0) -> Image.Image:
    """径向柔光。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = size / 2.0
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c + 0.5, y - c + 0.5) / c
            if d >= 1.0:
                continue
            a = (1.0 - d) ** power
            if core:
                a = min(1.0, a + core * (1.0 - d) ** (power * 5))
            px[x, y] = (*color, int(255 * max(0.0, min(1.0, a))))
    return img


def streak(w: int, h: int, color, fade_right: bool = True) -> Image.Image:
    """沿 X 的柔光条（手部拖影）。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            u = x / (w - 1)
            t = (1.0 - u) if fade_right else u
            vy = 1.0 - abs(y - (h - 1) / 2.0) / ((h - 1) / 2.0)
            a = (t ** 1.6) * (vy ** 1.8)
            px[x, y] = (*color, int(255 * max(0.0, min(1.0, a))))
    return img.filter(ImageFilter.GaussianBlur(1.2))


def bolt(w: int, h: int, color) -> Image.Image:
    """小电弧（锯齿折线 + 模糊发光）。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    n = 7
    for i in range(n + 1):
        x = 2 + (w - 4) * i / n
        y = h / 2 + (h * 0.30) * (1 if i % 2 else -1) * (0.4 + 0.6 * (i / n))
        pts.append((x, y))
    d.line(pts, fill=(*color, 255), width=max(2, h // 12), joint="curve")
    glow = img.filter(ImageFilter.GaussianBlur(max(2, h // 8)))
    return Image.alpha_composite(glow, img)


def starflash(size: int, color) -> Image.Image:
    """四角星闪。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2.0
    for sgn in (1, -1):
        d.polygon([(c, 0), (c + size * 0.055, c), (c, size), (c - size * 0.055, c)],
                  fill=(*color, 255))
        d.polygon([(0, c), (c, c + size * 0.055), (size, c), (c, c - size * 0.055)],
                  fill=(*color, 255))
    soft = img.filter(ImageFilter.GaussianBlur(size * 0.06))
    return Image.alpha_composite(soft, img)


def sparkburst(size: int, color, rays: int = 14) -> Image.Image:
    """放射火花。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2.0
    for i in range(rays):
        a = 2 * math.pi * i / rays + 0.17
        r0, r1 = size * 0.16, size * (0.42 if i % 2 else 0.30)
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)),
                (c + r1 * math.cos(a), c + r1 * math.sin(a))],
               fill=(*color, 255), width=max(1, size // 48))
    soft = img.filter(ImageFilter.GaussianBlur(size * 0.03))
    core = radial(int(size * 0.42), color, power=1.6, core=0.6)
    img = Image.alpha_composite(soft, img)
    img.alpha_composite(core, (int(c - size * 0.21), int(c - size * 0.21)))
    return img


# 附件尺寸相对贴图像素的缩放系数（骨架单位 vs 贴图像素）
FX_SCALE = 0.45

# (名称, 生成函数, 贴图宽, 贴图高, 挂到哪根骨骼, 图层位置)
FX = [
    ("glowie1",      lambda: radial(96, CYAN, 2.4, 0.35),            96,  96, "Hips_sphere", "back"),
    ("glowie2",      lambda: radial(64, PALE, 2.0, 0.5),             64,  64, "Hips_sphere", "back"),
    ("blender_blur", lambda: streak(112, 26, PALE),                 112,  26, "Arm_R_3",     "front"),
    ("blender_whisp_1", lambda: streak(112, 34, CYAN, False),       112,  34, "Arm_L_3",     "front"),
    ("binder_bolt",  lambda: bolt(72, 40, PALE),                     72,  40, "Arm_R_3",     "front"),
    ("blip_star",    lambda: starflash(56, WHITE),                   56,  56, "Neck_3",      "front"),
    ("flare",        lambda: radial(176, WHITE, 1.7, 0.55),         176, 176, "Hips_sphere", "front"),
    ("deathspark",   lambda: sparkburst(128, CYAN),                 128, 128, "Hips_sphere", "front"),
]


# ------------------------------------------------------------------ 图集
def extend_atlas() -> dict[str, tuple[int, int]]:
    """把特效贴图拼到原图下方，返回 {名称: (宽,高)}。"""
    base = Image.open(PNG).convert("RGBA")
    W = max(base.width, 464)

    imgs = []
    for name, gen, w, h, _bone, _layer in FX:
        imgs.append((name, gen(), w, h))

    band_h = 0
    shelf_x, shelf_y, shelf_h = 2, 2, 0
    rects: dict[str, tuple[int, int]] = {}
    for name, im, w, h in imgs:
        if shelf_x + w + 2 > W:
            shelf_x = 2
            shelf_y += shelf_h + 2
            shelf_h = 0
        rects[name] = (shelf_x, shelf_y, w, h)
        shelf_x += w + 2
        shelf_h = max(shelf_h, h)
    band_h = shelf_y + shelf_h + 2

    page = Image.new("RGBA", (W, base.height + band_h), (0, 0, 0, 0))
    # ★ 必须用 paste（无 mask）而不是 alpha_composite：
    #   alpha_composite 会做 out = src*src.a + dst*(1-src.a)，在透明底上等于把 RGB
    #   乘上 alpha（预乘），而 Spine/Godot 用的是**直通 alpha**，渲染时会再乘一次，
    #   半透明特效就会明显发暗。paste 是逐像素覆写，RGB 与 A 原样保留。
    page.paste(base, (0, 0))
    for name, im, w, h in imgs:
        x, y, _, _ = rects[name]
        page.paste(im, (x, base.height + y))
    page.save(PNG)
    print(f"  图集: {base.width}x{base.height} -> {W}x{page.height}")

    # 重写 atlas 文本
    text = ATLAS.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    for ln in lines:
        if ln.strip().startswith("size:"):
            out.append(f"\tsize: {W}, {page.height}")
        else:
            out.append(ln)
    for name, _gen, w, h, _bone, _layer in FX:
        x, y, _, _ = rects[name]
        out.append(name)
        out.append(f"\tbounds: {x}, {base.height + y}, {w}, {h}")
    ATLAS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  atlas 区域: 32 -> {32 + len(FX)}")
    return {n: (rects[n][2], rects[n][3]) for n in rects}


# ------------------------------------------------------------------ 骨架
def patch_skeleton(sizes: dict[str, tuple[int, int]]) -> None:
    sk = json.loads(JSON.read_text(encoding="utf-8"))

    back = [f for f in FX if f[5] == "back"]
    front = [f for f in FX if f[5] == "front"]

    def make_slot(name: str, bone: str) -> dict:
        return {"name": name, "bone": bone, "attachment": name, "color": "ffffff00"}

    # 背面层插到 shadow 之后；正面层追加到末尾
    idx = next(i for i, s in enumerate(sk["slots"]) if s["name"] == "shadow") + 1
    for name, _g, _w, _h, bone, _l in back:
        sk["slots"].insert(idx, make_slot(name, bone))
        idx += 1
    for name, _g, _w, _h, bone, _l in front:
        sk["slots"].append(make_slot(name, bone))

    # 皮肤附件（居中对齐到骨骼原点）
    atts = sk["skins"][0]["attachments"]
    # ★ 附件尺寸按「骨架单位」算，不按贴图像素。骨架 root 缩放了约 10 倍，
    #   直接用贴图尺寸(96~176)会让特效占掉身体的一半，缩到 45% 才像光效。
    for name, _g, w, h, _bone, _l in FX:
        aw, ah = w * FX_SCALE, h * FX_SCALE
        atts.setdefault(name, {})[name] = {
            "x": -aw / 2.0, "y": -ah / 2.0, "width": aw, "height": ah}

    print(f"  插槽: {len(sk['slots'])} 个（新增 {len(FX)}）")

    # ---- 透明度时间轴 ----
    # 值为「绝对颜色」，alpha 0 = 不可见。曲线缺省即线性（4.2 里 "linear" 会崩，别写）
    def tl(pairs):
        return [{"time": round(t, 4), "color": f"ffffff{int(round(a * 255)):02x}"}
                for t, a in pairs]

    def add(anim: str, slot: str, pairs) -> None:
        a = sk["animations"].setdefault(anim, {})
        a.setdefault("slots", {}).setdefault(slot, {})["rgba"] = tl(pairs)

    if "idle_loop" in sk["animations"]:
        add("idle_loop", "glowie1", [(0, 0.20), (3.33, 0.42), (6.66, 0.20)])
        add("idle_loop", "glowie2", [(0, 0.10), (1.66, 0.28), (3.33, 0.12),
                                     (5.0, 0.26), (6.66, 0.10)])
    add("relaxed_loop", "glowie1", [(0, 0.26), (4, 0.40), (8, 0.22), (12, 0.26)])
    add("low_health_loop", "glowie1",
        [(0, 0.10), (1.5, 0.05), (3, 0.16), (4.5, 0.04), (6, 0.12), (8, 0.06),
         (10, 0.14), (12, 0.10)])
    add("low_health_loop", "glowie2", [(0, 0.06), (5, 0.02), (9, 0.08), (12, 0.06)])
    add("process", "glowie1", [(0, 0.25), (0.5, 0.75), (0.9, 0.45), (1.2, 0.85), (1.57, 0.30)])
    add("process", "glowie2", [(0, 0.10), (0.6, 0.55), (1.0, 0.25), (1.3, 0.60), (1.57, 0.15)])
    add("process", "blip_star", [(0, 0), (0.55, 0.55), (0.75, 0.10), (1.25, 0.65), (1.5, 0)])
    add("cast", "blender_whisp_1", [(0, 0), (0.45, 0.85), (0.8, 0.95), (1.233, 0)])
    add("cast", "blender_blur", [(0, 0), (0.5, 0.7), (0.85, 0.85), (1.233, 0)])
    add("cast", "binder_bolt", [(0, 0), (0.35, 0.55), (0.6, 0.15), (0.9, 0.7), (1.233, 0)])
    add("cast", "glowie2", [(0, 0.15), (0.6, 0.8), (1.233, 0)])
    add("attack", "blender_blur", [(0, 0), (0.55, 0.15), (0.7, 0.9), (0.95, 0.25), (1.5, 0)])
    add("attack", "binder_bolt", [(0, 0), (0.5, 0.2), (0.68, 0.8), (0.9, 0), (1.5, 0)])
    add("attack", "blip_star", [(0, 0), (0.6, 0.7), (0.78, 0.12), (1.5, 0)])
    add("attack", "glowie2", [(0, 0.12), (0.65, 0.55), (1.5, 0)])
    add("hurt", "glowie1", [(0, 0.55), (0.15, 0.25), (0.3333, 0.12)])
    add("hurt", "deathspark", [(0, 0.55), (0.12, 0.20), (0.3333, 0)])
    add("die", "glowie1", [(0, 0.35), (0.9, 0.15), (2.2333, 0)])
    add("die", "deathspark", [(0, 0), (1.4, 0.55), (1.7, 0.85), (2.2333, 0)])
    add("die", "flare", [(0, 0), (1.55, 0.30), (1.75, 0.95), (2.2333, 0)])

    # ★ Spine 里「动画没 key 的属性会沿用上一个动画的残留值」。
    #   所以循环动画（玩家一定会回到的状态）必须把一次性特效显式清零，
    #   否则 die 打完 flare=0.95 之后切回 idle，那道白光会一直挂着。
    RESET = ["blender_blur", "blender_whisp_1", "binder_bolt", "blip_star",
             "flare", "deathspark"]
    # 每个动画都要把「它没用到的特效」显式清零：Spine 里未 key 的属性会沿用残留值，
    # 否则 cast 用过的手部拖影会一直挂到 die 上。
    DUR = {"idle_loop": 6.0, "relaxed_loop": 8.0, "low_health_loop": 6.0,
           "process": 1.5667, "attack": 1.5, "cast": 1.2333, "hurt": 0.3333, "die": 2.2333}
    for anim, dur in DUR.items():
        if anim not in sk["animations"]:
            continue
        keyed = set(sk["animations"][anim].get("slots", {}))
        for slot in RESET:
            if slot not in keyed:
                add(anim, slot, [(0, 0), (dur, 0)])
    add("hurt", "flare", [(0, 0), (0.3333, 0)])
    add("hurt", "blip_star", [(0, 0), (0.3333, 0)])

    JSON.write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  动画里的特效时间轴已加入")


def main() -> int:
    if not JSON.exists():
        raise SystemExit("先跑 tools/sts1_to_spine42.py 和 tools/retarget_anims.py")
    print("生成特效部件")
    sizes = extend_atlas()
    patch_skeleton(sizes)
    print("\n完成。记得重跑 make_rigs.py 与 assemble.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
