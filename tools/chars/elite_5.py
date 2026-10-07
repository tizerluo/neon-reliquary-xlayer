"""锁链殉道者 Chain Martyr（零域军团精英 · 源自类型 5 锁链苦修者）。

同一躯体放大 1.3 倍并升格：背上换成燃烧的金栅圣骸笼（白红火芯 + 火舌）、全身金链、尖刺光冠、金刺肩甲；
Attack 为抱臂蓄力 → 双臂猛张、笼火暴燃（五向扇形弹）。
"""

from chars import _legion, _legion_chain as body

TITLE = "Chain Martyr"
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
