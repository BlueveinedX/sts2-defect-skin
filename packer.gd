extends SceneTree
# 用 Godot 自带的 PCKPacker 打包，保证与游戏读取器 100% 兼容
# 用法: --script packer.gd -- <清单json> <输出pck>
func _initialize(): _run()
func _run():
	var a = OS.get_cmdline_user_args()
	if a.size() < 2:
		print("用法: -- <manifest.json> <out.pck>"); quit(2); return
	var data = JSON.parse_string(FileAccess.get_file_as_string(a[0]))
	if data == null:
		print("❌ 清单解析失败: ", a[0]); quit(1); return
	var files: Array = data["files"]
	var pk := PCKPacker.new()
	var err = pk.pck_start(a[1], 32)
	if err != OK:
		print("❌ pck_start 失败: ", err); quit(1); return
	for f in files:
		err = pk.add_file(f["target"], f["source"])
		if err != OK:
			print("❌ add_file 失败: ", f["target"], " err=", err); quit(1); return
	err = pk.flush(true)
	if err != OK:
		print("❌ flush 失败: ", err); quit(1); return
	print("✅ Godot PCKPacker 打包完成: ", a[1], "  文件数=", files.size())
	quit()
