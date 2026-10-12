# -*- coding: utf-8 -*-
# Defect 一代骨架专用姿势编辑器（第一阶段：旋转拖动 + 时间轴 + 关键帧 + 洋葱皮 + 导出）
#
# 关键设计：spine-godot 的 Manual 更新模式不重建渲染网格（实测渲染空白），
# 所以本节点必须作为 SpineSprite 的**后一个兄弟节点**——Godot 按树序调 _process，
# 后跑的覆盖先跑的，这样我在这里设的姿势才能生效并渲染出来。
extends Node2D

const SKEL := "res://animations/characters/defect/DefectSTS1.spine-json"
const ATLAS := "res://animations/characters/defect/DefectSTS1.atlas"
const OUT := "res://poses_export.json"   # 落在 godot-project/ 下，方便直接接进管线
const ANIMS := ["idle_loop","relaxed_loop","low_health_loop","process","attack","cast","hurt","die"]
const PICK_R := 18.0
const GHOST_ALPHA := 0.28

var atlas_res: SpineAtlasResource
var sk_json: Dictionary = {}      # 骨架 JSON 原文（用于生成临时预览骨架）
var tmp_n := 0
var skel_data: SpineSkeletonDataResource
var sprite: SpineSprite
var ghosts: Array[SpineSprite] = []
var skel: SpineSkeleton
var state: SpineAnimationState
var setup := {}            # 骨名 -> {rot,x,y}（从 JSON 读，不依赖 SpineBone 的 getter）
var bone_names: PackedStringArray = []
var keys := {}             # anim -> Array[{t, pose:{bone:{rot,tx,ty}}}]
var cur_anim := "attack"
var cur_t := 0.0
var sel := ""
var dragging := false
var ik_mode := false
var trans_mode := false          # 拖动=平移（Hips 或按住 Shift）
var drag_last := Vector2.ZERO
var drag_base := {}
var root_scale := 10.026
var drag_start_angle := 0.0
var drag_bone_angle := 0.0
var pan := Vector2(560, 700)
var zoom := 0.30
var show_ghost := true
var playing := false
# 拖末端骨骼 = 走 IK（解析余弦定理，和 tools/author_anims.py 同一套口径）
const IK_CHAINS := {
	"Arm_R_3": ["Arm_R_", "Arm_R_2", "Arm_R_3"],
	"Arm_L_3": ["Arm_L_", "Arm_L_2", "Arm_L_3"],
	"Leg_R_4": ["Leg_R_", "Leg_R_2", "Leg_R_4"],
	"Leg_L_4": ["Leg_L_", "Leg_L_2", "Leg_L_4"],
}

var opt: OptionButton
var slider: HSlider
var info: Label

func _ready() -> void:
	RenderingServer.set_default_clear_color(Color(0.09, 0.10, 0.13, 1))
	get_window().size = Vector2i(1280, 900)
	# --- 从 JSON 读静止姿态（不依赖 SpineBone 的 x/y getter）---
	var raw := FileAccess.get_file_as_string(SKEL)
	var j: Dictionary = JSON.parse_string(raw)
	for b in j["bones"]:
		setup[b["name"]] = {"rot": b.get("rotation", 0.0), "x": b.get("x", 0.0), "y": b.get("y", 0.0)}
		bone_names.append(b["name"])
		if b["name"] == "root":
			root_scale = float(b.get("scaleX", 1.0))
	# --- 洋葱皮先加（画在底下），再主精灵，最后 UI ---
	for i in 4:
		var g := _make_sprite()
		g.modulate = Color(1, 1, 1, GHOST_ALPHA)
		g.visible = false
		ghosts.append(g)
	for a in ANIMS:
		if not keys.has(a):
			keys[a] = []
	sprite = _make_sprite()
	_build_ui()
	_refresh()
	print("[姿势编辑器] 骨骼 ", bone_names.size(), " 根，动画 ", ANIMS.size(), " 个")

func _make_sprite() -> SpineSprite:
	if skel_data == null:
		var at := SpineAtlasResource.new(); at.load_from_atlas_file(ATLAS)
		atlas_res = at
		sk_json = JSON.parse_string(FileAccess.get_file_as_string(SKEL))
	var s := SpineSprite.new()
	add_child(s)
	return s

func _build_ui() -> void:
	var layer := CanvasLayer.new(); add_child(layer)
	var box := HBoxContainer.new(); box.position = Vector2(10, 8); layer.add_child(box)
	opt = OptionButton.new()
	for a in ANIMS: opt.add_item(a)
	opt.selected = ANIMS.find(cur_anim)
	opt.item_selected.connect(func(i): cur_anim = ANIMS[i]; cur_t = 0.0; _refresh())
	box.add_child(opt)
	var b_key := Button.new(); b_key.text = "打关键帧"; b_key.pressed.connect(_set_key); box.add_child(b_key)
	var b_del := Button.new(); b_del.text = "删关键帧"; b_del.pressed.connect(_del_key); box.add_child(b_del)
	var b_gh := Button.new(); b_gh.text = "洋葱皮"; b_gh.toggle_mode = true; b_gh.button_pressed = true
	b_gh.toggled.connect(func(v): show_ghost = v; _refresh()); box.add_child(b_gh)
	var b_ex := Button.new(); b_ex.text = "导出"; b_ex.pressed.connect(_export); box.add_child(b_ex)
	var b_play := Button.new(); b_play.text = "播放"; b_play.toggle_mode = true
	b_play.toggled.connect(func(v): playing = v); box.add_child(b_play)
	var b_re := Button.new(); b_re.text = "清空当前动画"; b_re.pressed.connect(func(): keys[cur_anim] = []; _refresh()); box.add_child(b_re)
	slider = HSlider.new()
	slider.min_value = 0.0; slider.max_value = 1.0; slider.step = 0.001
	slider.custom_minimum_size = Vector2(560, 0)
	slider.position = Vector2(10, 44); slider.value_changed.connect(func(v): cur_t = v; _refresh())
	layer.add_child(slider)
	info = Label.new(); info.position = Vector2(10, 74); layer.add_child(info)

func _anim_dur() -> float:
	match cur_anim:
		"idle_loop": return 6.0
		"relaxed_loop": return 8.0
		"low_health_loop": return 6.0
		"process": return 1.567
		"attack": return 1.5
		"cast": return 1.233
		"hurt": return 0.333
		"die": return 2.233
	return 1.0

# ---------------------------------------------------------------- 姿势求值
func _keys_sorted() -> Array:
	var a: Array = keys[cur_anim].duplicate()
	a.sort_custom(func(p, q): return p["t"] < q["t"])
	return a

func _eval(t: float) -> Dictionary:
	var a := _keys_sorted()
	if a.is_empty(): return {}
	if t <= a[0]["t"]: return a[0]["pose"]
	if t >= a[-1]["t"]: return a[-1]["pose"]
	var k := 0
	while k < a.size() - 1 and a[k + 1]["t"] <= t: k += 1
	var t0: float = a[k]["t"]; var t1: float = a[k + 1]["t"]
	var u := 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
	u = u * u * (3.0 - 2.0 * u)                      # smoothstep，和 author_anims.py 一致
	var pa: Dictionary = a[k]["pose"]; var pb: Dictionary = a[k + 1]["pose"]
	var out := {}
	for bn in setup:
		var va: Dictionary = pa.get(bn, {}); var vb: Dictionary = pb.get(bn, {})
		var r := 0.0; var x := 0.0; var y := 0.0
		r = lerp(va.get("rot", 0.0), vb.get("rot", 0.0), u)
		x = lerp(va.get("tx", 0.0), vb.get("tx", 0.0), u)
		y = lerp(va.get("ty", 0.0), vb.get("ty", 0.0), u)
		if abs(r) > 0.01 or abs(x) > 0.001 or abs(y) > 0.001:
			out[bn] = {"rot": r, "tx": x, "ty": y}
	return out

func _apply(pose: Dictionary) -> void:
	skel.set_to_setup_pose()
	var bs := skel.get_bones()
	for i in bs.size():
		var b: SpineBone = bs[i]
		var n: String = b.get_data().get_bone_name()
		var p: Dictionary = pose.get(n, {})
		var s: Dictionary = setup.get(n, {"rot": 0.0, "x": 0.0, "y": 0.0})
		b.set_rotation(s["rot"] + p.get("rot", 0.0))
		if b.has_method("set_x"):
			b.set_x(s["x"] + p.get("tx", 0.0))
			b.set_y(s["y"] + p.get("ty", 0.0))
	skel.update_world_transform(0)

# ★ 不能直接改骨骼：SpineSprite 自己的更新会把骨骼重写掉（实测两张截图逐像素相同）。
#   改成把姿势烘进一份「只含这一帧」的临时骨架 JSON，重建数据资源后播放 _live 动画。
#   每次重建都从 setup 开始，未被 key 的骨骼自然保持静止姿势。
func _show(sp: SpineSprite, pose: Dictionary) -> void:
	tmp_n += 1
	var tmp := "/tmp/pe_live_%d.spine-json" % (tmp_n % 8)
	var tl := {}
	for bn in pose:
		var pd: Dictionary = pose[bn]
		var one := {}
		if absf(pd.get("rot", 0.0)) > 0.001:
			one["rotate"] = [{"time": 0, "value": pd["rot"]}]
		if absf(pd.get("tx", 0.0)) > 0.001 or absf(pd.get("ty", 0.0)) > 0.001:
			one["translate"] = [{"time": 0, "x": pd.get("tx", 0.0), "y": pd.get("ty", 0.0)}]
		if not one.is_empty(): tl[bn] = one
	var j := {
		"skeleton": sk_json.get("skeleton", {}),
		"bones": sk_json.get("bones", []),
		"slots": sk_json.get("slots", []),
		"skins": sk_json.get("skins", []),
		"animations": {"_live": {"bones": tl}},
	}
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	f.store_string(JSON.stringify(j))
	f.close()
	var sf := SpineSkeletonFileResource.new(); sf.load_from_file(tmp)
	var dr := SpineSkeletonDataResource.new()
	dr.skeleton_file_res = sf
	dr.atlas_res = atlas_res
	sp.skeleton_data_res = dr
	var st := sp.get_animation_state()
	if st != null:
		st.clear_tracks()
		st.set_animation("_live", false, 0)
		st.update(0.0)
	var sk := sp.get_skeleton()
	if sk != null:
		sk.update_world_transform(0)
		if sp == sprite:
			skel = sk
			state = sp.get_animation_state()

func _refresh() -> void:
	for g in ghosts:
		g.position = pan
		g.scale = Vector2(zoom, zoom)
	sprite.position = pan
	sprite.scale = Vector2(zoom, zoom)
	var pose := _eval(cur_t)
	_show(sprite, pose)
	for i in ghosts.size():
		var off := (i + 1) * 0.06
		ghosts[i].visible = show_ghost
		if show_ghost:
			var gp := _eval(max(0.0, cur_t - off))
			if gp.is_empty(): gp = pose
			_show(ghosts[i], gp)
	info.text = "动画 %s   时长 %.3fs   当前 %.3fs   关键帧 %d   选中 %s   滚轮缩放 / 右键平移 / 拖 Hips 为平移" % [
		cur_anim, _anim_dur(), cur_t, keys[cur_anim].size(), (sel if sel != "" else "无")]

func _apply_to(sp: SpineSprite, pose: Dictionary) -> void:
	var sk := sp.get_skeleton()
	sk.set_to_setup_pose()
	var bs := sk.get_bones()
	for i in bs.size():
		var b: SpineBone = bs[i]
		var n: String = b.get_data().get_bone_name()
		var p: Dictionary = pose.get(n, {})
		var s: Dictionary = setup.get(n, {"rot": 0.0, "x": 0.0, "y": 0.0})
		b.set_rotation(s["rot"] + p.get("rot", 0.0))
		if b.has_method("set_x"):
			b.set_x(s["x"] + p.get("tx", 0.0))
			b.set_y(s["y"] + p.get("ty", 0.0))
	sk.update_world_transform(0)

# ---------------------------------------------------------------- IK
# 只靠「位置」解算，不依赖任何世界角 getter：
# 基线姿势下量出 L1/L2 与两段的基准方向，再用余弦定理求两解，取落点更准的那个。
func _chain_pos(chain: Array) -> Array:
	var out := []
	for n in chain:
		out.append(skel.find_bone(n).local_to_world(Vector2.ZERO))
	return out

func _base_pose(chain: Array) -> Dictionary:
	var p := _eval(cur_t).duplicate(true)
	for n in chain:
		if p.has(n): p[n].erase("rot")
	return p

# local_to_world 返回的是 y 翻转的坐标（肩在 y=-1174，骨架里是 +117）。
# 角度必须换算回 Spine 空间再当局部旋转用，否则整条手臂会朝镜像方向转。
func _sp(p: Vector2) -> Vector2:
	return Vector2(p.x, -p.y)

func solve_ik(chain: Array, target: Vector2) -> Dictionary:
	var base := _base_pose(chain)
	_apply(base)
	var pts := _chain_pos(chain)
	var sh: Vector2 = _sp(pts[0]); var mid: Vector2 = _sp(pts[1]); var tip: Vector2 = _sp(pts[2])
	target = _sp(target)
	var L1 := sh.distance_to(mid)
	var L2 := mid.distance_to(tip)
	if L1 < 0.001 or L2 < 0.001: return {}
	var base_root := (mid - sh).angle()
	var base_mid := (tip - mid).angle()
	var v := target - sh
	var dist: float = clampf(v.length(), absf(L1 - L2) + 0.0005, L1 + L2 - 0.0005)
	var ang := v.angle()
	var ca: float = clampf((L1 * L1 + dist * dist - L2 * L2) / (2.0 * L1 * dist), -1.0, 1.0)
	var a: float = acos(ca)
	var best := {}
	var best_err := 1e20
	for sgn in [1.0, -1.0]:
		var dir_root: float = ang + sgn * a
		var d_root := rad_to_deg(dir_root - base_root)
		var midp: Vector2 = sh + Vector2(L1, 0).rotated(dir_root)
		var d_mid := rad_to_deg((target - midp).angle() - base_mid) - d_root
		var res := {chain[0]: {"rot": d_root}, chain[1]: {"rot": d_mid}}
		var bp := base.duplicate(true)
		for k in res: bp[k] = res[k]
		_apply(bp)
		var got: Vector2 = _sp(skel.find_bone(chain[2]).local_to_world(Vector2.ZERO))
		var err := got.distance_to(target)
		if err < best_err: best_err = err; best = res
	_apply(_eval(cur_t))
	return best

# ---------------------------------------------------------------- 交互
func _to_screen(world: Vector2) -> Vector2:
	return pan + world * zoom

func _pick(pos: Vector2) -> String:
	var best := ""
	var bd := PICK_R
	var bs := skel.get_bones()
	for i in bs.size():
		var b: SpineBone = bs[i]
		var n: String = b.get_data().get_bone_name()
		var w: Vector2 = b.local_to_world(Vector2.ZERO)
		var d := _to_screen(w).distance_to(pos)
		if d < bd:
			bd = d; best = n
	return best

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP and e.pressed: zoom *= 1.12; _refresh()
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN and e.pressed: zoom /= 1.12; _refresh()
		elif e.button_index == MOUSE_BUTTON_LEFT:
			if e.pressed:
				sel = _pick(e.position)
				if sel != "":
					dragging = true
					ik_mode = IK_CHAINS.has(sel)
					# Hips（或按住 Shift）走平移：世界坐标换算成骨架单位，y 轴要翻转
					trans_mode = (sel == "Hips" or Input.is_key_pressed(KEY_SHIFT)) and not ik_mode
					drag_last = e.position
					var cur: Dictionary = _eval(cur_t).get(sel, {})
					drag_base = {"tx": cur.get("tx", 0.0), "ty": cur.get("ty", 0.0)}
					var b := skel.find_bone(sel)
					drag_start_angle = _to_screen(b.local_to_world(Vector2.ZERO)).angle_to_point(e.position)
					drag_bone_angle = b.get_rotation()
				_refresh()
			else:
				dragging = false
				ik_mode = false
				trans_mode = false
				_refresh()
		elif e.button_index == MOUSE_BUTTON_RIGHT and e.pressed:
			pass
	elif e is InputEventMouseMotion:
		if dragging and sel != "" and trans_mode:
			var wd: Vector2 = (e.position - drag_last)
			var ux := wd.x / zoom / root_scale
			var uy := -wd.y / zoom / root_scale          # 世界 y 与骨架 y 反向
			_upsert_key(cur_t, sel, "tx", drag_base["tx"] + ux)
			_upsert_key(cur_t, sel, "ty", drag_base["ty"] + uy)
			_refresh()
			info.text = "平移 %s  →  tx %.1f  ty %.1f（骨架单位）" % [sel, drag_base["tx"] + ux, drag_base["ty"] + uy]
		elif dragging and sel != "" and ik_mode:
			var world_t: Vector2 = (e.position - pan) / zoom
			var res := solve_ik(IK_CHAINS[sel], world_t)
			for k in res:
				_upsert_key(cur_t, k, "rot", res[k]["rot"])
			_apply(_eval(cur_t))
			var got: Vector2 = skel.find_bone(sel).local_to_world(Vector2.ZERO)
			info.text = "IK 拖 %s  →  落点 %s（目标 %s）  误差 %.1f" % [sel, got, world_t, got.distance_to(world_t)]
		elif dragging and sel != "":
			var b := skel.find_bone(sel)
			if b == null: return
			var cur := _to_screen(b.local_to_world(Vector2.ZERO)).angle_to_point(e.position)
			var delta := rad_to_deg(cur - drag_start_angle)
			# 写进当前时间点的关键帧（没有就在该时间创建一帧）
			_upsert_key(cur_t, sel, "rot", drag_bone_angle + delta)
			_apply(_eval(cur_t))
			info.text = "拖动 %s  →  %.1f°" % [sel, drag_bone_angle + delta]
		elif Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
			pan += e.relative; _refresh()

func _upsert_key(t: float, bone: String, field: String, value: float) -> void:
	var arr: Array = keys[cur_anim]
	for k in arr:
		if abs(k["t"] - t) < 0.0005:
			k["pose"][bone] = k["pose"].get(bone, {})
			k["pose"][bone][field] = value
			return
	arr.append({"t": t, "pose": {bone: {field: value}}})
	keys[cur_anim] = arr

func _set_key() -> void:
	# 把「当前时间点的完整姿势」存成一帧：先取已有求值结果，再覆盖选中骨骼
	var pose := _eval(cur_t)
	_upsert_full(cur_t, pose)

func _upsert_full(t: float, pose: Dictionary) -> void:
	var arr: Array = keys[cur_anim]
	for k in arr:
		if abs(k["t"] - t) < 0.0005:
			k["pose"] = pose
			return
	arr.append({"t": t, "pose": pose})
	keys[cur_anim] = arr
	_refresh()

func _del_key() -> void:
	var arr: Array = keys[cur_anim]
	for i in arr.size():
		if abs(arr[i]["t"] - cur_t) < 0.02:
			arr.remove_at(i); break
	keys[cur_anim] = arr
	_refresh()

func _export() -> void:
	var out := {"fps": 60, "animations": {}}
	for a in keys:
		var arr: Array = keys[a].duplicate()
		arr.sort_custom(func(p, q): return p["t"] < q["t"])
		out["animations"][a] = {"dur": _anim_dur(), "keys": arr}
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify(out, "  "))
	f.close()
	var abs_path := ProjectSettings.globalize_path(OUT)
	print("[姿势编辑器] 已导出 -> ", abs_path)
	info.text = "已导出 -> " + abs_path

func _process(dt: float) -> void:
	if playing:
		cur_t += dt
		if cur_t > _anim_dur(): cur_t = 0.0
		slider.set_value_no_signal(cur_t)
	# 姿势已经烘进临时骨架并由 _live 动画播放，这里只需维持视图变换
	sprite.position = pan
	sprite.scale = Vector2(zoom, zoom)
	slider.max_value = _anim_dur()
