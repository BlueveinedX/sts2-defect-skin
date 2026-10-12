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
	s.set_to_setup_pose(); s.update_world_transform(0)
	var slots = s.get_slots()
	print("插槽总数 ", slots.size())
	var with_att := 0
	for i in slots.size():
		var sl = slots[i]
		var at = sl.get_attachment()
		var nm = (at.get_attachment_name() if at else "❌无")
		if at: with_att += 1
		print("   %-18s bone=%-16s 附件=%s" % [
			sl.get_data().get_name(),
			sl.get_bone().get_data().get_bone_name(), nm])
	print("有附件的插槽: %d / %d" % [with_att, slots.size()])
	quit()
