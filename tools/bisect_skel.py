#!/usr/bin/env python3
"""二分定位：找出让 spine-cpp 4.2 解析崩溃的字段。

spine-cpp 遇到非法数据时是**硬崩**（signal 11）而不是优雅报错，
所以只能"删掉某部分再试"。每个变体都在独立 Godot 进程里加载，
崩了就是该部分有问题。

用法：python3 tools/bisect_skel.py
输出：/tmp/bis/v*.spine-json，再由外层 shell 逐个喂给 verify_one.gd
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC = HERE / "godot-project/animations/characters/defect/DefectSTS1.spine-json"
ATLAS = HERE / "godot-project/animations/characters/defect/DefectSTS1.atlas"
OUT = Path("/tmp/bis")


def region_sizes_from_atlas() -> dict[str, tuple[float, float]]:
    """从 4.x atlas 反推每个区域的「未旋转原始尺寸」。"""
    sizes: dict[str, tuple[float, float]] = {}
    cur = None
    for ln in ATLAS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        if not ln.startswith("\t"):
            cur = ln.strip()
            continue
        s = ln.strip()
        if s.startswith("bounds:") and cur:
            _, v = s.split(":", 1)
            x, y, w, h = [float(t) for t in v.split(",")]
            sizes[cur] = (w, h)
        elif s.startswith("rotate:") and cur:
            w, h = sizes[cur]
            sizes[cur] = (h, w)  # 换回未旋转尺寸
    return sizes


def skins_to_array(skins: dict) -> list:
    """旧的 {name: {slot: {att: {...}}}} → 4.2 的 [{name, attachments:{...}}]"""
    out = []
    for name, slots in skins.items():
        out.append({"name": name, "attachments": slots})
    return out


def meshes_to_regions(d: dict) -> int:
    """把 mesh 附件降级成 region 附件（丢掉形变，但保证 4.2 能读）。"""
    sizes = region_sizes_from_atlas()
    n = 0
    for slots in d.get("skins", {}).get("default", {}).values():
        for an, av in slots.items():
            if av.get("type") == "mesh":
                w, h = sizes.get(an, sizes.get(av.get("path", an), (0, 0)))
                av.clear()
                av.update({"x": -w / 2, "y": -h / 2, "width": w, "height": h})
                n += 1
    return n


def strip_deform(d: dict) -> int:
    n = 0
    for a in d.get("animations", {}).values():
        if a.pop("deform", None) is not None:
            n += 1
    return n


def main() -> None:
    base = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict] = {}

    v = copy.deepcopy(base); variants["v0_full"] = v

    v = copy.deepcopy(base); v.pop("animations", None); variants["v1_no_anims"] = v
    v = copy.deepcopy(base); v.pop("skins", None); variants["v2_no_skins"] = v
    v = copy.deepcopy(base); v.pop("ik", None); variants["v3_no_ik"] = v
    v = copy.deepcopy(base); v.pop("slots", None); variants["v4_no_slots"] = v

    v = copy.deepcopy(base); v["skins"] = skins_to_array(v["skins"])
    variants["v5_skins_array"] = v

    v = copy.deepcopy(base); strip_deform(v); variants["v6_no_deform"] = v

    v = copy.deepcopy(base); meshes_to_regions(v); variants["v7_mesh_to_region"] = v

    v = copy.deepcopy(base); meshes_to_regions(v); strip_deform(v)
    v["skins"] = skins_to_array(v.pop("skins"))
    variants["v8_all_fixes"] = v

    for name, data in variants.items():
        p = OUT / f"{name}.spine-json"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {name:<20} {p.stat().st_size:>8} 字节")
    print(f"\n共 {len(variants)} 个变体 -> {OUT}")


if __name__ == "__main__":
    main()
