"""裂隙头狼 Rift Alpha（零域军团精英 · 源自类型 1 裂隙猎犬）。

同一躯体放大 1.3 倍并升格：镀金下颚、背脊金刃、额前大弯角 + 脑后尖刺冠、金边肩甲、白红胸核、红色破鞍布；
Attack 为低头顶角的直线冲锋。
"""

from chars import _legion, _legion_hound as body

TITLE = "Rift Alpha"
ACCENT = (1.0, 0.45, 0.35)
CLIPS = ("Move", "Attack")
GAME_TRIS = 4500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=True)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
