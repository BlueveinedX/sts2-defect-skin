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
	var d = s.get_data()
	var names := []
	for i in d.get_animations().size(): names.append(d.get_animations()[i].get_name())
	print("骨骼=", s.get_bones().size(), " 插槽=", s.get_slots().size(), " 动画=", d.get_animations().size())
	s.set_to_setup_pose(); s.update_world_transform(0)
	var withatt := 0
	for i in s.get_slots().size():
		if s.get_slots()[i].get_attachment(): withatt += 1
	print("有附件的插槽: ", withatt, " / ", s.get_slots().size())
	var fxs := ["glowie1","glowie2","blender_blur","blender_whisp_1","binder_bolt","blip_star","flare","deathspark"]
	var ok := 0
	for f in fxs:
		var sl = s.find_slot(f)
		if sl == null: print("  ❌ 缺插槽 ", f); continue
		var att = sl.get_attachment()
		print("  %-17s 附件=%-17s setup色=%s" % [f, (att.get_attachment_name() if att else "无"), sl.get_color()])
		ok += 1
	print("特效插槽齐: ", ok, "/", fxs.size())
	print("--- 关键帧上的特效 alpha ---")
	var st = sprite.get_animation_state()
	for pair in [["idle_loop",0.0],["idle_loop",3.3],["process",1.2],["cast",0.8],["attack",0.7],["die",1.75],["hurt",0.0],["low_health_loop",3.0]]:
		st.clear_tracks(); st.set_animation(pair[0], false, 0)
		st.update(pair[1]); st.apply(s); s.update_world_transform(0)
		var g = s.find_slot("glowie1").get_color()
		var bl = s.find_slot("binder_bolt").get_color()
		var fl = s.find_slot("flare").get_color()
		print("  %-16s @%.2f  glowie1.a=%.2f  binder_bolt.a=%.2f  flare.a=%.2f"
			% [pair[0], pair[1], g.a, bl.a, fl.a])
	quit()
