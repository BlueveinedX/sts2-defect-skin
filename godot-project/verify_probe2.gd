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
	var ed = s.find_slot("Eye_down"); var eu = s.find_slot("Eye_up")

	s.set_to_setup_pose(); s.update_world_transform(0)
	print("setup            Eye_down.color = ", ed.get_color(), "  (插槽定义 = ffffff00)")
	var att = eu.get_attachment()
	print("setup            Eye_up.attachment = ", (att.get_data().get_name() if att else "无"))

	for pair in [["probe_color", 0.2], ["probe_att", 0.2], ["probe_att", 0.7]]:
		st.clear_tracks(); st.set_animation(pair[0], false, 0)
		st.update(pair[1]); st.apply(s); s.update_world_transform(0)
		var at = eu.get_attachment()
		print("%-12s @%.1f  Eye_down.color = %s   Eye_up.attachment = %s"
			% [pair[0], pair[1], ed.get_color(), (at.get_data().get_name() if at else "无")])
	quit()
