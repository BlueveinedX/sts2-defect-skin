#!/usr/bin/env python3
"""生成 mod 需要的 4 组资源（战斗 / 商店 / 营火 / 选人）。

· 战斗：直接用 tools/sts1_to_spine42.py + tools/retarget_anims.py 的产物
· 商店：复用战斗骨骼（游戏原版也是这样），只换图集页名
· 营火 / 选人：同一套内容，但 root 缩放按游戏本体对应骨骼的尺寸比例调整

缩放依据（实测游戏本体骨骼声明高度）：
    defect.skel              2339.0  -> 11.014x
    restsite_defect.skel      728.0  ->  3.428x
    characterselect_defect   3217.7  -> 15.152x
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROJ = HERE / "godot-project"
SRC = PROJ / "animations/characters/defect"

S1_BODY_H = 182.37  # 实测：一代骨架在 root scale=1 时的身体高度

# (输出目录, 图集基名, 缩放目标高度 或 None=沿用战斗骨骼)
# target_h = 实测的游戏原版对应骨骼「身体高度」（不是声明 bbox）
# ★ 商店比例：按 0.23 场景缩放实测，我的角色宽 513px / 原版 427px（宽 20%），
#   高 481px / 原版 512px。等比缩到 0.83 后宽度与原版一致（高度 399，略矮）。
#   要调整只改这一个数字：改小=整体更小，改大=更大。
MERCHANT_SCALE = 0.83

RIGS = [
    ("animations/merchant/defect", "DefectShopSTS1", 1828.5 * MERCHANT_SCALE),
    ("animations/rest_site/defect", "restsite_defect_sts1", 511.8),
    ("animations/character_select/defect", "characterselect_defect_sts1", 1440.2),
]


def rewrite_page(atlas_text: str, new_page: str) -> str:
    lines = atlas_text.splitlines()
    out = [new_page] + lines[1:]
    return "\n".join(out) + "\n"


def main() -> int:
    base_atlas = (SRC / "DefectSTS1.atlas").read_text(encoding="utf-8")
    base_png = (SRC / "DefectSTS1.png").read_bytes()
    base_json = json.loads((SRC / "DefectSTS1.spine-json").read_text(encoding="utf-8"))

    for outdir, basename, target_h in RIGS:
        d = PROJ / outdir
        d.mkdir(parents=True, exist_ok=True)

        (d / f"{basename}.atlas").write_text(rewrite_page(base_atlas, f"{basename}.png"),
                                             encoding="utf-8")
        (d / f"{basename}.png").write_bytes(base_png)

        if target_h is not None:
            # 独立骨骼：调整 root 缩放使整体尺寸匹配游戏本体的对应骨骼
            sk = json.loads(json.dumps(base_json))
            scale = target_h / S1_BODY_H
            for b in sk["bones"]:
                if b["name"] == "root":
                    b["scaleX"] = round(scale, 4)
                    b["scaleY"] = round(scale, 4)
            sk["skeleton"]["width"] = round(float(base_json["skeleton"]["width"]) * scale, 2)
            sk["skeleton"]["height"] = round(S1_BODY_H * scale, 2)
            (d / f"{basename}.spine-json").write_text(
                json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
            note = f"独立骨骼 root缩放={scale:.3f}"
        else:
            note = "复用战斗骨骼（assemble.py 已指向它）"

        print(f"  {outdir}/{basename}.*  {note}")

    print("\n4 组资源就绪。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
