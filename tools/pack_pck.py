#!/usr/bin/env python3
"""把一棵目录树打包成 Slay the Spire 2 (Godot 4.5.1) 能读的 .pck。

格式由 tools/pck.py 逆向得到，实测与游戏本体、Steam 创意工坊 mod 的 pck 一致：

  0x00  "GDPC"
  0x04  u32  format_version = 3
  0x08  u32  ver_major
  0x0C  u32  ver_minor
  0x10  u32  ver_patch
  0x14  u32  pack_flags      = 2   (PACK_REL_FILEBASE：目录里的 offset 相对 file_base)
  0x18  u64  file_base       = 128 (文件数据起点)
  0x20  u64  dir_offset      (目录区绝对偏移，位于文件末尾)
  0x28  ... 补零到 0x80
  0x80  ... 文件数据（未压缩，原样存放）
  dir_offset: u32 条目数，随后每条：
      u32   path_len        (不含结尾符，精确字符数)
      bytes path            (相对路径，不带 "res://")
      u64   offset          (相对 file_base)
      u64   size
      u8[16] md5
      u32   flags           (0 = 未压缩/未加密)

用法：
    python3 pack_pck.py <源目录> <输出.pck>
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys

HEADER_SIZE = 128
FORMAT_VERSION = 3


def pack(root: str, out_path: str, godot_ver: tuple[int, int, int] = (4, 5, 1)) -> int:
    files: list[tuple[str, str]] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            files.append((rel, full))
    files.sort()

    data = bytearray()
    entries: list[tuple[str, int, int, bytes]] = []
    for rel, full in files:
        blob = open(full, "rb").read()
        offset = len(data)
        entries.append((rel, offset, len(blob), hashlib.md5(blob).digest()))
        data += blob
        data += b"\x00" * ((-len(blob)) % 4)  # 4 字节对齐

    dir_offset = HEADER_SIZE + len(data)

    directory = bytearray(struct.pack("<I", len(entries)))
    for rel, offset, size, md5 in entries:
        pb = rel.encode("utf-8")
        directory += struct.pack("<I", len(pb)) + pb
        directory += struct.pack("<QQ", offset, size) + md5 + struct.pack("<I", 0)

    header = bytearray(HEADER_SIZE)
    struct.pack_into("<4sIIIII", header, 0, b"GDPC", FORMAT_VERSION,
                     godot_ver[0], godot_ver[1], godot_ver[2], 2)
    struct.pack_into("<Q", header, 24, HEADER_SIZE)
    struct.pack_into("<Q", header, 32, dir_offset)

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(data)
        f.write(directory)
    return len(entries)


def unpack(pck_path: str, out_dir: str) -> int:
    """把 .pck 解开到目录（反向验证用）。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pck as pckmod

    d = pckmod.parse(pck_path)
    with open(pck_path, "rb") as f:
        for path, offset, size in d["entries"]:
            f.seek(d["file_base"] + offset if d["flags"] & 2 else offset)
            blob = f.read(size)
            dest = os.path.join(out_dir, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as g:
                g.write(blob)
    return len(d["entries"])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    n = pack(sys.argv[1], sys.argv[2])
    print(f"已打包 {n} 个文件 -> {sys.argv[2]} ({os.path.getsize(sys.argv[2])} 字节)")
