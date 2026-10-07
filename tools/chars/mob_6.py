"""咒唱司铎 Hex Cantor（零域军团 · 类型 6）：悬浮长袍祭司机，高杖吊紫光提灯（#d995ff，与弹幕同色）的远程法术杂兵。

Move 为悬浮漂移，Attack 为举杖 → 前劈咒唱。刚性挂骨实例化方案（10 节骨，含下摆 Hem 与提灯 Lantern；4 种材质）；
构建逻辑在 chars/_legion_cantor.py。
"""

from chars import _legion, _legion_cantor as body

TITLE = "Hex Cantor"
ACCENT = (0.85, 0.58, 1.0)
CLIPS = ("Move", "Attack")
GAME_TRIS = 2500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=False)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
