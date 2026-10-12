extends SceneTree
func _initialize(): _run()
func _run():
	for i in 3: await process_frame
	var pck := OS.get_cmdline_user_args()[0]
	var ok = ProjectSettings.load_resource_pack(pck, false)
	print("load_resource_pack = ", ok)
	var rigs=["characters/defect/defect_skel_data","merchant/defect/defect_merchant_skel_data",
		"rest_site/defect/rest_site_defect_skel_data","character_select/defect/characterselect_defect_skel_data"]
	var imgs=["images/packed/character_select/char_select_defect.png",
		"images/ui/top_panel/character_icon_defect.png"]
	for r in rigs:
		var res = load("res://animations/%s.tres" % r)
		if res == null: print("  ❌ ", r); continue
		var sp = SpineSprite.new(); sp.skeleton_data_res = res; get_root().add_child(sp)
		var s = sp.get_skeleton()
		print("  ✅ %-44s 骨骼=%s 动画=%s" % [r.get_file(), (str(s.get_bones().size()) if s else "null"), (str(s.get_data().get_animations().size()) if s else "-")])
	for p in imgs:
		var t = load("res://%s" % p)
		print("  %s 贴图 %s" % ["✅" if t != null else "❌", p.get_file()])
	quit()
