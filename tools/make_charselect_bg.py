# -*- coding: utf-8 -*-
"""选角大背景：把 characterselect_defect_sts1 骨架换成「一根骨骼 + 一张静态立绘」。

不覆盖游戏原版场景 char_select_bg_defect.tscn（那里面有 NSpineAutoPlayer 和几十个
SpineMesh2D 子节点，游戏代码可能引用，风险高）。改成让这个骨架自己只画一张图 ——
场景照常渲染它，渲染出来就是静态立绘。

尺寸按场景实际变换反推：
  场景 SpineSprite: scale = 0.46, position = (-266, -27)
  父容器 DefectBg:  2560 x 1200（pivot 1280,600）
  => 图片在骨架单位里要 2560/0.46 = 5565 宽；
     按原图 1.6 宽高比 => 3478 高（横向铺满、上下裁切）
  ★ 位置模型（以你的真机截图为准，不靠推断）：
  游戏实例化这个场景时会按 pivot_offset 重新摆放 Control，等效于 Control 原点就在
  视口 (0,0)、中心在 (1280,600)。SpineSprite 在本地 (-266,-27)。
  实践修正：按此模型算出的 x 会让画面整体偏右约 120px（120/0.46 = 260 骨架单位），
  所以在 x 上减去 260。y 方向实测无需修正。
"""
import json, shutil
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "godot-project/animations/character_select/defect"
SRC = HERE / "ref-sts1-ui/images/ui/charSelect/defectPortrait.jpg"
BASE = "characterselect_defect_sts1"
# 贴合方式：按**高度**贴合容器 -> 整张图完整可见（不裁切）
#   容器高 1200px / 场景缩放 0.46 = 2609 骨架单位高；宽度按原图比例推得
CONTAINER_W, CONTAINER_H, SCENE_SCALE = 2560.0, 1200.0, 0.46
FILL = 1.10   # 图略大于屏幕：留出上下移动的余量，否则上移会露底
HEIGHT_UNITS = (CONTAINER_H / SCENE_SCALE) * FILL  # 2609 * 1.10 = 2870
WIDTH_UNITS = HEIGHT_UNITS * 1920.0 / 1200.0      # 4174（原图 1.6 宽高比）
ANIMS = ["idle_loop", "relaxed_loop", "low_health_loop", "process",
         "attack", "cast", "hurt", "die"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC).convert("RGBA")
    w, h = img.size
    height_units = HEIGHT_UNITS
    width_units = height_units * w / h
    img.save(OUT / f"{BASE}.png")

    (OUT / f"{BASE}.atlas").write_text(
        f"{BASE}.png\nsize: {w},{h}\nfilter: Linear, Linear\nbg\nbounds: 0, 0, {w}, {h}\n",
        encoding="utf-8")

    sk = {
        "skeleton": {"hash": "", "spine": "4.2.00",
                     "x": round(-width_units / 2), "y": round(-height_units / 2),
                     "width": round(width_units), "height": round(height_units)},
        "bones": [{"name": "root"}],
        "slots": [{"name": "bg", "bone": "root", "attachment": "bg"}],
        "skins": [{"name": "default", "attachments": {"bg": {"bg": {
            "x": 2780.0, "y": -1233.0,
            "width": round(width_units), "height": round(height_units)}}}}],
        # 游戏按名字取 8 个动画，全部给空动画 = 完全静止
        "animations": {n: {"bones": {}} for n in ANIMS},
    }
    (OUT / f"{BASE}.spine-json").write_text(
        json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  立绘 {w}x{h} -> 骨架单位 {width_units:.0f}x{height_units:.0f}"
          f"  -> 屏幕 {width_units*SCENE_SCALE:.0f}x{height_units*SCENE_SCALE:.0f}px"
          f"（容器 {CONTAINER_W:.0f}x{CONTAINER_H:.0f}，完整显示不裁切）")
    print(f"  已写出 {BASE}.png / .atlas / .spine-json（8 个空动画 = 静止）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
