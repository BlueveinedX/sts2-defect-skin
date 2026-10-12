# -*- coding: utf-8 -*-
"""加入一代的尸体贴图：die 时尸体淡入、主贴图淡出（用插槽 rgba 透明度实现）。

一代 corpse.png 是 512x512，实际画面只在 (99,397)-(414,495)，即 315x98。
把它裁出来贴到图集下方新区，注册成 `corpse` 区域，并挂到一个 `corpse` 插槽上
（默认全透明）。die 动画里把主插槽透明度降到 0、corpse 升到 1。
"""
import json, re
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
JSON = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"
ATLAS = HERE / "godot-project/animations/characters/defect/DefectSTS1.atlas"
PNG = HERE / "godot-project/animations/characters/defect/DefectSTS1.png"
CORPSE = HERE / "ref-sts1/images/characters/defect/corpse.png"
DIE_DUR = 2.233


def main() -> int:
    # 1) 裁出尸体画面并贴到图集底部
    cor = Image.open(CORPSE).convert("RGBA")
    art = cor.crop(cor.split()[3].getbbox())          # 315x98
    cw, ch = art.size
    page = Image.open(PNG).convert("RGBA")
    W, H = page.size
    y0 = H + 4
    page2 = Image.new("RGBA", (max(W, cw), y0 + ch + 4), (0, 0, 0, 0))
    page2.paste(page, (0, 0))
    page2.paste(art, (0, y0))
    page2.save(PNG)
    # ★ 必须同步图集头部的 size 声明，否则运行时按旧尺寸解析会错乱（渲染全黑）
    import re as _re
    at = ATLAS.read_text(encoding="utf-8")
    # ★ size: 那行前面有一个 Tab，表达式必须容忍前导空白（我两次栽在这）
    at = _re.sub(r'^(\s*)size:\s*\d+,\s*\d+',
                 lambda m: f"{m.group(1)}size: {page2.size[0]}, {page2.size[1]}",
                 at, count=1, flags=_re.M)
    ATLAS.write_text(at, encoding="utf-8")
    print(f"  图集 {W}x{H} -> {page2.size}，尸体区域 ({cw}x{ch}) 贴于 y={y0}")

    # 2) 图集文本里注册 corpse 区域
    txt = ATLAS.read_text(encoding="utf-8")
    if "\ncorpse\n" not in txt:
        txt = txt.rstrip("\n") + f"\ncorpse\n\tbounds: 0, {y0}, {cw}, {ch}\n"
        ATLAS.write_text(txt, encoding="utf-8")
        print("  已注册区域 corpse")

    # 3) 骨架：加插槽 + 皮肤附件
    d = json.loads(JSON.read_text(encoding="utf-8"))
    slots = {s["name"] for s in d["slots"]}
    if "corpse" not in slots:
        d["slots"].append({"name": "corpse", "bone": "root",
                           "attachment": "corpse", "color": "ffffff00"})   # 默认全透明
    d["skins"][0]["attachments"].setdefault("corpse", {})["corpse"] = {
        "x": 0.0, "y": ch / 2.0, "width": float(cw), "height": float(ch)}
    print("  已加插槽 corpse（默认 alpha=0）")

    # 4) die：主插槽淡出、corpse 淡入
    main_slots = [s["name"] for s in d["slots"]
                  if s["name"] not in ("corpse",) and s.get("attachment")]
    die = d["animations"].setdefault("die", {"bones": {}})
    die.setdefault("slots", {})
    for s in main_slots:
        die["slots"][s] = {"rgba": [{"time": 0.0, "color": "ffffffff"},
                                    {"time": 0.55, "color": "ffffffff"},
                                    {"time": 1.15, "color": "ffffff00"},
                                    {"time": DIE_DUR, "color": "ffffff00"}]}
    die["slots"]["corpse"] = {"rgba": [{"time": 0.0, "color": "ffffff00"},
                                       {"time": 0.55, "color": "ffffff00"},
                                       {"time": 1.15, "color": "ffffffff"},
                                       {"time": DIE_DUR, "color": "ffffffff"}]}
    print(f"  die: {len(main_slots)} 个主插槽淡出 + corpse 淡入")
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
