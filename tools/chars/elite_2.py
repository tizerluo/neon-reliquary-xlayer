"""壁垒院长 Bulwark Abbot（零域军团精英 · 源自类型 2 壁垒执事）。

同一躯体放大 1.3 倍并升格：金边塔盾 + 白红圣印、主教冠盔（发光十字）+ 尖刺光冠、肩甲金刺、红色长襟，
钉锤换成弯首权杖；Attack 为举杖蓄势 → 权杖前指（五向扇形弹）。
"""

from chars import _legion, _legion_bulwark as body

TITLE = "Bulwark Abbot"
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
