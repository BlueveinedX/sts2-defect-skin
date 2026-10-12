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
	var H = s.find_bone("Hips")
	s.set_to_setup_pose(); s.update_world_transform(0)
	print("setup     Hips.local = (%.2f, %.2f)" % [H.get_x(), H.get_y()])
	for anim in ["probe", "idle_loop"]:
		st.set_animation(anim, true, 0); st.update(0); st.apply(s); s.update_world_transform(0)
		print("%-10s Hips.local = (%.2f, %.2f)" % [anim, H.get_x(), H.get_y()])
	quit()
