# 角色工具包（tools/kit）

尼克斯的构建方法泛化而来。每个角色是 `tools/chars/<id>.py` 里的一份“配方”，由 `tools/build_char.py` 在 Blender 5.2 里构建。参考配方：`tools/chars/aurelian.py`（人形英雄，完整示范）、`tools/chars/_probe.py`（刚性挂骨杂兵结构）。

## 构建命令

```sh
# 只建几何 + 审图（不绑骨，几秒钟，适合快速迭代造型）
blender -b --python tools/build_char.py -- <id> --geo
# 完整构建 + 审图（不导出）
CHAR_POSES="Move:5,Cast:14" blender -b --python tools/build_char.py -- <id> --review --no-export
# 完整构建 + 导出两份 GLB
blender -b --python tools/build_char.py -- <id>
```

审图环境变量：`CHAR_VIEWS`（front,three-quarter,side,rear,detail,top,game）、`CHAR_SAMPLES`（默认 32）、`CHAR_SIZE`（默认 720）、`CHAR_POSES`（`动作:帧` 列表）、`CHAR_POSE_VIEWS`。审图输出在 `art/review/chars/<id>/`，用 Read 工具直接看 PNG。

产物：`visual-lab/assets/chars/<id>.glb`（展示版）、`<id>-game.glb`（游戏版，按 `GAME_TRIS` 自动减面、贴图减半、去掉 `ctx.hidden`）、`art/chars/<id>/<id>.blend`、`art/chars/<id>/textures/`。

## 配方接口

```python
TITLE = "Aurelian"                 # 材质 / 对象名前缀
ACCENT = (0.49, 0.93, 0.88)        # 主题色（审图轮廓光、网页光晕）
CLIPS = ("Idle", "Move", "Cast", "Channel")
GAME_TRIS = 62000                  # 游戏版三角面预算
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core")   # 这些材质名的网格不参与减面（细管会塌）
REVIEW_POSE = ("Idle", 1)
def build(ctx) -> dict             # 建材质与几何，返回给 skeleton/animate 用的状态
def skeleton(rig, st)              # 建骨；rig.done() 由驱动调用
def animate(rig, st)               # 写动作
```

## 坐标与命名约定

- Blender Z 向上，角色**正面朝 +Y**，单位米。导出后网页端正面为 -Z，与尼克斯一致。
- 左右：`side=-1, label="L"`（-X），`side=+1, label="R"`（+X）。角度 a=0 正前方，a 增大转向 +X，a=π 正后方。
- 标准人形骨名：`Root, Hover, Pelvis, Spine, Chest, Neck, Head, UpperArm.L/R, Forearm.L/R, Hand.L/R, Thumb/Index/Middle/Ring/Pinky.L/R, Thigh.L/R, Shin.L/R, Foot.L/R, Toe.L/R`（`kit.humanoid.add_skeleton`）。
- 布料链：`{prefix}{k}.{j}`。
- 网页端要按名字驱动的节点：`{ID}_SPIN`（或配方里单独说明，如 `AURELIAN_AEGIS`）用 `ctx.attach(obj, bone, keep=True)` 保留名字。展示页环绕武器 `{ID}_BLADE` 放进 `ctx.hidden`（只进展示版）。

## 模块速查

`kit.core`
- `Ctx`：`ctx.mat(key, suffix, base, metal=, rough=, emit=, strength=, coat=, sheen=, sheen_tint=, spec=)`、`ctx.texture(key, (base, emission, normal), emit_strength=, normal_strength=)`、`ctx.part(obj, 规格)`、`ctx.attach(obj, 骨, keep=False)`、`ctx.hidden`。
- 蒙皮规格：`rigid("Chest")`、`rigid(("Chest", .4), ("UpperArm.L", .6))`、`chain([骨...], 父骨, 窗口)`、`invdist([骨...])`、`bands([(z, 骨), ...])`、`garment(布料)`、`fn(lambda p: {骨: 权重})`。
- 网格：`surface(name, f(u,v), nu, nv, mats, closed_u, uvfn)`、`tube(name, 点列, 半径列, mats, n, fx, fy, up, closed, cap, per, twist)`、`ellipsoid`、`lathe(name, [(r,z)...], mats)`、`loft(name, 截面列表, mats)`、`plate(name, 二维轮廓, 厚度, mats, origin, xaxis, yaxis, bulge, bev)`（刃片 / 羽片 / 甲片）、`spike(name, 底, 尖, 半径, mats, sides, bend)`、`mirror_copy`、`join(objs, name, location)`、`projector(obj, 方向)`（把点投射到曲面上）、`trim(name, 点列, 半径, 材质, closed)`、`edge_trim`、`gem`、`ring_points`、`orient(obj, 内部参考点函数)`、`finish(obj, 厚度, offset, 细分, 倒角)`、`auto_smooth`。
- 贴图（numpy，返回 base/emission/normal）：`circuit_maps(发光色, base_rgb)`（尼克斯同款电路）、`filigree_maps`（金属雕花，建议 density≥20、width=1、低对比）、`crack_maps`（熔岩裂纹）、`scale_maps`（鳞片）、`frost_maps`（霜花）、`rune_maps`（符文带）、`hex_maps`（六边形能量网格）、`voronoi`。

`kit.garment`
- `Wrap(prefix, 父骨, a0, a1, top, bottom, r_top, r_bot, K, joints, cy, flow, folds, tails, tail_len, curl)`：环绕式布料（长袍 a0≈0.4→2π-0.4、披风 π±1.5）。`.build(ctx, [外, 内衬], name, hem=(材质, 半径), edges=(...))`。
- `Panel(prefix, 父骨, top, tip, 宽度表, 离轴深度表, side=±1)`：前后垂饰 / 腰布。
- 长布料用 5 节骨（`joints=(0,.16,.34,.52,.74,1)`）更平滑。骨在 `skeleton()` 里用 `rig.add_garment(g)` 建。

`kit.humanoid`
- `Body(height=2.0, shoulder, bulk, chest, waist, hips, limb, hover, arm_out, female, stance)`：比例关键点（`B.z(k)`、`B.arms[label]`、`B.legs[label]`、`B.torso_point(a, z, grow)`、`B.on_torso(x, z, grow, back)`）。
- `add_skeleton(rig, B, fingers=True, legs=True)`。
- 部件：`suit_torso / suit_arm / suit_leg / hand / shell / pauldron / limb_plate / rerebrace / vambrace / cuisse / poleyn / greave / sabaton / gorget / torso_inlay`。签名见源码注释；所有部件自动登记蒙皮规格。

`kit.rig.Rig`
- 建骨：`bone(name, head, tail, parent, roll)`、`chain(prefix, 点列, parent)`、`add_garment(g)`；`rig.translate[骨] = "_key"` 声明位移通道（`pose["_key"]` 为 float 表示 Z 位移，或 Vector）。
- 姿态：`pose[骨] = R((轴, 角), ...)`（静止骨架轴下的局部旋转，子骨累加父骨）。`rig.aim(pose, 骨, 世界方向)` 让骨指向某方向（父骨要先写好）；`rig.ik2(pose, 上骨, 下骨, 目标, 膝朝向, end=脚骨, end_dir=)`；`rig.head/tail(pose, 骨)` 求姿态下位置。
- 布料：`rig.garment_pose(pose, g, flare(k,j), side(k,j))`（径向外掀，适合悬浮 / 漂浮角色）、`rig.wind(pose, g, back(k,j), flare, side)`（统一向后飘，**奔跑角色的披风必须用它**）。
- 动作：`rig.loop(name, 帧数, f(t), step)`（t∈[0,2π)）、`rig.keyed(name, [(帧, 姿态), ...])`、`rig.sampled(name, 帧数, f(s))`。

`kit.motion`
- `gait(rig, B, t, stride, lift, stance, bob, lean, twist, arm, elbow, arm_in, width, sink ...)`：IK 跑 / 走 / 重步；`idle(...)`；`skate(...)`；`dangle(B, t, pose)`（悬浮垂腿）；`Legs(rig, B).plant(pose, label, 脚踝目标, pitch, yaw, knee_out)`；`blend(a, b, t)`；`fingers(pose, B, label, curl)`。

## 动作约定（游戏桥接依赖）

- 英雄：`Idle`（循环）、`Move`（循环）、`Cast`（技能，关键帧 1/8/14/20/32，≈1.33 s）、`Channel`（终结技，关键帧 1/13/28/42，**13–28 帧为保持段**，游戏里会停在 1.1 s 处直到终结技快结束）。
- Boss：`Idle`、`Move`（循环）、`Attack`（24–36 帧）、`Enrage`（约 48 帧，半血狂暴时播一次）。
- 杂兵 / 精英：`Move`（循环，16–24 帧）、`Attack`（12–24 帧）。**只用 `ctx.attach` 刚性挂骨，不要蒙皮**（游戏里按部件矩阵实例化上百只）。

## 质量清单（以尼克斯为标准）

1. 剪影一眼可辨：俯视战斗视角下也能认出（头部 / 肩部 / 背部的标志件）。
2. 三层材质：主体（金属 / 漆甲 / 织物）+ 滚边（贵金属细管）+ 自发光（光缝、嵌线、下摆、宝石），发光只占小面积。
3. 细节密度均匀：大面有程序化贴图（电路 / 雕花 / 裂纹 / 鳞片），边缘有滚边，关节有收口。
4. 动作无穿插、无翻转：看 `MOTION CHECK` 与动作帧审图；布料末端最大偏转一般 < 60°。
5. 游戏版三角面在预算内，展示版不超过约 30 万面、GLB 不超过约 12 MB。
