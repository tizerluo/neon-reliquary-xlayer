"""香炉炮手 Censer Gunner（零域军团 · 类型 4）：钟形重袍、肩扛冒烟香炉炮（薄荷绿 #8ee4b0，与弹幕同色）的远程杂兵。

Attack 为开炮后坐。刚性挂骨实例化方案（9 节骨，含 Cannon 后坐骨；4 种材质）；构建逻辑在
chars/_legion_censer.py，与精英“香炉审判官”共用。
"""

from chars import _legion, _legion_censer as body

TITLE = "Censer Gunner"
ACCENT = (0.56, 0.89, 0.69)
CLIPS = ("Move", "Attack")
GAME_TRIS = 2500
REVIEW_POSE = body.REVIEW_POSE


def build(ctx):
    return body.build(ctx, elite=False)


def skeleton(rig, st):
    _legion.skeleton(rig, st)


def animate(rig, st):
    body.animate(rig, st)
