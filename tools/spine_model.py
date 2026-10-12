#!/usr/bin/env python3
"""极简 Spine 4.2 骨架模型：世界变换计算 + 动画采样 + 火柴人预览。

只用于**理解和创作动画**（不追求渲染精度）：
  · 支持 bones / slots / 默认皮肤 / rotate+translate+scale 时间轴 / 插槽 rgba
  · 忽略 shear 与网格权重（对火柴人预览影响很小）
  · 时间轴采用线性插值；stepped 按阶梯处理

用途：
  · layout()  打印 setup pose 各骨骼的世界坐标，搞清角色朝向与比例
  · pose_at() 采样某动画某时刻的骨骼世界变换
  · draw()    画成 PNG 火柴人 + 附件框，用来肉眼验证姿势

命令行：
  python3 tools/spine_model.py layout <skeleton.spine-json>
  python3 tools/spine_model.py draw   <skeleton.spine-json> <atlas匹配的png> <输出png> [动画名] [时间]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# PIL u5ef6u8fdfu5bfcu5165uff08layout u547du4ee4u4e0du9700u8981uff09


# ------------------------------------------------------------------ 模型
class Skeleton:
    def __init__(self, data: dict):
        self.data = data
        self.bones = data["bones"]
        self.bone_by_name = {b["name"]: b for b in self.bones}
        self.order = [b["name"] for b in self.bones]
        # 索引（时间轴按名查）
        self.idx = {n: i for i, n in enumerate(self.order)}
        self.slots = data["slots"]
        self.skins = data.get("skins")
        self.rest = self._rest_pose()

    # ---------- 静态定义 ----------
    def _rest_pose(self) -> dict:
        """setup pose 的局部变换（缺省值补全）。"""
        r = {}
        for b in self.bones:
            r[b["name"]] = {
                "x": float(b.get("x", 0.0)),
                "y": float(b.get("y", 0.0)),
                "rotation": float(b.get("rotation", 0.0)),
                "scaleX": float(b.get("scaleX", 1.0)),
                "scaleY": float(b.get("scaleY", 1.0)),
                "length": float(b.get("length", 0.0)),
            }
        return r

    def reset(self) -> None:
        self.local = {k: dict(v) for k, v in self.rest.items()}

    # ---------- 时间轴求值 ----------
    @staticmethod
    def _sample(tl: list, t: float, field: str, default: float) -> float:
        if not tl:
            return default
        prev = None
        for i, kf in enumerate(tl):
            kt = kf.get("time", 0.0)
            if kt > t:
                if prev is None:
                    return float(kf.get(field, default))
                nxt = kf
                pv = float(prev.get(field, default))
                nv = float(nxt.get(field, default))
                curve = prev.get("curve")
                span = kt - prev.get("time", 0.0)
                u = 0.0 if span <= 0 else (t - prev["time"]) / span
                if curve == "stepped":
                    return pv
                return pv + (nv - pv) * u
            prev = kf
        return float(prev.get(field, default))

    def apply_animation(self, name: str, t: float) -> None:
        self.reset()
        anims = self.data.get("animations", {})
        if name not in anims:
            raise KeyError(f"没有动画 {name}；可用：{list(anims)}")
        a = anims[name]
        for bone, tls in a.get("bones", {}).items():
            if bone not in self.local:
                continue
            loc = self.local[bone]
            if "rotate" in tls:
                loc["rotation"] = self._sample(tls["rotate"], t, "angle", loc["rotation"])
            if "translate" in tls:
                loc["x"] = self._sample(tls["translate"], t, "x", loc["x"])
                loc["y"] = self._sample(tls["translate"], t, "y", loc["y"])
            if "scale" in tls:
                loc["scaleX"] = self._sample(tls["scale"], t, "x", loc["scaleX"])
                loc["scaleY"] = self._sample(tls["scale"], t, "y", loc["scaleY"])

    # ---------- 世界变换 ----------
    def world(self) -> dict:
        """按层级顺序算世界变换（忽略 shear）。"""
        out: dict[str, dict] = {}
        for name in self.order:
            b = self.bone_by_name[name]
            loc = self.local[name]
            parent = b.get("parent")
            if parent and parent in out:
                p = out[parent]
                pr = math.radians(p["rotation"])
                cos_r, sin_r = math.cos(pr), math.sin(pr)
                wx = p["x"] + loc["x"] * p["scaleX"] * cos_r - loc["y"] * p["scaleY"] * sin_r
                wy = p["y"] + loc["x"] * p["scaleX"] * sin_r + loc["y"] * p["scaleY"] * cos_r
                out[name] = {
                    "x": wx, "y": wy,
                    "rotation": p["rotation"] + loc["rotation"],
                    "scaleX": p["scaleX"] * loc["scaleX"],
                    "scaleY": p["scaleY"] * loc["scaleY"],
                    "length": loc["length"],
                }
            else:
                out[name] = {
                    "x": loc["x"], "y": loc["y"],
                    "rotation": loc["rotation"],
                    "scaleX": loc["scaleX"], "scaleY": loc["scaleY"],
                    "length": loc["length"],
                }
        return out

    def anim_names(self) -> list[str]:
        return list(self.data.get("animations", {}))

    def duration(self, name: str) -> float:
        a = self.data["animations"][name]
        best = 0.0
        for tls in a.get("bones", {}).values():
            for tl in tls.values():
                if tl:
                    best = max(best, float(tl[-1].get("time", 0.0)))
        for tls in a.get("slots", {}).values():
            for tl in tls.values():
                if tl:
                    best = max(best, float(tl[-1].get("time", 0.0)))
        return best


# ------------------------------------------------------------------ 布局
def layout(sk: Skeleton) -> None:
    sk.reset()
    w = sk.world()
    print(f"{'骨骼':<20}{'世界X':>10}{'世界Y':>10}{'世界角度':>10}  父")
    for name in sk.order:
        b = sk.bone_by_name[name]
        t = w[name]
        print(f"{name:<20}{t['x']:>10.2f}{t['y']:>10.2f}{t['rotation']:>10.2f}  {b.get('parent','-')}")
    xs = [t["x"] for t in w.values()]
    ys = [t["y"] for t in w.values()]
    print(f"\n世界范围: x [{min(xs):.1f}, {max(xs):.1f}]  y [{min(ys):.1f}, {max(ys):.1f}]")


# ------------------------------------------------------------------ 预览
def draw(sk: Skeleton, png: Path, out: Path, anim: str | None, t: float,
         scale: float = 3.0) -> None:
    from PIL import Image, ImageDraw
    if anim:
        sk.apply_animation(anim, t)
    else:
        sk.reset()
    w = sk.world()

    xs = [v["x"] for v in w.values()]
    ys = [v["y"] for v in w.values()]
    pad = 30
    minx, maxx = min(xs) - pad, max(xs) + pad
    miny, maxy = min(ys) - pad, max(ys) + pad
    W = int((maxx - minx) * scale)
    H = int((maxy - miny) * scale)

    def tx(x, y):
        return ((x - minx) * scale, H - (y - miny) * scale)  # Spine y 向上

    img = Image.new("RGBA", (W, H), (24, 26, 32, 255))
    d = ImageDraw.Draw(img)

    # 骨骼连线
    for name in sk.order:
        b = sk.bone_by_name[name]
        p = b.get("parent")
        if p and p in w:
            x0, y0 = tx(w[p]["x"], w[p]["y"])
            x1, y1 = tx(w[name]["x"], w[name]["y"])
            d.line([x0, y0, x1, y1], fill=(120, 200, 255, 160), width=2)
    # 关节点 + 名称
    for name in sk.order:
        x, y = tx(w[name]["x"], w[name]["y"])
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 220, 90, 255))
        d.text((x + 5, y - 12), name, fill=(200, 200, 210, 255))

    # 插槽附件框（用区域尺寸画一个矩形，位置取所属骨骼）
    for s in sk.slots:
        bone = s.get("bone")
        att = s.get("attachment")
        if not bone or not att or bone not in w:
            continue
        t2 = w[bone]
        x, y = tx(t2["x"], t2["y"])
        d.rectangle([x - 4, y - 4, x + 4, y + 4], outline=(255, 120, 120, 200))

    img.save(out)
    print(f"  写出 {out}  ({W}x{H})  动画={anim or 'setup'} t={t}")


# ------------------------------------------------------------------ main
def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    sk = Skeleton(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    if cmd == "layout":
        layout(sk)
        return 0
    if cmd == "draw":
        png, out = Path(sys.argv[3]), Path(sys.argv[4])
        anim = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "-" else None
        t = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
        draw(sk, png, out, anim, t)
        return 0
    print(f"未知命令 {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
