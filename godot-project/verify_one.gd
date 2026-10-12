extends SceneTree
func _init():
	var a = OS.get_cmdline_user_args()
	if a.size() < 2:
		print("用法: --script verify_one.gd -- <skeleton> <atlas>"); quit(2); return
	var skel = SpineSkeletonFileResource.new()
	skel.load_from_file(a[0])
	var atlas = SpineAtlasResource.new()
	atlas.load_from_atlas_file(a[1])
	var data = SpineSkeletonDataResource.new()
	data.skeleton_file_res = skel
	data.atlas_res = atlas
	var sprite = SpineSprite.new()
	sprite.skeleton_data_res = data
	get_root().add_child(sprite)
	var s = sprite.get_skeleton()
	if s == null:
		print("❌ 骨架构建失败（skeleton == null）"); quit(1); return
	print("  骨骼=", s.get_bones().size(), " 插槽=", s.get_slots().size())
	var d = s.get_data()
	var names = []
	for i in d.get_animations().size(): names.append(d.get_animations()[i].get_name())
	print("  动画(", names.size(), ")=", names)
	print("✅ 全部成功")
	quit()
