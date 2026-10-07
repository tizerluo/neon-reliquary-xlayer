"""香炉审判官 Censer Inquisitor（零域军团精英 · 源自类型 4 香炉炮手）。

同一躯体放大 1.3 倍并升格：双肩双香炉炮、金边法衣与肩甲、尖刺光冠、白红胸核；
Attack 为双炮高仰齐射（游戏里配薄荷绿地面范围圈）。
"""

from chars import _legion, _legion_censer as body

TITLE = "Censer Inquisitor"
ACCENT = (0.56, 0.89, 0.69)
CLIPS = ("Move", "Attack")
GAME_TRIS = 4500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=True)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
