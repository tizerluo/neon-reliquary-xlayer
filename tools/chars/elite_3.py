"""帷影处刑者 Veil Executioner（零域军团精英 · 源自类型 3 帷影刺客）。

同一躯体放大 1.3 倍并升格：金面具 + 尖刺光冠、金边尖肩甲、白红胸核，双刃换成新月形长镰（金身 + 白红刃口），
红色长燕尾；Attack 为跃起双镰砸地（游戏里配紫色地面范围圈）。
"""

from chars import _legion, _legion_veil as body

TITLE = "Veil Executioner"
ACCENT = (0.85, 0.58, 1.0)
CLIPS = ("Move", "Attack")
GAME_TRIS = 4500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=True)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
