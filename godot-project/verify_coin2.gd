extends SceneTree
func _init():
	var a = OS.get_cmdline_user_args()
	var skel = SpineSkeletonFileResource.new(); skel.load_from_file(a[0])
	var atlas = SpineAtlasResource.new(); atlas.load_from_atlas_file(a[1])
	var data = SpineSkeletonDataResource.new()
	data.skeleton_file_res = skel; data.atlas_res = atlas
	var sprite = SpineSprite.new(); sprite.skeleton_data_res = data
	get_root().add_child(sprite)
	var s = sprite.get_skeleton(); var st = sprite.get_animation_state()
	var sh = s.find_bone("shine")
	s.set_to_setup_pose(); s.update_world_transform(0)
	print("setup           shine.local.x = %.2f   (官方 setup x=243.14)" % sh.get_x())
	for t in [0.0, 0.6667, 1.3333]:
		st.set_animation("animation", true, 0); st.update(t); st.apply(s); s.update_world_transform(0)
		print("animation@%-7s shine.local.x = %.2f   (时间轴值 -473.39 -> 绝对? 加性?)" % [t, sh.get_x()])
	quit()
