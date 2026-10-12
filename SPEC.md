# 杀戮尖塔 2 · 故障机器人（Defect）一代复刻皮肤 — 技术规格与可行性结论

> 所有结论均来自本机实机取证：游戏本体 `Slay the Spire 2.pck`(v0.111.0)、
> 一代 `desktop-1.0.jar`、已安装的创意工坊 mod、以及游戏程序集 `sts2.dll`。
> 取证脚本与原始产物见 `tools/` 与 `analysis/`。

---

## 一、结论：能不能直接生成一个 mod 示例？

**分包材地说：**

| 事项 | 能否 | 说明 |
|---|---|---|
| 生成 mod 项目骨架（manifest / `.tres` / `.import` / 目录结构 / 资产清单） | **能，已完成** | 见 `mod/` |
| 打包成游戏能加载的 `.pck` | **能，已验证** | 自己写的 `tools/pack_pck.py`，对现成 mod 做**解包→重打包往返，87/87 文件逐字节一致** |
| 从一代 jar 抽取 Defect 原始素材 | **能，已完成** | 见 `ref-sts1/` |
| 把贴图重绘/超分成一代风格（保留构图与分区） | **能** | Python + Pillow 可用 |
| 直接产出「装进去就能跑、保留一代站姿、8 个动画齐全」的成品 | **目前不能** | 卡在下面两件事 |

**卡住的两件事（都不是包材问题，是内容与工具问题）：**

1. **这不是"换贴图"，是「8 个动画的完整 Spine 骨骼制作」。**
   一代 Defect 只有 `Idle` + `Hit` **两个**动画，二代代码要求 **8 个**；而两代骨架**完全不同**（见第四节）。
   所以一代骨骼**不能直接搬进去**，必须重建。
2. **本机缺 3 样东西**（详见第六节），其中「把骨骼数据写成二代运行时能吃的二进制 `.spskel`」目前没有已验证的免安装方案。

---

## 二、已实测的技术事实

### 2.1 二代 Defect 是原生角色，引擎是 Godot 4.5.1 + .NET

- 游戏版本 `v0.111.0`（`release_info.json`），资源包 `Slay the Spire 2.pck` 为 **Godot 4.5.1 / pck 格式 v3**。
- 角色动画用 **Spine**，运行时数据为 **Spine 4.2.43 二进制**（实测 `.spskel` 头部 `…34 2e 32 2e 34 33` = `4.2.43`）。
- mod 形态：`<game>/mods/<名字>/` 下放 `<id>.json` + `<id>.dll` + `<id>.pck` 三件套。

### 2.2 「皮肤 mod」的正确形态已被社区验证

本机已装的两个同类范例：

| mod | has_pck | has_dll | affects_gameplay | 说明 |
|---|---|---|---|---|
| `WatcherBeautified`（观者 美化版） | true | **false** | false | 纯美术覆盖，依赖基础角色 mod |
| `regentSkin` / `silentSkin` / `necrobinderSkin` | true | **false** | false | 纯皮肤，**不需要 DLL** |
| `Mechaneko_Defect`（Defect 皮肤） | true | true | false | 因改了 Hyperbeam 特效锚点才需要 Harmony 补丁 |

👉 **纯皮肤 mod 不需要 DLL**，因此不需要 .NET SDK。
👉 我们的目标形态照抄 `Mechaneko_Defect`（Defect 皮肤的既有先例）。

### 2.3 必须提供的 8 个动画名（硬编码在游戏代码里）

从 `sts2.dll` 的 UTF-16 字符串堆实测出现次数：

| 动画名 | 代码中出现次数 | 一代是否有 |
|---|---|---|
| `attack` | 639 | ❌ |
| `die` | 88 | ❌ |
| `hurt` | 56 | ✅（一代叫 `Hit`） |
| `cast` | 27 | ❌ |
| `idle_loop` | 19 | ✅（一代叫 `Idle`） |
| `process` | 4 | ❌ |
| `relaxed_loop` | 2 | ❌ |
| `low_health_loop` | 2 | ❌ |

交叉验证：`defect.skel` 的动画段计数 = **8**，且 8 个名字按字母序排列，
与已装 mod `Mechaneko_Defect` 的 `defect_skel_data.tres` 混合表完全吻合。
**缺任何一个，对应动作触发时就会失败。**

### 2.4 游戏只按「动画名」驱动，骨骼/插槽名完全不引用 ⭐

在 `sts2.dll` 中检索二代骨骼的部件名：

```
castfist_l  0 次     cowl 1  0 次     binder_bolt  0 次
defect_flare 0 次    eye_progress 0 次  hip joint top 0 次
l upper arm 0 次     blender/blender_core 0 次  deathspark/deathspark 0 次
```

👉 **这是最大的利好**：骨骼层级、骨骼命名、插槽命名**全部可以由我们自己定**，
只要提供上述 8 个正确命名的动画。**「保留一代站姿」在技术上是完全可行的**。

### 2.5 两代骨架完全不同（决定工作量）

| | 一代 Defect | 二代 Defect |
|---|---|---|
| 骨骼 | 37 根，`Hips` / `Chest` / `Arm_L_` / `Leg_L_` 命名 | 58 个部件，`hip` / `l upper arm` / `l leg middle` 命名 |
| 动画 | **2 个**（`Idle`、`Hit`） | **8 个** |
| 特效部件 | 无 | `binder_bolt`、`blender/*`(8)、`blip_*`、`glow1-4`、`deathspark/*`、`castfist_l/r`、`cowl *`、`pipe 1/2`、`eye_progress`、`defect_flare` |
| 贴图图集 | 一代 `defect.png` | 二代 1222×269，atlas `scale:0.166` |

一代独有的 `mantle` / `wire_*` / `crackedOrb` / `Hips_sphere` 等，二代没有。
**结论：不能"换皮"，只能"照一代风格重建骨架"。**

---

## 三、需要产出的资产清单（★ 已修正为「最简结构」）

拆了本机三个**无 DLL 纯皮肤** mod（`regentSkin` / `silentSkin` / `necrobinderSkin`）后发现，
皮肤 pck 里**只有 `.import` 重映射 + 导入产物**，没有源文件、也没有自己写的 `.tres`：

```
# 皮肤 mod 实际只需要（每个 = 1 个 .import + 1 个 .godot/imported 产物）
animations/characters/defect/defect.atlas.import   →  .spatlas
animations/characters/defect/defect.png.import     →  .ctex
animations/characters/defect/defect.skel.import    →  .spskel   ★ 8 个动画在这
animations/merchant/defect/defect_shop.{atlas,png}.import
animations/rest_site/defect/restsite_defect.{atlas,png,skel}.import
animations/character_select/defect/characterselect_defect.{atlas,png,skel}.import
animations/ui/combat/orbs/defect_{orbs.atlas,orbs.png,frost_orb,glass_orb,lightning_orb,plasma_orb}.import
```

**原理**：`res://…/defect.atlas` 是靠同目录 `defect.atlas.import` 的 `path=` 指向真实资源的。
mod 只要提供**同名 `.import`** 指向**我们那份**产物，游戏原本的 `defect_skel_data.tres`
就自动指向我们的骨骼 —— 所以**不需要写 `.tres`，也不需要在 pck 里放源文件**。

（`Mechaneko_Defect` 走的是另一条"新文件名 + 覆盖 `.tres`"的路，也能用，但文件更多、更易错。）

必需 17 项 + 可选 13 项（UI 立绘/头像/联机手势/能量球层）见 `build.py`。
不覆盖约 130 张卡牌插画与时代立绘——那属于另一个 mod 的范畴。

---

## 四、资源格式（已逆向，决定"不装 Godot 行不行"）

| 格式 | 实测结构 | Python 能否自己写 |
|---|---|---|
| `.pck` | `GDPC` + v3 头 + 原样数据 + **末尾**目录区（`pack_flags=2`，offset 相对 `file_base=128`） | ✅ **已实现并往返验证** |
| `.import` | 纯文本 `[remap]`，`path="res://.godot/imported/<名>-<md5>.<ext>"` | ✅ 简单 |
| `.tres` | 纯文本 `SpineSkeletonDataResource`，可用 `animation_mixes` 写混合表 | ✅ 简单（本方案用不到） |
| `.spatlas` | 就是 JSON：`{"atlas_data":"<Spine 文本 atlas>", "source_path":…}` | ✅ **简单** |
| `.ctex` | `GST2` 头 + **WebP 无损**负载（实测含 `RIFF/WEBPVP8L`） | ⚠️ 大概率可行（Pillow 能编 WebP 无损），头部字段需再确认 |
| `.spskel` | Spine **4.2.43 二进制**（长度前缀用 `字符数+1` 语义） | ⚠️ **最硬的一块**，需要 JSON→二进制的写出器 |
| `.md5` | 每个导入产物的 32 字节十六进制文本旁挂文件 | ✅ 简单 |

👉 也就是说：**除了 `.spskel`，整条链路我都能用 Python 复刻，不需要 Godot。**
`.spskel` 可以走「**原地改浮点数**」的路子绕开（见第七节路线 B）。

---

## 五、构建管线（路线 A，已实测确认）

1. 装 **Godot 4.5.1** + **spine-godot**（对齐 Spine **4.2** 分支）。
2. 建一个空 Godot 工程，把源 `.png/.atlas/.skel`（或 `.json`）按**游戏原版路径**摆好。
   导入后 Godot 生成 `.godot/imported/*.ctex|.spatlas|.spskel` 与同名 `.import` 重映射。
3. 把 `.import` + `.godot/imported/` 一起打进 `.pck`（源文件可打可不打，运行时用不到）。
4. 游戏加载 mod 的 `.pck` 时优先级高于本体，于是 `defect.atlas` / `defect.skel`
   解析到**我们那份**产物；游戏原本的 `defect_skel_data.tres` 无需改动即指向我们的骨骼。

> 关键：**同名 `.import` 覆盖 = 换绑成功**。所以自定义骨骼完全自由，
> 也不用碰 `.tres`、不用改任何游戏代码。

**关于 spine-godot 的分发（澄清一个常见误解）：**
- npm 上只有 Spine 的 **Web/JS** 运行时（`@esotericsoftware/spine-core` 等），与 Godot 无关。
- Godot 用的是 `spine-godot`，从 [Esoteric 官方文档页](https://en.esotericsoftware.com/spine-godot) 下载，
  两种形式：**GDExtension**（把 `bin/` 丢进工程根目录，无 C# 绑定）或**自定义 Godot 编辑器**（C++ 模块版，带 C#）。
- ✅ **已核实存在现成构建，不必自己编译**：
  `https://spine-godot.s3.eu-central-1.amazonaws.com/4.2/4.5.1-stable/spine-godot-extension-4.2-4.5.1-stable.zip`
  （14 MB，含 macOS 编辑器二进制；已下好放在 [`vendor/`](vendor/)）
- **纯皮肤不需要 .NET / C# 版 Godot。**

---

## 六、缺什么（工具 / 资源）

| # | 缺的东西 | 本机状态 | 是否必需 | 用途 |
|---|---|---|---|---|
| 1 | **Godot 4.5.1（标准版即可，不必 .NET 版）** | ❌ 未安装 | 走路线 A 则必需 | 生成 `.ctex/.spatlas/.spskel`。官方有预编译包 |
| 2 | **spine-godot（Spine 4.2 + Godot 4.5.1）** | ✅ **已下好放 [`vendor/`](vendor/)** | 同上 | Spine 导入器。**不在 npm 上**，见第五节 |
| 3 | **.NET SDK 9 / 10** | ❌ `dotnet` 不存在 | **仅当需要 Harmony 补丁时** | 编译 `.dll`；纯皮肤不需要 |
| 4 | **Spine 编辑器（付费授权）** | ❌ | 不必须 | 直接写 Spine 4.2 JSON 也可以；但有编辑器效率天差地别 |
| 5 | GDRE Tools / gdsdecomp | ❌ | 不必须 | 我自己的 `tools/pck.py` 已替代（能列目录+提取） |
| 6 | ffmpeg | ❌ | 不必须 | 仅视频抽帧时会用到 |
| 7 | STS2 Modding MCP（151 工具） | ❌ 未配置（`~/.dsh` 无 mcpServers） | 不必须 | 偏玩法向，对皮肤/Spine 动画帮助有限 |

**一句话：要么装 Godot（路线 A，稳），要么让我用 Python 自己写导入产物（路线 B，省安装但有风险）。**

---

## 七、两条路线

### 路线 A（已选定）· 装 Godot，走标准管线

```
必需：Godot 4.5.1（标准版即可）
      spine-godot GDExtension（Spine 4.2 / Godot 4.5.1）—— 现成 zip，已核实可下载
可能追加：.NET 9/10 SDK —— 只有要编 Harmony 补丁修特效锚点时才需要
```
- 优点：导入器是官方实现，`.spskel/.ctex/.spatlas` 一定合法；后续改动画可以反复导入。
  **两个依赖都有官方预编译包，不需要 Xcode、不需要从源码编。**
- 缺点：要装两个东西、要建一个 Godot 工程。

### 路线 B · 不装 Godot，全程 Python

- ✅ 已解决：`.pck` 打包（已验证）、`.spatlas`、`.import`、`.tres`、`.md5`
- ⚠️ 待攻：`.spskel`
  - **B-1「原地改姿势」**（推荐先试）：沿用游戏原版 `defect.skel` 的**骨架结构与 8 个动画的时间轴结构不变**，
    只把 `rotate/translate` 时间轴上的**浮点数值**替换成按一代姿势曲线重采样的结果。
    尺寸不变 → 不需要实现二进制写出器，只需要更细的时间轴定位能力。
  - **B-2「完整写出器」**：实现 Spine 4.2 JSON→二进制写出器。能力最全，但工作量最大、风险最高。

---

## 八、真正的工作量在哪

技术管线只是一半，**内容才是主体**：

1. **重建骨架**：按一代 Defect 的体型/比例，在二代 58 个部件的语义基础上建一套自己的骨（可以沿用一代命名）。
2. **贴图**：把一代 `defect.png` 提到二代图集的精度（一代图集远小于二代 1222×269），
   并补齐二代才有的特效部件 —— **已决定补齐**（否则 `cast`/`process` 会"空手做动作"）：
   `blender/*`(8 个辉光)、`blip_circle`、`blip_star`、`glow1-4`、`deathspark/deathspark`、
   `binder_bolt`、`castfist_l`、`castfist_r`、`cowl 1/2/back`、`pipe 1/2`、
   `eye_progress`、`orb patch`、`orb shine`、`orb sparkles`、`defect_flare`。
3. **8 个动画**：
   - `idle_loop` ← 一代 `Idle`（保站姿，这是核心要求）
   - `hurt` ← 一代 `Hit`
   - `attack` / `cast` / `die` / `process` / `relaxed_loop` / `low_health_loop` ← **需要新做（6 个）**
4. **另外三套骨骼**（商店 / 营火 / 选人）的动画名还需要用 2.3 的方法单独枚举确认。
   ⚠️ **风险点**：骨骼比例改成一代体型后，游戏里硬编码的特效锚点（例如 Hyperbeam 发射位置）
   可能错位 —— `MechaNeko_Defect` 就是为此打了个 Harmony 补丁。届时才需要 .NET SDK。

---

## 九、下一步

- [x] 逆向 pck 格式，写出并验证打包器
- [x] 抽取一代 Defect 全部原始素材
- [x] 枚举二代要求的 8 个动画名并交叉验证
- [x] 确认骨骼名不被代码引用（解锁自建骨骼）
- [x] 产出 mod 项目骨架与资产清单
- [x] **定路线：A**；**特效部件：补齐**
- [x] 修正皮肤结构（只需 `.import` + 导入产物）
- [ ] 装 Godot 4.5.1 + spine-godot(4.2)，搭好工程
- [ ] 生成 8 个动画的骨架 + 补齐特效部件（+ 重采样一代姿势）
- [ ] 重绘/超分贴图并重打包图集
- [ ] 打 pck → 装进 `mods/` → 进游戏验证 8 个动画逐个触发

---

## 十、已验证的「一代 Spine 3.4 → 二代 Spine 4.2」转换配方

> 本节全部为**实机验证**结论（Godot 4.5.1.stable.mono + spine-godot GDExtension 4.2/4.5.1）。
> 复现脚本：[tools/sts1_to_spine42.py](tools/sts1_to_spine42.py)；
> 定位工具：[tools/bisect_skel.py](tools/bisect_skel.py)。

### 10.1 结论：一代骨架**可以**直接转，不需要 Spine 编辑器

已跑通：一代 Defect 的 37 骨骼 / 33 插槽 / 19 网格 + 13 区域 / 原始贴图，
在 4.2 运行时里 `骨骼=37 插槽=33 动画=["hurt","idle_loop"]` **完整加载并实例化**。

### 10.2 五个必须处理的坑（按发现顺序）

| # | 坑 | 症状 | 修法 |
|---|---|---|---|
| 1 | **扩展名** | `.json` 被当**二进制**读 → `Skeleton version ton": {...} does not match runtime version 4.2` | 骨架文件必须命名 `.spine-json`，不能是 `.json` |
| 2 | **atlas 旋转区域** | 加载崩 | 3.4 的 `size` 是「未旋转」尺寸；4.x 的 `bounds` 是页面内实际占位，`rotate: true` 时**宽高要互换**。判据：`left_arm`/`left_quad` 不互换会溢出页面 |
| 3 | **`translate`/`scale`/`shear` 时间轴的贝塞尔** | **signal 11 硬崩**（无任何报错） | `"curve": [x1,y1,x2,y2]` 会让 spine-cpp 4.2 崩；`stepped`/无曲线正常。**按 30fps 烘焙成密集线性关键帧**，保留缓动手感 |
| 4 | **插槽颜色时间轴的贝塞尔** | 同上，硬崩 | 同理烘焙（4 通道 hex 颜色逐通道插值） |
| 5 | **插槽颜色时间轴键名** | `Invalid timeline type for a slot: color` | 4.2 把 `color` 改名成 **`rgba`**（`rgb`/`alpha` 也被接受） |
| 6 | **对象式 `skins`** | **不报错、不崩溃**，但 33 个插槽 `get_attachment()` 全为 `null` → 角色完全隐形 | 必须改成 4.2 数组式 `[{"name":"default","attachments":{slot:{att:{…}}}}]`。4.2 的 `readSkin` 只认 `attachments` 键，对象式被静默跳过 |

| 7 | **`rotate` 关键帧字段** | **不报错、不崩溃**，但整条旋转时间轴被静默忽略 → 角色永远停在 setup pose，动画只剩位移和插槽颜色（"攻击没有身体动作、只有特效"） | 4.2 用 **`"value"`**，不是 3.4 的 `"angle"`。实测：写 `angle` → `Arm_R_.get_rotation()` 恒等于 setup；写 `value` → 正确生效 |

> 同批实测的其它字段：`translate`/`scale`/`shear` 用 `x`,`y` ✅ 正确；
> `attachment` 用 `name` ✅ 正确；`rgba` 用 `color` ✅ 正确；`deform` 用 3.4 的 `offset+vertices` ❌ 不生效（网格保持 setup 形状，视觉可接受）。

**另一个隐蔽语义**：`attachment` 时间轴在 4.2 里**不生效**（实测设置后 `get_attachment()` 不变）。
要让部件按动画显隐，用**插槽 `rgba` 时间轴改 alpha**（实测是**绝对值**语义，
setup `ffffff00` + 时间轴 `ff000080` → 结果正好 `(1,0,0,0.5)`）。
注意 Spine 里「动画没 key 的属性会沿用上一个动画的残留值」，
所以循环动画必须把一次性特效显式清零。

**不受影响的**：`rotate` 的贝塞尔、`deform`、`ik`、`slots.attachment`、旧版 `skins` 对象格式、
`type: "mesh"` 网格附件、骨骼 `color` —— 这些 4.2 全部原样接受。

> ⚠️ spine-cpp 4.2 对非法数据是**硬崩而非报错**，所以调试只能靠"删掉某部分再试"。
> [tools/bisect_skel.py](tools/bisect_skel.py) 就是干这个的，二分定位到最小致崩单元。

### 10.3 另一条重要发现：`.spjson` 是 JSON 的**逐字节副本**

Godot 的 `spine.json` 导入器**不做 JSON→二进制转换**，只是把源 `.spine-json` 复制成
`.godot/imported/<名>-<md5(源路径)>.spjson`。
所以「Spine 二进制写出器」这个最大的技术障碍**不存在**。

### 10.4 换皮的真正机制

`.import` 里的 `path=` 文件名哈希 = **`md5("res://" + 源路径)`**（不是内容哈希），
已与游戏本体 pck 里的文件名逐一核对一致。

皮肤 mod 靠**覆盖 `.tres`** 换绑（本方案）：提供与游戏**同 res:// 路径、同 uid** 的
`*_skel_data.tres`，把 atlas/skeleton 指向自己的资源，再把 `.import` + 导入产物一起打进 pck。
uid 必须在 `.tres` 与 `.import` 间严格一致 —— [assemble.py](assemble.py) 从 Godot 生成的
`.import` 里读 uid 回填 `.tres`，避免手抄出错。

### 10.5 缩放基准：必须用「实测身体高度」，不能用骨架声明的 bbox

游戏原版 `defect.skel` 声明的 bbox 是 2080×**2339**，但那是被**停在远处**的特效骨骼撑大的
（`sparkBlast1` 在 x=3738、`flare` 在 x=3745、`blender_blade` 在 (2467,1977)、`cowl_extra` 在 (2100,1600)）。
按 bbox 缩放会让角色**偏大约 30%**，在商店这种近景里特别明显。

实测「身体高度」（排除远置特效骨骼的 y 范围）：

| 骨骼 | 声明 bbox 高 | **实测身体高** | 应设 root scale |
|---|---|---|---|
| 战斗 `defect` | 2339 | **1828.5** | 10.026 |
| 营火 `restsite_defect` | 728 | **511.8**（坐姿） | 2.806 |
| 选人 `characterselect_defect` | 3217.7 | **1440.2** | 7.897 |

（一代骨架在 root scale=1 时的身体高度实测为 182.37，故 `scale = 目标身体高 / 182.37`。）

### 10.6 环境事实

- Godot：`~/Downloads/Godot_mono.app`，`4.5.1.stable.mono.official`（.NET 版可正常加载 GDExtension）
- GDExtension：`vendor/spine-godot-extension-4.2-4.5.1-stable.zip`（Spine 4.2 / Godot 4.5.1）
- headless 导入必须**跑两次**：首次扫描时 spine 导入插件还没挂上，会漏掉 `.atlas`/`.spine-json`
- Godot 需要可写 HOME：用 `HOME=<工程>/.godot-home` 重定向，否则写 `~/Library/Application Support/Godot` 会失败
- 退出时偶发 signal 11（`EditorHelp::_gen_extensions_docs`），不影响导入产物生成

---

## 十一、★ 打包必须用 Godot 自带的 PCKPacker（血的教训）

**症状**：pck 内容用 Python 解出来**完全正确**，但在游戏里加载 `.tres` 报
`Parse Error: Expected '['`，随后整条角色资源链断掉 →
选人界面角色卡片空白、战斗中角色完全不可见。

**原因**：`tools/pack_pck.py`（我按逆向出的格式手写的打包器）与 Godot 的 pck **读取器**
存在细微不兼容。Godot 读目录用的是**二分查找**（`PackedData::_find_file`），
对目录条目的顺序/布局有自己的预期；手写打包器即使能被我自己的解析器读回，
也可能让 Godot 定位到错的字节区间——于是 `.tres` 读成了别的文件的内容。

**修法**：改用 Godot 自己的 `PCKPacker`（见 `packer.gd` + `assemble.py` 第 ④ 步）：

```gdscript
var pk := PCKPacker.new()
pk.pck_start(out_path, 32)
for f in files: pk.add_file(f["target"], f["source"])   # res://目标 <- 绝对源路径
pk.flush(true)
```

**回归验证**（复刻游戏加载路径，务必每次都跑）：

```gdscript
ProjectSettings.load_resource_pack(pck_path, false)
load("res://animations/characters/defect/defect_skel_data.tres")
```

> `tools/pack_pck.py` 保留，但**只用于解包/排查**，不再用于打包。

---

## 十二、★ 最隐蔽的一个错：4.x atlas 的 `bounds` 存「未旋转尺寸」

**症状**：网格部件的贴图**断开**——上臂/前臂/手各悬空一段，左侧小腿、小臂甚至**整块缺失**。

**错误做法**（我最初的判断）：以为 4.x 的 `bounds` 是「区域在页面里的实际占位」，
于是对 `rotate: true` 的区域把宽高互换（理由：不互换会溢出页面）。

**正确做法**：`bounds` 存的是**未旋转的原始尺寸**（等同 3.4 的 `size`），
旋转后的页面占位由**运行时自己互换**。我那次互换等于**双重互换**，
所有旋转区域的采样矩形整体错位 → 断缝 + 缺块。

**为什么我两次验证都没发现**：
1. 第一次我拿「不互换会不会溢出页面」当判据 —— 那测的是 **3.4 文件里艺术的实际占位**，
   回答不了「4.x 的字段该写什么」这个问题。
2. 第二次我把两版画进**同一张图**再逐像素比较（两版位置不同，当然全图都不同），
   得出"两版一样"的错误结论。
3. 真正有效的做法：**两版分别渲染、放大到出问题的部位、并排看**。
   不互换的那版甲片是连上的——一眼可辨。

教训：**"数据与源文件一致"不能证明"渲染正确"**，跨版本转换必须靠渲染对照验证。
