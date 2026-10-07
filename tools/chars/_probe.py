"""导出结构探针：只含刚性挂骨部件（杂兵实例化方案），验证 GLB 里骨节点与动画是否保留。"""

import math

from mathutils import Vector

from kit.core import ellipsoid, tube
from kit.rig import R, X

TITLE = "Probe"
ACCENT = (1.0, 0.3, 0.3)
CLIPS = ("Move", "Attack")
GAME_TRIS = 2000


def build(ctx):
    ctx.mat("body", "body", (0.2, 0.2, 0.22), metal=0.5, rough=0.4)
    ctx.mat("eye", "eye", (1, 0.2, 0.2), emit=(1, 0.2, 0.2), strength=6)
    ctx.attach(ellipsoid("probe torso", (0, 0, 1.2), (0.25, 0.18, 0.35), [ctx.M["body"]]), "Body")
    ctx.attach(ellipsoid("probe eye", (0, 0.17, 1.4), (0.05, 0.02, 0.02), [ctx.M["eye"]]), "Body")
    ctx.attach(tube("probe arm", [(0.3, 0, 1.4), (0.35, 0.1, 0.9)], [0.06, 0.04], [ctx.M["body"]]), "Arm")
    return {}


def skeleton(rig, st):
    rig.bone("Root", (0, 0, 0), (0, 0, 0.2))
    rig.bone("Body", (0, 0, 0.8), (0, 0, 1.6), "Root")
    rig.bone("Arm", (0.3, 0, 1.4), (0.35, 0.1, 0.9), "Body")


def animate(rig, st):
    rig.loop("Move", 16, lambda t: {"Body": R((X, 0.2 * math.sin(t)))}, step=2)
    rig.keyed("Attack", [(1, {}), (8, {"Arm": R((X, 1.2))}), (16, {})])
