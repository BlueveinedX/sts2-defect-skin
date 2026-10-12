#!/bin/bash
# Defect 一代骨架 · 专用姿势编辑器
# 双击本文件即可启动。操作说明：
#   · 左键点骨骼 → 拖动 = 旋转；该时刻会自动记录/更新一帧关键帧
#   · 滚轮 = 缩放      右键拖动 = 平移画面
#   · 顶栏选动画 / 拖时间轴滑块 / 「打关键帧」把当前完整姿势存成帧
#   · 「洋葱皮」显示当前帧之前若干帧的半透明叠影（看轨迹用）
#   · 「导出」写出 godot-project/poses_export.json，交给管线
cd "$(dirname "$0")"
GODOT="/Users/lwx/Downloads/Godot_mono.app/Contents/MacOS/Godot"
if [ ! -x "$GODOT" ]; then echo "找不到 Godot: $GODOT"; read -n1; exit 1; fi
export HOME="$PWD/godot-project/.godot-home"
exec "$GODOT" --path "$PWD/godot-project" res://pose_editor.tscn
