# NEON RELIQUARY v3 — Oath Network

中世纪 × 赛博朋克 / 原生 WebGL2 / 英中双语 / 一名玩家与最多三位 AI 队友。

本版以 Neon Reliquary v2 为基础修改，保留自动攻击、定向破阵、闪避、终极技，以及征途、无尽、八首领挑战。原始上传文件和 v2 未覆盖。单文件游戏、模型和合成声音均不依赖外部 CDN。

## 直接开始

用桌面浏览器打开 `Neon_Reliquary_v3.html`。点 `ENTER THE CITADEL` → `FORM YOUR PARTY` → `FILL WITH LOCAL BOTS` → `RETURN` → `DEPLOY KNIGHT`，即可体验玩家与三位规则机器人同场战斗。席位可独立关闭或改为外部 Agent。本地机器人不是大语言模型，游戏也没有内置模型账号、API key 或推理服务。

右上角 `EN / ZH` 热切换界面；英文模式没有预置中文视觉文字，中国风人物、背景和技能图标不再使用。外部 Agent 自己取的名字作为用户内容显示，不会强制翻译。手机建议横屏；竖屏会提示旋转。

键位：WASD / 方向键移动；按住鼠标瞄准；Space 闪避；E 战技；R 终极技；1/2/3 升级；P 小队；Esc 暂停；M 声音；F 全屏。触屏为左摇杆与右下技能按钮。

在战斗中打开小队面板会暂停。关闭面板后仍需玩家点击继续，不会自动恢复。切到其他窗口或标签时也可能进入暂停，接入 Agent 时保持游戏可见并运行。

## 角色和 BOSS

六名玩家角色有分层胸甲、关节、面罩、发光目镜、肩甲、护手、披风褶皱与职业装备。八位 BOSS 不再共用一个骑士换色模型：

| 名称 | 真实三维形态 |
|---|---|
| The Cinder King | 熔炉胸腔、七尖王冠、王袍、处刑巨刃 |
| Pale Wyrm | 长颈龙、四足、膜翼、脊尾和有颌骨的头部 |
| Iron Behemoth | 重甲四足攻城兽、背甲、撞角、液压支腿 |
| Hollow Marshal | 骷髅统帅、空洞肋骨、冠冕、军旗、长戟 |
| Deus Machina | 六足机械底盘、同心反应堆、双炮、机械光环 |
| Null Oracle | 兜帽无脸身形、虚空核心、神龛、悬浮圣物 |
| Venom Trinity | 三头曲颈毒兽、毒腺、承重躯体 |
| Ash Seraph | 三对机械羽翼、羽刃、骨面和仪式权杖 |

首页 `ARCHIVE` 点击首领卡片，进入实时模型图鉴，拖动旋转或滚轮缩放。这些与战斗中使用的模型相同，不是替代模型的平面立绘。美术是风格化几何模型，不是写实扫描或影视级角色资产。性能不足可在设置中选 Performance；WebGL2 不可用时，Canvas 2D 兼容路径保留游戏功能，但不具备三维材质效果。

## 真正独立的协作角色

玩家始终控制自己的角色；AI 只控制自己的一个队友。最多 1 人 + 3 队友，总计 4 个角色；规则机器人和外部 Agent 共同占用这三个席位。

每个队友具有独立位置、生命、护盾、伤害、弹丸归属、技能冷却、终极技和升级偏好。敌人可以追踪和伤害任意存活队员。经验和关卡进度共享，升级偏好分别应用；队友不会抢走玩家的升级选择。

任意队员倒地后，附近盟友停留约 2.4 秒可救起；牧师施救更快。救起恢复 40% 生命并短暂无敌。全队倒地才失败；独行时仍是玩家倒地即失败。牧师战技可以治疗附近队友。当前未设倒地流血死亡倒计时。

## 难度增加，不是简单堆秒杀伤害

下表是相对于同一手动难度档的额外倍率。本地机器人与外部 Agent 一视同仁。

| 队友数 | 小怪生命 | BOSS 生命 | 敌军生成数量 | 敌方伤害 | BOSS 攻击频率 |
|---:|---:|---:|---:|---:|---:|
| 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1 | 1.30 | 1.65 | 1.18 | 1.05 | 1.04 |
| 2 | 1.60 | 2.30 | 1.36 | 1.10 | 1.08 |
| 3 | 1.90 | 2.95 | 1.54 | 1.15 | 1.12 |

倍率在每波开始按已部署人数锁定。中途加入排队到下一波；退队、倒地或心跳过期不会降低当前波的倍率。下一波再按实际席位重算。数量有取整与对象池上限，故每一波实际数量不保证严格等于 1.54 倍。

参数位于 `src/coop.js` 的 `coopScale()`。这是可调的初版平衡参数，已做逻辑回归，尚未通过长时间真实玩家与大模型组队的难度调优。

## 接入自己的 AI Agent

完整说明在 `WEBMCP_INTEGRATION.md`。先由玩家在小队面板预留 `EXTERNAL AGENT` 席位、指定职业，并勾选允许外部 Agent，然后由 Agent 调用 `nr_join` 入队。

已实现七个结构化工具：`nr_roster`、`nr_observe`、`nr_join`、`nr_command`、`nr_heartbeat`、`nr_leave`、`nr_events`。注册接口优先当前 `document.modelContext`，再检测旧 `navigator.modelContext`。不支持原生 WebMCP 时保留 `window.NRCoop.call(name,args)` 和 `listTools()`，便于你的宿主桥接。

这是**游戏页内协作**，不是远程多人房间服务器。普通聊天窗口不会因为下载此文件就自动拥有游戏工具；外部 Agent 的浏览器宿主仍须能发现或桥接它们。游戏不负责创建大模型、连接你的账号、保存 API key 或管理模型计费。

工具采用“低频战术指令 + 本地逐帧执行”，不要求模型每帧按键。每名 Agent 建议每 1–2 秒观察一次，下达跟随、护卫、突击、集火、救援、驻守或移动；引擎负责走位、判定和正常冷却。失去心跳约 90 秒后回退到本地防御护卫，角色仍在队伍里。

## 源码结构与构建

```
Neon_Reliquary_v3.html    可直接运行的单文件
build.py                仅使用 Python 标准库重新构建
src/core.js             战斗、对象池、波次；显式角色归属
src/coop.js             三席位、协作、权限、难度、工具注册
src/models.js           六角色与八 BOSS 的程序化三维模型
src/renderer.js         WebGL2/阴影/辉光/动画/Canvas 兼容
src/inspector.js        交互式 BOSS 模型图鉴
src/runtime.js          生命周期、输入、双语和测试入口
src/i18n.js              双语文案
src/audio.js             本地合成声音
src/style.css            桌面/触屏样式
src/shell.html           HTML 模板
examples/               控制客户端与明确标注的规则策略示例
```

重新构建：`python build.py`。Python 3.10+ 即可，游玩不需要 Python。外部 WebMCP 接入建议部署到 HTTPS 或本地开发服务器后，在目标宿主环境验证；单人和本地机器人模式可直接打开 HTML。

## 测试与边界

`tests/test_results.json` 记录 26 项核心测试全部通过。覆盖 3 席位并发、第四席位拒绝、独立弹丸、授权、过期命令、冷却、租约、退队、波次锁定、共享升级、倒地救援、全队失败、三模式推进、六职业、八 BOSS 狂暴、双语、Canvas 和现代 WebMCP 注册契约。

`tests/ui_results.json` 另记录6项桌面/触屏 UI 验证，全部通过；`tests/client_results.json` 记录4项示例客户端模拟传输测试。截图在 `previews/`，来源为交付 HTML 的真实 WebGL2 渲染。测试使用 Chromium + Xvfb + SwiftShader 软件图形；浏览器内容通过 set_content 加载。当前环境禁止 URL 导航，未修改该策略，未把本地 file:// 导航或线上部署冒充为已验证。

运行回归需 Chromium、Xvfb 和 requirements.txt 中的 Playwright。无 DISPLAY 时：`env -u DISPLAY python tests/test_v3.py`；UI：`python tests/test_ui.py`。测试仅在内存副本开启测试入口并手动推进模拟，不修改交付 HTML。首领连胜/结算用强制击杀验证流程；1442 敌人测试验证对象池稳定性，都不是实战通关能力或真实设备帧率基准。

原生 WebMCP 注册与执行契约通过模拟接口验证；没有运行真实外部 LLM、跨设备连接、浏览器 Agent 权限弹窗链路或 Safari/iPhone 实机验收。浏览器原生支持仍需目标环境确认。

## English quick start

Open the standalone HTML, choose **Form your party**, fill with **Local bots**, return and deploy. You remain in control of the human; up to three companions have separate health, attacks and abilities. Bots are explicitly rule-based, not LLMs. Reserve **External Agent** seats and enable access to connect a real agent through the documented tools. Native WebMCP is feature-detected; a local JavaScript bridge remains available. The package does not include a model service, API keys or a multiplayer network server. Source, reproducible tests and integration examples are included.
