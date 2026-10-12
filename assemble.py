#!/usr/bin/env python3
"""全自动装配 DefectSTS1Skin mod。

用法：
    python3 assemble.py --import     # 让 Godot 导入 godot-project/（会自动跑两次）
    python3 assemble.py --collect    # 把导入产物收进 mod/，并生成 4 个 .tres
    python3 assemble.py --check      # 校验 mod/ 的内部一致性
    python3 assemble.py              # 上面三步全做 + 打包到 dist/

★ 两个已实测的关键机制（决定了这个脚本的写法）：

  A. 导入产物的文件名哈希 = md5("res://" + 源路径)（不是内容哈希）。
     例：md5("res://animations/characters/defect/defect.png") = d9a4219263a117f0ba83c83a65391b33
         —— 与游戏本体 pck 里的文件名完全一致，已核验。

  B. 皮肤 mod 靠 **覆盖 .tres** 来换绑：
     游戏原版 defect_skel_data.tres 里按 uid 引用 atlas 与 skeleton。
     我们提供**同一个 res:// 路径 + 同一个 uid** 的 .tres，把 atlas/skeleton 换成自己的资源，
     再把自己的 .import + 导入产物一起打进 pck。uid 在三处必须严格一致：
        .tres 的 [ext_resource uid]  ==  .import 的 uid  ==  Godot 生成值
     本脚本从 Godot 生成的 .import 里读 uid，回填进 .tres，避免手抄出错。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GODOT_PROJECT = HERE / "godot-project"
MOD_DIR = HERE / "mod"
DIST_DIR = HERE / "dist"
GODOT_BIN = Path.home() / "Downloads/Godot_mono.app/Contents/MacOS/Godot"

MOD_ID = "DefectSTS1Skin"

# ---------------------------------------------------------------- 资源布局
# 每组 = 一套骨骼数据。tres_uid 取自游戏原版（必须一致才能覆盖）。
GROUPS = {
    "combat": {
        "tres": "animations/characters/defect/defect_skel_data.tres",
        "tres_uid": "uid://c0hdeqc1rqeah",
        "atlas": "animations/characters/defect/DefectSTS1.atlas",
        "skel": "animations/characters/defect/DefectSTS1.spine-json",
        "png": "animations/characters/defect/DefectSTS1.png",
    },
    "merchant": {
        "tres": "animations/merchant/defect/defect_merchant_skel_data.tres",
        "tres_uid": "uid://dd4yiy85jllb6",
        "atlas": "animations/merchant/defect/DefectShopSTS1.atlas",
        "skel": "animations/merchant/defect/DefectShopSTS1.spine-json",  # 商店独立骨骼（比例单独调）
        "png": "animations/merchant/defect/DefectShopSTS1.png",
    },
    "rest_site": {
        "tres": "animations/rest_site/defect/rest_site_defect_skel_data.tres",
        "tres_uid": "uid://bs7i15i8l37n7",
        "atlas": "animations/rest_site/defect/restsite_defect_sts1.atlas",
        "skel": "animations/rest_site/defect/restsite_defect_sts1.spine-json",
        "png": "animations/rest_site/defect/restsite_defect_sts1.png",
    },
    "character_select": {
        "tres": "animations/character_select/defect/characterselect_defect_skel_data.tres",
        "tres_uid": "uid://dgfn1vhmivjmd",
        "atlas": "animations/character_select/defect/characterselect_defect_sts1.atlas",
        "skel": "animations/character_select/defect/characterselect_defect_sts1.spine-json",
        "png": "animations/character_select/defect/characterselect_defect_sts1.png",
    },
}

# 纯贴图覆盖（不进 .tres，只换 .ctex 内容）——法球与 UI
TEXTURE_ONLY = [
    "animations/ui/combat/orbs/defect_orbs.png",
    "images/packed/character_select/char_select_defect.png",
    "images/packed/character_select/char_select_defect_locked.png",
    "images/ui/top_panel/character_icon_defect.png",
    "images/ui/top_panel/character_icon_defect_outline.png",
    "images/ui/hands/multiplayer_hand_defect_paper.png",
    "images/ui/hands/multiplayer_hand_defect_point.png",
    "images/ui/hands/multiplayer_hand_defect_rock.png",
    "images/ui/hands/multiplayer_hand_defect_scissors.png",
]

IMMEDIATE_EXT = {".png": ".ctex", ".atlas": ".spatlas", ".spine-json": ".spjson"}

IMPORT_PATH_RE = re.compile(r'^\s*path\s*=\s*"res://([^"]+)"', re.M)
IMPORT_UID_RE = re.compile(r'^\s*uid\s*=\s*"([^"]+)"', re.M)
IMPORT_TYPE_RE = re.compile(r'^\s*type\s*=\s*"([^"]+)"', re.M)
IMPORT_IMPORTER_RE = re.compile(r'^\s*importer\s*=\s*"([^"]+)"', re.M)
TRES_EXTRES_RE = re.compile(r'\[ext_resource[^\]]*path\s*=\s*"res://([^"]+)"[^\]]*\]')


# ---------------------------------------------------------------- 步骤 1
def run_import() -> None:
    """让 Godot 导入工程。

    ★ 实测：**首次** --import 时 spine 导入插件还没挂上，.atlas/.spine-json 会被漏掉；
      必须再跑一次才稳定。所以这里跑两次（第二次是增量的，很快）。
    """
    if not GODOT_BIN.exists():
        sys.exit(f"✗ 找不到 Godot: {GODOT_BIN}")
    if not (GODOT_PROJECT / "bin" / "spine_godot_extension.gdextension").exists():
        sys.exit("✗ godot-project/bin/ 里没有 spine-godot GDExtension，先解压 vendor/ 里的 zip 进去")

    env = dict(os.environ, HOME=str(GODOT_PROJECT / ".godot-home"))
    (GODOT_PROJECT / ".godot-home").mkdir(exist_ok=True)

    for i in (1, 2):
        print(f"  · Godot 导入 第 {i}/2 次…")
        p = subprocess.run(
            [str(GODOT_BIN), "--headless", "--path", str(GODOT_PROJECT), "--import"],
            env=env, capture_output=True, text=True, timeout=900,
        )
        blob = (p.stdout or "") + (p.stderr or "")
        bad = [ln for ln in blob.splitlines()
               if "ERROR" in ln and "editor_doc_cache" not in ln and "editor_settings" not in ln]
        for ln in bad[:12]:
            print(f"      {ln.strip()}")
        if "handle_crash" in blob or "signal 11" in blob:
            print("      (退出时崩了一下，但导入产物已在崩溃前写完，可忽略)")


# ---------------------------------------------------------------- 工具
def read_import(rel_src: str) -> dict | None:
    """读取 godot-project 里某个源文件生成的 .import 信息。"""
    imp = GODOT_PROJECT / (rel_src + ".import")
    if not imp.exists():
        return None
    t = imp.read_text(encoding="utf-8", errors="replace")
    def g(rx):
        m = rx.search(t)
        return m.group(1) if m else None
    return {
        "uid": g(IMPORT_UID_RE),
        "type": g(IMPORT_TYPE_RE),
        "importer": g(IMPORT_IMPORTER_RE),
        "path": g(IMPORT_PATH_RE),
        "text": t,
    }


def imported_artifact(rel_src: str) -> Path | None:
    """找到源文件对应的 .godot/imported 产物。"""
    info = read_import(rel_src)
    if not info or not info["path"]:
        return None
    return GODOT_PROJECT / info["path"]


# ---------------------------------------------------------------- 步骤 2
def collect() -> None:
    if MOD_DIR.exists():
        shutil.rmtree(MOD_DIR)
    MOD_DIR.mkdir(parents=True)

    (MOD_DIR / f"{MOD_ID}.json").write_text(
        (HERE / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")

    copied = 0
    missing: list[str] = []

    def ship(rel_src: str) -> dict | None:
        nonlocal copied
        info = read_import(rel_src)
        if not info:
            missing.append(rel_src)
            return None
        art = imported_artifact(rel_src)
        if art is None or not art.exists():
            missing.append(f"{rel_src} (导入产物缺失)")
            return None
        for p, data in ((MOD_DIR / (rel_src + ".import"), info["text"]),
                        (MOD_DIR / info["path"], art.read_bytes())):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data.encode() if isinstance(data, str) else data)
            copied += 1
        return info

    # 每组：图集 + 骨骼 + 贴图
    for name, g in GROUPS.items():
        ship(g["atlas"])
        ship(g["png"])
        if not any(g["skel"] == o["skel"] for o in list(GROUPS.values())[:list(GROUPS).index(name)]):
            ship(g["skel"])  # 商店复用战斗骨骼，避免重复

    for rel in TEXTURE_ONLY:
        ship(rel)

    # 生成 4 个 .tres
    for name, g in GROUPS.items():
        a, s = read_import(g["atlas"]), read_import(g["skel"])
        if not a or not s:
            missing.append(f"{name}: 缺 atlas 或 skeleton 的 .import，无法生成 .tres")
            continue
        txt = (
            f'[gd_resource type="SpineSkeletonDataResource" format=3 uid="{g["tres_uid"]}"]\n\n'
            f'[ext_resource type="SpineAtlasResource" uid="{a["uid"]}" '
            f'path="res://{g["atlas"]}" id="1_atlas"]\n'
            f'[ext_resource type="SpineSkeletonFileResource" uid="{s["uid"]}" '
            f'path="res://{g["skel"]}" id="2_skel"]\n\n'
            "[resource]\n"
            'atlas_res = ExtResource("1_atlas")\n'
            'skeleton_file_res = ExtResource("2_skel")\n'
        )
        dest = MOD_DIR / g["tres"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(txt, encoding="utf-8")
        copied += 1

    print(f"  · 收进 mod/ 共 {copied} 个文件")
    if missing:
        print(f"  ⚠ 有 {len(missing)} 项没找到：")
        for m in missing:
            print(f"      {m}")


# ---------------------------------------------------------------- 步骤 3
def check() -> list[str]:
    problems: list[str] = []
    if not MOD_DIR.exists():
        return ["mod/ 不存在，先跑 --collect"]

    n_manifest = len(list(MOD_DIR.glob("*.json")))
    if n_manifest != 1:
        problems.append(f"mod/ 根目录应恰好 1 个 manifest，实际 {n_manifest}")

    # 每个 .import 的 path= 目标必须随包一起发出（否则等于没换）
    for imp in sorted(MOD_DIR.rglob("*.import")):
        t = imp.read_text(encoding="utf-8", errors="replace")
        m = IMPORT_PATH_RE.search(t)
        if not m:
            problems.append(f"{imp.relative_to(MOD_DIR)}: 无 path=")
            continue
        if not (MOD_DIR / m.group(1)).exists():
            problems.append(f"{imp.relative_to(MOD_DIR)}: 指向的产物未随包发出 → {m.group(1)}")

    # .tres 引用必须存在
    for tres in sorted(MOD_DIR.rglob("*.tres")):
        for res in TRES_EXTRES_RE.findall(tres.read_text(encoding="utf-8", errors="replace")):
            if not (MOD_DIR / res).exists() and not (MOD_DIR / (res + ".import")).exists():
                problems.append(f"{tres.relative_to(MOD_DIR)} 引用了不存在的资源：{res}")

    # 四个 .tres 的 uid 必须等于游戏原版
    for name, g in GROUPS.items():
        f = MOD_DIR / g["tres"]
        if not f.exists():
            problems.append(f"缺少覆盖用 .tres：{g['tres']}（{name}）")
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'uid="(uid://[^"]+)"', t)
        if not m or m.group(1) != g["tres_uid"]:
            problems.append(f"{g['tres']}: 顶层 uid 必须是 {g['tres_uid']}，实际 {m.group(1) if m else '无'}")

    # 8 个动画名必须在骨骼 JSON 里齐活
    skel = MOD_DIR / GROUPS["combat"]["skel"]
    if skel.exists():
        try:
            data = json.loads(skel.read_text(encoding="utf-8"))
            have = set(data.get("animations", {}))
            need = {"idle_loop", "relaxed_loop", "low_health_loop", "process",
                    "attack", "cast", "hurt", "die"}
            lack = need - have
            if lack:
                problems.append(f"骨骼缺少必需动画：{sorted(lack)}")
        except Exception as e:
            problems.append(f"骨骼 JSON 解析失败：{e}")

    # 大小写冲突
    seen: dict[str, str] = {}
    for f in MOD_DIR.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(MOD_DIR).as_posix()
        k = rel.lower()
        if k in seen and seen[k] != rel:
            problems.append(f"大小写冲突：{seen[k]} 与 {rel}")
        seen[k] = rel

    return problems


def main() -> int:
    args = sys.argv[1:]
    do_all = not args

    if do_all or "--import" in args:
        print("① 让 Godot 导入资源")
        run_import()
    if do_all or "--collect" in args:
        print("② 收集产物并生成 .tres")
        collect()
    if do_all or "--check" in args:
        print("③ 校验")
        problems = check()
        if problems:
            print(f"❌ {len(problems)} 个问题：")
            for p in problems:
                print(f"   · {p}")
            return 1
        print("   ✅ 通过")

    if not do_all:
        return 0

    print("④ 打包（用 Godot 自带的 PCKPacker）")
    import json as _json
    import subprocess as _sp
    DIST_DIR.mkdir(exist_ok=True)
    out = DIST_DIR / f"{MOD_ID}.pck"
    files = []
    for f in sorted(MOD_DIR.rglob("*")):
        if f.is_file():
            files.append({"target": "res://" + f.relative_to(MOD_DIR).as_posix(),
                          "source": str(f)})
    manifest = HERE / "build" / "pck_manifest.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(_json.dumps({"files": files}, indent=1), encoding="utf-8")
    env = dict(os.environ, HOME=str(GODOT_PROJECT / ".godot-home"))
    p = _sp.run([str(GODOT_BIN), "--headless", "--path", str(GODOT_PROJECT),
                 "--script", str(HERE / "packer.gd"), "--", str(manifest), str(out)],
                env=env, capture_output=True, text=True, timeout=600)
    blob = (p.stdout or "") + (p.stderr or "")
    for ln in blob.splitlines():
        if "PCKPacker" in ln or "❌" in ln:
            print("   " + ln.strip())
    if not out.exists():
        print("❌ 打包失败"); print(blob[-1500:]); return 1
    (DIST_DIR / f"{MOD_ID}.json").write_bytes((MOD_DIR / f"{MOD_ID}.json").read_bytes())
    print(f"   📦 {len(files)} 个文件 -> {out.relative_to(HERE)} ({out.stat().st_size} 字节)")
    print(f"   把 {DIST_DIR.relative_to(HERE)}/ 复制到 <游戏>/mods/{MOD_ID}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
