# 本机同玩

启动：在项目目录运行 `python3 tools/live_server.py`，打开 http://127.0.0.1:8766/ 。服务只在本机监听，不使用外部模型账号或密钥。不要同时开启多个游戏页。

玩家在小队面板预留 EXTERNAL AGENT 席位、勾选允许，再由助手通过 `live_call.py` 调用 nr_join。助手保存返回身份到 `tools/.companion-session.json`（权限600，不加入版本管理）。点击部署开始；玩家操作主角，助手控制队友。

当前会话已完成加入与现场演示，身份已保存在本机。继续操作：

- `python3 tools/companion.py observe` 获取当前有限战场信息并续约；这一步把观察上下文存于本机。
- 模型读取观察并决定战术；然后 `python3 tools/companion.py command` 从stdin读取例如 `{"tactic":"guard","stance":"defensive","duration":20,"autoSkills":true}`。
- 过时或跨局命令会被拒绝，需重新观察/思考。不要自动无限重放旧命令。
- `python3 tools/companion.py heartbeat` 只续约，不修改战术。

工具循环不会自动启动模型，也不会自动操作主角或继续暂停的游戏。切出游戏会暂停，开始协作后保持游戏前台即可。刷新页面需重新授权/加入；重启server更换连接凭证且需刷新页面。关闭服务即停止工具桥。

试玩与延迟证据：`evidence/live-coop/REPORT.md`。

## 誓约远征首版补充（2026-09-23）

主角可在工坊选择“外部 AI”，然后使用 `nr_join` 的 `slot:0`，返回 `agentId:leader`。三个队友仍是 `slot:1..3`。主角的观测实体在 AI 控制期间为 `leader`，人工接管后为 `human`；接管立即撤销旧 token。新增 `objective` 与 `retreat` 战术，观测包含任务位置、进度、完整度、首领破绽、芯片与圣物状态。

路线选择和营地阶段不运行战斗，工具会拒绝战斗命令；外部 Agent 续心跳后等待用户继续即可。可用 `NR_PORT=8767 python3 tools/live_server.py` 选择其他本机端口，生成的私有连接文件仍由本机工具使用。不要同时混用不同服务的凭证。
