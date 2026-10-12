# 故障机器人 · 一代复刻皮肤（Slay the Spire 2）

把《杀戮尖塔》**初代故障机器人**的美术按原始精度移植到《杀戮尖塔 2》：
一代原版贴图、原版站姿、8 个动画、死亡切换一代尸体图、选角大立绘。

> **纯美术覆盖**，不含 DLL，不改变玩法。

---

## 给玩家：安装

1. 到 [Releases](../../releases) 下载 `DefectSTS1Skin-v0.1.0.zip`
2. 解压出 `DefectSTS1Skin/` 文件夹
3. 放进游戏的 **Mods** 目录：

| 平台 | 路径 |
|---|---|
| **macOS** | `<游戏>/SlayTheSpire2.app/Contents/MacOS/Mods/` |
| Windows | `<游戏>/Mods/` |

> ⚠ macOS 下必须是 **app 包内的 `Contents/MacOS/Mods/`**，不是游戏根目录的同名文件夹——游戏只扫前者。

4. 启动游戏，在模组列表里确认已启用。

---

## 给想自己构建的人

### 1. 取素材（**本仓库不含任何游戏素材**）

《杀戮尖塔》与《杀戮尖塔 2》的美术版权归 MegaCrit。所有素材都从**你自己合法拥有的安装**里提取：

```bash
python3 tools/extract_assets.py                # 自动探测 Steam 常见路径
python3 tools/extract_assets.py --sts1 <路径> --sts2 <路径>
python3 tools/extract_assets.py --check        # 只检查齐全性
```

素材会提取到 `.gitignore` 已排除的目录（`ref-sts1/`、`game-rigs/` 等），**不会进仓库**。

### 1.5 装 spine-godot 扩展

本仓库不含扩展二进制。下载 `spine-godot` 4.2 / 4.5.1 版本，解压到
`godot-project/bin/`（该目录已被 `.gitignore` 排除）。

### 2. 六步管线（顺序不能错）

```bash
python3 tools/sts1_to_spine42.py          # 1. Spine 3.4 -> 4.2 转换
<py>    tools/make_sts1_anims.py          # 2. 8 个动画（一代原版 + 整体平移）
<py>    tools/add_fx.py                    # 3. 二代特效部件
<py>    tools/add_corpse.py                # 4. 死亡切一代尸体图
python3 tools/make_rigs.py                # 5. 商店/营火/选人三套骨骼
<py>    tools/make_charselect_bg.py        # 6. 选角背景（★必须在 5 之后）
python3 assemble.py                       # 7. 打包 + 校验
```

> ⚠ **第 6 步必须在第 5 步之后**：`make_rigs.py` 会把选人骨骼重写成战斗骨骼的副本，
> 顺序反了静态立绘就被覆盖。

### 3. 验证（改完必跑）

用 `ProjectSettings.load_resource_pack()` **挂载 pck 再加载**——完全复刻游戏的加载路径：

```bash
<godot> --headless --path <空工程> --script verify_final.gd -- dist/DefectSTS1Skin.pck
```

> 这一步不能省。把 pck 解成散文件再加载是**测不出 pck 读取问题的**。

---

## 附带工具

| 工具 | 用途 |
|---|---|
| `tools/motion_metrics.py` | **动作量化对比**：把「动作像不像人做的」拆成可测指标（静止帧占比、发力点、峰值速度、轨迹总长），并拿游戏原版动画当基准 |
| `tools/author_anims.py` | 手写动画：FK 模型 + **解析 2 骨 IK**（余弦定理），关键帧按 60fps + smoothstep 烘焙 |
| `姿势编辑器.command` | 专用姿势编辑器（Godot）：拖骨骼旋转、拖手脚末端走 IK、洋葱皮、时间轴打关键帧、导出 JSON。见 [姿势编辑器说明.md](姿势编辑器说明.md) |
| `tools/pck.py` | Godot pck 解包（排查用） |

## 已知限制

- 仅在 **macOS** 上构建与验证过（`.pck` 本身跨平台，但未在 Windows/Linux 实测）
- 选角界面是**静态立绘**，不是 Spine 骨骼
- `cast` 动画幅度受「双手抱核心」设定的物理限制（一代手臂可达环带只有约 47 单位行程）

## 版权

- **代码**：MIT（见 [LICENSE](LICENSE)）
- **美术素材**：归 **MegaCrit** 所有，本仓库不含任何素材；请从自己的游戏安装提取，提取后请勿再分发

## 技术笔记

跨版本移植踩到的坑（Spine 3.4→4.2 的字段语义、pck 打包器兼容性、rgba 八位色等十二条）都记在 [SPEC.md](SPEC.md)，希望对做同类移植的人有用。
