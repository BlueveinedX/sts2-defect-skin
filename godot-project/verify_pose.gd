extends SceneTree
func _init():
	var a = OS.get_cmdline_user_args()
	var skel = SpineSkeletonFileResource.new(); skel.load_from_file(a[0])
	var atlas = SpineAtlasResource.new(); atlas.load_from_atlas_file(a[1])
	var data = SpineSkeletonDataResource.new()
	data.skeleton_file_res = skel
	data.atlas_res = atlas
	var sprite = SpineSprite.new()
	sprite.skeleton_data_res = data
	get_root().add_child(sprite)
	var s = sprite.get_skeleton()
	var st = sprite.get_animation_state()
	var Hips = s.find_bone("Hips")
	var Neck3 = s.find_bone("Neck_3")

	s.set_to_setup_pose(); s.update_world_transform(0)
	dump("setup  ", Hips, Neck3)
	for pair in [["idle_loop", 0.0], ["idle_loop", 0.5], ["hurt", 0.5]]:
		st.set_animation(pair[0], true, 0)
		st.update(pair[1]); st.apply(s); s.update_world_transform(0)
		dump("%s@%s" % [pair[0], pair[1]], Hips, Neck3)
	quit()

func dump(tag, Hips, Neck3):
	var hw = Hips.local_to_world(Vector2.ZERO)
	var nw = Neck3.local_to_world(Vector2.ZERO)
	print("%-14s Hips.local=(%7.2f,%7.2f) world=(%7.2f,%7.2f) | Neck_3 world=(%7.2f,%7.2f)"
		% [tag, Hips.get_x(), Hips.get_y(), hw.x, hw.y, nw.x, nw.y])
