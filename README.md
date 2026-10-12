# 故障机器人 · 一代复刻皮肤（Slay the Spire 2）

初代《杀戮尖塔》故障机器人的美术移植到《杀戮尖塔 2》，保留初代**风格与站姿**，
并提供二代要求的**全部 8 个动画**。纯美术覆盖，不改变玩法（`has_dll: false`）。

## 成果物

| 文件 | 说明 |
|---|---|
| `dist/DefectSTS1Skin.pck` | 3.5 MB / 27 条目，Godot 4.5.1 pck v3 |
| `dist/DefectSTS1Skin.json` | mod manifest（`min_game_version: 0.111.0`） |

安装：把 `dist/` 整个目录放到 **`<游戏>/SlayTheSpire2.app/Contents/MacOS/mods/DefectSTS1Skin/`**
（注意是 **app 包内**的 `Contents/MacOS/mods/`，游戏不读顶层的 `<游戏>/mods/`）。

---

## 已完成并已验证

### ✅ 8 个动画齐全

| 动画 | 时长 | 来源 |
|---|---|---|
| `idle_loop` | 6.667s | **一代原版**（保站姿） |
| `hurt` | 0.333s | **一代原版** |
| `attack` | 1.500s | 二代原版动作重定向 |
| `cast` | 1.233s | 二代原版动作重定向 |
| `die` | 2.233s | 二代原版动作重定向 |
| `process` | 1.567s | 二代原版动作重定向 |
| `relaxed_loop` | 12.000s | 二代原版动作重定向 |
| `low_health_loop` | 12.000s | 二代原版动作重定向 |

### ✅ 一代骨架原样可用

37 骨骼 / **41 插槽** / 19 网格 + 13 区域 + **8 个特效部件**，全部一代原始贴图（原始 454×141 图集逐字节复用，下方扩展出 464×419 容纳特效）。
骨头定义（站姿）原样搬运，网格形变（`deform`）与原版 IK 都保留了。

### ✅ 二代特效部件已补齐

程序化生成 8 个特效贴图并接进骨架（图集 32 → 40 区域）：

| 部件 | 对应二代部件 | 挂载骨骼 |
|---|---|---|
| `glowie1` / `glowie2` | `glowie1..4` 法球光晕 | `Hips_sphere` |
| `blender_blur` / `blender_whisp_1` | `blender/blur`、`blender/whisp_*` 手部拖影 | `Arm_R_3` / `Arm_L_3` |
| `binder_bolt` | `binder_bolt` 小电弧 | `Arm_R_3` |
| `blip_star` | `blip_star` 星闪 | `Neck_3` |
| `flare` | `flare` 爆闪 | `Hips_sphere` |
| `deathspark` | `deathspark` 放射火花 | `Hips_sphere` |

**显隐机制**：把特效插槽的 setup alpha 设为 0（不可见），再用**插槽 rgba 时间轴**
在需要时把 alpha 打上去。这样 `cast` / `attack` / `process` / `die` 会有对应光效，
其余时间完全安静。

> 实测两个坑：
> 1. Spine 4.2 的插槽 `rgba` 是**绝对值**语义（setup `ffffff00` + 时间轴 `ff000080` → 正好 `(1,0,0,0.5)`），
>    所以可以用它做显隐，比 `attachment` 时间轴可靠 —— **`attachment` 时间轴在 4.2 里实测不生效**。
> 2. Spine 里「动画没 key 的属性会沿用上一个动画的残留值」，所以循环动画
>    （`idle_loop` / `relaxed_loop` / `low_health_loop`）必须显式把一次性特效清零，
>    否则 `die` 打完 `flare=0.95` 之后切回 idle，那道白光会一直挂着。

### ✅ 端到端验证

1. **打包产物自洽**：把 `.pck` 里的文件原样还原成 Godot 工程后加载，
   4 套 `.tres` 全部成功（复刻游戏的运行时路径解析）：
   ```
   ✅ defect_skel_data.tres                    骨骼=37 插槽=41(有附件40) 动画=8
   ✅ defect_merchant_skel_data.tres           骨骼=37 插槽=41(有附件40) 动画=8
   ✅ rest_site_defect_skel_data.tres          骨骼=37 插槽=41(有附件40) 动画=8
   ✅ characterselect_defect_skel_data.tres    骨骼=37 插槽=41(有附件40) 动画=8
      8 个动画逐个 apply 完成，无异常；特效插槽 glowie1 alpha=0.34
   ```
2. **游戏内加载成功**（实机日志）：
   ```
   [INFO] Found mod manifest file .../Contents/MacOS/mods/DefectSTS1Skin/DefectSTS1Skin.json
   [INFO] Loading Godot PCK .../DefectSTS1Skin.pck
   [INFO] Finished mod initialization for '故障机器人 · 一代复刻皮肤' (DefectSTS1Skin).
   WARNING: res://animations/character_select/defect/characterselect_defect_skel_data.tres:3
            - ext_resource, invalid UID: uid://ckw6d2bysi6et
            - using text path instead: res://animations/character_select/defect/characterselect_defect_sts1.atlas
   ```
   那条 UID 警告正是**覆盖生效的证据**：游戏读到了我们的 `.tres`，并回退到我们资源的文本路径。
   全程**无骨骼/数据加载错误**。

---

## 最终验证（每次改完都要跑）

`verify_final.gd`：用 `ProjectSettings.load_resource_pack()` 挂载交付的 pck
（**完全复刻游戏的加载路径**），逐个检查：

```
load_resource_pack = true
  ✅ defect_skel_data                  骨骼=37 插槽=41(附件40) 动画=8 特效部件=6/6 apply错误=0
  ✅ defect_merchant_skel_data         骨骼=37 插槽=41(附件40) 动画=8 特效部件=6/6 apply错误=0
  ✅ rest_site_defect_skel_data        骨骼=37 插槽=41(附件40) 动画=8 特效部件=6/6 apply错误=0
  ✅ characterselect_defect_skel_data  骨骼=37 插槽=41(附件40) 动画=8 特效部件=6/6 apply错误=0
  ✅ UI贴图 char_select_defect.png (132,195) / _locked / character_icon (85,85) / _outline
=== 最终结论: 全部通过 ===
```

游戏内日志（v0.111.0，DEFECT 运行中）：

```
Parse Error 数: 0        我们的 4 个 .tres 全部加载        与 mod 相关的 ERROR: 0
```

> 那些 `invalid UID ... using text path instead` 是**预期且无害**的：
> 我们的 `.tres` 用的是自建 uid，游戏的 uid 缓存不认识，于是回退到文本路径 —— 正是我们想要的结果。

## 未完成

1. **游戏内 8 个动画的"触发"与观感未经真人确认**：需要实际开一局 Defect
   （选人 → 战斗 → 攻击/施法/受击/死亡/低血量）逐条看。
   （资源层面已验证：8 个动画名齐全、逐个 apply 无异常、游戏能加载我们的 `.tres`。）
3. 位移幅度与缩放比例（`SIZE_RATIO ≈ 11.01`）是按游戏本体骨骼声明尺寸对齐的，
   实际屏幕表现可能需要微调。
4. 商店 / 营火 / 选人三套目前**共用同一套一代美术**（二代这三处原本有各自的立绘）。
5. 贴图未做超分/重绘（直接复用一代原始像素；一代图集比二代小很多）。

---

## 复现 / 继续开发

```bash
# 1) 一代 3.4 → 4.2（atlas 与骨架，含贝塞尔烘焙、color→rgba 等修正）
python3 tools/sts1_to_spine42.py

# 2) 从二代原版重定向出 6 个动画（需要 game-defect/anims.json，见下）
python3 tools/retarget_anims.py

# 3) 补二代特效部件（程序化生成贴图 + 扩图集 + 加插槽与透明度时间轴）
python3 tools/add_fx.py

# 4) 生成商店 / 营火 / 选人 三组资源（各自 root 缩放对齐游戏本体尺寸）
python3 tools/make_rigs.py

# 5) 导入 + 收集 + 生成 .tres + 校验 + 打包（全自动）
python3 assemble.py
```

重新导出二代原版动画（仅在需要更新参考数据时）：

```bash
G=~/Downloads/Godot_mono.app/Contents/MacOS/Godot
HOME=$PWD/godot-project/.godot-home "$G" --headless --path "$PWD/godot-project" \
  --script dump_anims.gd -- "$PWD/game-defect/defect.skel" "$PWD/game-defect/defect.atlas" \
  "$PWD/game-defect/anims.json"
```

工具一览：

| 脚本 | 作用 |
|---|---|
| `tools/pck.py` | pck v3 解析 / 提取（逆向实现，可读游戏本体与工坊 mod） |
| `tools/pack_pck.py` | pck v3 打包（往返验证 87/87 逐字节一致） |
| `tools/sts1_to_spine42.py` | 3.4 → 4.2 转换（atlas + 骨架 + 贝塞尔烘焙） |
| `tools/retarget_anims.py` | 二代动作 → 一代骨架的世界空间重定向 |
| `tools/add_fx.py` | 程序化生成特效部件并接进骨架/图集 |
| `tools/make_rigs.py` | 生成 4 组资源（含各组缩放） |
| `tools/spine_model.py` | 骨架世界变换 / 动画采样 / 火柴人预览 |
| `tools/bisect_skel.py` | 二分定位让 spine-cpp 崩溃的字段 |
| `assemble.py` | 全自动装配：导入 → 读 uid 生成 `.tres` → 收集 → 校验 → 打包 |

---

## 关键实测结论（踩过的坑）

见 [SPEC.md](SPEC.md) 第十节。最关键的三条：

1. **Spine JSON 的时间轴值是「相对 setup 姿势的偏移量」**，引擎会自动叠加。
   （已用官方 coin 示例交叉验证：写 `x: -473.39` + setup `243.14` → 实际 `-230.25`。）
   所以两代之间搬动作要基于**同一参考姿势**，否则会带上恒定偏置。
2. **spine-cpp 4.2 对两类数据会 signal 11 硬崩**（无报错）：
   `translate`/`scale`/`shear` 时间轴里的贝塞尔数组、以及插槽颜色时间轴的贝塞尔。
   规避：按 30fps **烘焙成密集线性关键帧**（保留缓动手感）。
   另：插槽颜色时间轴的键名在 4.2 里从 `color` 改成了 **`rgba`**。
3. **Spine 4.2 不再支持 3.4 的对象式 `skins` 格式**（`{"default": {slot: {att: {...}}}}`），
   会被**静默读成 0 个附件** —— 表现为「骨骼、动画全对，但角色完全隐形」。
   必须改成数组式 `[{"name":"default","attachments":{...}}]`。
   （这个坑很阴：它不报错、不崩溃，只是什么都不显示；靠 `get_attachment()` 逐个查才发现。）
4. **`.`spjson` 就是源 JSON 的逐字节副本**——Godot 的 spine 导入器不做 JSON→二进制转换，
   所以"Spine 二进制写出器"这个最大障碍根本不存在。

### 打包与回归验证（重要）

**必须用 Godot 自带的 `PCKPacker` 打包**（`packer.gd`，由 `assemble.py` 第 ④ 步调用）。
手写打包器（`tools/pack_pck.py`）与 Godot 的 pck 读取器存在细微不兼容
（Godot 用二分查找目录），会表现为游戏里 `.tres` 报 `Parse Error: Expected '['`，
进而整条角色资源链断掉——**选人卡片空白、战斗角色不可见**。
`tools/pack_pck.py` 现在只用于解包排查。

每次改完务必跑这个回归验证（复刻游戏的加载路径，能测出散文件测试测不到的问题）：

```bash
G=~/Downloads/Godot_mono.app/Contents/MacOS/Godot
HOME=/tmp/loadpck/.h "$G" --headless --path /tmp/loadpck \
  --script "$PWD/verify_pck.gd" -- "$PWD/dist/DefectSTS1Skin.pck"
```
（`/tmp/loadpck` 是一个只放了 `bin/` 与 `.godot/extension_list.cfg` 的空工程）

### 姿势编辑器的回路（重要：顺序有陷阱）

用户在 `姿势编辑器.command` 里调完姿势、点「导出」后，**导入必须放在手写动画之后**：

```bash
python3 tools/sts1_to_spine42.py      # 1. 3.4 -> 4.2 转换
python3 tools/make_hand_anims.py      # 2. 手写动画打底（8 个动画的基准）
python3 tools/import_poses.py         # 3. 用编辑器导出覆盖被编辑的那几个
python3 tools/add_fx.py               # 4. 特效部件与逐帧透明度
python3 tools/make_rigs.py            # 5. 营火 / 选人 / 商店三套骨骼
python3 assemble.py                   # 6. 打包 + 校验
```

> ⚠ **第 3 步不能单独跑**：`poses_export.json` 里 8 个动画都有一项（没被编辑的是空关键帧列表），
> 若跳过第 2 步直接导入，那 7 个没被编辑的动画会没有时间轴 -> 角色在游戏里不动。
> 顺序反了或漏跑第 2 步，都要重跑。
>
> 编辑器导出格式与 `tools/author_anims.py` 的 `bake()` 直接对接
> （`{t, pose:{骨骼:{rot/tx/ty}}}`），导入脚本负责补首尾关键帧、按 60fps + smoothstep 烘焙。

### 完整管线（顺序不能错）

```bash
python3 tools/sts1_to_spine42.py          # 1. 3.4 -> 4.2 转换（含 bounds 修复）
<py> tools/make_sts1_anims.py             # 2. 8 个动画（一代原版 + 整体平移）
<py> tools/add_fx.py                      # 3. 二代特效部件
<py> tools/add_corpse.py                  # 4. 死亡切一代尸体图
python3 tools/make_rigs.py                # 5. 商店/营火/选人三套骨骼
<py> tools/make_charselect_bg.py          # 6. 选角背景换成静态立绘（★必须在 5 之后）
python3 assemble.py                       # 7. 打包
```

> ⚠ 第 6 步**必须在第 5 步之后**：`make_rigs.py` 会把选人骨骼重写成战斗骨骼的副本，
> 顺序反了静态立绘就被覆盖。
