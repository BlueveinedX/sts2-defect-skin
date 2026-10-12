# 补齐清单（让 `python3 build.py --check` 变绿）

进度看 `python3 build.py --check`：**必需 0/17 · 可选 0/13**（当前 mod/ 内只有 manifest）。

---

## 0. ⚠️ 结构已修正：皮肤 mod 比想象的简单得多

我拆了本机三个「无 DLL 纯皮肤」mod（`regentSkin` / `silentSkin` / `necrobinderSkin`），
它们的 pck 里**只有 14 个 `.import` + 14 个导入产物**：

- ❌ 没有源 `.png / .atlas / .skel`
- ❌ 没有自己写的 `*_skel_data.tres`
- ✅ 只有 `.import` 重映射 + `res://.godot/imported/*.ctex|.spatlas|.spskel`

**原理**：游戏里 `res://animations/characters/defect/defect.atlas` 是通过同目录的
`defect.atlas.import` 里的 `path=` 指向真正资源的。mod 只要提供**同名 `.import`**、
让它指向**我们那份**导入产物，游戏原本的 `defect_skel_data.tres` 就自动指向我们的骨骼。

所以：**不用写 `.tres`，也不用把源文件打包。**（对比：`MechaNeko_Defect` 走的是"新文件名 + 覆盖 .tres"那条路，也能用，但文件更多、更容易错。）

---

## 1. 路线 A 的准确安装步骤（**spine-godot 不在 npm 上**）

> npm 上只有 Spine 的 **Web/JS** 运行时（`@esotericsoftware/spine-core@4.2.x` 等），
> 那是给浏览器/JS 用的，**驱动不了 Godot**。Godot 用的是 `spine-godot`。

`spine-godot` 有两种分发形式（[官方文档](https://en.esotericsoftware.com/spine-godot)）：

| 形式 | 怎么装 | 说明 |
|---|---|---|
| **GDExtension**（推荐） | 从官方下载页下 `.zip`，把 `bin/` 丢到你的 Godot 工程根目录 | 支持所有平台；**没有 C# 绑定**，但我们用不到 |
| 自定义 Godot 编辑器（C++ 模块版） | 下官方编译好的 `Godot.app` | 只有需要 C# 时才要；纯皮肤不需要 |

**版本必须配对，两个维度都要对：**

- **Godot 版本 → 4.5.1**（游戏本体 pck 头写的就是 Godot 4.5.1）
- **Spine 版本 → 4.2**（游戏内运行时实测是 Spine **4.2.43**；[官方 `4.2` 分支 README](https://raw.githubusercontent.com/EsotericSoftware/spine-runtimes/4.2/spine-godot/README.md) 明确写 "works with data exported from Spine 4.2.xx"）

### ✅ 已核实：现成构建存在，**不需要编译**

下载地址的规律是
`https://spine-godot.s3.eu-central-1.amazonaws.com/<Spine版本>/<Godot标签>/spine-godot-extension-<Spine版本>-<Godot标签>.zip`

我们需要的那个（实测 HTTP 200）：

| 要装的东西 | 地址 | 备注 |
|---|---|---|
| **Godot 4.5.1**（标准版，非 .NET） | `https://github.com/godotengine/godot/releases/download/4.5.1-stable/Godot_v4.5.1-stable_macos.universal.zip` | 与游戏本体 pck 头的 4.5.1 精确对齐 |
| **spine-godot GDExtension**（Spine 4.2 + Godot 4.5.1） | `https://spine-godot.s3.eu-central-1.amazonaws.com/4.2/4.5.1-stable/spine-godot-extension-4.2-4.5.1-stable.zip` | 14 MB，含 macOS 编辑器二进制 |

第二个我已经下好并校验，放在本仓库里了：
[`vendor/spine-godot-extension-4.2-4.5.1-stable.zip`](vendor/spine-godot-extension-4.2-4.5.1-stable.zip)
（sha256 `47c823a4…4ee57`，见 [`vendor/SHA256SUMS.txt`](vendor/SHA256SUMS.txt)）

安装方式：解压 → 把里面的 `bin/` 整个复制到你的 Godot **工程根目录**，
使工程里出现 `bin/spine_godot_extension.gdextension`，然后用 Godot 编辑器打开工程即可。

> 若哪天要换版本，改 URL 里那两段即可（例如 `4.2/4.4.1-stable` 也存在，实测 200；`4.5-stable` 则是 403，没有）。
> 想确认某组合存不存在，`curl -I` 那个 URL 看返回码就行。
>
> 官方 `4.2` 分支的 README 里写着"Godot 3.5.x / 4.0.x"，那是过时文案；
> S3 上确实有 4.5.1-stable 的构建，且与游戏版本精确匹配。

**纯皮肤不需要 .NET SDK。** 但如果最后发现特效锚点（比如 Hyperbeam 的发射位置）因为骨骼比例变了而错位，
就需要 .NET SDK 编一个 Harmony 补丁去修——`MechaNeko_Defect` 就是这么干的（`NHyperbeamVfx_Create_Patch`）。

---

## 2. 要产出的东西：17 个必需重映射 + 13 个可选

每个重映射 = 一个 `.import` 文件 + 一个指向的导入产物。

**必需（11 个角色本体 + 6 个法球）：**

```
animations/characters/defect/defect.atlas.import              → .spatlas
animations/characters/defect/defect.png.import                → .ctex
animations/characters/defect/defect.skel.import               → .spskel   ★ 8 个动画在这
animations/merchant/defect/defect_shop.atlas.import           → .spatlas
animations/merchant/defect/defect_shop.png.import             → .ctex
animations/rest_site/defect/restsite_defect.atlas.import      → .spatlas
animations/rest_site/defect/restsite_defect.png.import        → .ctex
animations/rest_site/defect/restsite_defect.skel.import       → .spskel
animations/character_select/defect/characterselect_defect.atlas.import  → .spatlas
animations/character_select/defect/characterselect_defect.png.import    → .ctex
animations/character_select/defect/characterselect_defect.skel.import   → .spskel
animations/ui/combat/orbs/defect_orbs.atlas.import            → .spatlas
animations/ui/combat/orbs/defect_orbs.png.import              → .ctex
animations/ui/combat/orbs/defect_frost_orb.atlas.import       → .spatlas
animations/ui/combat/orbs/defect_glass_orb.atlas.import       → .spatlas
animations/ui/combat/orbs/defect_lightning_orb.atlas.import   → .spatlas
animations/ui/combat/orbs/defect_plasma_orb.atlas.import      → .spatlas
```

**可选（UI 立绘/图标/能量层，让整个角色一致）：** 见 [build.py](build.py) 里的 `OPTIONAL_REMAPS`，
包含选人立绘、顶栏头像、联机手势 4 张、能量球 5 层。

> 不做的部分：约 130 张卡牌插画（`images/packed/card_portraits/defect/*`）、时代立绘、成就图。
> 那些不属于"角色皮肤"，改了反而是另一个 mod 的范畴。

---

## 3. `.import` 模板

**骨骼 `defect.skel.import`**
```
[remap]

importer="spine.skel"
type="SpineSkeletonFileResource"
uid="uid://by8dcdhwdsh35"
path="res://.godot/imported/defect.skel-<我们自己的哈希>.spskel"

[deps]

source_file="res://animations/characters/defect/defect.skel"
dest_files=["res://.godot/imported/defect.skel-<我们自己的哈希>.spskel"]
```

**图集 `defect.atlas.import`** —— 同上，`importer="spine.atlas"`、`type="SpineAtlasResource"`、后缀 `.spatlas`。

**贴图 `defect.png.import`**
```
[remap]

importer="texture"
type="CompressedTexture2D"
uid="uid://78m6b8ewv064"
path="res://.godot/imported/defect.png-<我们自己的哈希>.ctex"

[deps]

source_file="res://animations/characters/defect/defect.png"
dest_files=["res://.godot/imported/defect.png-<我们自己的哈希>.ctex"]

[params]

compress/mode=1
process/fix_alpha_border=true
detect_3d/compress_to=1
```

> `uid` 保持和游戏原版一致（上面就是原版的值），`path=` 的哈希必须换成我们自己的——
> `build.py` 会检查这一点，防止"哈希没换 = 其实没替换"。

---

## 4. 8 个动画必须齐全

```
idle_loop   relaxed_loop   low_health_loop   process
attack      cast           hurt              die
```

一代只有 `Idle` / `Hit`，另 6 个要新做。骨骼名/插槽名可以完全自由
（已实测 `sts2.dll` 不引用任何二代部件名），所以可以按一代体型与命名重建。

**特效部件（已决定补）** —— 二代有而一代没有的：
`blender/*`(8 个辉光)、`blip_circle`、`blip_star`、`glow1-4`、`deathspark/deathspark`、
`binder_bolt`、`castfist_l`、`castfist_r`、`cowl 1/2/back`、`pipe 1/2`、
`eye_progress`、`orb_sparkles`、`defect_flare`、`orb patch`、`orb shine`

需要在保持一代风格的前提下补画这些部件，`cast` / `process` 才不会"空手做动作"。

---

## 5. 检查与打包

```bash
python3 build.py --check     # 校验重映射链：.import → 导入产物 → 哈希是否真换了 → 大小写冲突
python3 build.py             # 通过后打包
```

产物：`dist/DefectSTS1Skin.pck` + `dist/DefectSTS1Skin.json`
→ 把 `dist/` 整个目录复制到 `<游戏>/mods/DefectSTS1Skin/`。
