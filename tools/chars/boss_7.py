"""Boss 7 · 灰烬炽天使 · 终末协议（The Ash Seraph · Terminal Protocol）——终局 Boss，全游戏最华丽（第五轮：游戏内亮度 + 合并网格 + 圣心）。

设定：堕落天使战争机器，身高约 6 m（含光环与火冠约 9 m）、翼展约 14.8 m。锻打暗钢板甲（嵌金卷草雕花 + 稀疏余烬嵌线）
+ 鎏金雕花胸板 / 背板 + 炭黑枪铁副甲 + 暗金滚边 + 小面积珊瑚色余烬自发光。标志件：
- 体量：巨人比例（胸宽 2.2 m、臂围加粗 1.95 倍、手臂放长 12%、头盔放大 1.22 倍）。巨型花瓣肩甲：六层圆顶甲环 + 两排长花瓣羽甲
  （暗钢底、金边金脊金羽枝）+ 前向日轮徽 + 五枚冲天刃羽；肩甲挂在跟随上臂一半转动的肩骨（Shoulder.L/R）上；
  三层尖底分片护喉、背后高领、圆顶护肘甲（上下关节罩 + 三叠金刃）。
- 胸前“终末圣心”（第四轮立意、第五轮改形）：刻面红宝石（九边不规则切面、左右不对称、整体微倾；玫瑰式切割，每个刻面按位置与
  朝向分到热橙 / 红橙 / 深红三档自发光，读成内部燃烧的宝石）+ 熔裂心板 + 金框镶口 + 荆棘藤 + 两侧金色羽翼环抱（贴着胸甲的鎏金羽片）
  + 金链垂饰（实现在 _b7r5_heart）。第四轮是渐变贴图的粉橙标准心形，像贴纸。
- 铠甲手（第四轮）：手背拱甲 + 四指各三节嵌金卷草甲片（纵向节缝金条、掌指护指杠与尖刺、指尖内扣尖爪）+ 顺剑柄压在指上的粗壮拇指，
  手指整圈包住剑柄；不再是一圈圈的环。
- 两对灰烬刃羽翼：主翼四节金属翼骨（枪铁翼臂 + 暗钢前缘护刃 + 暗金液压杆 + 发光关节环），刃羽分层——大覆羽（炭黑、金前缘）/
  中覆羽与小覆羽（金边金脊暗钢羽甲、鎏金甲鳞）/ 次级飞羽（内侧笔直下垂）/ 初级飞羽（翼尖扇开）/ 衬羽 / 翼背覆羽，阔羽形、金色中脊，
  羽身自灰烬黑羽根渐变到炽热橙红刃口（第四轮：翼背覆羽改灰烬黑 + 橙红刃口 + 金脊，去掉冷光下泛灰蓝的鎏金羽甲）；
  每主翼另有三枚可发射的“羽刃”（Dart 骨）与四处半透明火舌；主翼下方一对较小的次级翼（三节翼骨），与主翼同步但幅度减半。
- 头后燃烧的符文光环（BOSS_7_HALO，网页端可绕法线自转；含符文金环、十六道金色日芒、十二枚金钉、背后半透明放射光盘）+ 十三条
  半透明火舌冠（Flare 骨，缩放通道驱动燃起）。
- 双手握持的“终末之剑”（Sword 骨，挂在 Hover 下；双臂每帧两段 IK 握住剑柄）：熔裂暗钢长刃 + 双面发光血槽与符文菱宝石 +
  刃口发光线与伸出的半透明火舌、光环母题的日轮护手（金环 + 符文带 + 金芒 + 火舌）、剑格两面镶核心宝石、三叠翼形护手、四爪剑首。
- 层叠下身：三排错位分片装甲裙甲（金边铆钉宝石，挂 Tasset 骨链）叠在撕裂的灰黑长袍（左右两片，前后开衩露出余烬红内裙，
  纵向褶皱、尖角破边、余烬发光下摆）之上，六条带金边的长飘带（Ban 骨链）垂在裙外，前垂一面电路符文垂饰。
- 环绕的余烬碎片与飘落的灰羽（第四轮减半，只散落在翅膀后缘下方与下摆周围；刚性挂骨，扁平小件）。
第四轮发光层次：主发光区 = 光环 / 圣心 / 剑 / 翼缘；腰扣、翼座与翼关节宝石、裙甲 / 飘带宝石、肩甲日轮徽等次要发光件改用低强度的
glow2 材质，裙与内裙的余烬纹自发光也降低。第四轮减面（游戏版目标 ≥ 0.2，实测见构建日志）：从源头削减被长袍 / 甲遮住的部分
（紧身衣、内裙、飘带、裙甲片、羽片段数与层数）、火舌薄片的横向分段（贴图控制轮廓，2 列足够）、余烬碎片与小宝石面数，
骨骼由 215 减到 179（内裙骨链 3 节 × 8 条、长袍 5 条）。
第五轮（技术性修整，造型 / 动作 / 剪影不变）：
1. 发光从源头重分配（游戏端 glow.js 的 EMISSIVE_DAMP 因此可以删除）：发光只留四个主区——光环（火冠 + 符文圈 + 光盘）、圣心、
   终末之剑刃口（刃口细发光带 + 血槽 / 刃口发光管 + 火舌）、翼缘（飞羽 / 羽刃最外侧刃口细线，带内侧快速衰减的肩）；
   覆羽 / 衬羽 / 翼背羽、长袍、内裙、垂饰、羽甲、熔缝钢的发光贴图只留电路 / 刃口细线，强度降到 0.6；羽身的橙红由基础色渐变承担；
   次要宝石改名 gem（不再触发 glowWeight 的 glow 权重）并降到 1.0，余烬 1.0，嵌线 1.0，下摆光 1.3，火舌 / 光盘略降（_b7r5_maps）。
2. 合并网格：挂骨件（翅膀羽片、火舌、羽刃、剑、余烬碎片）全部改成刚性蒙皮，按材质合并；游戏版 207 节点 / 214 图元
   → 24 节点 / 33 图元（_b7r5_merge），BOSS_7_HALO 仍是独立节点。
3. 圣心改形（_b7r5_heart）。
与英雄塞拉芙（玫红漆甲、三对小机械翼）区分：灰烬色、两对巨翼、光环火冠、压迫性的体量。
动作：Idle（悬浮、翅膀缓慢起伏）/ Move（前倾悬浮、缓慢有力的振翅）/ Attack（32 帧：举剑蓄势 → 双翼前扫劈斩并发射羽刃）/
Enrage（48 帧：收翼蓄力 → 双翼全展、光环与翼火爆燃、举剑向天 → 末日冲锋起势 → 回到待机）。
网页端节点：BOSS_7_HALO（自转件）。私有模块：_b7_lib（第一至二轮）、_b7r3_parts（第三轮）、_b7r4_parts（第四轮：护喉 /
铠甲手 / 护肘）、_b7r5_maps / _b7r5_heart / _b7r5_merge（第五轮：细线发光贴图 / 刻面红宝石圣心 / 合并网格）、
_b7r3_shots / _b7r4_shots（审图取景）、_b7r5_shots + _b7r5_simcomp（游戏条件模拟）、_b7r5_check（合并后动画回归）、_b7r5_sheets（印样）。
"""

import math
import random

from mathutils import Matrix, Vector

from kit.core import (TAU, clamp, ellipsoid, filigree_maps, finish, frame_from, gem, interp, invdist, join, lerp,
                      orient, projector, radial, rigid, smoothstep, spike, surface, transform, tube)
from kit.garment import Panel, Wrap
from kit.humanoid import SIDES, Body, add_skeleton, rerebrace, shell, suit_arm, suit_torso, vambrace
from kit.rig import R, X, Y, Z

from chars._b2r2_parts import flame_material
from chars._b7r3_parts import (aura_disc, aura_maps, find_part, plume_maps, plume_width, fire, flame_mats, gilded_maps, inlay_maps, petal_maps, petal_surface, scale_uv,
                               shard, shell2)
from chars._b7r4_parts import couter_r4, gauntlet_r4, gorget_plates
from chars._b7r5_heart import build_sacred_heart_r5
from chars._b7r5_merge import skin_attach
from chars._b7r5_maps import blade_maps_r5, burn_cloth_maps_r5, plume_maps_r5
from chars._b7_lib import (Clearance, blob, burn_cloth_maps, burning_blade_maps, circuit_maps, ease, ease_out,
                           ember_crack_maps,
                           ember_feather_maps, feather_width, flame, flame_maps, forged_maps, loop, mat_slerp,
                           pauldron_lite, ridge_blade, rim, ring_around, sampled, seam_check, stats, sweep, track)

TITLE = "Ash Seraph"
ACCENT = (1.0, 0.60, 0.49)
CLIPS = ("Idle", "Move", "Attack", "Enrage")
# 第五轮：挂骨件改成蒙皮并按材质合并后，网格名只剩材质名；feather（羽片，扁平薄片不能减面）/ gem（小宝石）/ blade 补进保留表
GAME_TRIS = 88500
LOD_KEEP = ("inlay", "glow", "hem", "trim", "core", "flame", "feather", "gem", "blade")
REVIEW_POSE = ("Idle", 1)
EMBER = (1.0, 0.50, 0.30)
J5 = (0, 0.16, 0.34, 0.52, 0.74, 1.0)
J3 = (0, 0.30, 0.62, 1.0)                         # 内裙大部分被长袍遮住，三节骨链够用

# 握剑拳（掌心 +n 一侧握住剑柄，剑柄轴 = 拇指方向 sv）：握点相对腕部的偏移（手掌比例 HS × 身高比例 s）
HS = 1.45                                         # 铠甲手放大系数（巨人的手要撑得住大剑）
GRIP_A, GRIP_B, GRIP_R = 0.064, 0.033, 0.021
HAND_GAP = 0.22                                   # 两手中心到剑柄中心的距离（米）
P0 = math.radians(24)                             # 静止时剑尖相对竖直向下的前倾角
U0 = Vector((0.0, math.sin(P0), -math.cos(P0)))   # 静止时剑尖方向


def make_body():
    """第三轮体型：身高 6.0、肩宽 / 胸厚 / 臂围全面加粗，撑得起 14 m 翼展。"""
    B = Body(height=6.0, shoulder=0.345, bulk=1.55, chest=1.20, waist=0.95, hips=1.22, limb=1.95, hover=1.05,
             arm_out=0.44, arm_fwd=0.14, elbow_bend=0.30)
    for a in B.arms.values():          # 巨人的长臂：整条手臂放长 12%（够得着身前的剑柄，肘部还有余量弯曲）
        S, E, W = a["shoulder"], a["elbow"], a["wrist"]
        a["elbow"] = S + (E - S) * 1.12
        a["wrist"] = a["elbow"] + (W - E) * 1.12
    return B


B0 = make_body()
SWORD_GRIP = Vector((0.0, 1.02, B0.pelvis_z + 0.16))   # 静止时剑柄中心
BLADE_L, BLADE_W = 4.15, 0.70
BLADE_0 = 0.82                                    # 刃根到剑柄中心的距离

HC = Vector((0.0, -0.74, B0.head_c.z + 0.24))     # 光环中心
HALO_TILT = math.radians(6)                       # 光环顶部后仰
HN = Vector((0.0, math.cos(HALO_TILT), math.sin(HALO_TILT)))
HU = Vector((0.0, -math.sin(HALO_TILT), math.cos(HALO_TILT)))
HALO_R = 1.02
FLARES = ((0, 0.84), (-22, 0.74), (22, 0.74), (-44, 0.66), (44, 0.66), (-66, 0.60), (66, 0.60), (-90, 0.52),
          (90, 0.52), (-114, 0.44), (114, 0.44), (-138, 0.36), (138, 0.36))   # (角度°，火舌长)

# 两对翅膀：主翼四节、次级翼三节；k 为羽片尺寸系数，gain 为动作幅度系数
WZ = B0.shoulder_z - 0.28                        # 翼根高度（肩胛处）
WINGS = (
    dict(pre="Wing", root=(0.95, -1.24, WZ), seg=((1.52, 52, 8), (1.66, 26, 12), (1.34, -12, 16), (1.07, -40, 20)),
         k=1.34, r=(0.21, 0.09), tilt=24, yaw=14, gain=1.0, lift0=0.0, prim=15, sec=11, cov=11, rear=9, scale=7, under=10, mid=10),
    dict(pre="WingLo", root=(0.74, -1.30, WZ - 0.66), seg=((1.05, 4, 24), (1.12, -22, 30), (0.92, -46, 36)),
         k=0.74, r=(0.13, 0.058), tilt=30, yaw=26, gain=0.55, lift0=0.0, prim=8, sec=5, cov=6, rear=0, scale=3, under=4, mid=5),
)
DART_RANGE = 10.0


# ===== 材质 =====
def materials(ctx):
    M = ctx.M
    steel = (0.185, 0.176, 0.168)
    ctx.mat("steel", "forged engraved dark steel", steel, metal=0.70, rough=0.36, coat=0.25)
    # 余烬嵌线用几何细管做；大面是锻打暗钢 + 暗金嵌线卷草（线粗、金色亮，近看是嵌金雕花）
    ctx.texture("steel", inlay_maps(steel, (0.62, 0.43, 0.19), size=1024, seed=31, dimples=14, density=5, line=2),
                normal_strength=0.55)
    ctx.mat("slate", "engraved gunmetal", (0.06, 0.057, 0.057), metal=0.92, rough=0.30, coat=0.3)
    ctx.texture("slate", filigree_maps((0.065, 0.061, 0.060), (0.34, 0.23, 0.12), size=1024, seed=19, density=20,
                                       width=1), normal_strength=0.4)
    # 羽甲 / 花瓣甲：暗钢底 + 金边 + 金中脊 + 金羽枝
    ctx.mat("petal", "gilt-edged feather plate", (0.12, 0.105, 0.095), metal=0.42, rough=0.46, coat=0.1)
    ctx.texture("petal", petal_maps((0.13, 0.125, 0.12), (0.80, 0.56, 0.26), EMBER, size=512, seed=5, barbs=7.0,
                                    glow=0.5), emit_strength=0.6, normal_strength=0.6)   # 第五轮：羽甲只剩金脊 / 羽枝细线发光，强度 1.2 → 0.6
    # 鎏金雕花：金底暗卷草（大块鎏金甲面）
    ctx.mat("gilded", "gilded engraved plate", (0.78, 0.55, 0.27), metal=1.0, rough=0.30)
    ctx.texture("gilded", gilded_maps((0.80, 0.57, 0.28), (0.16, 0.09, 0.04), size=1024, seed=19, density=8,
                                      width=2), normal_strength=0.7)
    ctx.mat("molten", "molten-seamed steel", (0.10, 0.09, 0.085), metal=0.6, rough=0.38, coat=0.3)
    ctx.texture("molten", ember_crack_maps(EMBER, base_rgb=(0.11, 0.10, 0.095), size=1024, seed=17, cells=6,
                                           width=0.026, fine=0.0, heat=0.9, soot=0.5, keep=0.5),
                emit_strength=0.6, normal_strength=0.7)   # 第五轮：只留少量熔缝，强度 3.0 → 0.6（只剩心板 / 手背板两处小件）
    ctx.mat("gilt", "burnished dark gold", (0.78, 0.55, 0.27), metal=1.0, rough=0.28)
    ctx.mat("trim", "burnished gold trim", (0.84, 0.60, 0.30), metal=1.0, rough=0.24)
    # 紧身衣不加 sheen：掠射角的 sheen 在肩顶 / 腋下露出处泛成一片灰
    ctx.mat("suit", "charred undersuit", (0.012, 0.010, 0.010), metal=0.1, rough=0.72)
    ctx.mat("robe", "torn ash-black robe", (0.075, 0.068, 0.065), rough=0.8, sheen=0.18, sheen_tint=(1, 0.8, 0.7),
            spec=0.3)
    ctx.texture("robe", burn_cloth_maps_r5(EMBER, base_rgb=(0.080, 0.072, 0.068), line_rgb=(0.16, 0.07, 0.04),
                                           size=2048, seed=51, buses=6, burn=0.12,
                                           reach=(0.14, 0.40)), emit_strength=0.6)   # 第五轮：电路细线 + 燃烧线，1.7 → 0.6
    ctx.mat("under", "smoulder-red underskirt", (0.12, 0.028, 0.018), rough=0.7, sheen=0.2, sheen_tint=(1, 0.5, 0.4),
            spec=0.3)
    ctx.texture("under", burn_cloth_maps_r5(EMBER, base_rgb=(0.115, 0.027, 0.017), line_rgb=(0.26, 0.07, 0.03),
                                            size=1024, seed=63, buses=10, burn=0.08), emit_strength=0.6)   # 1.5 → 0.6
    ctx.mat("tabard", "charcoal rune tabard", (0.07, 0.064, 0.062), rough=0.66, sheen=0.15, spec=0.3)
    ctx.texture("tabard", circuit_maps(EMBER, base_rgb=(0.070, 0.064, 0.062), line_rgb=(0.30, 0.10, 0.05), size=1024,
                                       seed=23, buses=7), emit_strength=0.6)   # 第五轮 1.6 → 0.6（只是细电路线）
    ctx.mat("lining", "ember satin lining", (0.20, 0.045, 0.022), rough=0.45, sheen=0.35, sheen_tint=(1, 0.6, 0.4))
    # 刃羽：灰烬黑羽根 → 炭灰羽身 → 炽热刃口；金属度压低（高金属度在暗场里只反射黑色环境）
    ctx.mat("feather", "ember-edged blade feather", (0.11, 0.092, 0.080), metal=0.12, rough=0.66, spec=0.18)
    # 第五轮：飞羽（含羽刃）= 翼缘主发光区——只在最外侧一条细刃口线（+ 内侧一圈快速衰减的肩）发光（强度 3.0），羽身的橙红由基础色渐变承担
    ctx.texture("feather", plume_maps_r5(EMBER, (0.012, 0.010, 0.009), (0.060, 0.048, 0.040), (0.085, 0.068, 0.054),
                                         (0.78, 0.54, 0.24), size=1024, seed=5, edge=0.20, tip=0.46, line=0.12,
                                         shoulder=0.50, shoulder_w=0.30),
                emit_strength=3.0, normal_strength=0.5)
    ctx.mat("plume", "charcoal covert feather", (0.09, 0.073, 0.062), metal=0.12, rough=0.70, spec=0.18)
    # 覆羽 / 衬羽：橙红只在基础色里，刃口线极淡（强度 0.6）
    ctx.texture("plume", plume_maps_r5(EMBER, (0.011, 0.009, 0.008), (0.055, 0.045, 0.038), (0.075, 0.062, 0.050),
                                       (0.74, 0.50, 0.22), size=1024, seed=9, edge=0.12, tip=0.30, rib=0.7,
                                       line=0.045, heat_alb=0.85),
                emit_strength=0.6, normal_strength=0.5)
    # 翼背覆羽（后视图压在飞羽根部的那一层）：灰烬黑 → 橙红刃口 + 金脊，与正面同一色调（原先用鎏金羽甲，冷色逆光下读成灰蓝金属）
    ctx.mat("dorsal", "ash dorsal feather", (0.10, 0.075, 0.060), metal=0.10, rough=0.72, spec=0.16)
    ctx.texture("dorsal", plume_maps_r5(EMBER, (0.010, 0.008, 0.007), (0.055, 0.043, 0.035), (0.080, 0.064, 0.050),
                                        (0.80, 0.55, 0.24), size=1024, seed=13, edge=0.17, tip=0.40, rib=0.9,
                                        line=0.045, heat_alb=0.9),
                emit_strength=0.6, normal_strength=0.5)
    ctx.mat("blade", "molten terminal blade", (0.085, 0.078, 0.072), metal=0.55, rough=0.46, coat=0.1)
    # 第五轮：终末之剑刃口 = 主发光区——刃口一条细发光带 + 少量熔缝，强度 3.6 → 2.6
    ctx.texture("blade", blade_maps_r5(EMBER, (0.085, 0.078, 0.072), size=1024, seed=23, edge=0.13, heat=0.75, keep=0.55), emit_strength=2.6,
                normal_strength=0.6)
    ctx.mat("glow", "ember core glow", (1.0, 0.45, 0.25), emit=(1.0, 0.46, 0.24), strength=3.0)
    # 次要发光件（腰扣 / 翼座与翼关节宝石 / 裙甲宝石 / 飘带宝石 / 肩甲日轮徽 / 护肘与手背宝石）：强度压低，
    # 把视线让给光环、圣心、剑与翼缘四个主发光区（材质名含 glow，游戏版同样不减面）
    # 第五轮：次要宝石改名 gem（glow.js 的 glowWeight 对名字含 core / glow / eye / heart / slit 的材质给 0.5 的强辉光权重，
    # 次要件不该参与强辉光），强度 1.45 → 1.0
    ctx.mat("glow2", "ember accent gem", (0.70, 0.30, 0.16), emit=(1.0, 0.40, 0.18), strength=1.0)
    # 圣心刻面红宝石（第五轮）：热橙 / 红橙 / 深红三档，不带发光贴图（带贴图的材质辉光权重只有 0.12，圣心是主发光区，要吃 0.5）
    ctx.mat("ruby_hot", "sacred heart glow hot", (0.42, 0.04, 0.015), emit=(1.0, 0.30, 0.04), strength=1.8, rough=0.10,
            spec=0.8, coat=0.6)
    ctx.mat("ruby_mid", "sacred heart glow mid", (0.30, 0.018, 0.012), emit=(1.0, 0.07, 0.014), strength=1.25,
            rough=0.10, spec=0.8, coat=0.6)
    ctx.mat("ruby_deep", "sacred heart glow deep", (0.16, 0.008, 0.008), emit=(0.75, 0.010, 0.010), strength=0.55,
            rough=0.10, spec=0.8, coat=0.6)
    ctx.mat("inlay", "ember circuit inlay", (0.6, 0.3, 0.2), emit=EMBER, strength=1.0)
    ctx.mat("ember", "ember shard", (0.45, 0.10, 0.04), emit=(1.0, 0.27, 0.06), strength=1.0)
    ctx.mat("hem", "ember hem light", (0.6, 0.3, 0.2), emit=EMBER, strength=1.3)
    # 火焰：根部金黄 → 尖端暗红的渐变贴图；强度压低，AgX 会把高亮自发光压成发白的桃色
    ctx.mat("flame", "terminal flame", (0.25, 0.04, 0.0), emit=(1.0, 0.30, 0.05), strength=1.6)
    ctx.texture("flame", flame_maps(256, seed=3), emit_strength=1.9)
    ctx.mat("fcore", "flame core", (1.0, 0.58, 0.20), emit=(1.0, 0.58, 0.20), strength=2.2)
    ctx.texture("fcore", flame_maps(256, seed=5, hot=(1.0, 0.92, 0.62), mid=(1.0, 0.62, 0.20), tip=(1.0, 0.30, 0.05),
                                    fade=0.6), emit_strength=2.4)
    flame_mats(M, ctx.title, strength_out=2.4, strength_in=2.8)
    M["aura"] = flame_material(f"{ctx.title} halo aura flame", aura_maps(256), 1.6)
    return M


def small_gem(name, c, r, mat, stretch=(1.0, 0.6, 1.3)):
    """省面的发光宝石（kit.gem 用 12×8 段，这里 8×5）。"""
    return ellipsoid(name, c, (r * stretch[0], r * stretch[1], r * stretch[2]), [mat], 8, 5)


def shell_rims(ctx, name, pt, mat, r, spec, full=False, n=48, sides=True, lift=2.6):
    """甲壳上下缘（与开口两侧）的四棱滚边：代替 kit.humanoid.shell 自带的六棱滚边（Boss 的滚边太多，六棱超预算）。"""
    for v in (0.0, 1.0):
        pts = [radial(pt(i / (n if full else n - 1), v), r * lift) for i in range(n)]
        ctx.part(rim(f"{name} rim {v}", pts, r, mat, closed=full), spec)
    if not full and sides:
        for u in (0.0, 1.0):
            pts = [radial(pt(u, j / 12), r * lift) for j in range(13)]
            ctx.part(rim(f"{name} side {u}", pts, r, mat), spec)


def torso_paths(ctx, B, name, paths, grow, mat, spec, radius, per=4):
    """贴合躯干表面的折线（右半侧 (x, z) 身高比例坐标，自动镜像）：代替 kit.torso_inlay 的六棱、每段 8 点细管。"""
    s = B.s
    for sd in (-1, 1):
        for i, path in enumerate(paths):
            pts = []
            for (x0, z0), (x1, z1) in zip(path, path[1:]):
                for k in range(per):
                    t = k / per
                    pts.append(B.on_torso(sd * lerp(x0, x1, t) * s, B.z(lerp(z0, z1, t)), grow))
            pts.append(B.on_torso(sd * path[-1][0] * s, B.z(path[-1][1]), grow))
            ctx.part(rim(f"{name} {sd}{i}", pts, radius * s, mat), spec)


def limb_rims(ctx, name, pt, a, b, r, mat, spec, n=22, closed=False):
    """肢体甲片上下缘的四棱滚边（kit.limb_plate 自带的滚边是六棱、nu+8 点）。"""
    a, b = Vector(a), Vector(b)
    ab = b - a
    for v in (0.0, 1.0):
        pts = []
        for i in range(n):
            p = pt(i / (n if closed else n - 1), v)
            c = a + ab * clamp((p - a).dot(ab) / ab.length_squared)
            pts.append(p + (p - c).normalized() * r * 1.6)
        ctx.part(rim(f"{name} {v}", pts, r, mat, closed=closed), spec)


# ===== 躯干 =====
def build_torso(ctx, B, M):
    s = B.s
    T = ctx.title
    suit_torso(ctx, B, M["suit"], nu=22, nv=14)     # 紧身衣大部分被胸甲遮住：细分到够托住甲壳即可

    def pec(a, z):
        front = max(0.0, math.cos(a))
        return (0.024 * s * math.exp(-((z - B.z(1.53)) / (0.075 * s)) ** 2) * front ** 2 *
                (1 - 0.65 * math.exp(-(math.sin(a) / 0.10) ** 2)) +
                0.008 * s * math.exp(-(math.sin(a) / 0.05) ** 2) * front * smoothstep(B.z(1.36), B.z(1.46), z))
    spec = invdist(["Spine", "Chest"])
    # 甲壳上缘一直包到肩顶（加宽后的躯干肩顶是一圈缓坡，露出紧身衣会在审图里泛灰）
    pt = shell2(ctx, B, f"{T} cuirass", lambda a: B.z(1.698) - 0.05 * s * max(0.0, math.cos(a)) ** 8,
                lambda a: B.z(1.34) - 0.05 * s * max(0.0, math.cos(a)) ** 5, 0.014 * s, M["steel"], spec,
                thick=0.010 * s, shape=pec, nu=66, nv=24)
    shell_rims(ctx, f"{T} cuirass", pt, M["trim"], 0.0048 * s, spec, full=True, n=44)
    # 鎏金胸板：风筝形（上宽下尖）的鎏金雕花甲，托住胸核；边缘一圈暗金滚边
    def sternum(u, v):
        hw = 0.215 * (1 - v ** 2.2) ** 0.62 * (0.82 + 0.18 * smoothstep(0.0, 0.2, v))
        return B.on_torso((2 * u - 1) * hw * s, B.z(lerp(1.645, 1.300, v)), 0.034 * s)
    plate = surface(f"{T} sternum plate", sternum, 11, 14, [M["gilded"]])
    orient(plate, lambda c: Vector((0, 0, c.z)))
    scale_uv(plate, 1.5, 1.3)
    ctx.part(finish(plate, 0.010 * s, 0, 0), invdist(["Spine", "Chest"]))
    outline = [sternum(0.0, j / 16) for j in range(17)] + [sternum(i / 8, 1.0) for i in range(1, 8)] + \
              [sternum(1.0, 1 - j / 16) for j in range(1, 17)] + [sternum(1 - i / 12, 0.0) for i in range(1, 12)]
    ctx.part(rim(f"{T} sternum rim", [radial(p, 0.004 * s) for p in outline], 0.0052 * s, M["trim"], closed=True),
             invdist(["Spine", "Chest"]))
    spec = invdist(["Pelvis", "Spine"])
    pt = shell2(ctx, B, f"{T} plackart", lambda a: B.z(1.43),
                lambda a: B.z(1.27) - 0.06 * s * max(0.0, math.cos(a)) ** 3, 0.028 * s, M["steel"], spec, a0=-1.10,
                a1=1.10, nu=30, nv=10, thick=0.008 * s)
    shell_rims(ctx, f"{T} plackart", pt, M["trim"], 0.0038 * s, spec, n=30)
    # 腹甲三道横向分片
    for k, zz in enumerate((1.39, 1.35, 1.31)):
        line = [radial(pt(i / 23, (1.43 - zz) / 0.16), 0.004 * s) for i in range(24)]
        ctx.part(rim(f"{T} plackart lame {k}", line, 0.0030 * s, M["trim"]), spec)
    shell(ctx, B, f"{T} belt", B.z(1.29), B.z(1.25), 0.034 * s, M["gilt"], spec, nu=64, nv=4, thick=0.008 * s, sub=0)
    for k in range(10):
        a = k / 10 * TAU + math.pi / 10
        c = B.torso_point(a, B.z(1.27), 0.044 * s)
        ctx.part(ellipsoid(f"{T} belt stud {k}", c, (0.011 * s,) * 3, [M["gilt"]], 8, 5), spec)
    buckle = B.on_torso(0, B.z(1.27), 0.046 * s)
    ctx.part(ellipsoid(f"{T} buckle", buckle, (0.046 * s, 0.014 * s, 0.032 * s), [M["gilt"]], 16, 8), rigid("Pelvis"))
    ctx.part(small_gem(f"{T} buckle gem", buckle + Vector((0, 0.013 * s, 0)), 0.014 * s, M["glow2"], (1.2, 0.5, 0.9)),
             rigid("Pelvis"))
    # 胸前“终末圣心”：熔裂心板 + 心形发光宝石 + 金框荆棘 + 羽翼环抱 + 金链（第四轮：不再是方舟反应堆式的圆盘）
    build_sacred_heart_r5(ctx, B, M, B.z(1.535), small_gem)
    # 护喉：三层尖底分片甲（逐层向下放大、错位相压）；第四轮取代一圈圈的颈环
    gorget_plates(ctx, B, M, ((1.640, 1.690, 0.168, 0.200, 8, 0.0, TAU, 0.020),
                              (1.676, 1.724, 0.146, 0.172, 7, 0.5, 4.4, 0.018),
                              (1.710, 1.756, 0.126, 0.146, 6, 0.0, 3.6, 0.016)))

    # 背后高领：绕后颈张开的暗钢甲领 + 一排金色尖芒
    def collar(u, v):
        a = math.pi + (2 * u - 1) * 1.80
        z = lerp(B.z(1.635), B.z(1.870), v) + 0.035 * s * v * (1 - abs(2 * u - 1)) ** 2
        r = lerp(0.118 * s, 0.190 * s, v ** 1.3)
        return Vector((r * math.sin(a) * 1.12, 0.010 * s + r * math.cos(a), z))
    col = surface(f"{T} collar", collar, 32, 8, [M["steel"]])
    orient(col, lambda c: Vector((0, 0.01 * s, c.z)))
    ctx.part(finish(col, 0.009 * s, 1, 0), invdist(["Chest", "Neck"]))
    ctx.part(rim(f"{T} collar rim", [radial(collar(i / 39, 1.0), 0.006 * s, 0.01 * s) for i in range(40)],
                 0.0048 * s, M["trim"]), invdist(["Chest", "Neck"]))
    for k in range(7):
        u = 0.14 + k / 6 * 0.72
        base = collar(u, 0.96)
        out = Vector((base.x, base.y - 0.01 * s, 0)).normalized()
        L = (0.12 if k == 3 else (0.085 if k % 2 else 0.065)) * s
        ctx.part(spike(f"{T} collar tine {k}", base, base + (out * 0.45 + Vector((0, 0, 1))).normalized() * L,
                       0.012 * s, [M["gilt"]], sides=4, fx=1.0, fy=0.45, up=tuple(out)), invdist(["Chest", "Neck"]))


# ===== 握剑的铠甲手（第四轮：分节手指 + 拇指 + 手背甲，实现在 _b7r4_parts.gauntlet_r4；整只刚性挂 Hand 骨） =====
def gauntlet(ctx, B, side, label, M):
    gauntlet_r4(ctx, B, side, label, M, HS, GRIP_A, GRIP_B, small_gem)


def build_pauldron(ctx, B, M, side, label):
    """巨型花瓣肩甲：六层圆顶甲环（鎏金帽盖 + 暗钢嵌金甲片）+ 两排长花瓣羽甲（金边金脊）+ 前向日轮徽 + 五枚冲天刃羽。"""
    s = B.s
    T = ctx.title
    spec = rigid(f"Shoulder.{label}")          # 肩甲挂在跟随上臂一半转动的肩骨上（两骨线性混合会把大圆顶压扁）
    RAD, SPREAD, RISE, TILT = 0.292, 1.42, 1.04, 0.30
    theta = ((0.0, 0.78), (0.55, 1.08), (0.88, 1.38), (1.18, 1.70), (1.50, 2.02), (1.80, 2.30))
    lp, sh = pauldron_lite(ctx, B, side, label, M["steel"], lames=6, radius=RAD, spread=SPREAD, rise=RISE, tilt=TILT,
                           spire=0.0, theta=theta, shrink=(1.0, 0.975, 0.95, 0.925, 0.90, 0.875), ridge=0.05,
                           spec=spec, thick=0.008, nu=28, nv=8)
    for k in range(6):
        edge = [lp(k, 2 * i / 14 - 1, 1.0) for i in range(15)]
        edge = [p + (p - sh).normalized() * 0.005 * s for p in edge]
        ctx.part(rim(f"{T} pauldron {label}{k} rim", edge, 0.0046 * s, M["trim"]), spec)
    for i in range(11):
        p = lp(0, 2 * (i + 0.5) / 11 - 1, 0.90)
        ctx.part(ellipsoid(f"{T} pauldron rivet {label}{i}", p + (p - sh).normalized() * 0.008 * s,
                           (0.0075 * s,) * 3, [M["gilt"]], 8, 5), spec)
    # 花瓣羽甲：外排长瓣压在圆顶上，内排短瓣压住外排根部（金边金脊的暗钢羽片）
    rows = ((8, -1.30, 0.375, 0.08, 1.96, 0.26, 1.075, 0.10), (7, -1.125, 0.375, 0.10, 1.55, 0.235, 1.135, 0.06))
    for r, (n, phi0, dphi, ta, tb, half, rr, lift) in enumerate(rows):
        for k in range(n):
            petal, pt = petal_surface(f"{T} pauldron petal {label}{r}{k}", sh, side, RAD * s * rr, phi0 + k * dphi,
                                      half, ta, tb, RISE, TILT, [M["petal"]], lift=lift, curl=0.14, nu=6, nv=10,
                                      thick=0.011 * s)
            ctx.part(petal, spec)
            if r == 0 and k % 2 == 0:
                tip = pt(0.0, 1.0)
                ctx.part(ellipsoid(f"{T} petal stud {label}{k}", tip + (tip - sh).normalized() * 0.01 * s,
                                   (0.012 * s,) * 3, [M["glow2"]], 8, 5), spec)
    # 前向日轮徽：光环母题的小光环，朝前上方立在肩甲正面
    cen = sh + Vector((side * 0.52, 0.74, 0.58))
    nrm = Vector((side * 0.30, 0.90, 0.30)).normalized()
    a1v = Vector((0, 0, 1)) - nrm * nrm.z
    a1v.normalize()
    a2v = nrm.cross(a1v)

    def at(a, r, dn=0.0):
        return cen + a2v * (math.sin(a) * r) + a1v * (math.cos(a) * r) + nrm * dn
    M2 = dict(M, glow=M["glow2"])
    for o in halo_ring(T, M2, at, 0.36, 0.52, 8, f"{T} pauldron sun {label}", both=False, seg=24):
        ctx.part(o, spec)
    for k in range(12):
        a = (k + 0.5) / 12 * TAU
        L = 0.15 if k % 2 == 0 else 0.09
        ctx.part(spike(f"{T} pauldron sun ray {label}{k}", at(a, 0.37), at(a, 0.37 + L), 0.022, [M["gilt"]], sides=4,
                       fx=1.0, fy=0.45, up=tuple(nrm)), spec)
    ctx.part(blob(f"{T} pauldron sun disc {label}", cen + nrm * 0.02, (0.17, 0.17, 0.05), [M["gilt"]], 14, 8,
                  axes=(a2v, a1v, nrm)), spec)
    ctx.part(small_gem(f"{T} pauldron sun gem {label}", cen + nrm * 0.07, 0.085, M["glow2"], (1, 1, 1)), spec)
    # 冲天刃羽：向上略向前外扬起的五枚暗钢 / 金刃
    for i, (u, L, lean, mat) in enumerate(((-0.62, 0.30, -0.55, "steel"), (-0.32, 0.43, -0.38, "gilt"),
                                           (0.0, 0.52, -0.22, "steel"), (0.32, 0.42, -0.05, "gilt"),
                                           (0.60, 0.29, 0.10, "steel"))):
        base = lp(0, u, 0.30)
        d = Vector((side * 0.40, lean + 0.28, 0.86)).normalized()
        nrm2 = Vector((side, 0.25, 0)).normalized()
        ya = nrm2.cross(d).normalized()
        ya = ya if ya.z > 0 or ya.y > 0 else -ya
        ctx.part(ridge_blade(f"{T} pauldron blade {label}{i}", L * s, 0.075 * s, 0.020 * s, [M[mat]],
                             base - d * 0.02 * s, d, ya, n=8, sweep=0.10, bend=0.02), spec)


def build_arms(ctx, B, M):
    s = B.s
    T = ctx.title
    for side, label in SIDES:
        suit_arm(ctx, B, side, label, M["suit"])
        gauntlet(ctx, B, side, label, M)
        build_pauldron(ctx, B, M, side, label)
        a = B.arms[label]
        pt = rerebrace(ctx, B, side, label, M["steel"], None, r=(0.062, 0.053), sub=0, nu=26, nv=8, closed=True)
        limb_rims(ctx, f"{T} rerebrace rim {label}", pt, a["shoulder"], a["elbow"], 0.0032 * s, M["trim"],
                  rigid(f"UpperArm.{label}"), n=22)
        # 护肘：圆顶护肘甲 + 上下关节罩 + 三叠金刃（第四轮：整个肘部被甲遮住）
        couter_r4(ctx, B, M, side, label, small_gem, ridge_blade)
        pt = vambrace(ctx, B, side, label, M["steel"], None, inlay=M["inlay"], r=(0.046, 0.052),
                      spur=(M["gilt"], 0.085), sub=0)
        limb_rims(ctx, f"{T} vambrace rim {label}", pt, a["elbow"], a["wrist"], 0.0030 * s, M["trim"],
                  rigid(f"Forearm.{label}"), n=20, closed=True)
        # 腕口外翻的金色护腕
        e, w = a["elbow"], a["wrist"]
        fd = (w - e).normalized()
        cuff = [p for p in ring_around(w - fd * 0.075 * s, w - fd * 0.03 * s, 0.5, 0.060 * s * B.limb, 24)]
        ctx.part(tube(f"{T} cuff {label}", cuff, [0.009 * s] * 24, [M["gilt"]], n=6, closed=True, per=1),
                 rigid(f"Forearm.{label}"))


# ===== 头盔：修长面甲、V 形余烬目缝、金冠与后掠刃冠 =====
def build_helm(ctx, B, M):
    s = B.s * 1.22                        # 头盔按 1.22 倍放大：巨肩上的头不能显小
    T = ctx.title
    hc = B.head_c
    rx, ry = 0.100 * s, 0.118 * s
    eye_z = hc.z + 0.004 * s
    prof = [(0.0, (0.00, 0.170)), (0.10, (0.42, 0.158)), (0.26, (0.76, 0.118)), (0.44, (0.95, 0.055)),
            (0.56, (1.00, 0.012)), (0.70, (0.96, -0.040)), (0.84, (0.86, -0.090)), (1.0, (0.80, -0.132))]

    def hp(u, v):
        a = u * TAU
        r, dz = interp(prof, v)
        front, back = max(0.0, math.cos(a)), max(0.0, -math.cos(a))
        x = rx * r * math.sin(a)
        z = hc.z + dz * s
        keel = 0.020 * s * math.exp(-(x / (0.016 * s)) ** 2) * front ** 2 * smoothstep(0.08, 0.75, v)
        brow = 0.014 * s * math.exp(-((z - eye_z - 0.020 * s) / (0.010 * s)) ** 2) * front ** 1.5
        chin = 0.028 * s * front ** 3 * smoothstep(0.72, 1.0, v)
        tail = 0.045 * s * back ** 2 * smoothstep(0.12, 0.55, v) * (1 - smoothstep(0.70, 1.0, v))
        z -= 0.034 * s * front ** 4 * smoothstep(0.78, 1.0, v) * math.exp(-(x / (0.05 * s)) ** 2)
        y = ry * r * math.cos(a) + hc.y + keel + brow + chin - tail
        d = Vector((x, y - hc.y, 0))
        d = d.normalized() if d.length > 1e-6 else Vector((0, 0, 0))
        return Vector((x, y, z)) + d * 0.010 * s * smoothstep(0.86, 1.0, v)
    helm = surface(f"{T} helm", hp, 48, 26, [M["steel"]])
    orient(helm, lambda c: hc)
    helm = finish(helm, 0.006 * s, -1, 0)
    ctx.part(helm, rigid("Head"))
    proj = projector(helm, (0, -1, 0))
    # V 形怒目：两道向中线下斜的余烬目缝 + 上方金色眉线
    for sd in (-1, 1):
        slit = [proj(Vector((sd * lerp(0.012, 0.072, i / 12) * s, 1, eye_z + lerp(-0.010, 0.012, i / 12) * s)),
                     0.0012 * s) for i in range(13)]
        ctx.part(tube(f"{T} eye slit {sd}", slit, [0.0042 * s] * 13, [M["glow"]], n=6, per=1), rigid("Head"))
        brow = [proj(Vector((sd * lerp(0.010, 0.078, i / 12) * s, 1, eye_z + lerp(0.004, 0.028, i / 12) * s)),
                     0.0030 * s) for i in range(13)]
        ctx.part(rim(f"{T} brow line {sd}", brow, 0.0028 * s, M["trim"]), rigid("Head"))
        cheek = [proj(Vector((sd * lerp(0.020, 0.070, i / 8) * s, 1, eye_z - lerp(0.030, 0.085, i / 8) * s)),
                      0.0030 * s) for i in range(9)]
        ctx.part(rim(f"{T} cheek line {sd}", cheek, 0.0024 * s, M["trim"]), rigid("Head"))
    keel = [proj(Vector((0, 1, eye_z + (0.030 - i * 0.012) * s)), 0.0022 * s) for i in range(9)]
    ctx.part(rim(f"{T} keel line", keel, 0.0026 * s, M["trim"]), rigid("Head"))
    for i in range(3):
        z = eye_z - (0.052 + i * 0.013) * s
        grille = [proj(Vector((x * s, 1, z)), 0.0016 * s) for x in (-0.030, -0.015, 0.0, 0.015, 0.030)]
        ctx.part(rim(f"{T} grille {i}", grille, 0.0022 * s, M["glow"] if i == 1 else M["trim"]), rigid("Head"))
    # 金冠：额带 + 前额七枚焰形尖齿 + 额心宝石
    band = [radial(hp(i / 64, 0.40), 0.004 * s, hc.y) for i in range(64)]
    ctx.part(rim(f"{T} circlet", band, 0.0055 * s, M["trim"], closed=True), rigid("Head"))
    for k in range(7):
        u = (k - 3) / 3 * 0.17
        base = radial(hp(u % 1.0, 0.40), 0.003 * s, hc.y)
        out = Vector((base.x, base.y - hc.y, 0)).normalized()
        L = (0.095 if k == 3 else (0.065 if k % 2 else 0.050)) * s
        ctx.part(spike(f"{T} crown tine {k}", base, base + (out * 0.35 + Vector((0, 0, 1))).normalized() * L,
                       0.0105 * s, [M["gilt"]], sides=4, fx=1.0, fy=0.45, up=tuple(out)), rigid("Head"))
    ctx.part(gem(f"{T} brow gem", radial(hp(0.0, 0.40), 0.010 * s, hc.y) + Vector((0, 0, 0.004 * s)), 0.012 * s,
                 M["glow"], (0.8, 0.5, 1.4)), rigid("Head"))
    # 后掠刃冠：大小两对 + 顶脊一枚
    for side, label in SIDES:
        for big in (True, False):
            base = Vector((side * rx * (0.80 if big else 0.92), hc.y - 0.02 * s, hc.z + (0.085 if big else 0.030) * s))
            d = Vector((side * (0.42 if big else 0.62), -0.60 if big else -0.66, 0.68 if big else 0.36)).normalized()
            nrm = Vector((side, 0.55, 0)).normalized()
            ya = nrm.cross(d).normalized()
            ya = ya if ya.z > 0 else -ya
            L, W = (0.26 * s, 0.080 * s) if big else (0.17 * s, 0.055 * s)
            origin = base - d * 0.03 * s
            ctx.part(ridge_blade(f"{T} crest {label}{int(big)}", L, W, 0.016 * s, [M["steel"] if big else M["gilt"]],
                                 origin, d, ya, n=9, sweep=0.16, bend=0.03), rigid("Head"))
            if big:
                edge = [origin + d * (t * L) + ya * (0.5 * W * feather_width(t) + 0.16 * L * t * t + 0.004 * s)
                        for t in [0.12 + i / 9 * 0.8 for i in range(10)]]
                ctx.part(rim(f"{T} crest edge {label}", edge, 0.0032 * s, M["trim"]), rigid("Head"))
    top = Vector((0, hc.y + 0.02 * s, hc.z + 0.16 * s))
    d = Vector((0, -0.62, 0.78)).normalized()
    ya = Vector((1, 0, 0)).cross(d).normalized()
    ya = ya if ya.z > 0 else -ya
    ctx.part(ridge_blade(f"{T} crest top", 0.16 * s, 0.052 * s, 0.014 * s, [M["gilt"]], top - d * 0.02 * s, d, ya,
                         n=8, sweep=0.12), rigid("Head"))
    return hc


# ===== 背后圣骸引擎与翼座 =====
def build_harness(ctx, B, M):
    s = B.s
    T = ctx.title
    spec = rigid("Chest")
    ec = Vector((0, -0.80, B0.z(1.50)))
    ctx.part(blob(f"{T} engine", ec, (0.34, 0.20, 0.64), [M["steel"]], 22, 14, tile=0.8), spec)
    for zz in (-0.42, 0.0, 0.42):
        k = math.sqrt(max(0.0, 1 - (zz / 0.64) ** 2))
        ring = [ec + Vector((math.sin(t) * 0.345 * k, math.cos(t) * 0.205 * k, zz)) for t in [i / 20 * TAU for i in range(20)]]
        ctx.part(rim(f"{T} engine rib {zz:.2f}", ring, 0.017, M["trim"], closed=True), spec)
    for i, zz in enumerate((-0.30, -0.10, 0.10, 0.30)):
        k = math.sqrt(max(0.0, 1 - (zz / 0.64) ** 2))
        y = ec.y - 0.20 * k - 0.006
        ctx.part(tube(f"{T} engine vent {i}", [(-0.15 * k, y, ec.z + zz), (0.15 * k, y, ec.z + zz)], [0.022, 0.022],
                      [M["glow2"]], n=6, per=1), spec)
    for k, x in enumerate((-0.17, 0.0, 0.17)):
        base = Vector((x, ec.y - 0.02, ec.z + 0.52))
        ctx.part(spike(f"{T} engine spire {k}", base, base + Vector((x * 0.5, -0.16, 0.52 if k == 1 else 0.36)),
                       0.064, [M["gilt"]], sides=6), spec)
        ctx.part(small_gem(f"{T} engine spire gem {k}", base + Vector((0, -0.07, 0.03)), 0.040, M["glow2"], (1, 1, 1)),
                 spec)
    for cfg in WINGS:
        big = cfg["pre"] == "Wing"
        for side, label in SIDES:
            mc = Vector((side * (cfg["root"][0] - 0.08), cfg["root"][1] + 0.20, cfg["root"][2] - 0.02))
            rr = 0.32 if big else 0.20
            ctx.part(blob(f"{T} {cfg['pre']} mount {label}", mc, (rr, rr * 0.8, rr * 1.1), [M["steel"]], 18, 10), spec)
            ring = [Vector((side * (mc.x * side + rr * 0.68), mc.y + math.cos(t) * rr * 0.66, mc.z + math.sin(t) * rr * 0.78))
                    for t in [i / 24 * TAU for i in range(24)]]
            ctx.part(tube(f"{T} {cfg['pre']} mount ring {label}", ring, [0.034 if big else 0.022] * 24, [M["gilt"]],
                          n=6, closed=True, per=1), spec)
            ctx.part(small_gem(f"{T} {cfg['pre']} mount gem {label}", Vector((side * (mc.x * side + rr * 0.74), mc.y, mc.z)),
                               0.08 if big else 0.05, M["glow2"], (0.6, 1.0, 1.0)), spec)
            if big:
                for zz in (-0.16, 0.14):
                    back = B.torso_point(math.pi - side * 0.55, mc.z + zz, 0.020 * s)
                    ctx.part(tube(f"{T} wing strut {label}{zz}", [back, back.lerp(mc, 0.5), mc - Vector((side * 0.05, 0, 0))],
                                  [0.065, 0.058, 0.055], [M["gilt"]], n=8, per=2), spec)
                ctx.part(tube(f"{T} engine arm {label}", [ec + Vector((side * 0.24, 0, 0.26)),
                                                          mc + Vector((-side * 0.14, 0, -0.06))],
                              [0.078, 0.068], [M["slate"]], n=8, per=1), spec)
            else:
                ctx.part(tube(f"{T} engine arm lo {label}", [ec + Vector((side * 0.22, 0, -0.30)),
                                                             mc + Vector((-side * 0.08, 0, 0.0))],
                              [0.062, 0.054], [M["slate"]], n=8, per=1), spec)
    # 背甲：上背一块鎏金风筝形肩胛板（与胸前鎏金胸板呼应）+ 脊椎一列暗钢 / 金椎片，翼座与引擎都压在它前面
    def scap(u, v):
        hw = 0.24 * (1 - v ** 2.0) ** 0.6 * (0.80 + 0.20 * smoothstep(0.0, 0.2, v))
        return B.on_torso((2 * u - 1) * hw * s, B.z(lerp(1.655, 1.34, v)), 0.030 * s, back=True)
    plate = surface(f"{T} scapular plate", scap, 11, 14, [M["gilded"]])
    orient(plate, lambda c: Vector((0, 0, c.z)))
    scale_uv(plate, 1.6, 1.3)
    ctx.part(finish(plate, 0.010 * s, 0, 0), invdist(["Spine", "Chest"]))
    outline = [scap(0.0, j / 16) for j in range(17)] + [scap(i / 8, 1.0) for i in range(1, 8)] + \
              [scap(1.0, 1 - j / 16) for j in range(1, 17)] + [scap(1 - i / 12, 0.0) for i in range(1, 12)]
    ctx.part(rim(f"{T} scapular rim", [radial(p, 0.004 * s) for p in outline], 0.0052 * s, M["trim"], closed=True),
             invdist(["Spine", "Chest"]))
    for k in range(6):
        zz = B.z(1.40 - k * 0.026)
        c = B.torso_point(math.pi, zz, 0.040 * s)
        w = (0.060 - k * 0.006) * s
        ctx.part(blob(f"{T} spine plate {k}", c, (w, 0.020 * s, 0.015 * s), [M["gilt"] if k % 2 == 0 else M["steel"]], 12, 6),
                 invdist(["Spine", "Chest"]))


# ===== 翅膀 =====
def wing_frame(side, cfg):
    rx, ry, rz = cfg["root"]
    root = Vector((side * rx, ry, rz))
    pts, dirs = [root], []
    for L, e, b in cfg["seg"]:
        e, b = math.radians(e), math.radians(b)
        d = Vector((side * math.cos(e) * math.cos(b), -math.sin(b), math.sin(e) * math.cos(b))).normalized()
        dirs.append(d)
        pts.append(pts[-1] + d * L)
    davg = (pts[-1] - pts[0]).normalized()
    n = davg.cross(Z).normalized()                 # 抬翼轴：绕它正转即上抬
    nb = n if n.y < 0 else -n
    return pts, dirs, n, nb


def main_theta(sv, top=50.0):
    """主羽在翼面内相对“下垂方向”朝翼尖扇开的角度：内侧次级飞羽笔直下垂，腕关节以外的初级飞羽逐渐扇开。"""
    return lerp(2.0, top, smoothstep(0.30, 1.0, sv) ** 0.9)


def wing_plane(side, cfg):
    """翼面标架：down（后倾的下垂方向）、out（翼面内朝翼尖的水平方向）、N（翼面法线，指向身后上方）。"""
    tilt, yaw = math.radians(cfg["tilt"]), math.radians(cfg["yaw"])
    down = Vector((0, -math.sin(tilt), -math.cos(tilt)))
    out = Vector((side * math.cos(yaw), -math.sin(yaw), 0))
    out = (out - down * out.dot(down)).normalized()
    N = out.cross(down).normalized()
    return down, out, (N if N.y < 0 else -N)


def build_wing(ctx, B, M, side, label, clear, cfg):
    T = ctx.title
    big = cfg["pre"] == "Wing"
    kk = cfg["k"]
    pts, dirs, n, nb = wing_frame(side, cfg)
    nseg = len(cfg["seg"])
    bones = [f"{cfg['pre']}{label}.{j}" for j in range(1, nseg + 1)]
    lens = [L for L, _, _ in cfg["seg"]]
    cum = [0.0]
    for L in lens:
        cum.append(cum[-1] + L)
    total = cum[-1]
    down0, out0, N0 = wing_plane(side, cfg)
    r0_, r1_ = cfg["r"]
    radius = lambda t: lerp(r0_, r1_, t)       # noqa: E731
    tag = "" if big else "lo "
    # 翼骨：枪铁翼臂 + 暗钢前缘护刃（金边）+ 暗金液压杆 + 余烬嵌线 + 金箍 / 关节球 + 发光关节环
    for j in range(nseg):
        a, b = pts[j], pts[j + 1]
        r0, r1 = radius(j / nseg), radius((j + 1) / nseg)
        d = dirs[j]
        up = d.cross(nb).normalized()
        up = up if up.z > 0 else -up
        seg = (b - a).length
        ctx.attach(sweep(f"{T} wing arm {tag}{label}{j}", [a - d * 0.05, b], [r0, r1], [M["slate"]], n=12, per=1,
                         tile=0.7), bones[j])
        gw = (0.30 - 0.05 * j) * kk
        wfn = lambda t: max(0.25, math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.5)   # noqa: E731
        go = a + up * r0 * 0.55 - nb * 0.01
        ctx.attach(ridge_blade(f"{T} wing guard {tag}{label}{j}", seg * 1.04, gw, 0.05 * kk, [M["steel"]], go, d, up,
                               width=wfn, n=8), bones[j])
        gedge = [go + d * (t * seg * 1.04) + up * (0.5 * gw * wfn(t) + 0.012 * kk) for t in [0.06 + i / 7 * 0.88
                                                                                     for i in range(8)]]
        ctx.attach(rim(f"{T} wing guard edge {tag}{label}{j}", gedge, 0.016 * kk, M["trim"]), bones[j])
        # 液压杆：翼臂下侧两根平行金管
        for o in (-1, 1):
            off = (-up * 0.8 + nb * 0.6 * o).normalized() * (lerp(r0, r1, 0.5) + 0.03 * kk)
            ctx.attach(tube(f"{T} wing piston {tag}{label}{j}{o}", [a.lerp(b, 0.12) + off, a.lerp(b, 0.88) + off],
                            [0.020 * kk, 0.016 * kk], [M["gilt"]], n=6, per=1), bones[j])
        line = [a.lerp(b, t) - nb * (lerp(r0, r1, t) + 0.012) for t in (0.08, 0.35, 0.65, 0.92)]
        ctx.attach(tube(f"{T} wing inlay {tag}{label}{j}", line, [0.014 * kk] * 4, [M["inlay"]], n=6, per=2), bones[j])
        ctx.attach(rim(f"{T} wing band {tag}{label}{j}", ring_around(a, b, 0.88, lerp(r0, r1, 0.88) + 0.012, 14),
                       0.018 * kk, M["trim"], closed=True), bones[j])
        if j > 0:
            ctx.attach(ellipsoid(f"{T} wing knuckle {tag}{label}{j}", a, (r0 * 1.35,) * 3, [M["gilt"]], 12, 8), bones[j])
            ctx.attach(rim(f"{T} wing joint glow {tag}{label}{j}", ring_around(a - d * r0 * 0.4, a + d * r0 * 0.4, 0.5,
                                                                             r0 * 1.42, 14),
                           0.028 * kk, M["glow2"], closed=True), bones[j])
            ctx.attach(small_gem(f"{T} wing knuckle gem {tag}{label}{j}", a - nb * r0 * 1.3, 0.050 * kk, M["glow2"],
                                 (1, 1, 1)), bones[j])
        for t in (0.4, 0.8):
            if j < 2:
                clear.point(bones[j], a.lerp(b, t), f"wing arm {tag}{label}{j}", "wing")
    up2 = dirs[1].cross(nb).normalized()
    up2 = up2 if up2.z > 0 else -up2
    if big:
        ctx.attach(spike(f"{T} wing claw {label}", pts[2], pts[2] + (dirs[1] * 0.35 + up2 * 0.65 - nb * 0.45).normalized() * 0.70,
                         0.085, [M["gilt"]], sides=6, bend=0.05, up=tuple(up2)), bones[2])
    ctx.attach(spike(f"{T} wing tip {tag}{label}", pts[-1] - dirs[-1] * 0.05, pts[-1] + dirs[-1] * 0.75 * kk,
                     0.070 * kk, [M["gilt"]], sides=6), bones[-1])

    def station(sv):
        dist = sv * total
        j = min(nseg - 1, max(k for k in range(nseg) if dist >= cum[k] - 1e-9))
        anchor = pts[j].lerp(pts[j + 1], min(1.0, (dist - cum[j]) / lens[j]))
        return anchor, j

    def feather(name, sv, th_deg, L, W, lift, mat, edge=False, bone=None, depth=0.045, sweep_=0.06, wfn=plume_width,
                nrow=6, bend=0.025):
        """刃羽都落在同一张后倾翼面里：th=0 笔直下垂，th 增大在翼面内朝翼尖扇开；宽度方向指向扇开方向（前缘）。
        edge=True 时沿前缘加一道金色滚边。"""
        anchor, j = station(sv)
        th = math.radians(th_deg)
        bd = down0 * math.cos(th) + out0 * math.sin(th)
        ya = -down0 * math.sin(th) + out0 * math.cos(th)
        origin = anchor + N0 * lift - bd * 0.10 * kk
        fe = ridge_blade(name, L, W, depth * kk, [mat], origin, bd, ya, width=wfn, n=nrow, bend=bend, sweep=sweep_,
                         lite=True)
        ctx.attach(fe, bone or bones[j])
        if edge:
            pts_e = [origin + bd * (t * L) + ya * (0.5 * W * wfn(t) + sweep_ * L * t * t + 0.008 * kk)
                     for t in (0.16, 0.42, 0.68, 0.90)]
            ctx.attach(rim(f"{name} edge", pts_e, 0.014 * kk, M["trim"]), bone or bones[j])
        return origin, bd, ya, j
    # 飞羽：内侧次级飞羽笔直下垂、外侧初级飞羽扇开，由内向外逐片向后叠层；每片都有金色前缘
    ns, npr = cfg["sec"], cfg["prim"]
    flight = [(lerp(0.03, 0.44, i / (ns - 1)), "sec") for i in range(ns)] + \
             [(lerp(0.46, 1.0, i / (npr - 1)), "prim") for i in range(npr)]
    for i, (sv, kind) in enumerate(flight):
        if kind == "sec":
            L = (2.15 + 0.60 * smoothstep(0.0, 0.44, sv)) * kk
            W = 0.46 * kk
        else:
            L = (3.00 - 0.95 * smoothstep(0.62, 1.0, sv)) * kk * (1.06 if i == len(flight) - 1 else 1.0)
            W = 0.46 * kk
        o, bd, ya, j = feather(f"{T} {kind} {tag}{label}{i}", sv, main_theta(sv, 54 if big else 40), L, W,
                               (0.03 + i * 0.013) * kk, M["feather"], edge=True)
        if sv < 0.40:
            for fr in (0.5, 1.0):
                clear.point(bones[j], o + bd * L * fr, f"{kind} {tag}{label}{i}", "feather")
    # 衬羽：飞羽缝隙里的一排炭灰短羽（比飞羽短、略靠后），让翼面成片而不是一排长矛
    nu_ = cfg["under"]
    for i in range(nu_):
        sv = lerp(0.06, 0.98, (i + 0.5) / nu_)
        feather(f"{T} under {tag}{label}{i}", sv, main_theta(sv, 54 if big else 40) + 3.0, lerp(1.9, 2.5, 1 - sv) * kk,
                0.50 * kk, (0.20 + i * 0.006) * kk, M["plume"])
    # 背侧覆羽（后视图压住飞羽根部）
    for i in range(cfg["rear"]):
        sv = lerp(0.04, 0.80, i / (cfg["rear"] - 1))
        feather(f"{T} rear covert {tag}{label}{i}", sv, main_theta(sv, 44), lerp(1.00, 1.50, sv) * kk, 0.42 * kk,
                (0.34 + i * 0.008) * kk, M["dorsal"], nrow=6)
    # 大覆羽：前侧一排炭黑宽羽，金色前缘
    nc = cfg["cov"]
    for i in range(nc):
        sv = lerp(0.02, 0.86, i / (nc - 1))
        L = lerp(1.95, 1.50, sv) * kk
        o, bd, ya, j = feather(f"{T} covert {tag}{label}{i}", sv, main_theta(sv, 46), L, 0.46 * kk,
                               (-0.050 - i * 0.010) * kk, M["plume"], edge=True)
        if sv < 0.4:
            clear.point(bones[j], o + bd * L, f"covert {tag}{label}{i}", "feather")
    # 中覆羽：金边金脊的暗钢羽甲
    nm = cfg["mid"]
    for i in range(nm):
        sv = lerp(0.02, 0.80, i / (nm - 1))
        feather(f"{T} median covert {tag}{label}{i}", sv, main_theta(sv, 42), lerp(1.25, 0.95, sv) * kk, 0.42 * kk,
                (-0.20 - i * 0.007) * kk, M["petal"], depth=0.05, sweep_=0.03, nrow=8)
    # 小覆羽：贴着翼臂的鎏金甲鳞
    nsc = cfg["scale"]
    for i in range(nsc):
        sv = lerp(0.02, 0.72, i / (nsc - 1))
        feather(f"{T} scale {tag}{label}{i}", sv, main_theta(sv, 38), lerp(0.62, 0.50, sv) * kk, 0.36 * kk,
                (-0.36 - i * 0.006) * kk, M["petal"], depth=0.055, sweep_=0.02, nrow=6)
    darts, flames = [], []
    if not big:
        return {"cfg": cfg, "side": side, "label": label, "pts": pts, "dirs": dirs, "n": n, "nb": nb, "bones": bones,
                "darts": darts, "flames": flames}
    # 可发射的羽刃（Dart 骨）：发光中脊的刃羽，夹在覆羽与飞羽之间
    for k, sv in enumerate((0.40, 0.58, 0.76)):
        anchor, j = station(sv)
        name = f"Dart{label}{k}"
        L = 2.40
        o, bd, ya, _ = feather(f"{T} dart {label}{k}", sv, main_theta(sv, 54), L, 0.38, -0.022 * kk, M["feather"], bone=name,
                               depth=0.06, sweep_=0.02)
        nrm = bd.cross(ya).normalized()
        for sgn in (1, -1):
            spine = [o + bd * (t * L) + nrm * sgn * (0.5 * 0.06 * kk * min(1.0, plume_width(t) / 0.22) ** 0.7 + 0.006)
                     for t in (0.08, 0.35, 0.62, 0.86)]
            ctx.attach(tube(f"{T} dart spine {label}{k}{sgn}", spine, [0.016, 0.016, 0.013, 0.007], [M["glow"]], n=3,
                            per=2), name)
        darts.append({"name": name, "parent": bones[j], "head": o.copy(), "tail": o + bd * L, "k": k,
                      "dir": Vector((side * (0.20 + 0.18 * k), 1.0, -0.20)).normalized()})
    # 翼关节火舌（WFlare 骨，待机时小、Enrage 时燃起）
    for j in (1, 2, 3, 4):
        jb = min(j, 3)
        up = dirs[jb].cross(nb).normalized()
        up = up if up.z > 0 else -up
        base = pts[j] + up * radius(j / 4) * 0.8
        fd = (Vector((0, -0.25, 1.0)) + up * 0.3).normalized()
        name = f"WFlare{label}{j}"
        hh, ww = (1.60, 0.30) if j == 4 else (1.05, 0.24)
        for o in fire(f"{T} wing {label}{j}", base, fd, hh, ww, M, n=3, seed=j * 1.7 + side):
            ctx.attach(o, name)
        flames.append((name, bones[jb], base, base + fd * 0.4))
    return {"cfg": cfg, "side": side, "label": label, "pts": pts, "dirs": dirs, "n": n, "nb": nb, "bones": bones,
            "darts": darts, "flames": flames}


# ===== 燃烧光环（BOSS_7_HALO 自转件：金环 + 枪铁符文带 + 发光符文；另挂十一条火舌） =====
def halo_ring(T, M, at, R0, scale, n_runes, name, both=None, seg=48):
    """光环本体（终末之剑的日轮护手、肩甲日轮徽复用同一母题）：外金环 + 内细环 + 枪铁符文带 + 发光符文 + 余烬珠。
    at(角度, 半径, 法向偏移) 给出环面上的点；seg 为外环取点数（小件用更少的点）。"""
    k = scale
    s_in = max(16, int(seg * 5 / 6))
    objs = [tube(f"{name} rim", [at(i / seg * TAU, R0) for i in range(seg)], [0.034 * k] * seg, [M["gilt"]], n=6 if seg >= 40 else 5,
                 closed=True, per=1),
            tube(f"{name} inner", [at(i / s_in * TAU, R0 * 0.76) for i in range(s_in)], [0.018 * k] * s_in, [M["trim"]],
                 n=5 if seg >= 40 else 4, closed=True, per=1)]
    bnd = surface(f"{name} band", lambda u, v: at(u * TAU, lerp(R0 * 0.963, R0 * 0.78, v)), max(24, int(seg * 1.0)), 3, [M["slate"]],
                  closed_u=True, uvfn=lambda u, v: (u * 6, v * 0.25))
    objs.append(finish(bnd, 0.016 * k, 0, 0))
    # 发光符文：一竖 + 一对 V 形短划，贴在符文带正面（两面都贴，护手从两侧都看得到）
    for k2 in range(n_runes):
        a = (k2 + 0.5) / n_runes * TAU
        da = 0.05 * 20 / n_runes
        for fs in ((1,) if (scale >= 1 if both is None else not both) else (1, -1)):
            dn = 0.012 * k * fs
            strokes = [[at(a, R0 * 0.814, dn), at(a, R0 * 0.929, dn)],
                       [at(a - da, R0 * 0.917, dn), at(a, R0 * 0.868, dn)],
                       [at(a + da, R0 * 0.917, dn), at(a, R0 * 0.868, dn)] if k2 % 2 else
                       [at(a + da, R0 * 0.841, dn), at(a + da, R0 * 0.902, dn)]]
            for i, st in enumerate(strokes):
                objs.append(rim(f"{name} rune {k2}{i}{fs}", st, 0.0085 * k, M["glow"]))
    for k2 in range(4):
        a = k2 / 4 * TAU + math.pi / 4
        objs.append(ellipsoid(f"{name} ember {k2}", at(a, R0, 0.03 * k), (0.055 * k, 0.030 * k, 0.055 * k),
                              [M["glow"]], 6, 4))
    return objs


def build_halo(ctx, M):
    T = ctx.title
    au, av = Vector((1, 0, 0)), HU

    def at(a, r, dn=0.0):
        return HC + au * (math.sin(a) * r) + av * (math.cos(a) * r) + HN * dn
    parts = halo_ring(T, M, at, HALO_R, 1.05, 16, f"{T} halo", seg=40)
    # 火舌之间的金色日芒：细长的放射金刺，长短相间；顶部一枚最长
    for k in range(16):
        deg = -155 + k * (310 / 15)
        a = math.radians(deg)
        L = 0.78 if k % 2 else 0.50
        if abs(deg) < 12:
            L = 1.10
        parts.append(spike(f"{T} halo ray {k}", at(a, HALO_R + 0.04), at(a, HALO_R + 0.04 + L), 0.07, [M["gilt"]],
                           sides=4, fx=1.0, fy=0.40, up=tuple(HN)))
    # 环面上的菱形金钉：把符文带之外的金环分成二十四格
    for k in range(12):
        a = (k + 0.5) / 12 * TAU
        parts.append(ellipsoid(f"{T} halo stud {k}", at(a, HALO_R, 0.0), (0.050, 0.034, 0.050), [M["gilt"]], 6, 3))
    # 圣光日轮：光环背后的半透明放射光盘（RGBA 贴图、双面 BLEND），随光环一起自转
    # （join 以第一个对象为主：光盘带 UV，必须排第一，否则合并后的贴图坐标全丢）
    parts.insert(0, aura_disc(f"{T} halo aura", HC - HN * 0.10, au, HU, HALO_R * 1.78, [M["aura"]], nu=48, nv=3))
    halo = join(parts, f"{ctx.ID}_HALO", HC)
    ctx.attach(halo, "Halo", keep=True)
    flares = []
    for k, (deg, L) in enumerate(FLARES):
        a = math.radians(deg)
        radial_d = (au * math.sin(a) + av * math.cos(a)).normalized()
        d = (radial_d + Vector((0, 0, 0.55))).normalized()
        base = at(a, HALO_R + 0.01)
        for o in fire(f"{T} halo {k}", base - d * 0.05, d, L * 1.35, 0.19 if k < 3 else 0.15, M, n=3, seed=k * 1.3):
            ctx.attach(o, f"Flare{k}")
        flares.append((base, d, L))
    return flares


# ===== 终末之剑（局部坐标：原点为剑柄中心，+Y 指向剑尖，X 为刃宽，±Z 为刃面） =====
def sword_width(t):
    w = (1 - 0.12 * t) * (1 - smoothstep(0.80, 1.0, t) ** 1.1)
    if 0.10 < t < 0.34:
        w -= 0.14 * max(0.0, math.sin((t - 0.10) / 0.24 * math.pi * 4)) ** 6
    return max(0.0, w)


def build_sword(ctx, M):
    """终末之剑（第三轮）：长柄双手剑，剑首四爪托宝石；翼形三叠护手 + 光环母题的日轮护手（金环符文带 + 十六道金芒）
    + 剑格两面核心宝石；刃身熔裂暗钢 + 双面发光血槽 + 沿血槽的符文菱宝石 + 刃口发光线，
    刃口两侧伸出的半透明火舌（外焰 / 内焰两层 RGBA 薄片，alphaMode=BLEND）。"""
    T = ctx.title
    gr = GRIP_R * 2.6 * HS
    gy = 0.58                                       # 护手高度
    objs = [sweep(f"{T} sword grip", [(0, -0.52, 0), (0, 0.50, 0)], [gr, gr], [M["steel"]], n=12, per=1, tile=0.9)]    # 第四轮：剑柄不再用细密线纹（读成螺纹 / 弹簧），改嵌金卷草大纹样
    for i in range(4):
        y = -0.40 + i * 0.30
        objs.append(rim(f"{T} sword grip band {i}", ring_around((0, y - 0.01, 0), (0, y + 0.01, 0), 0.5, gr + 0.008, 14),
                        0.013, M["trim"], closed=True))
    # 剑首：金球 + 四爪托住余烬宝石 + 一圈金环
    objs.append(blob(f"{T} sword pommel", (0, -0.66, 0), (0.15, 0.16, 0.15), [M["gilt"]], 14, 8))
    objs.append(small_gem(f"{T} sword pommel gem", (0, -0.70, 0), 0.10, M["glow"], (0.8, 0.8, 1.35)))
    objs.append(rim(f"{T} sword pommel ring", [Vector((math.sin(t) * 0.17, -0.66, math.cos(t) * 0.17))
                                               for t in [i / 24 * TAU for i in range(24)]], 0.014, M["trim"],
                    closed=True))
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        o = Vector((math.cos(a) * 0.12, -0.68, math.sin(a) * 0.12))
        objs.append(spike(f"{T} sword pommel claw {k}", o, o + Vector((math.cos(a) * 0.07, -0.20, math.sin(a) * 0.07)),
                          0.032, [M["gilt"]], sides=4))
    objs.append(blob(f"{T} sword guard", (0, gy, 0), (0.34, 0.13, 0.17), [M["gilt"]], 16, 8))
    objs.append(rim(f"{T} sword guard ring", [Vector((math.sin(t) * 0.36, gy, math.cos(t) * 0.19))
                                              for t in [i / 28 * TAU for i in range(28)]], 0.013, M["trim"],
                    closed=True))
    # 剑格两面的核心宝石（金托 + 余烬宝石）
    for sz in (1, -1):
        c = Vector((0, gy + 0.03, sz * 0.15))
        objs.append(tube(f"{T} sword core setting {sz}", [c + Vector((math.sin(t) * 0.11, math.cos(t) * 0.11, 0))
                                                          for t in [i / 20 * TAU for i in range(20)]],
                         [0.020] * 20, [M["gilt"]], n=6, closed=True, per=1))
        objs.append(gem(f"{T} sword core gem {sz}", c + Vector((0, 0, sz * 0.012)), 0.095, M["glow"], (1.0, 1.2, 0.55)))
    # 翼形护手：每侧三叠金 / 暗钢刃羽，自剑格向外上扬，最大一枚带金边
    for sd in (-1, 1):
        for k, (L, W, ang, mat) in enumerate(((1.30, 0.26, 0.30, "gilt"), (1.00, 0.21, 0.02, "steel"),
                                              (0.72, 0.17, -0.30, "gilt"))):
            d = Vector((sd * math.cos(ang), math.sin(ang), 0)).normalized()
            ya = Vector((0, 1, 0)) - d * d.y
            ya.normalize()
            origin = Vector((sd * 0.18, gy - 0.02 * k, 0.0))
            objs.append(ridge_blade(f"{T} sword quillon {sd}{k}", L, W, 0.07, [M[mat]], origin, d, ya, n=9,
                                    sweep=0.16 - 0.10 * k))
            if k == 0:
                edge = [origin + d * (t * L) + ya * (0.5 * W * feather_width(t) + 0.16 * L * t * t + 0.008)
                        for t in [0.10 + i / 8 * 0.8 for i in range(9)]]
                objs.append(rim(f"{T} sword quillon edge {sd}", edge, 0.014, M["trim"]))
    # 日轮护手：光环母题的光环套在刃根，外缘一圈金芒与火舌
    rc, R0 = Vector((0, gy + 0.34, 0)), 0.62

    def at(a, r, dn=0.0):
        return rc + Vector((math.sin(a) * r, math.cos(a) * r, dn))
    objs += halo_ring(T, M, at, R0, 0.78, 14, f"{T} sword sun", seg=36)
    for k in range(20):
        a = (k + 0.5) / 20 * TAU
        if abs(math.cos(a)) > 0.94:
            continue
        L = 0.22 if k % 2 == 0 else 0.13
        objs.append(spike(f"{T} sword sun ray {k}", at(a, R0 + 0.02), at(a, R0 + 0.02 + L), 0.036, [M["gilt"]],
                          sides=4, fx=1.0, fy=0.45, up=(0, 0, 1)))
    for k, deg in enumerate((-62, -32, 32, 62, -122, 122)):
        a = math.radians(deg)
        d = Vector((math.sin(a), math.cos(a), 0))
        objs += fire(f"{T} sword sun {k}", at(a, R0 + 0.03), d, 0.50, 0.11, M, n=3, seed=k * 1.9)
    objs.append(blob(f"{T} sword ricasso", (0, gy + 0.14, 0), (0.36, 0.12, 0.07), [M["gilt"]], 16, 8))
    y0 = BLADE_0
    objs.append(ridge_blade(f"{T} sword blade", BLADE_L, BLADE_W, 0.095, [M["blade"]], Vector((0, y0, 0)),
                            Vector((0, 1, 0)), Vector((1, 0, 0)), width=sword_width, edge=0.16, n=48, smooth_angle=5))
    # 双面血槽发光线 + 沿线的符文菱宝石
    for sz in (1, -1):
        line = []
        for i in range(14):
            t = 0.05 + i / 13 * 0.78
            hc = 0.5 * 0.095 * min(1.0, sword_width(t) / 0.22) ** 0.7
            line.append(Vector((0, y0 + t * BLADE_L, sz * (hc + 0.005))))
        objs.append(tube(f"{T} sword fuller {sz}", line, [0.026] * 13 + [0.006], [M["glow"]], n=6, per=2))
        for t in (0.24, 0.46, 0.68):
            hc = 0.5 * 0.095 * min(1.0, sword_width(t) / 0.22) ** 0.7
            objs.append(small_gem(f"{T} sword rune {sz}{t}", Vector((0, y0 + t * BLADE_L, sz * (hc + 0.012))), 0.045,
                                  M["glow"], (1.2, 1.7, 0.5)))
    # 燃烧刃口：两侧刃口一道发光线 + 刃口伸出的半透明火舌（朝剑格方向倾斜）
    for sd in (-1, 1):
        edge = [Vector((sd * (0.5 * BLADE_W * sword_width(t) + 0.004), y0 + t * BLADE_L, 0))
                for t in [0.03 + i / 21 * 0.95 for i in range(22)]]
        objs.append(tube(f"{T} sword edge glow {sd}", edge, [0.020] * 21 + [0.004], [M["glow"]], n=4, per=1))
        for k, t in enumerate((0.18, 0.33, 0.48, 0.63, 0.78)):
            x = sd * (0.5 * BLADE_W * sword_width(t) + 0.01)
            d = Vector((sd * 0.80, -0.50 - 0.05 * (k % 2), 0)).normalized()
            objs += fire(f"{T} sword blaze {sd}{k}", Vector((x, y0 + t * BLADE_L, 0)), d, 0.95 + 0.35 * (k % 3) / 2,
                         0.15, M, n=3, seed=k * 1.37 + sd, lean=0.25 * sd)
    m = Matrix.Translation(SWORD_GRIP) @ frame_from(U0, (0, 1, 0)).to_4x4()
    for o in objs:
        transform(o, m)
        ctx.attach(o, "Sword")


# ===== 余烬碎片与飘落的灰羽（刚性挂骨，扁平小件） =====
def build_embers(ctx, M):
    """第四轮：余烬碎片 34→14 片、灰羽 16→7 片，只散落在翅膀后缘下方与下摆周围（四个主发光区之外不再到处飘）；
    挂 Hover 骨随身浮动，躲开翅膀与躯体 / 长裙占据的空间。"""
    T = ctx.title
    rnd = random.Random(11)

    def spot(zone):
        while True:
            if zone == "wing":                         # 翅膀后缘下方：左右各半
                sx = rnd.choice((-1, 1))
                x = sx * rnd.uniform(3.0, 6.5)
                zmax = 1.6 + 1.4 * smoothstep(3.0, 5.0, abs(x))
                return Vector((x, rnd.uniform(-3.8, -0.3), rnd.uniform(0.8, zmax)))
            ang = rnd.uniform(0, TAU)                  # 下摆周围
            r = rnd.uniform(3.0, 3.9)
            p = Vector((math.sin(ang) * r, math.cos(ang) * r * 0.85, rnd.uniform(0.3, 2.0)))
            if p.y < -0.5 and abs(p.x) < 2.2:
                continue                               # 避开身后的飘带
            return p
    for i in range(14):
        ctx.attach(shard(f"{T} ember shard {i}", spot("wing" if i < 8 else "hem"), rnd.uniform(0.06, 0.12), [M["ember"]],
                         seed=i * 1.7), "Hover")
    for i in range(7):
        p = spot("wing" if i < 4 else "hem")
        d = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), -1.0)).normalized()
        ya = d.orthogonal().normalized()
        ctx.attach(ridge_blade(f"{T} ash feather {i}", rnd.uniform(0.50, 0.85), 0.16, 0.018, [M["plume"]], p, d, ya,
                               n=5, sweep=0.06, width=plume_width, lite=True), "Hover")


# ===== 布料与裙甲 =====
def cloth(B):
    """内裙（整圈余烬红）→ 长袍左右两片（前后开衩、撕裂尖角下摆）→ 分片裙甲骨链（无褶）→ 前垂饰。
    第三轮：整体外扩成喇叭形钟裙（腰窄、下摆宽），与 3.7 m 肩宽、14 m 翼展协调。"""
    zt = B.z(1.258)
    under = Wrap("Under", "Pelvis", -math.pi + 0.004, math.pi - 0.004, top=zt, bottom=1.10,
                 r_top=(0.50, 0.54), r_bot=(1.62, 1.50), K=8, joints=J3, cy=0.0, flow=0.10, flare_exp=1.45,
                 folds=(12.0, 0.012, 0.060), seed=1.3, tails=16, tail_len=(0.20, 0.12), curl=(0.04, 0.015))
    kw = dict(top=zt, bottom=1.38, r_top=(0.55, 0.59), r_bot=(2.00, 1.84), K=5, joints=J5, cy=-0.02, flow=0.24,
              flare_exp=1.45, folds=(13.0, 0.018, 0.10), tails=7, tail_len=(0.66, 0.38), curl=(0.07, 0.025))
    robe_r = Wrap("RobeR", "Pelvis", 0.46, math.pi - 0.26, seed=0.9, **kw)
    robe_l = Wrap("RobeL", "Pelvis", math.pi + 0.26, TAU - 0.46, seed=2.3, **kw)
    tasset = Wrap("Tasset", "Pelvis", 0.40, TAU - 0.40, top=B.z(1.262), bottom=2.45, r_top=(0.61, 0.64),
                  r_bot=(1.46, 1.36), K=12, joints=(0, 0.5, 1.0), cy=-0.01, flow=0.03, flare_exp=1.4, widen=0.0,
                  folds=(0.0, 0.0, 0.0), seed=0.0, top_win=0.20)

    def extent(z):
        best = 0.0
        for i in range(9):
            u = lerp(0.46, 0.54, i / 8)
            top, bot = under.top(u), under.bottom(u)
            v = clamp((top - z) / max(1e-4, top - bot))
            best = max(best, under.point(u, v).y)
        return best
    ft, fb = B.z(1.245), 1.05
    tabard = Panel("Tabard", "Pelvis", ft, fb, [(0, 0.78), (0.5, 0.74), (1.0, 0.62)],
                   lambda v: extent(lerp(ft, fb, v)) + 0.07, side=1, K=1, joints=J5, curve=0.5, point=0.14)
    banners = []
    for k, (a_c, wid, seed) in enumerate(((0.80, 0.30, 0.4), (-0.80, 0.30, 1.1), (1.60, 0.38, 2.2), (-1.60, 0.38, 3.0),
                                          (2.45, 0.34, 4.1), (-2.45, 0.34, 5.3))):
        a0, a1 = (a_c - wid / 2) % TAU, (a_c + wid / 2) % TAU
        if a1 < a0:
            a1 += TAU
        banners.append(Wrap(f"Ban{k}", "Pelvis", a0, a1, top=zt, bottom=0.86, r_top=(0.69, 0.73), r_bot=(2.64, 2.50),
                            K=1, joints=(0, 0.34, 0.68, 1.0), cy=-0.02, flow=0.20, flare_exp=1.45, widen=0.0,
                            folds=(3.0, 0.012, 0.045), seed=seed, tails=1, tail_len=(0.62, 0.0), curl=(0.0, 0.0),
                            top_win=0.16))
    return under, robe_r, robe_l, tasset, tabard, banners


def cloth_hem(ctx, g, name, mat, r, n, spec_edges=None, lift=0.006):
    """布料下摆 / 开襟的四棱滚边（Wrap.build 自带的下摆滚边按 nu×3 取点、六棱，太贵）。"""
    pts = [radial(g.point(i / (n - 1), 1.0), lift, g.cy) for i in range(n)]
    ctx.part(rim(f"{name} hem", pts, r, mat), ("garment", g))
    if spec_edges:
        for u in (0.0, 1.0):
            e = [radial(g.point(u, j / 20), lift, g.cy) for j in range(21)]
            ctx.part(rim(f"{name} edge {u}", e, spec_edges[1], spec_edges[0]), ("garment", g))


def build_tassets(ctx, M, g):
    """分片装甲裙甲：沿 Tasset 布料面排布的尖底弧形甲片，上排压下排、错位半片；
    每片暗钢雕花 + 左右 / 下缘金边 + 顶部一排铆钉 + 中线余烬嵌线，按 Tasset 骨链蒙皮（随长袍摆动）。"""
    T = ctx.title
    spec = ("garment", g)
    rows = ((12, 0.0, 1.0, 0.0, 0.40, 0.070, 0.11), (11, 1 / 24, 23 / 24, 0.24, 0.68, 0.045, 0.13),
            (10, 1 / 20, 19 / 20, 0.52, 0.94, 0.020, 0.16))
    for row, (n, u0, u1, v0, v1, lift, tipv) in enumerate(rows):
        du = (u1 - u0) / n
        for i in range(n):
            ua, ub = u0 + i * du - du * 0.05, u0 + (i + 1) * du + du * 0.05

            def P(x, y, ua=ua, ub=ub, v0=v0, v1=v1, lift=lift, tipv=tipv):
                u = lerp(ua, ub, x)
                vb = v1 + tipv * (1 - abs(2 * x - 1)) ** 1.5
                p = g.point(u, lerp(v0, vb, y))
                # 甲片中线起一道纵脊，左右缘微微外翻
                x2 = 2 * x - 1
                return radial(p, lift + 0.030 * math.exp(-(x2 / 0.18) ** 2) + 0.022 * x2 * x2 + 0.020 * y, g.cy)
            name = f"{T} tasset {row}{i}"
            pl = surface(name, P, 9, 6, [M["steel"]], uvfn=lambda x, y: (x * 0.6, y * 0.8))
            orient(pl, lambda c: Vector((0, g.cy, c.z)))
            ctx.part(finish(pl, 0.024, 1, 0), spec)
            out = 0.030
            left = [radial(P(0.0, j / 2), out, g.cy) for j in range(3)]
            right = [radial(P(1.0, j / 2), out, g.cy) for j in range(3)]
            bottom = [radial(P(k / 4, 1.0), out, g.cy) for k in range(5)]
            ctx.part(rim(f"{name} rim", left + bottom[1:-1] + right[::-1], 0.017, M["trim"]), spec)
            if row == 0:                                   # 铆钉只留最上一排（下两排的顶部被上排压住）
                c = radial(P(0.5, 0.07), out + 0.004, g.cy)
                ctx.part(ellipsoid(f"{name} rivet", c, (0.026,) * 3, [M["gilt"]], 6, 4), spec)
            line = [radial(P(0.5, y), out + 0.012, g.cy) for y in (0.40, 0.70, 0.97)]
            ctx.part(tube(f"{name} inlay", line, [0.011, 0.010, 0.005], [M["inlay"]], n=4, per=1), spec)
            if row == 2:
                ctx.part(ellipsoid(f"{name} gem", radial(P(0.5, 0.27), out + 0.016, g.cy), (0.030, 0.022, 0.040),
                                   [M["glow2"]], 6, 4), spec)


# ===== 构建 =====
def build(ctx):
    skin_attach(ctx)          # 第五轮：挂骨件改刚性蒙皮，按材质合并（BOSS_7_HALO 仍独立）
    M = materials(ctx)
    B = make_body()
    clear = Clearance()
    build_torso(ctx, B, M)
    build_arms(ctx, B, M)
    build_helm(ctx, B, M)
    build_harness(ctx, B, M)
    wings = [build_wing(ctx, B, M, side, label, clear, cfg) for cfg in WINGS for side, label in SIDES]
    flares = build_halo(ctx, M)
    build_sword(ctx, M)
    build_embers(ctx, M)
    under, robe_r, robe_l, tasset, tabard, banners = cloth(B)
    T = ctx.title
    under.build(ctx, [M["under"], M["lining"]], f"{T} underskirt", nu=56, nv=22, thickness=0.015, uv_scale=2.0)
    cloth_hem(ctx, under, f"{T} underskirt", M["hem"], 0.011, 110)
    for g, nm in ((robe_r, "robe R"), (robe_l, "robe L")):
        g.build(ctx, [M["robe"], M["lining"]], f"{T} {nm}", nu=50, nv=30, thickness=0.018, uv_scale=1.2)
        cloth_hem(ctx, g, f"{T} {nm}", M["hem"], 0.014, 70, spec_edges=(M["trim"], 0.013))
    build_tassets(ctx, M, tasset)
    for k, g in enumerate(banners):
        g.build(ctx, [M["tabard"], M["lining"]], f"{T} banner {k}", nu=9, nv=22, thickness=0.014, uv_scale=1.0)
        for u in (0.0, 1.0):
            e = [radial(g.point(u, j / 8), 0.006, g.cy) for j in range(9)]
            ctx.part(rim(f"{T} banner {k} edge {u}", e, 0.011, M["trim"]), ("garment", g))
        cap = [radial(g.point(i / 8, 0.50), 0.010, g.cy) for i in range(9)]
        ctx.part(rim(f"{T} banner {k} band", cap, 0.016, M["trim"]), ("garment", g))
        ctx.part(small_gem(f"{T} banner {k} gem", radial(g.point(0.5, 0.52), 0.030, g.cy), 0.050, M["glow2"], (1, 0.5, 1.2)),
                 ("garment", g))
    tabard.build(ctx, [M["tabard"], M["lining"]], f"{T} tabard", nu=14, nv=32, thickness=0.014)
    tspec = ("garment", tabard)
    for u in (0.0, 1.0):
        pts = [tabard.point(u, j / 26) + Vector((0, 0.004, 0)) for j in range(27)]
        ctx.part(rim(f"{T} tabard edge {u}", pts, 0.013, M["trim"]), tspec)
    ctx.part(rim(f"{T} tabard top", [tabard.point(i / 12, 0.0) + Vector((0, 0.004, 0.003)) for i in range(13)], 0.013,
                 M["trim"]), tspec)
    ctx.part(rim(f"{T} tabard spine", [tabard.point(0.5, j / 24) + Vector((0, 0.005, 0)) for j in range(2, 23)], 0.009,
                 M["inlay"]), tspec)
    # 身体胶囊体（穿插自检；半径按第三轮体型：护臂、巨肩甲、宽胸）
    for side, label in SIDES:
        a = B.arms[label]
        clear.capsule(f"UpperArm.{label}", a["shoulder"], a["elbow"], 0.40, f"upper arm {label}")
        clear.capsule(f"Shoulder.{label}", a["shoulder"] + Vector((0, 0, 0.10)), a["shoulder"] + Vector((side * 0.55, 0, -0.05)),
                      0.95, f"pauldron {label}")
        clear.capsule(f"Forearm.{label}", a["elbow"], a["wrist"], 0.33, f"forearm {label}")
        h = B.hands[label]
        clear.capsule(f"Hand.{label}", h["wrist"], h["knuckle"], 0.30, f"hand {label}")
    clear.capsule("Chest", (-0.45, 0, B.z(1.50)), (0.45, 0, B.z(1.50)), 0.58, "chest")
    clear.capsule("Chest", (0, -0.80, 5.00), (0, -0.80, 6.10), 0.30, "engine")
    clear.capsule("Head", B.head_c - Vector((0, 0, 0.22)), B.head_c + Vector((0, 0, 0.20)), 0.50, "head")
    clear.capsule("Pelvis", (0, 0, B.z(1.29)), (0, 0, B.z(1.00)), 0.60, "waist")
    for z0 in (4.4, 3.6, 2.8, 2.0, 1.4):
        vv = clamp((under.top(0.5) - z0) / (under.top(0.5) - under.bottom(0.5)))
        clear.capsule("Pelvis", (0, 0.0, z0 + 0.3), (0, 0.0, z0 - 0.3), under.point(0.5, vv).y - 0.05, f"robe {z0}",
                      "robe")
    for t in (0.25, 0.5, 0.75, 1.0):
        clear.point("Sword", SWORD_GRIP + U0 * (BLADE_0 + t * BLADE_L), f"blade {t}", "sword")
    clear.point("Sword", SWORD_GRIP - U0 * 0.50, "pommel", "pommel")
    for sd in (-1, 1):
        clear.point("Sword", SWORD_GRIP + U0 * 0.58 + Vector((sd * 1.0, 0, 0.0)), f"quillon {sd}", "sword")
    st = {"B": B, "wings": wings, "flares": flares, "under": under, "robes": (robe_r, robe_l), "tasset": tasset,
          "tabard": tabard, "banners": banners, "clear": clear}
    stats(ctx, GAME_TRIS, LOD_KEEP)
    return st


def rest_pole(B, label):
    a = B.arms[label]
    S, E, W = a["shoulder"], a["elbow"], a["wrist"]
    d = (W - S).normalized()
    p = E - S
    return (p - d * p.dot(d)).normalized()


def skeleton(rig, st):
    B = st["B"]
    add_skeleton(rig, B, fingers=False, legs=False)
    for side, label in SIDES:
        S = B.arms[label]["shoulder"]
        rig.bone(f"Shoulder.{label}", S, S + Vector((side * 0.35, 0.0, 0.30)), "Chest", roll=Y)
    rig.bone("Sword", SWORD_GRIP, SWORD_GRIP - U0 * 0.8, "Hover", roll=Y)
    rig.translate["Sword"] = "_sword"
    rig.bone("Halo", HC, HC + HN * 0.4, "Head", roll=Z)
    rig.translate["Halo"] = "_halo"
    scaled = []
    for k, (base, d, L) in enumerate(st["flares"]):
        rig.bone(f"Flare{k}", base, base + d * max(0.2, L * 0.5), "Halo", roll=HN)
        scaled.append(f"Flare{k}")
    for w in st["wings"]:
        for j in range(len(w["bones"])):
            rig.bone(w["bones"][j], w["pts"][j], w["pts"][j + 1], "Chest" if j == 0 else w["bones"][j - 1], roll=w["n"])
        for name, parent, head, tail in w["flames"]:
            rig.bone(name, head, tail, parent, roll=w["nb"])
            scaled.append(name)
        for d in w["darts"]:
            rig.bone(d["name"], d["head"], d["tail"], d["parent"], roll=w["nb"])
            rig.translate[d["name"]] = "_" + d["name"]
            scaled.append(d["name"])
    for g in (st["under"], *st["robes"], st["tasset"], st["tabard"], *st["banners"]):
        rig.add_garment(g)
    rig.scaled = scaled
    st["grip_off"] = {label: B.hands[label]["f"] * GRIP_A * B.s * HS + B.hands[label]["n"] * GRIP_B * B.s * HS
                      for label in ("L", "R")}
    st["rest_pole"] = {label: rest_pole(B, label) for label in ("L", "R")}


# ===== 动作 =====
BASE_Q = dict(hover=0.0, lean=0.0, arch=0.0, twist=0.0, breath=0.0, head=0.0, look=0.0,
              lift=0.04, sweep=0.0, bend=(0.0, 0.0, 0.0), wtwist=0.0, fold=(0.0, 0.0, 0.0),
              grip=SWORD_GRIP.copy(), pitch=P0, yaw=0.0, roll=0.0,
              flare=0.04, ripple=0.025, back=0.0, side=0.0,
              fire=1.0, wfire=0.60, halo_up=0.0, halo_tilt=0.0)


def grip_hand(rig, st, p, label, gp, u):
    """单手握剑：拳心握点落在 gp、拇指指向剑尖方向 u；先两段 IK 定腕，再转手骨。返回腕部误差（米）。"""
    B = st["B"]
    h = B.hands[label]
    side = -1 if label == "L" else 1
    S = rig.head(p, f"UpperArm.{label}")
    v = gp - S
    f_new = v - u * v.dot(u)
    if f_new.length < 1e-4:
        f_new = Vector((0, 1, 0)) - u * u.y
    f_new.normalize()
    rot = frame_from(f_new, u) @ frame_from(h["f"], h["s"]).transposed()
    wrist = gp - rot @ st["grip_off"][label]
    rig.ik2(p, f"UpperArm.{label}", f"Forearm.{label}", wrist, Vector((side * 0.85, -0.40, -0.35)),
            rest_pole=st["rest_pole"][label])
    rig.aim(p, f"Hand.{label}", f_new, up=u, rest_up=h["s"])
    return (rig.tail(p, f"Forearm.{label}") - wrist).length


def hold_sword(rig, st, p, q):
    Rs = R((X, q["pitch"] - P0), (Z, q["yaw"]))
    u = (Rs @ U0).normalized()
    p["Sword"] = Matrix.Rotation(q["roll"], 3, u) @ Rs
    p["_sword"] = Vector(q["grip"]) - SWORD_GRIP
    G = rig.head(p, "Sword")
    err = max(grip_hand(rig, st, p, "R", G - u * HAND_GAP, u), grip_hand(rig, st, p, "L", G + u * HAND_GAP, u))
    key = st.get("clip", "?")
    errs = st.setdefault("grip_err", {})
    errs[key] = max(errs.get(key, 0.0), err)


def wings_pose(p, st, q):
    """两对翅膀共用一组参数；次级翼按 gain 缩小幅度，并在上抬上叠 lift0 偏置。"""
    for w in st["wings"]:
        side, n, b, cfg = w["side"], w["n"], w["bones"], w["cfg"]
        g = cfg["gain"]
        p[b[0]] = R((w["dirs"][0], side * q["wtwist"] * g), (n, q["lift"] * g + cfg["lift0"]), (Z, side * q["sweep"] * g))
        for j in range(1, len(b)):
            p[b[j]] = R((n, q["bend"][j - 1] * g), (Z, side * q["fold"][j - 1] * g))


def robes_pose(rig, st, p, q, t):
    fl, rp, bk, sd = q["flare"], q["ripple"], q["back"], q["side"]
    flare = lambda k, j: fl + rp * math.sin(t + k * 0.8 + j * 0.9)          # noqa: E731
    side = lambda k, j: sd + 0.6 * rp * math.sin(t + k * 0.9 + j * 0.6)     # noqa: E731
    back = lambda k, j: bk + 0.3 * rp * math.sin(t + k * 0.7 + j * 1.1)     # noqa: E731
    for g in (st["under"], *st["robes"]):
        rig.wind(p, g, back, flare, side)
    for g in st["banners"]:
        rig.wind(p, g, lambda k, j: bk * 1.3 + 0.5 * rp * math.sin(t + g.seed + j * 0.9),
                 lambda k, j: fl * 1.4 + 0.9 * rp * math.sin(t * 1.0 + g.seed * 1.7 + j * 0.8),
                 lambda k, j: sd + 1.2 * rp * math.sin(t + g.seed + j * 0.6))
    # 裙甲是硬甲片：只跟随一半的风压与外掀，不做侧摆
    rig.wind(p, st["tasset"], lambda k, j: bk * 0.6, lambda k, j: fl * 0.5 + 0.3 * rp * math.sin(t + k * 0.8))
    rig.wind(p, st["tabard"], back, lambda k, j: fl * 0.6 + 0.02)


def darts_pose(rig, st, p, state):
    for w in st["wings"]:
        for d in w["darts"]:
            name = d["name"]
            tr, aim, sc = state.get(name, (0.0, 0.0, 1.0)) if state else (0.0, 0.0, 1.0)
            p["_scale"][name] = sc
            if tr <= 0 and aim <= 0:
                p["_" + name] = Vector((0, 0, 0))
                continue
            pd = rig.delta(p, d["parent"], {})
            p["_" + name] = pd.inverted() @ (d["dir"] * tr)
            rig.aim(p, name, d["dir"])
            p[name] = mat_slerp(p[name], aim)


def compose(rig, st, q, t=0.0, darts=None):
    """由参数字典 q 合成整身姿态：躯干 → 双手握剑 IK → 翅膀 → 长袍 → 光环 / 火舌缩放 → 羽刃。"""
    p = {"_hover": q["hover"]}
    lean, arch, tw = q["lean"], q["arch"], q["twist"]
    p["Pelvis"] = R((Z, tw * 0.3), (X, -lean * 0.40 + arch * 0.15))
    p["Spine"] = R((Z, tw * 0.3), (X, -lean * 0.30 + arch * 0.35))
    p["Chest"] = R((Z, tw * 0.4), (X, -lean * 0.30 + arch * 0.50 - q["breath"]))
    p["Neck"] = R((X, lean * 0.45 - arch * 0.35 + q["head"] * 0.4))
    p["Head"] = R((X, lean * 0.45 - arch * 0.35 + q["head"] * 0.6), (Z, q["look"]))
    hold_sword(rig, st, p, q)
    for label in ("L", "R"):
        p[f"Shoulder.{label}"] = mat_slerp(p[f"UpperArm.{label}"], 0.22)
    wings_pose(p, st, q)
    robes_pose(rig, st, p, q, t)
    p["_halo"] = Vector((0, 0, q["halo_up"]))
    p["Halo"] = R((X, q["halo_tilt"]))
    sc = {}
    for k in range(len(st["flares"])):
        sc[f"Flare{k}"] = q["fire"] * (1 + 0.10 * math.sin(3 * t + k * 1.9))
    for w in st["wings"]:
        for i, (name, *_) in enumerate(w["flames"]):
            sc[name] = q["wfire"] * (1 + 0.14 * math.sin(3 * t + i * 2.3 + w["side"]))
    p["_scale"] = sc
    darts_pose(rig, st, p, darts)
    return p


def idle_q(t):
    q = dict(BASE_Q)
    q.update(hover=0.10 * math.sin(t), breath=0.018 * math.sin(t + 1.0), head=0.02 * math.sin(t + 2.0),
             look=0.05 * math.sin(t), lift=0.05 + 0.05 * math.sin(t - 0.4),
             bend=(0.03 * math.sin(t - 0.9), 0.035 * math.sin(t - 1.4), 0.04 * math.sin(t - 1.9)),
             wtwist=0.02 * math.sin(t), grip=SWORD_GRIP + Vector((0, 0, 0.03 * math.sin(t + 0.5))),
             pitch=P0 + 0.025 * math.sin(t + 0.2), yaw=0.03 * math.sin(t + 0.7))
    return q


def move_q(t):
    q = dict(BASE_Q)
    q.update(hover=0.08 - 0.13 * math.sin(t - 0.5), lean=0.22 + 0.02 * math.cos(t), breath=0.015 * math.cos(t),
             head=-0.02, lift=0.12 + 0.30 * math.sin(t), sweep=-0.05 + 0.10 * math.cos(t),
             bend=(0.16 * math.sin(t - 0.7), 0.20 * math.sin(t - 1.3), 0.22 * math.sin(t - 1.9)),
             wtwist=0.10 * math.cos(t), grip=SWORD_GRIP + Vector((0, 0.18, 0.10)), pitch=0.70 + 0.03 * math.sin(t - 0.6),
             flare=0.05, ripple=0.03, back=0.18, fire=1.1, wfire=0.6)
    return q


def G(dx, dy, dz, k=1.15):
    """相对静止握点的位移（旧体型 5.2 m 的位移 × 1.15 放大到 6.0 m 体型）。"""
    return SWORD_GRIP + Vector((dx, dy, dz)) * k


def attack_keys():
    """举剑蓄势（双翼后扬）→ 双翼前扫、劈斩、羽刃出膛（14–16 帧）→ 随势 → 收回待机。"""
    I = idle_q(0)
    K = lambda **kw: {**I, **kw}     # noqa: E731
    return [
        (1, I, "lin"),
        (10, K(hover=0.28, lean=-0.10, arch=0.14, head=0.08, lift=0.36, sweep=-0.40, bend=(0.10, 0.12, 0.10),
               wtwist=-0.10, fold=(-0.05, -0.08, -0.05), grip=G(0.25, 0.23, 0.80), pitch=2.65, yaw=0.30, flare=0.08,
               fire=1.25, wfire=0.7), "io"),
        (15, K(hover=0.05, lean=0.24, arch=-0.04, head=-0.04, lift=0.00, sweep=0.52, bend=(-0.10, -0.14, -0.12),
               wtwist=0.16, fold=(0.08, 0.10, 0.08), grip=G(0.05, 0.35, 0.50), pitch=1.50, yaw=-0.04, flare=0.10,
               back=0.10, fire=1.35, wfire=0.9), "in"),
        (20, K(hover=0.02, lean=0.27, lift=-0.04, sweep=0.60, bend=(-0.12, -0.16, -0.14), wtwist=0.12,
               fold=(0.10, 0.12, 0.10), grip=G(0.00, 0.39, 0.40), pitch=1.36, yaw=-0.08, flare=0.08, back=0.12,
               fire=1.3, wfire=0.85), "out"),
        (26, K(hover=0.06, lean=0.12, lift=0.06, sweep=0.20, grip=G(0.00, 0.21, 0.18), pitch=0.80, fire=1.15,
               wfire=0.6), "io"),
        (33, I, "io"),
    ]


def attack_darts(st, f):
    """羽刃：13.5 / 14.7 / 15.9 帧依次出膛，7 帧飞出 8 m 并缩小隐去，26–32 帧在翼上重新长出。"""
    state = {}
    for w in st["wings"]:
        for d in w["darts"]:
            L0 = 13.5 + d["k"] * 1.2
            if f < L0:
                state[d["name"]] = (0.0, 0.0, 1.0)
                continue
            x = (f - L0) / 7.0
            if x <= 1.0:
                state[d["name"]] = (ease_out(x) * DART_RANGE, min(1.0, (f - L0) / 1.5),
                                    1.0 - 0.999 * smoothstep(0.55, 1.0, x))
            elif f < 26:
                state[d["name"]] = (0.0, 0.0, 0.001)
            else:
                state[d["name"]] = (0.0, 0.0, max(0.001, ease((f - 26) / 6.0)))
    return state


def enrage_keys():
    """收翼蓄力 → 双翼全展（拉直翼弓、翼尖抬平）、光环与翼火爆燃、举剑向天（20–32 帧）→ 末日冲锋起势（40 帧）→ 回到待机。
    16 帧的中间键让剑沿身前的弧线上举（剑首不扫过胸甲）。"""
    I = idle_q(0)
    K = lambda **kw: {**I, **kw}     # noqa: E731
    return [
        (1, I, "lin"),
        (12, K(hover=-0.10, lean=0.26, arch=-0.08, head=-0.12, lift=-0.20, sweep=0.34, bend=(-0.14, -0.18, -0.20),
               fold=(0.22, 0.28, 0.20), wtwist=0.05, grip=G(0.00, -0.10, 0.40), pitch=0.12, flare=0.02, fire=0.55,
               wfire=0.2), "io"),
        (16, K(hover=0.25, lean=0.05, arch=0.10, head=0.10, lift=-0.05, sweep=0.0, bend=(0.10, 0.14, 0.06),
               fold=(0.0, 0.0, 0.0), grip=G(0.00, 0.35, 1.15), pitch=1.75, flare=0.10, fire=1.3, wfire=0.9,
               halo_up=0.12), "io"),
        (20, K(hover=0.55, lean=-0.14, arch=0.26, head=0.26, lift=-0.16, sweep=-0.10, bend=(0.28, 0.40, 0.24),
               fold=(-0.05, -0.06, -0.04), wtwist=-0.04, grip=G(0.00, -0.45, 2.10), pitch=2.95, flare=0.12,
               ripple=0.03, fire=1.9, wfire=1.5, halo_up=0.30), "out"),
        (32, K(hover=0.62, lean=-0.12, arch=0.24, head=0.22, lift=-0.12, sweep=-0.12, bend=(0.30, 0.42, 0.26),
               fold=(-0.05, -0.06, -0.04), grip=G(0.00, -0.43, 2.12), pitch=2.95, flare=0.12, ripple=0.035, fire=2.0,
               wfire=1.6, halo_up=0.32), "lin"),
        (36, K(hover=0.45, lean=0.14, arch=0.08, head=0.02, lift=0.02, sweep=-0.28, bend=(0.16, 0.20, 0.12),
               fold=(-0.12, -0.14, -0.10), grip=G(0.06, 0.37, 1.25), pitch=2.05, flare=0.09, back=0.16, fire=1.8,
               wfire=1.4, halo_up=0.24), "io"),
        (40, K(hover=0.25, lean=0.36, arch=-0.04, head=-0.18, lift=0.20, sweep=-0.46, bend=(0.04, 0.02, 0.0),
               fold=(-0.18, -0.20, -0.14), wtwist=0.08, grip=G(0.12, 0.37, 0.50), pitch=1.42, yaw=-0.05, flare=0.06,
               back=0.30, fire=1.6, wfire=1.2, halo_up=0.15), "io"),
        (49, I, "io"),
    ]


GROUPS = {"feather": ("body",), "wing": ("body",), "sword": ("body", "robe"), "pommel": ("body",)}


def animate(rig, st):
    rec = {}

    def keep(name, fn):
        def g(x):
            st["clip"] = name
            pose = fn(x)
            rec.setdefault(name, []).append(pose)
            return pose
        return g
    loop(rig, "Idle", 72, keep("Idle", lambda t: compose(rig, st, idle_q(t), t)), step=2)
    loop(rig, "Move", 32, keep("Move", lambda t: compose(rig, st, move_q(t), t)), step=1)
    ak = attack_keys()
    sampled(rig, "Attack", 32, keep("Attack", lambda f: compose(rig, st, track(ak, f), TAU * (f - 1) / 32,
                                                                attack_darts(st, f))))
    ek = enrage_keys()
    sampled(rig, "Enrage", 48, keep("Enrage", lambda f: compose(rig, st, track(ek, f), TAU * (f - 1) / 24)))
    seam_check(rig, ["Idle", "Move"])
    for name, poses in rec.items():
        st["clear"].report(rig, name, poses[::2] if len(poses) > 30 else poses, GROUPS)
    print("MOTION CHECK+ grip: max wrist IK error " +
          ", ".join(f"{k} {v * 100:.1f} cm" for k, v in st.get("grip_err", {}).items()))
