"""角色工具包 · 人形动作：脚步轨迹 + 两段式 IK 的跑 / 走 / 重步 / 滑冰 / 站立，以及姿态混合。

所有函数返回或修改 pose 字典（见 kit.rig 的约定）；腿部 IK 必须在骨盆、脊柱姿态写好之后调用。
"""

import math

from mathutils import Matrix, Quaternion, Vector

from kit.core import TAU, clamp, lerp, smoothstep
from kit.rig import I3, R, X, Y, Z


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def blend(a, b, t):
    """两个姿态逐骨球面插值（浮点键线性插值）。"""
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if isinstance(va, (int, float)) or isinstance(vb, (int, float)):
            out[k] = lerp(va or 0.0, vb or 0.0, t)
            continue
        qa = (va or I3).to_quaternion()
        qb = (vb or I3).to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        out[k] = qa.slerp(qb, t).to_matrix()
    return out


def fingers(pose, B, label, curl, spread=0.0):
    """手指弯曲：curl(i) 为第 i 根手指（拇指起）的弯曲角。"""
    h = B.hands.get(label)
    if not h:
        return
    axis = h["f"].cross(h["n"])
    for i, name in enumerate(("Thumb", "Index", "Middle", "Ring", "Pinky")):
        c = curl(i) if callable(curl) else curl
        pose[f"{name}.{label}"] = R((axis, c), (h["n"], spread * (i - 2) * 0.1))


class Legs:
    """双腿 IK 助手：脚踝目标 + 脚掌俯仰 / 偏航，膝盖朝前（可外撇）。"""

    def __init__(self, rig, B, ground=0.0):
        self.rig, self.B, self.ground = rig, B, ground
        self.rest = {}
        for label in ("L", "R"):
            L = B.legs[label]
            self.rest[label] = {"ankle": L["ankle"].copy(), "ball": L["ball"].copy(),
                                "foot": (L["ball"] - L["ankle"]), "hip": L["hip"].copy()}

    def plant(self, pose, label, ankle, pitch=0.0, yaw=0.0, knee_out=0.0, roll=0.0):
        side = -1 if label == "L" else 1
        foot = self.rest[label]["foot"]
        d = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(-pitch, 3, "X") @ foot
        up = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(side * roll, 3, "Y") @ Z
        pole = Matrix.Rotation(yaw, 3, "Z") @ (Y + Vector((side * knee_out, 0, 0)))
        self.rig.ik2(pose, f"Thigh.{label}", f"Shin.{label}", ankle, pole, end=f"Foot.{label}",
                     end_dir=d.normalized(), end_up=up)
        return d

    def toe(self, pose, label, bend):
        pose[f"Toe.{label}"] = R((X, bend))

    def stand(self, pose, spread=0.0, bend=0.0, yaw=0.08):
        """原地站立：双脚踩在静止位置（可略外撇），膝盖微屈。"""
        for label in ("L", "R"):
            side = -1 if label == "L" else 1
            a = self.rest[label]["ankle"] + Vector((side * spread, 0, 0))
            a.z = self.rest[label]["ankle"].z
            self.plant(pose, label, a, yaw=-side * yaw, knee_out=0.15 + bend)


def foot_track(p, stride, lift, stance, heel=0.05, toe_off=0.9, strike=0.25):
    """单脚相位 p∈[0,1)：前半段支撑（向后滑过身体下方），后半段摆动（抬起前送）。
    返回 (前后偏移 dy, 抬高 dz, 脚掌俯仰 pitch)。"""
    if p < stance:
        q = p / stance
        dy = stride * (0.5 - q)
        heel_up = smoothstep(0.65, 1.0, q)
        return dy, heel * heel_up, toe_off * heel_up * 0.6 - strike * (1 - smoothstep(0.0, 0.18, q))
    q = (p - stance) / (1 - stance)
    dy = stride * (-0.5 + ease(q))
    dz = lift * math.sin(math.pi * q) ** 0.8 + heel * (1 - smoothstep(0.0, 0.3, q))
    pitch = toe_off * (1 - smoothstep(0.0, 0.35, q)) * 0.9 - strike * smoothstep(0.7, 1.0, q) + 0.25 * math.sin(math.pi * q)
    return dy, dz, pitch


def gait(rig, B, t, stride=0.52, lift=0.16, stance=0.40, bob=0.035, lean=0.16, twist=0.10, arm=0.55,
         elbow=1.05, arm_in=0.38, width=0.0, heel=0.05, knee_out=0.10, head_stab=0.7, sink=0.05, sway=0.012,
         phase_bob=0.0, chest_twist=None, pose=None):
    """通用步态：跑步（stance≈0.38、bob 大）、行走（stance≈0.6、bob 小）、重步（width、sink 大）。
    t∈[0, 2π) 一个完整周期（左右各一步）。"""
    s = B.s
    pose = {} if pose is None else pose
    legs = Legs(rig, B)
    # 骨盆：跑步支撑中段最低（每周期两次），左右轻摆，前倾
    pose["_hover"] = -sink * s + bob * s * math.cos(2 * t + phase_bob)
    yaw = twist * math.sin(t)
    pose["Pelvis"] = R((Z, yaw), (Y, sway * math.sin(t) * 3), (X, -lean))
    ct = chest_twist if chest_twist is not None else -1.6 * twist
    pose["Spine"] = R((Z, ct * 0.5 * math.sin(t)), (X, -lean * 0.15))
    pose["Chest"] = R((Z, ct * 0.5 * math.sin(t)), (X, 0.02 * math.cos(2 * t)))
    pose["Neck"] = R((Z, -yaw * 0.5), (X, lean * head_stab * 0.5))
    pose["Head"] = R((X, lean * head_stab * 0.5))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        dy, dz, pitch = foot_track(p, stride * s, lift * s, stance, heel * s)
        base = legs.rest[label]["ankle"]
        a = Vector((base.x + side * width * s, base.y + dy, base.z + dz))
        legs.plant(pose, label, a, pitch=pitch, yaw=-side * 0.06, knee_out=knee_out)
        legs.toe(pose, label, clamp(pitch * 0.8, 0, 0.9) if p < stance else -0.1)
        # 摆臂与对侧腿反相
        sw = math.sin(t + (0 if label == "L" else math.pi))
        # 绕 Y 轴：右臂正角内收、左臂负角内收（side * arm_in）
        pose[f"UpperArm.{label}"] = R((Y, side * arm_in), (X, arm * sw))
        pose[f"Forearm.{label}"] = R((X, elbow + 0.25 * max(0.0, sw)))
        pose[f"Hand.{label}"] = R((X, -0.15))
    return pose


def idle(rig, B, t, breathe=0.02, sway=0.015, arms=0.04, spread=0.02, bend=0.05, pose=None):
    """站立待机：呼吸、重心左右微移、双脚 IK 钉地。"""
    s = B.s
    pose = {} if pose is None else pose
    pose["_hover"] = -0.012 * s + 0.006 * s * math.sin(2 * t)
    pose["Pelvis"] = R((Y, sway * math.sin(t)), (Z, 0.02 * math.sin(t + 0.5)))
    pose["Spine"] = R((X, -breathe * 0.5 * math.sin(2 * t + 1.0)))
    pose["Chest"] = R((X, -breathe * math.sin(2 * t + 1.3)), (Y, -sway * 0.8 * math.sin(t)))
    pose["Neck"] = R((X, 0.01 * math.sin(2 * t + 2.0)))
    pose["Head"] = R((X, 0.02 * math.sin(t + 2.2)), (Z, 0.05 * math.sin(t)))
    for label, sg in (("L", -1), ("R", 1)):
        pose[f"UpperArm.{label}"] = R((Y, sg * (0.30 + arms * math.sin(t + 0.5 * sg))), (X, 0.04 + 0.03 * math.sin(t + 1)))
        pose[f"Forearm.{label}"] = R((X, 0.18 + 0.04 * math.sin(t + 1.4)))
        pose[f"Hand.{label}"] = R((X, 0.06 * math.sin(2 * t + 0.3 * sg)))
        fingers(pose, B, label, lambda i: 0.18 + 0.06 * math.sin(2 * t + i * 0.6))
    Legs(rig, B).stand(pose, spread * s, bend)
    return pose


def skate(rig, B, t, push=0.30, glide=0.34, lift=0.07, lean=0.30, arm=0.45, pose=None):
    """冰上滑行：支撑脚斜向后外侧蹬出，另一脚收回前送；上身随蹬冰左右摆。"""
    s = B.s
    pose = {} if pose is None else pose
    legs = Legs(rig, B)
    pose["_hover"] = -0.08 * s + 0.02 * s * math.cos(2 * t)
    roll = 0.10 * math.sin(t)
    pose["Pelvis"] = R((Y, roll), (Z, 0.18 * math.sin(t)), (X, -lean))
    pose["Spine"] = R((Z, -0.12 * math.sin(t)), (X, -0.05))
    pose["Chest"] = R((Z, -0.10 * math.sin(t)))
    pose["Neck"] = R((X, lean * 0.4))
    pose["Head"] = R((X, lean * 0.4), (Z, -0.08 * math.sin(t)))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        base = legs.rest[label]["ankle"]
        if p < 0.55:                       # 蹬冰：沿斜线向后外滑出
            q = p / 0.55
            dx, dy, dz = side * push * s * ease(q), glide * s * (0.5 - q), 0.0
            yaw = -side * (0.25 + 0.3 * q)
        else:                              # 收腿：离冰前送
            q = (p - 0.55) / 0.45
            dx, dy = side * push * s * (1 - ease(q)), glide * s * (-0.5 + ease(q))
            dz = lift * s * math.sin(math.pi * q)
            yaw = -side * (0.55 - 0.55 * q)
        legs.plant(pose, label, Vector((base.x + dx, base.y + dy, base.z + dz)), pitch=0.05, yaw=yaw, knee_out=0.25)
        sw = math.sin(t + (0 if label == "L" else math.pi))
        pose[f"UpperArm.{label}"] = R((Y, side * (-0.15 + 0.25 * max(0.0, -sw))), (X, arm * sw))
        pose[f"Forearm.{label}"] = R((X, 0.45))
    return pose


def dangle(B, t, pose, swing=0.10, bend=0.35):
    """漂浮角色的双腿：自然下垂、微屈、缓慢摆动（纯 FK）。"""
    for label, sg in (("L", -1), ("R", 1)):
        pose[f"Thigh.{label}"] = R((X, 0.12 + swing * math.sin(t + (0 if sg < 0 else 1.3))), (Y, sg * -0.04))
        pose[f"Shin.{label}"] = R((X, -bend - 0.08 * math.sin(t + 0.6)))
        pose[f"Foot.{label}"] = R((X, 0.45))
    return pose


def cape_run(rig, g, t, base=0.35, flap=0.10, side_amt=0.05):
    """奔跑时披风向后扬起并起伏。"""
    return lambda pose: rig.garment_pose(pose, g, lambda k, j: base + flap * math.sin(2 * t + k * 0.8 + j * 1.1),
                                         lambda k, j: side_amt * math.sin(t + k + j * 0.8))
