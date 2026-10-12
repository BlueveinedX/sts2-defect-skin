extends SceneTree
func _initialize(): _run()
func _run():
	for i in 3: await process_frame
	var pck := OS.get_cmdline_user_args()[0]
	print("load_resource_pack = ", ProjectSettings.load_resource_pack(pck, false))
	var need := ["idle_loop","relaxed_loop","low_health_loop","process","attack","cast","hurt","die"]
	var rigs := ["characters/defect/defect_skel_data","merchant/defect/defect_merchant_skel_data",
		"rest_site/defect/rest_site_defect_skel_data","character_select/defect/characterselect_defect_skel_data"]
	var ok := true
	for r in rigs:
		var res = load("res://animations/%s.tres" % r)
		if res == null: print("  ❌ ", r); ok = false; continue
		var sp = SpineSprite.new(); sp.skeleton_data_res = res; get_root().add_child(sp)
		var s = sp.get_skeleton()
		if s == null: print("  ❌ 骨架构建失败 ", r); ok = false; continue
		var d = s.get_data(); var names := []
		for i in d.get_animations().size(): names.append(d.get_animations()[i].get_name())
		var miss := []
		for w in need:
			if not names.has(w): miss.append(w)
		var wa := 0; s.set_to_setup_pose(); s.update_world_transform(0)
		for i in s.get_slots().size():
			if s.get_slots()[i].get_attachment(): wa += 1
		var fx := 0
		for f in ["glowie1","blender_blur","binder_bolt","blip_star","flare","deathspark"]:
			if s.find_slot(f) != null: fx += 1
		# 逐个动画 apply
		var st = sp.get_animation_state(); var errs := 0
		for w in need:
			st.clear_tracks(); st.set_animation(w, false, 0); st.update(0.05); st.apply(s); s.update_world_transform(0)
			if s.find_bone("Hips") == null: errs += 1
		print("  %s %-38s 骨骼=%d 插槽=%d(附件%d) 动画=%d 特效部件=%d/6 apply错误=%d %s"
			% ["✅" if miss.is_empty() and wa > 0 else "❌", r.get_file(), s.get_bones().size(),
			   s.get_slots().size(), wa, names.size(), fx, errs,
			   ("缺:" + str(miss)) if not miss.is_empty() else ""])
		if not miss.is_empty() or wa == 0: ok = false
	var ui := ["images/packed/character_select/char_select_defect.png",
		"images/packed/character_select/char_select_defect_locked.png",
		"images/ui/top_panel/character_icon_defect.png",
		"images/ui/top_panel/character_icon_defect_outline.png"]
	for p in ui:
		var t = load("res://%s" % p)
		print("  %s UI贴图 %-46s %s" % ["✅" if t != null else "❌", p.get_file(), (str(t.get_size()) if t else "")])
		if t == null: ok = false
	print("=== 最终结论: ", ("全部通过" if ok else "有问题"), " ===")
	quit(0 if ok else 1)
