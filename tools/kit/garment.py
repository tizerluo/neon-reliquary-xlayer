"""角色工具包 · 布料：环绕式（长袍 / 披风 / 裙甲）与片状（前后垂饰 / 腰布），自带骨链与权重。

角度约定：a=0 为正前方（+Y），a 增大时转向 +X（角色左手侧从正面看是画面右侧），a=π 为正后方。
"""

import math

from mathutils import Vector

from kit.core import (TAU, clamp, crest, garment, hash01, interp, lerp, orient, radial, smoothstep, solidify,
                      apply_all, surface, trim)


def cloth_fold(a, v, freq, amp, seed):
    phase = 0.9 * math.sin(a * 2.3 + seed) + 0.5 * math.sin(a * 3.7 + seed * 1.7)
    phase2 = 0.7 * math.sin(a * 1.9 + seed * 2.1)
    mod = 0.65 + 0.35 * math.sin(a * 3.1 + seed * 0.7 + v * 1.3)
    return amp * mod * (0.72 * crest(a * freq + phase) + 0.28 * v * crest(a * freq * 2.1 + phase2))


def tail_weight(u, count, jitter=0.0):
    """飘带中心为 1、两条飘带之间的缺口为 0。"""
    if count <= 0:
        return 0.0
    x = u * count
    d = abs((x % 1.0) - 0.5 - jitter * math.sin(math.floor(x) * 2.3))
    return max(0.0, 1 - 2 * d) ** 1.5


def chain_v(v, bones, parent, joints, top_win, win=0.07):
    s = max(i for i in range(len(bones)) if v >= joints[i] - 1e-9)
    w = {bones[s]: 1.0}
    if s == 0 and v < top_win:
        pw = 1 - v / top_win
        w = {parent: pw, bones[0]: 1 - pw}
    elif s > 0 and v - joints[s] < win:
        t = 0.5 * (1 - (v - joints[s]) / win)
        w[bones[s - 1]] = t
        w[bones[s]] -= t
    if s < len(bones) - 1 and joints[s + 1] - v < win:
        t = 0.5 * (1 - (joints[s + 1] - v) / win)
        w[bones[s + 1]] = w.get(bones[s + 1], 0) + t
        w[bones[s]] -= t
    return w


class ClothBase:
    prefix = "Cloth"
    parent = "Pelvis"
    K = 1
    joints = (0, 0.30, 0.62, 1.0)
    top_win = 0.12

    @property
    def J(self):
        return len(self.joints) - 1

    def weights(self, u, v):
        x = u * self.K - 0.5
        k0 = math.floor(x)
        f = x - k0
        if k0 < 0:
            mix = [(0, 1.0)]
        elif k0 >= self.K - 1:
            mix = [(self.K - 1, 1.0)]
        else:
            mix = [(k0, 1 - f), (k0 + 1, f)]
        out = {}
        for k, cw in mix:
            names = [f"{self.prefix}{k}.{j}" for j in range(1, self.J + 1)]
            for name, w in chain_v(v, names, self.parent, self.joints, self.top_win).items():
                out[name] = out.get(name, 0) + w * cw
        return out

    def chain_points(self, k):
        u = (k + 0.5) / self.K
        return [self.inset(self.point(u, v)) for v in self.joints]

    def axes(self, k, seg):
        """链 k 的切向轴（正角为外掀）与径向轴（侧摆）。"""
        a0, a1 = seg[f"{self.prefix}{k}.1"]
        r = self.outward(a1)
        return Vector((r.y, -r.x, 0)).normalized(), r


class Wrap(ClothBase):
    """环绕式布料：u 沿角度 a0→a1，v 自上而下；bottom 可带飘带尖角。"""

    def __init__(self, prefix, parent, a0, a1, top, bottom, r_top, r_bot, K=6, joints=(0, 0.30, 0.62, 1.0),
                 cy=0.0, flow=0.10, flare_exp=1.2, widen=0.06, folds=(6.0, 0.006, 0.03), seed=0.8,
                 tails=0, tail_len=(0.14, 0.04), curl=(0.05, 0.018), top_win=0.12, inset=0.012,
                 radius_fn=None):
        self.prefix, self.parent, self.a0, self.a1 = prefix, parent, a0, a1
        self._top, self._bottom = top, bottom
        self.r_top, self.r_bot, self.K, self.joints = r_top, r_bot, K, tuple(joints)
        self.cy, self.flow_amt, self.flare_exp, self.widen = cy, flow, flare_exp, widen
        self.freq, self.amp0, self.amp1 = folds
        self.seed, self.tails, self.tail_len, self.curl = seed, tails, tail_len, curl
        self.top_win, self._inset, self.radius_fn = top_win, inset, radius_fn

    def top(self, u):
        return self._top(u) if callable(self._top) else self._top

    def bottom(self, u):
        base = self._bottom(u) if callable(self._bottom) else self._bottom
        if not self.tails:
            return base
        k = min(self.tails - 1, int(u * self.tails))
        tip = base - self.tail_len[0] - self.tail_len[1] * hash01(k, self.seed)
        return lerp(base, tip, tail_weight(u, self.tails, 0.08))

    def flow(self, v):
        return -self.flow_amt * v ** 1.6

    def angle(self, u):
        return self.a0 + u * (self.a1 - self.a0)

    def point(self, u, v):
        a = self.angle(u)
        z = lerp(self.top(u), self.bottom(u), v)
        e = v ** self.flare_exp
        if self.radius_fn:
            rx, ry = self.radius_fn(u, v, a)
        else:
            rx, ry = lerp(self.r_top[0], self.r_bot[0], e), lerp(self.r_top[1], self.r_bot[1], e)
        r = cloth_fold(a, v, self.freq, self.amp0 + self.amp1 * v, self.seed)
        if self.tails:
            tip = tail_weight(u, self.tails, 0.08)
            r += smoothstep(0.6, 1.0, v) * (self.curl[0] * tip - self.curl[1] * (1 - tip))
        return Vector(((rx + r) * math.sin(a) * (1 + self.widen * v),
                       (ry + r) * math.cos(a) + self.cy + self.flow(v), z))

    def param(self, p):
        y, v, u = p.y, 0.5, 0.5
        span = self.a1 - self.a0
        for _ in range(3):
            a = math.atan2(p.x, y - self.cy)
            # 把角度展开到 [a0, a0+2π) 再归一化
            a = self.a0 + ((a - self.a0) % TAU)
            u = clamp((a - self.a0) / span) if abs(span) > 1e-6 else 0.5
            top, bot = self.top(u), self.bottom(u)
            v = clamp((top - p.z) / max(1e-4, top - bot))
            y = p.y - self.flow(v)
        return u, v

    def inset(self, p):
        return radial(p, -self._inset, self.cy)

    def outward(self, p):
        r = Vector((p.x, p.y - self.cy, 0))
        return r.normalized() if r.length > 1e-6 else Vector((0, -1, 0))

    def roll_dir(self, k, p):
        return self.outward(p)

    def build(self, ctx, mats, name, nu=96, nv=56, thickness=0.007, uv_scale=1.6, hem=None, edges=None,
              extra_spec=None):
        """生成布面并登记；hem=(材质, 半径) 下摆滚边，edges=(材质, 半径) 左右开襟滚边。"""
        cloth = surface(name, self.point, nu, nv, mats, uvfn=lambda u, v: (u * uv_scale, 1 - v))
        orient(cloth, lambda c: Vector((0, self.cy, c.z)))
        solidify(cloth, thickness, 0, inner_offset=1 if len(mats) > 1 else 0)
        spec = extra_spec or garment(self)
        ctx.part(apply_all(cloth), spec)
        if hem:
            n = nu * 3
            pts = [radial(self.point(i / (n - 1), 1.0), 0.005, self.cy) for i in range(n)]
            ctx.part(trim(f"{name} hem", pts, hem[1], hem[0]), spec)
        if edges:
            for u in (0.0, 1.0):
                pts = [radial(self.point(u, j / 60), 0.004, self.cy) for j in range(61)]
                ctx.part(trim(f"{name} edge {u}", pts, edges[1], edges[0]), spec)
        return cloth


class Panel(ClothBase):
    """片状垂饰：side=+1 前片、-1 后片；width(v) 宽度，depth(v) 离轴距离，底端可收尖。"""

    def __init__(self, prefix, parent, top, tip, width, depth, side=1, K=1, joints=(0, 0.30, 0.62, 1.0),
                 curve=1.2, point=0.1, cx=0.0, top_win=0.12, flutter=0.004):
        self.prefix, self.parent, self._top, self._tip = prefix, parent, top, tip
        self._width, self._depth, self.side, self.K = width, depth, side, K
        self.joints, self.curve, self.pointy, self.cx = tuple(joints), curve, point, cx
        self.top_win, self.flutter = top_win, flutter

    def width(self, v):
        w = self._width(v) if callable(self._width) else interp(self._width, v)
        return w * min(1.0, (1 - v) / max(1e-3, self.pointy)) ** 0.7 if self.pointy else w

    def depth(self, v):
        return self._depth(v) if callable(self._depth) else interp(self._depth, v)

    def point(self, u, v):
        w = self.width(v)
        x = (u - 0.5) * w
        y = self.side * (self.depth(v) - self.curve * x * x) + self.flutter * math.sin(u * math.pi * 3 + v * 4) * v
        return Vector((self.cx + x, y, lerp(self._top, self._tip, v)))

    def param(self, p):
        v = clamp((self._top - p.z) / max(1e-4, self._top - self._tip))
        w = max(1e-4, self.width(v))
        return clamp((p.x - self.cx) / w + 0.5), v

    def inset(self, p):
        return p - Vector((0, self.side * 0.01, 0))

    def outward(self, p):
        return Vector((0, self.side, 0))

    def roll_dir(self, k, p):
        return Vector((0, self.side, 0))

    def axes(self, k, seg):
        # 绕 +X 正转会把下垂的骨尖推向 +Y，所以前片（side=+1）外掀轴为 +X，后片为 -X
        return Vector((self.side, 0, 0)), Vector((0, self.side, 0))

    def build(self, ctx, mats, name, nu=18, nv=56, thickness=0.006, edges=None, spine=None, tipgem=None):
        panel = surface(name, self.point, nu, nv, mats)
        orient(panel, lambda c: Vector((self.cx, 0, c.z)))
        solidify(panel, thickness, 0, inner_offset=1 if len(mats) > 1 else 0)
        ctx.part(apply_all(panel), garment(self))
        if edges:
            for u in (0.0, 1.0):
                pts = [self.point(u, j / 60) + Vector((0, self.side * 0.003, 0)) for j in range(61)]
                ctx.part(trim(f"{name} edge {u}", pts, edges[1], edges[0]), garment(self))
            pts = [self.point(i / 30, 0.0) + Vector((0, self.side * 0.003, 0.002)) for i in range(31)]
            ctx.part(trim(f"{name} top", pts, edges[1], edges[0]), garment(self))
        if spine:
            pts = [self.point(0.5, j / 40) + Vector((0, self.side * 0.0035, 0)) for j in range(3, 38)]
            ctx.part(trim(f"{name} spine", pts, spine[1], spine[0]), garment(self))
        return panel
