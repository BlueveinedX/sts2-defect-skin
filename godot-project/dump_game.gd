extends SceneTree
func _init():
	var a = OS.get_cmdline_user_args()
	print("读取 skeleton...")
	var skel = SpineSkeletonFileResource.new(); skel.load_from_file(a[0])
	print("读取 atlas...")
	var atlas = SpineAtlasResource.new(); atlas.load_from_atlas_file(a[1])
	print("构建 data...")
	var data = SpineSkeletonDataResource.new()
	data.skeleton_file_res = skel; data.atlas_res = atlas
	print("创建 sprite...")
	var sprite = SpineSprite.new(); sprite.skeleton_data_res = data
	get_root().add_child(sprite)
	print("取 skeleton...")
	var s = sprite.get_skeleton()
	if s == null: print("❌ 构建失败"); quit(1); return
	var d = s.get_data()
	print("骨骼=", s.get_bones().size(), " 插槽=", s.get_slots().size(), " 动画=", d.get_animations().size())
	for i in d.get_animations().size():
		var an = d.get_animations()[i]
		print("   %-20s 时长 %.4f" % [an.get_name(), an.get_duration()])
	quit()
