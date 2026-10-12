# -*- coding: utf-8 -*-
"""从「你自己合法拥有的游戏安装」中提取构建所需的素材。

本仓库不含任何游戏美术素材（版权归 MegaCrit）。公开使用前请先跑这个脚本，
它会把你本机的素材提取到 .gitignore 已排除的目录里。

用法：
    python3 tools/extract_assets.py                 # 自动探测常见安装路径
    python3 tools/extract_assets.py --sts1 <路径> --sts2 <路径>
    python3 tools/extract_assets.py --check          # 只检查素材是否齐全

STS1 路径可以是 desktop-1.0.jar，也可以是 .app / 游戏根目录（会自动找 jar）。
STS2 路径可以是 Slay the Spire 2.pck，也可以是 .app / 游戏根目录。
"""
import argparse, io, json, os, re, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))

# ── 需要从 STS1 提取的文件（jar 内路径 -> 本仓库相对路径）──
STS1_FILES = {
    "images/characters/defect/idle/skeleton.json": "ref-sts1/images/characters/defect/idle/skeleton.json",
    "images/characters/defect/idle/skeleton.atlas": "ref-sts1/images/characters/defect/idle/skeleton.atlas",
    "images/characters/defect/idle/defect.png": "ref-sts1/images/characters/defect/idle/defect.png",
    "images/characters/defect/corpse.png": "ref-sts1/images/characters/defect/corpse.png",
    "images/ui/charSelect/defectPortrait.jpg": "ref-sts1-ui/images/ui/charSelect/defectPortrait.jpg",
    "images/ui/charSelect/defectButton.png": "ref-sts1-ui/images/ui/charSelect/defectButton.png",
}

# ── 需要从 STS2 提取的（pck 内路径关键字 -> 输出目录/文件名）──
STS2_RIGS = {
    "combat":  ("imported/defect.skel-", "imported/defect.atlas-", "imported/defect.png-"),
    "rest":    ("imported/restsite_defect.skel-", "imported/restsite_defect.atlas-", "imported/restsite_defect.png-"),
    "select":  ("imported/characterselect_defect.skel-", "imported/characterselect_defect.atlas-", "imported/characterselect_defect.png-"),
}

STS1_CANDIDATES = [
    "~/Library/Application Support/Steam/steamapps/common/Slay the Spire",
    "/Applications/SlayTheSpire.app",
    "~/.steam/steam/steamapps/common/Slay the Spire",
    "C:/Program Files (x86)/Steam/steamapps/common/Slay the Spire",
]
STS2_CANDIDATES = [
    "~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2",
    "/Applications/SlayTheSpire2.app",
    "~/.steam/steam/steamapps/common/Slay the Spire 2",
    "C:/Program Files (x86)/Steam/steamapps/common/Slay the Spire 2",
]


def find_sts1_jar(p: Path):
    if p.is_file() and p.suffix == ".jar":
        return p
    for pat in ("**/desktop-1.0.jar", "**/*.jar"):
        hits = [x for x in p.glob(pat) if "desktop" in x.name]
        if hits:
            return hits[0]
    return None


def find_sts2_pck(p: Path):
    if p.is_file() and p.suffix == ".pck":
        return p
    for x in p.rglob("*.pck"):
        if "Slay the Spire 2" in x.name or x.stat().st_size > 50_000_000:
            return x
    return None


def extract_sts1(jar: Path) -> None:
    n = 0
    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        for src, dst in STS1_FILES.items():
            if src not in names:
                print(f"  ⚠ jar 里没有 {src}")
                continue
            out = HERE / dst
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(src))
            n += 1
            print(f"  ✅ {dst}")
    print(f"  STS1 提取 {n}/{len(STS1_FILES)} 个文件")


def extract_sts2(pck_path: Path) -> None:
    import pck as pckmod
    from PIL import Image
    d = pckmod.parse(str(pck_path))
    f = open(pck_path, "rb")

    def grab(key):
        for p, o, s in d["entries"]:
            if key in p:
                f.seek(d["file_base"] + o if d["flags"] & 2 else o)
                return p, f.read(s)
        return None, None

    for name, (ks, ka, kp) in STS2_RIGS.items():
        out = HERE / f"game-rigs/{name}"
        out.mkdir(parents=True, exist_ok=True)
        _, bs = grab(ks); _, ba = grab(ka); _, bp = grab(kp)
        if not bs or not ba:
            print(f"  ⚠ STS2 缺少 {name} 的骨架/图集")
            continue
        (out / f"{name}.skel").write_bytes(bs)
        j = json.loads(ba.decode("utf-8"))
        ad = j["atlas_data"]
        lines = ad.splitlines()
        lines[0] = f"{name}.png"            # 页名必须与 png 文件名一致
        (out / f"{name}.atlas").write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            i = bp.find(b"RIFF")
            Image.open(io.BytesIO(bp[i:])).convert("RGBA").save(out / f"{name}.png")
        except Exception:
            # 部分贴图是 GPU 压缩格式，量骨骼用占位图即可
            m = re.search(r"size:\s*([\d.]+)\s*,\s*([\d.]+)", ad)
            w, h = (int(float(m.group(1))), int(float(m.group(2)))) if m else (512, 512)
            Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(out / f"{name}.png")
            print(f"  ⚠ {name} 贴图无法解码，已用 {w}x{h} 占位图（量骨骼够用）")
        print(f"  ✅ game-rigs/{name}/")
    f.close()


def check() -> bool:
    need = list(STS1_FILES.values()) + [
        "game-rigs/combat/combat.skel", "game-rigs/combat/combat.atlas"]
    ok = True
    for rel in need:
        e = (HERE / rel).exists()
        print(f"  {'✅' if e else '❌'} {rel}")
        ok = ok and e
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sts1"); ap.add_argument("--sts2")
    ap.add_argument("--check", action="store_true", help="只检查素材是否齐全")
    a = ap.parse_args()
    if a.check:
        print("素材检查：")
        return 0 if check() else 1

    jar = Path(os.path.expanduser(a.sts1)) if a.sts1 else None
    if jar is None:
        for c in STS1_CANDIDATES:
            p = Path(os.path.expanduser(c))
            if p.exists():
                jar = find_sts1_jar(p)
                if jar: break
    if jar is None or not Path(jar).exists():
        print("❌ 找不到《杀戮尖塔》安装。请用 --sts1 指定 desktop-1.0.jar 或游戏目录")
        return 1
    print(f"STS1: {jar}")
    extract_sts1(Path(jar))

    pck = Path(os.path.expanduser(a.sts2)) if a.sts2 else None
    if pck is None:
        for c in STS2_CANDIDATES:
            p = Path(os.path.expanduser(c))
            if p.exists():
                pck = find_sts2_pck(p)
                if pck: break
    if pck is None or not Path(pck).exists():
        print("❌ 找不到《杀戮尖塔 2》的 .pck。请用 --sts2 指定")
        return 1
    print(f"STS2: {pck}")
    extract_sts2(Path(pck))
    print("\n完成。现在可以按 README 的六步管线构建。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
