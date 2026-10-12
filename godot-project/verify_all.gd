extends SceneTree
func _init():
	var a = OS.get_cmdline_user_args()
	var skel = SpineSkeletonFileResource.new(); skel.load_from_file(a[0])
	var atlas = SpineAtlasResource.new(); atlas.load_from_atlas_file(a[1])
	var data = SpineSkeletonDataResource.new()
	data.skeleton_file_res = skel; data.atlas_res = atlas
	var sprite = SpineSprite.new(); sprite.skeleton_data_res = data
	get_root().add_child(sprite)
	var s = sprite.get_skeleton()
	if s == null: print("❌ 构建失败"); quit(1); return
	var d = s.get_data(); var st = sprite.get_animation_state()
	print("骨骼=", s.get_bones().size(), " 插槽=", s.get_slots().size(), " 动画=", d.get_animations().size())
	var names := []
	for i in d.get_animations().size(): names.append(d.get_animations()[i].get_name())
	print("动画名: ", names)
	var need = ["idle_loop","relaxed_loop","low_health_loop","process","attack","cast","hurt","die"]
	for w in need:
		if not names.has(w): print("  ❌ 缺动画 ", w)
	print("--- setup pose 基准 ---")
	s.set_to_setup_pose(); s.update_world_transform(0); show(s)
	for anim in names:
		var dur = 0.0
		for i in d.get_animations().size():
			if d.get_animations()[i].get_name() == anim: dur = d.get_animations()[i].get_duration()
		st.clear_tracks(); st.set_animation(anim, false, 0)
		var third = dur / 3.0
		for k in 3:
			st.update(0.0 if k == 0 else third)
			st.apply(s); s.update_world_transform(0)
			print("--- %s @%.2f ---" % [anim, (k * third)])
			show(s)
	quit()

func show(s):
	var h = s.find_bone("Hips").local_to_world(Vector2.ZERO)
	var n = s.find_bone("Neck_3").local_to_world(Vector2.ZERO)
	var fl = s.find_bone("Leg_L_4").local_to_world(Vector2.ZERO)
	var fr = s.find_bone("Leg_R_4").local_to_world(Vector2.ZERO)
	print("    Hips(%.0f,%.0f) Neck(%.0f,%.0f) 脚L(%.0f,%.0f) 脚R(%.0f,%.0f) 身高=%.0f"
		% [h.x,h.y,n.x,n.y,fl.x,fl.y,fr.x,fr.y, (h.y-n.y)])
