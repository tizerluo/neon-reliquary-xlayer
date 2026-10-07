/* 程序化音频 · DSP 基础。
   浏览器与 Node 测试共用：只操作 Float32Array，不依赖 Web Audio。
   随机数全部来自独立种子，不消耗游戏的 Math.random；同一配方同一种子每次渲染逐样本一致。 */
const NRDSP = (() => {
  // SR 可被 withRate 临时改写（暗色的垫音/贝斯用 22.05 kHz 渲染以节省内存）
  let SR = 44100;
  const TAU = Math.PI * 2;
  function withRate(rate, fn) { const keep = SR; SR = rate; try { return fn(); } finally { SR = keep; } }

  // mulberry32：小而稳定的种子随机数
  function rng(seed) {
    let a = (seed >>> 0) || 1;
    return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  // 字符串 → 种子（FNV-1a）
  function hash(text) { let h = 2166136261; for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  const len = sec => Math.max(1, Math.ceil(sec * SR));
  const val = (v, t) => typeof v === 'function' ? v(t) : v;
  const mtof = m => 440 * 2 ** ((m - 69) / 12);
  const clamp = (v, a, b) => v < a ? a : v > b ? b : v;

  /* ---------- 包络（返回 t→增益 的函数） ---------- */
  // 线性起音 + 指数衰减
  const ad = (attack, tau) => t => t < attack ? t / attack : Math.exp(-(t - attack) / tau);
  // 点列包络 [[t, v], ...]，curve>0 时每段先快后慢
  function env(points, curve = 0) {
    return t => {
      if (t <= points[0][0]) return points[0][1];
      for (let i = 1; i < points.length; i++) {
        const [t1, v1] = points[i];
        if (t <= t1) {
          const [t0, v0] = points[i - 1];
          let u = (t - t0) / ((t1 - t0) || 1);
          if (curve) u = (1 - Math.exp(-curve * u)) / (1 - Math.exp(-curve));
          return v0 + (v1 - v0) * u;
        }
      }
      return points[points.length - 1][1];
    };
  }
  // 钟形包络：在 peak 处达到 1，两侧平滑（适合呼啸）
  const swell = (dur, peak = .5, power = 1.6) => t => {
    const u = t / dur; if (u <= 0 || u >= 1) return 0;
    return (u < peak ? Math.sin(Math.PI / 2 * u / peak) : Math.cos(Math.PI / 2 * (u - peak) / (1 - peak))) ** power;
  };
  // 指数频率滑动：f0 → f1，用时 time 秒
  const glide = (f0, f1, time) => t => f0 * (f1 / f0) ** Math.min(1, t / time);
  // 冲击式下滑：从 f0 迅速落到 f1（鼓与冲击）
  const drop = (f0, f1, tau) => t => f1 + (f0 - f1) * Math.exp(-t / tau);

  /* ---------- 振荡器 ---------- */
  function blep(t, dt) {
    if (t < dt) { t /= dt; return t + t - t * t - 1; }
    if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
    return 0;
  }
  // type: sine / tri / saw / square（锯齿与方波带 polyBLEP 抗混叠）
  function osc(dur, freq, amp = 1, type = 'sine', phase = 0) {
    const n = len(dur), out = new Float32Array(n);
    let ph = phase;
    for (let i = 0; i < n; i++) {
      const t = i / SR, dt = Math.min(.45, val(freq, t) / SR);
      let s;
      if (type === 'sine') s = Math.sin(TAU * ph);
      else if (type === 'tri') s = 1 - 4 * Math.abs(((ph + .25) % 1) - .5);
      else if (type === 'saw') s = 2 * ph - 1 - blep(ph, dt);
      else s = (ph < .5 ? 1 : -1) + blep(ph, dt) - blep((ph + .5) % 1, dt);
      out[i] = s * val(amp, t);
      ph += dt; ph -= Math.floor(ph);
    }
    return out;
  }
  // 简单两算子 FM：载波 fc，调制比 ratio，调制指数 index(t)
  function fm(dur, fc, ratio, index, amp = 1, seed = 1) {
    const n = len(dur), out = new Float32Array(n), r = rng(seed);
    let pc = r(), pm = r();
    for (let i = 0; i < n; i++) {
      const t = i / SR, f = val(fc, t);
      out[i] = Math.sin(TAU * pc + val(index, t) * Math.sin(TAU * pm)) * val(amp, t);
      pc += f / SR; pm += f * ratio / SR; pc -= Math.floor(pc); pm -= Math.floor(pm);
    }
    return out;
  }
  // 噪声：white / pink / brown
  function noise(dur, amp = 1, color = 'white', seed = 1) {
    const n = len(dur), out = new Float32Array(n), r = rng(seed);
    let b0 = 0, b1 = 0, b2 = 0, br = 0;
    for (let i = 0; i < n; i++) {
      const w = r() * 2 - 1;
      let s = w;
      if (color === 'pink') { b0 = .99765 * b0 + w * .099046; b1 = .963 * b1 + w * .2965164; b2 = .57 * b2 + w * 1.0526913; s = (b0 + b1 + b2 + w * .1848) * .2; }
      else if (color === 'brown') { br = (br + .02 * w) / 1.02; s = br * 3.5; }
      out[i] = s * val(amp, i / SR);
    }
    return out;
  }
  // 模态合成：一组指数衰减的正弦 [[频率, 振幅, 衰减秒]]，用于金属、玻璃、钟
  function modal(dur, modes, seed = 1) {
    const n = len(dur), out = new Float32Array(n), r = rng(seed);
    for (const [f, a, d] of modes) {
      if (!(f > 20 && f < SR * .45) || !a) continue;
      const w = TAU * f / SR, c = 2 * Math.cos(w), k = Math.exp(-1 / (Math.max(.002, d) * SR)), ph = r() * TAU;
      let s1 = Math.sin(ph), s2 = Math.sin(ph - w), g = a;
      for (let i = 0; i < n && g > 1e-5; i++) { const s = c * s1 - s2; s2 = s1; s1 = s; out[i] += s * g; g *= k; }
    }
    return out;
  }
  // Karplus-Strong 拨弦：分数延迟保证音准；bright 0..1 控制激励亮度，t60 为衰减到 -60dB 的秒数
  function pluck(dur, f, t60 = 2, bright = .6, seed = 1) {
    const n = len(dur), out = new Float32Array(n), r = rng(seed);
    const s = .5 - bright * .42, D = SR / f - s, g = 10 ** (-3 / (t60 * f));
    const exN = Math.ceil(D) + 1, ex = new Float32Array(exN);
    let lp = 0;
    for (let i = 0; i < exN; i++) { lp += ((r() * 2 - 1) - lp) * (.25 + bright * .75); ex[i] = lp; }
    let mean = 0; for (const v of ex) mean += v / exN; for (let i = 0; i < exN; i++) ex[i] -= mean;
    for (let i = 0; i < n; i++) {
      let v = i < exN ? ex[i] : 0;
      const p = i - D;
      if (p >= 1) {
        const i0 = Math.floor(p), fr = p - i0;
        const a = out[i0] * (1 - fr) + out[i0 + 1 < i ? i0 + 1 : i0] * fr;
        const b = out[i0 - 1] * (1 - fr) + out[i0] * fr;
        v += g * ((1 - s) * a + s * b);
      }
      out[i] = v;
    }
    return out;
  }
  // 稀疏噼啪：随机位置的短促噪声爆点（火焰、电弧、冰裂）
  function crackle(dur, rate, amp = 1, seed = 1, grain = .004) {
    const n = len(dur), out = new Float32Array(n), r = rng(seed), g = Math.max(4, Math.round(grain * SR));
    const count = Math.round(rate * dur);
    for (let k = 0; k < count; k++) {
      const pos = Math.floor(r() * n), a = (r() * .8 + .2) * (r() < .5 ? -1 : 1) * val(amp, pos / SR), gl = Math.floor(g * (.4 + r()));
      for (let j = 0; j < gl && pos + j < n; j++) out[pos + j] += (r() * 2 - 1) * a * Math.exp(-j / (gl * .3));
    }
    return out;
  }

  /* ---------- 处理 ---------- */
  // RBJ 双二阶滤波：lp / hp / bp / peak / notch；freq 可为时间函数（每 16 样本更新一次系数）
  function filter(x, type, freq, q = .707, gainDb = 0) {
    const out = new Float32Array(x.length);
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0, b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    const set = f => {
      f = clamp(f, 12, SR * .45);
      const w = TAU * f / SR, cs = Math.cos(w), sn = Math.sin(w), al = sn / (2 * q), A = 10 ** (gainDb / 40);
      let a0 = 1 + al;
      if (type === 'lp') { b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; a1 = -2 * cs; a2 = 1 - al; }
      else if (type === 'hp') { b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; a1 = -2 * cs; a2 = 1 - al; }
      else if (type === 'bp') { b0 = al; b1 = 0; b2 = -al; a1 = -2 * cs; a2 = 1 - al; }
      else if (type === 'notch') { b0 = 1; b1 = -2 * cs; b2 = 1; a1 = -2 * cs; a2 = 1 - al; }
      else { b0 = 1 + al * A; b1 = -2 * cs; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * cs; a2 = 1 - al / A; }
      b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
    };
    const dynamic = typeof freq === 'function';
    if (!dynamic) set(freq);
    for (let i = 0; i < x.length; i++) {
      if (dynamic && (i & 15) === 0) set(freq(i / SR));
      const xi = x[i], y = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
      x2 = x1; x1 = xi; y2 = y1; y1 = y; out[i] = y;
    }
    return out;
  }
  const lp = (x, f, q) => filter(x, 'lp', f, q), hp = (x, f, q) => filter(x, 'hp', f, q), bp = (x, f, q) => filter(x, 'bp', f, q);
  // 软削波饱和
  function drive(x, k = 2) { const out = new Float32Array(x.length), n = Math.tanh(k); for (let i = 0; i < x.length; i++) out[i] = Math.tanh(x[i] * k) / n; return out; }
  // 逐样本乘包络
  function shape(x, fn) { const out = new Float32Array(x.length); for (let i = 0; i < x.length; i++) out[i] = x[i] * fn(i / SR); return out; }
  // 混合多层：[数组, 增益, 起始秒]
  function mix(...layers) {
    let n = 1;
    for (const [a, , at = 0] of layers) if (a) n = Math.max(n, a.length + Math.round(at * SR));
    const out = new Float32Array(n);
    for (const [a, g = 1, at = 0] of layers) {
      if (!a) continue;
      const o = Math.round(at * SR);
      for (let i = 0; i < a.length; i++) out[i + o] += a[i] * g;
    }
    return out;
  }
  // 短延迟回声（单声道烘焙用）
  function echo(x, time, feedback = .35, wet = .4, tail = 0) {
    const d = Math.max(1, Math.round(time * SR)), out = new Float32Array(x.length + Math.round(tail * SR));
    for (let i = 0; i < out.length; i++) { const dry = i < x.length ? x[i] : 0; out[i] = dry + (i >= d ? out[i - d] * feedback : 0); }
    for (let i = 0; i < out.length; i++) out[i] = (i < x.length ? x[i] : 0) * (1 - wet) + out[i] * wet;
    return out;
  }
  // Schroeder 全通（用于去相关、扩宽立体声）
  function allpass(x, time, g = .6) {
    const d = Math.max(1, Math.round(time * SR)), out = new Float32Array(x.length), buf = new Float32Array(d);
    let p = 0;
    for (let i = 0; i < x.length; i++) { const b = buf[p], v = x[i] + b * g; out[i] = b - v * g; buf[p] = v; p = (p + 1) % d; }
    return out;
  }
  // 单声道 → 立体声：中/侧结构，侧声道来自全通扩散
  function widen(x, amount = .5, seed = 1) {
    const r = rng(seed);
    const side = allpass(allpass(x, .0047 + r() * .003, .62), .0113 + r() * .004, .55);
    const L = new Float32Array(x.length), R = new Float32Array(x.length);
    for (let i = 0; i < x.length; i++) { L[i] = x[i] + side[i] * amount; R[i] = x[i] - side[i] * amount; }
    return [L, R];
  }
  // 末端处理：去直流、淡入淡出、按峰值归一
  function finish(x, peak = .95, fadeIn = .0015, fadeOut = .012) {
    const chans = Array.isArray(x) ? x : [x];
    for (const c of chans) {
      let px = 0, py = 0;
      for (let i = 0; i < c.length; i++) { const y = c[i] - px + .9985 * py; px = c[i]; py = y; c[i] = y; }
      const fi = Math.min(c.length, Math.round(fadeIn * SR)), fo = Math.min(c.length, Math.round(fadeOut * SR));
      for (let i = 0; i < fi; i++) c[i] *= i / fi;
      for (let i = 0; i < fo; i++) c[c.length - 1 - i] *= i / fo;
    }
    let m = 0;
    for (const c of chans) for (let i = 0; i < c.length; i++) m = Math.max(m, Math.abs(c[i]));
    if (m > 0 && peak) for (const c of chans) for (let i = 0; i < c.length; i++) c[i] *= peak / m;
    return Array.isArray(x) ? chans : chans[0];
  }
  // 去掉尾部静音（低于阈值）
  function trim(x, threshold = .0006) {
    const chans = Array.isArray(x) ? x : [x];
    let end = 1;
    for (const c of chans) for (let i = c.length - 1; i >= end; i--) if (Math.abs(c[i]) > threshold) { end = i + 1; break; }
    const cut = chans.map(c => c.slice(0, Math.min(c.length, end + 64)));
    return Array.isArray(x) ? cut : cut[0];
  }
  // 混响脉冲响应：立体声衰减噪声 + 早期反射，越晚越暗
  function impulse(sec, { seed = 1, pre = .012, bright = 7000, dark = 900, early = 6 } = {}) {
    const r = rng(seed), out = [];
    for (let ch = 0; ch < 2; ch++) {
      let x = noise(sec, t => Math.exp(-t * 6.9 / sec) * (t < pre ? 0 : 1), 'white', seed * 7 + ch);
      x = filter(x, 'lp', t => dark + (bright - dark) * Math.exp(-t * 4 / sec), .6);
      for (let k = 0; k < early; k++) { const p = Math.round((pre * .4 + r() * pre * 2.2) * SR); if (p < x.length) x[p] += (r() * .8 + .2) * (r() < .5 ? -1 : 1) * .7; }
      out.push(x);
    }
    let e = 0;
    for (const c of out) for (let i = 0; i < c.length; i++) e += c[i] * c[i];
    const g = 1 / Math.sqrt(e / 2 || 1) * .6;
    for (const c of out) for (let i = 0; i < c.length; i++) c[i] *= g;
    return out;
  }
  // 采样循环：把 loopEnd 前的一段与 loopStart 前的素材交叉淡化，让循环无缝
  function loopify(x, ls, le, xf = .08) {
    const a = Math.round(ls * SR), b = Math.min(x.length, Math.round(le * SR)), w = Math.min(Math.round(xf * SR), a, b - a);
    for (let i = 0; i < w; i++) { const u = i / w, k = Math.sqrt(u); x[b - w + i] = x[b - w + i] * Math.sqrt(1 - u) + x[a - w + i] * k; }
    return { data: x.slice(0, b), loopStart: a / SR, loopEnd: b / SR };
  }
  // 短时响度：近似 K 加权（70 Hz 高通 + 3 kHz 提升），取 150 ms 窗口里最大的 RMS（接近人耳的时间积分）
  function loudness(x, win = .15) {
    const c = filter(hp(Array.isArray(x) ? x[0] : x, 70), 'peak', 3000, .8, 4), w = Math.max(1, Math.round(win * SR));
    let sum = 0, best = 0;
    for (let i = 0; i < c.length; i++) { sum += c[i] * c[i]; if (i >= w) sum -= c[i - w] * c[i - w]; best = Math.max(best, sum / w); }
    return Math.sqrt(Math.max(0, best));
  }
  // 按短时响度归一到 target；峰值会超过 peak 时先软限幅压低峰均比，再归一（最多两轮）
  function level(x, target = .1, peak = .98) {
    const chans = Array.isArray(x) ? x : [x];
    for (let round = 0; round < 3; round++) {
      const l = loudness(x);
      let m = 0; for (const c of chans) for (let i = 0; i < c.length; i++) m = Math.max(m, Math.abs(c[i]));
      if (!l || !m) return x;
      const g = target / l;
      if (m * g <= peak || round === 2) { const k = Math.min(g, peak / m); for (const c of chans) for (let i = 0; i < c.length; i++) c[i] *= k; return x; }
      // 软限幅：把超出部分用 tanh 收进 peak，保留瞬态形状
      const knee = peak / g;
      for (const c of chans) for (let i = 0; i < c.length; i++) { const v = c[i], a = Math.abs(v); if (a > knee * .6) c[i] = Math.sign(v) * (knee * .6 + knee * .4 * Math.tanh((a - knee * .6) / (knee * .4))); }
    }
    return x;
  }
  // 简单测量：峰值、RMS、亮度（一阶差分能量比换算的等效频率）
  function measure(x) {
    const c = Array.isArray(x) ? x[0] : x;
    let peak = 0, sum = 0, diff = 0, prev = 0;
    for (let i = 0; i < c.length; i++) { const v = c[i]; peak = Math.max(peak, Math.abs(v)); sum += v * v; diff += (v - prev) ** 2; prev = v; }
    const rms = Math.sqrt(sum / c.length);
    // 差分能量 / 原能量 ≈ (2πf/SR)^2 的加权平均，换算成“等效频率”
    const bright = sum ? SR / TAU * Math.sqrt(diff / sum) : 0;
    return { peak, rms, bright, seconds: c.length / SR };
  }

  return { get SR() { return SR; }, withRate, loudness, level, TAU, rng, hash, len, val, mtof, clamp, ad, env, swell, glide, drop, osc, fm, noise, modal, pluck, crackle, filter, lp, hp, bp, drive, shape, mix, echo, allpass, widen, finish, trim, impulse, loopify, measure };
})();
if (typeof module !== 'undefined') module.exports = NRDSP;
