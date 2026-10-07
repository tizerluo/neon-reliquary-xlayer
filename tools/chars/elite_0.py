"""仆从百夫长 Thrall Centurion（零域军团精英 · 源自类型 0 空壳仆从）。

同一躯体放大 1.3 倍并升格：镀金鸡冠盔 + 尖刺光冠、加大的枪铁刃（白红刃口）、双肩重甲、破红披风；
Attack 为直线冲锋（蓄势 → 平举刃前刺狂奔 → 收势）。
"""

from chars import _legion, _legion_husk as body

TITLE = "Thrall Centurion"
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
