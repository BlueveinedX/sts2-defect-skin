# -*- coding: utf-8 -*-
"""把网格(mesh)附件转成普通矩形(region)附件。

动机：网格渲染出来的部件之间有明显断裂（已排除 bounds 互换/deform/根骨骼缩放/权重
四个假设，骨骼与插槽数据经逐项比对与一代完全一致）。矩形附件直接按区域矩形采样，
绕开「区域 -> 网格 UV」这条链路，用来判定问题是否出在网格 UV 上。

矩形附件参数：
  x, y    = 网格顶点包围盒的中心（相对骨骼原点的偏移）
  width/height = 该区域**未旋转**的原始尺寸（1:1 对应骨架单位，图集无 scale 字段）
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
JSON = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"
ATLAS34 = HERE / "ref-sts1/images/characters/defect/idle/skeleton.atlas"


def region_sizes() -> dict:
    """从一代 3.4 图集读取每个区域的未旋转原始尺寸。"""
    out = {}
    txt = ATLAS34.read_text(encoding="utf-8")
    for b in re.split(r'\n(?=\S)', txt)[1:]:
        L = b.strip().splitlines()
        if not L:
            continue
        nm = L[0].strip()
        size = None
        for ln in L[1:]:
            if ln.strip().startswith("size:"):
                size = tuple(int(v) for v in ln.split(":", 1)[1].split(","))
        if size:
            out[nm] = size
    return out


def main() -> int:
    sizes = region_sizes()
    d = json.loads(JSON.read_text(encoding="utf-8"))
    atts = d["skins"][0]["attachments"]
    n = 0
    for slot, group in atts.items():
        for name, a in list(group.items()):
            if a.get("type") != "mesh":
                continue
            v = a.get("vertices", [])
            if len(v) < 2:
                continue
            xs = v[0::2]
            ys = v[1::2]
            cx = (min(xs) + max(xs)) / 2.0
            cy = (min(ys) + max(ys)) / 2.0
            sz = sizes.get(name)
            if sz is None:
                bw, bh = max(xs) - min(xs), max(ys) - min(ys)
                sz = (round(bw), round(bh))
                print(f"  ⚠ {slot}/{name} 图集里没找到，用网格包围盒 {sz}")
            w, h = sz
            group[name] = {"x": round(cx, 3), "y": round(cy, 3),
                           "width": float(w), "height": float(h)}
            n += 1
    JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  网格 -> 矩形：转换 {n} 个附件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
