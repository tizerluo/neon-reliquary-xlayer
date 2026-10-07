/* 程序化音效配方。每个音效 = 元数据 + render(seed)；render 返回单声道 Float32Array 或 [左, 右]。
   元数据：lu 目标响度（缺省按类别表 LU）；gap 同名最短间隔（秒）；max 同名最多并发；pri 抢占优先级（高者可挤掉低者）；
   send 混响发送量；vars 预渲染变体数；pj 随机音高抖动（半音）；duck 触发时压低配乐的量（0..1）。
   英雄 0–5 依次：晓斌（天枢银剑）、阿喵（金焰重剑）、旺财（雷剑）、吱吱（千机剑针）、柳如烟（花影）、小蓝（冰魄）。
   Boss 0–7 依次：赤焰魔尊（火）、玄冰骨龙（冰）、啸岳妖王（兽）、九幽尸将（亡魂）、天机巨神（机械）、万魂神坛（灵）、碧厄三首（毒）、烬天凰皇（凰火）。 */
const NRSFX = (() => {
  const D = NRDSP, TAU = Math.PI * 2;
  // 五声音阶（G 宫）上的频率，用于让零碎的清音彼此和谐
  const PENTA = [0, 2, 4, 7, 9];
  const penta = (step, base = 67) => D.mtof(base + PENTA[((step % 5) + 5) % 5] + 12 * Math.floor(step / 5));

  /* ---------- 积木 ---------- */
  const K = {
    // 下滑正弦：低频冲击
    thump: (dur, f0, f1, tau, decay) => D.osc(dur, D.drop(f0, f1, tau), D.ad(.0015, decay)),
    // 高通噪声瞬态
    click: (dur, hpf, seed, decay = dur * .25) => D.hp(D.noise(dur, D.ad(.0002, decay), 'white', seed), hpf),
    // 带通扫频呼啸
    whoosh: (dur, f0, f1, q, seed, peak = .5, color = 'pink', power = 1.6) => D.filter(D.noise(dur, D.swell(dur, peak, power), color, seed), 'bp', D.glide(f0, f1, dur), q),
    // 剑刃 / 金属条：自由梁模态比，带细微失谐产生拍频光泽
    metal(dur, f, seed, decay = .5, bright = 1, spread = .0035) {
      const ratios = [1, 2.756, 5.404, 8.933, 13.344], amps = [1, .7, .5, .34, .2], modes = [];
      ratios.forEach((r, i) => {
        const a = amps[i] * (i ? bright : 1), d = decay * [1, .72, .5, .34, .24][i];
        modes.push([f * r, a, d], [f * r * (1 + spread), a * .55, d * .9]);
      });
      return D.modal(dur, modes, seed);
    },
    // 金属板：更密集的不和谐泛音（盔甲、铁砧）
    plate(dur, f, seed, decay = .25) {
      const r = D.rng(seed), modes = [];
      for (const k of [1, 1.58, 2.31, 2.9, 3.62, 4.4, 5.3, 6.4]) modes.push([f * k * (1 + (r() - .5) * .02), 1 / (1 + k * .5), decay / (1 + k * .25)]);
      return D.modal(dur, modes, seed);
    },
    // 玻璃 / 冰晶
    glass: (dur, f, seed, decay = .18) => D.modal(dur, [[f, 1, decay], [f * 2.32, .6, decay * .6], [f * 4.25, .35, decay * .4], [f * 6.63, .2, decay * .3]], seed),
    // Risset 钟：不和谐泛音 + 拍频
    bell(dur, f, seed, decay = 2) {
      const P = [[.56, 1, 1], [.563, .67, .9], [.92, 1, .65], [.923, 1.8, .55], [1.19, 2.67, .325], [1.7, 1.67, .35], [2, 1.46, .25], [2.74, 1.33, .2], [3, 1.33, .15], [3.76, 1, .1], [4.07, 1.33, .075]];
      return D.modal(dur, P.map(([r, a, d]) => [f * r, a, decay * d]), seed);
    },
    // 清音：正弦 + 少量泛音，快速衰减（拾取、花瓣）
    ping: (dur, f, decay, seed = 1, bright = .25) => D.modal(dur, [[f, 1, decay], [f * 2, bright, decay * .5], [f * 3.01, bright * .4, decay * .3]], seed),
    // 爆炸低频团块
    boom(dur, seed, f0 = 420, f1 = 70, decay = .45) {
      const body = D.filter(D.noise(dur, D.ad(.003, decay), 'brown', seed), 'lp', D.glide(f0, f1, dur * .6), .8);
      return D.mix([body, 1.6], [K.thump(dur, 110, 38, .06, decay * .8), .9], [K.click(.02, 900, seed + 1), .35]);
    },
    // 上升张力：噪声与锯齿同步上扬，结尾骤停
    riser(dur, f0, f1, seed, tone = .25) {
      const e = t => (t / dur) ** 2.2;
      return D.mix([D.filter(D.noise(dur, e, 'white', seed), 'bp', D.glide(f0, f1, dur), 2), 1], [D.lp(D.osc(dur, D.glide(f0 / 4, f1 / 4, dur), e, 'saw'), f1 * .6), tone]);
    },
    // 闪烁：若干五声清音，随机时间
    sparkle(dur, n, seed, low = 10, high = 17, decay = .12) {
      const r = D.rng(seed), parts = [];
      for (let k = 0; k < n; k++) parts.push([K.ping(decay * 3, penta(low + Math.floor(r() * (high - low))), decay * (.6 + r() * .8), seed + k), .25 + r() * .5, r() * dur]);
      return D.mix(...parts);
    },
    // 电弧：采样保持的随机音高锯齿 + 失真 + 高频噼啪
    zap(dur, seed, lo = 70, hi = 190, center = 2200) {
      const r = D.rng(seed), steps = [];
      for (let k = 0; k < Math.ceil(dur / .004) + 1; k++) steps.push(lo + r() * (hi - lo));
      const buzz = D.drive(D.osc(dur, t => steps[Math.floor(t / .004)], 1, 'saw'), 3.5);
      return D.mix([D.bp(buzz, center, .7), 1], [D.hp(D.crackle(dur, 900 * dur + 40, 1, seed + 3, .0015), 2500), .8]);
    },
    // 雷声：脆裂 + 隆隆尾音
    thunder(dur, seed) {
      const crack = D.hp(D.noise(.12, D.ad(.0004, .025), 'white', seed), 900);
      const roll = D.lp(D.noise(dur, t => D.ad(.02, dur * .35)(t) * (.7 + .3 * Math.sin(t * 23 + Math.sin(t * 7) * 3)), 'brown', seed + 1), 260);
      return D.mix([crack, 1.2], [roll, 2.4], [K.zap(.25, seed + 2), .5]);
    },
    // 火焰：噼啪 + 呼呼的带通噪声
    fire(dur, seed, density = 120, amp = 1) {
      const base = D.filter(D.noise(dur, amp, 'pink', seed), 'bp', 900, .6);
      return D.mix([base, .5], [D.hp(D.crackle(dur, density * dur, amp, seed + 2, .003), 1500), 1]);
    },
    // 喉音：锯齿 + 粗糙度调幅 → 共振峰（Boss 吼叫）
    growl(dur, f0, rough, formants, seed, breath = .35, driveAmt = 2) {
      const r = D.rng(seed), jit = r() * 10;
      const src = D.osc(dur, t => D.val(f0, t) * (1 + .025 * Math.sin(TAU * 5.3 * t + jit)), 1, 'saw');
      const am = D.shape(src, t => .5 + .5 * Math.sin(TAU * rough * t + 1.4 * Math.sin(TAU * rough * .31 * t + jit)));
      const exc = D.mix([am, 1], [D.noise(dur, breath, 'pink', seed + 1), 1]);
      return D.drive(D.mix(...formants.map(([f, q, g]) => [D.filter(exc, 'bp', f, q), g])), driveAmt);
    },
    // 合唱 / 哀嚎：多条失谐的元音锯齿
    wail(dur, f0, voices, seed, vowel = [[500, 4, 1], [900, 5, .6], [2500, 8, .25]], env = null) {
      const r = D.rng(seed), parts = [];
      for (let v = 0; v < voices; v++) {
        const det = 1 + (r() - .5) * .03, rate = 4 + r() * 2, ph = r() * TAU;
        const tone = D.osc(dur, t => D.val(f0, t) * det * (1 + .012 * Math.sin(TAU * rate * t + ph)), 1, 'saw');
        parts.push([D.mix(...vowel.map(([f, q, g]) => [D.filter(tone, 'bp', f, q), g])), 1 / voices]);
      }
      const out = D.mix(...parts);
      return env ? D.shape(out, env) : out;
    },
    // 气泡：随机频率的上滑短正弦
    bubbles(dur, n, seed, lo = 300, hi = 900) {
      const r = D.rng(seed), parts = [];
      for (let k = 0; k < n; k++) { const f = lo + r() * (hi - lo); parts.push([D.osc(.06, D.glide(f, f * 1.8, .05), D.ad(.002, .02)), .3 + r() * .5, r() * dur]); }
      return D.mix(...parts);
    },
    // 快速连发的针尖滴答
    ticks(dur, n, seed, accel = 1, hpf = 4500) {
      const r = D.rng(seed), parts = [];
      for (let k = 0; k < n; k++) { const u = (k / n) ** accel; parts.push([D.mix([K.click(.008, hpf, seed + k), 1], [K.ping(.04, 5200 + r() * 3000, .015, seed + k), .5]), .4 + r() * .6, u * dur]); }
      return D.mix(...parts);
    },
    // 拨弦（古筝风格）
    zheng: (f, dur = 1.2, seed = 1, t60 = 1.4, bright = .7) => D.pluck(dur, f, t60, bright, seed),
    // 太鼓
    taiko(dur, seed, f = 62) {
      return D.mix([K.thump(dur, f * 2.1, f, .03, .32), 1], [D.lp(D.noise(dur, D.ad(.001, .05), 'pink', seed), 1100), .5], [K.click(.01, 2500, seed + 1), .15]);
    },
    // 大锣：密集不和谐泛音，带渐强的嗡鸣
    gong(dur, f, seed) {
      const r = D.rng(seed), modes = [];
      for (let k = 0; k < 26; k++) modes.push([f * (1 + k * .37 + r() * .2) * (1 + r() * .01), 1 / (1 + k * .18), dur * (.35 - k * .009)]);
      const body = D.shape(D.modal(dur, modes, seed), D.env([[0, .5], [.12, 1], [dur, 1]]));
      return D.mix([body, 1], [K.thump(dur, f * 1.5, f, .05, .5), .6], [D.lp(D.noise(dur, D.ad(.002, .2), 'pink', seed + 2), 3000), .2]);
    },
    // 只记录扩宽量：单声道存储，立体感由引擎的扩宽总线在运行时生成（省一半内存）
    stereo: (x, amount = .5) => { x.wide = amount; return x; }
  };

  /* ---------- 配方 ---------- */
  const R = {};
  // 目标响度（dBFS，150 ms 近似 K 加权 RMS，增益为 1、居中时）：所有缓冲统一归一到 -20 dB，
  // 运行时增益由目标推算；配方里的 gain 只作为同类内的微调（1 = 不调）。
  const LU = [
    [/^shot\d$/, -22], [/^tint\d$/, -30], [/^pulse\d$/, -20], [/^skill\d$/, -14], [/^ult\d$/, -11],
    [/^(hit|armor)$/, -25], [/^bosshit$/, -22], [/^crit$/, -27], [/^kill$/, -26], [/^elitekill$/, -18], [/^bossdie$/, -10],
    [/^(chain|shatter|bomb)$/, -24], [/^(drain|stun|freeze)$/, -23], [/^dash$/, -22], [/^block$/, -20],
    [/^hurt$/, -17], [/^shieldhit$/, -21], [/^shieldbreak$/, -16], [/^(downed|revive)$/, -15], [/^heartbeat$/, -19],
    [/^(levelup|chest|breakout)$/, -15], [/^upgrade$/, -19], [/^ultready$/, -17], [/^heal$/, -24], [/^orb$/, -27],
    [/^roar\d$/, -11], [/^volley\d$/, -22], [/^boom\d?$/, -18], [/^(warn|warnlane)$/, -21], [/^eshot$/, -27],
    [/^(summon|charge|zone)$/, -19], [/^enrage$/, -12], [/^(stage|wave)$/, -13], [/^(win|fail)$/, -12],
    [/^ui_click$/, -26], [/^(ui_select|ui_back|route)$/, -22], [/^(ui_confirm|ui_open)$/, -20], [/^(camp|reward)$/, -18], [/^amb_/, -31]
  ];
  const BASE = -20;
  // 渲染采样率：默认 32 kHz（16 kHz 以上在游戏里几乎不可闻，省内存）；低沉的声音用 22.05 kHz
  const DARK = /^(boom\d?|bossdie|stage|wave|downed|heartbeat|hurt|charge|summon|bosshit|block|roar[0236]|amb_(creak|gust|bell|anvil|whisper))$/;
  const def = (name, meta, render) => {
    const lu = meta.lu ?? (LU.find(([re]) => re.test(name)) || [0, -22])[1];
    R[name] = { gap: .06, max: 4, pri: 2, send: .12, vars: 1, pj: 0, duck: 0, rate: DARK.test(name) ? 22050 : 32000, ...meta, lu, trim: 1, gain: 10 ** ((lu - BASE) / 20), render };
  };

  // —— 英雄：普攻齐射（频繁，短而有辨识度）——
  def('shot0', { gap: .11, max: 3, vars: 3, pj: .8, send: .08 }, s => D.mix(
    [K.whoosh(.16, 2600, 6200, 1.1, s, .22, 'white'), .55],
    [K.metal(.24, 2200 + (s % 7) * 40, s, .09, .65), .32]));
  def('shot1', { gap: .13, max: 3, vars: 3, pj: .7, send: .08 }, s => D.mix(
    [K.whoosh(.28, 180, 720, .9, s, .35), 1.2],
    [K.thump(.2, 120, 72, .04, .07), .35],
    [D.shape(K.fire(.26, s + 5, 160), D.ad(.01, .09)), .35]));
  def('shot2', { gap: .1, max: 3, vars: 3, pj: .6, send: .06 }, s => D.mix([D.shape(K.zap(.2, s, 80, 210, 2600), D.ad(.001, .075)), 1], [K.whoosh(.14, 1800, 4200, 1.2, s + 7, .2, 'white'), .3]));
  def('shot3', { gap: .09, max: 3, vars: 3, pj: 1, send: .06 }, s => D.mix(
    [K.ticks(.1, 6, s), .8],
    [D.osc(.16, D.glide(3400, 5400, .14), D.swell(.16, .3), 'sine'), .25],
    [K.whoosh(.16, 3000, 6500, 1.4, s + 9, .25, 'white'), .35]));
  def('shot4', { gap: .11, max: 3, vars: 5, pj: 0, send: .2 }, s => D.mix(
    [K.whoosh(.22, 1100, 2600, 1.4, s, .3), .7],
    [K.ping(.3, penta(10 + (s % 5)), .16, s), .28]));
  def('shot5', { gap: .11, max: 3, vars: 3, pj: 1, send: .16 }, s => D.mix(
    [K.glass(.2, 3300 + (s % 5) * 170, s, .1), .5],
    [D.hp(D.noise(.18, D.ad(.002, .05), 'white', s), 6000), .35],
    [D.hp(D.crackle(.1, 60, 1, s + 2, .001), 4000), .25]));

  // —— 英雄：技能 E ——
  def('skill0', { gap: .3, max: 2, pri: 4, send: .28, duck: .15 }, s => K.stereo(D.mix(
    [K.whoosh(.5, 380, 3200, .7, s, .45), 1.1],
    [K.metal(1, 880, s, .55, .8), .45, .08], [K.metal(1, 1318, s + 1, .45, .7), .3, .1],
    [K.thump(.4, 130, 48, .05, .18), .7, .08]), .4, s));
  def('skill1', { gap: .3, max: 2, pri: 4, send: .26, duck: .2 }, s => K.stereo(D.mix(
    [K.whoosh(.45, 150, 900, .8, s, .6), 1.2],
    [K.boom(.9, s + 1, 380, 70, .4), 1, .3],
    [D.shape(K.fire(1.1, s + 2, 100), D.ad(.05, .4)), .45, .32]), .45, s));
  def('skill2', { gap: .3, max: 2, pri: 4, send: .3, duck: .18 }, s => K.stereo(D.mix(
    [K.thunder(1.1, s), 1],
    [D.shape(K.zap(.45, s + 4, 90, 260, 1900), D.ad(.002, .2)), .55]), .55, s));
  def('skill3', { gap: .3, max: 2, pri: 4, send: .22, duck: .1 }, s => K.stereo(D.mix(
    [K.ticks(.38, 16, s, .6), .9],
    [K.riser(.42, 900, 5200, s + 1, .1), .45],
    [K.sparkle(.25, 5, s + 2, 12, 18, .08), .35, .32]), .5, s));
  def('skill4', { gap: .3, max: 2, pri: 4, send: .38, duck: .1 }, s => K.stereo(D.mix(
    [K.whoosh(.65, 900, 2500, 1.6, s, .4), .8],
    ...[0, 1, 2, 3, 4, 5].map(k => [K.ping(.6, penta(7 + k), .4, s + k, .3), .3, k * .065]),
    [K.thump(.3, 180, 80, .04, .12), .3]), .6, s));
  def('skill5', { gap: .3, max: 2, pri: 4, send: .35, duck: .15 }, s => {
    const r = D.rng(s);
    return K.stereo(D.mix(
      [D.hp(K.whoosh(.6, 6500, 1500, .8, s, .25, 'white'), 1200), .9],
      ...[0, 1, 2, 3, 4, 5].map(k => [K.glass(.5, 2000 + r() * 4000, s + k, .2), .25, .03 + r() * .2]),
      [K.thump(.5, 95, 55, .06, .25), .55],
      [D.hp(D.crackle(.8, 70, D.ad(.02, .3), s + 9, .002), 2200), .5]), .55, s);
  });

  // —— 英雄：无双起手（大，压低配乐）——
  def('ult0', { gap: 1, max: 1, pri: 6, send: .4, duck: .55 }, s => K.stereo(D.mix(
    [D.shape(D.mix([K.metal(.6, 1760, s, .5, 1), 1], [K.metal(.6, 2637, s + 1, .5, 1), .7]), t => (t / .55) ** 2 * (t < .55 ? 1 : 0)), .35],
    [K.riser(.55, 600, 4800, s + 2, .15), .5],
    [K.boom(1.6, s + 3, 500, 55, .6), 1.1, .55],
    [K.metal(2, 440, s + 4, 1.2, .9), .55, .55], [K.metal(2, 660, s + 5, 1.1, .8), .4, .56], [K.metal(2, 880, s + 6, 1, .7), .3, .57]), .5, s));
  def('ult1', { gap: 1, max: 1, pri: 6, send: .36, duck: .55 }, s => K.stereo(D.mix(
    [D.shape(K.fire(.65, s, 200), t => (t / .6) ** 1.5), .9],
    [K.whoosh(.65, 200, 1600, .7, s + 1, .85), 1],
    [K.boom(1.8, s + 2, 600, 45, .7), 1.3, .6],
    [D.shape(K.fire(1.6, s + 3, 140), D.ad(.02, .6)), .6, .62]), .55, s));
  def('ult2', { gap: 1, max: 1, pri: 6, send: .42, duck: .55 }, s => {
    const r = D.rng(s), zaps = [];
    for (let k = 0; k < 6; k++) zaps.push([D.shape(K.zap(.2, s + k, 90, 300, 2400), D.ad(.001, .07)), .4, .1 + r() * 1.3]);
    const howl = K.wail(1.3, D.env([[0, 330], [.5, 560], [1.3, 420]]), 2, s + 9, [[400, 3, 1], [800, 4, .5]], D.swell(1.3, .45));
    return K.stereo(D.mix([K.thunder(2, s), 1.3], ...zaps, [howl, .25, .15]), .6, s);
  });
  def('ult3', { gap: 1, max: 1, pri: 6, send: .3, duck: .5 }, s => K.stereo(D.mix(
    [K.ticks(1.6, 70, s, .7), 1],
    [K.whoosh(1.7, 700, 5000, .5, s + 1, .4, 'white', 1), .45],
    [K.riser(.35, 800, 4000, s + 2, .1), .4]), .65, s));
  def('ult4', { gap: 1, max: 1, pri: 6, send: .5, duck: .5 }, s => K.stereo(D.mix(
    [K.wail(1.8, D.mtof(55), 3, s, [[730, 5, 1], [1090, 6, .5], [2440, 9, .2]], D.swell(1.8, .4)), .7],
    [K.wail(1.8, D.mtof(62), 3, s + 1, [[730, 5, 1], [1090, 6, .5], [2440, 9, .2]], D.swell(1.8, .45)), .55],
    [K.wail(1.8, D.mtof(71), 2, s + 2, [[730, 5, 1], [1090, 6, .5], [2440, 9, .2]], D.swell(1.8, .5)), .4],
    [K.whoosh(1.4, 700, 2600, 1.3, s + 3, .5), .5],
    [K.sparkle(1.2, 12, s + 4, 10, 20, .2), .4, .2]), .7, s));
  def('ult5', { gap: 1, max: 1, pri: 6, send: .5, duck: .55 }, s => {
    const r = D.rng(s), shards = [];
    for (let k = 0; k < 12; k++) shards.push([K.glass(.9, 1800 + r() * 5000, s + k, .35), .22, .5 + r() * .18]);
    return K.stereo(D.mix(
      [D.hp(K.whoosh(1.2, 9000, 900, .7, s, .4, 'white'), 600), .9],
      ...shards,
      [K.boom(1.4, s + 20, 300, 50, .5), .8, .5],
      [D.lp(D.mix([D.osc(2.2, 55, D.env([[0, 0], [.5, 1], [2.2, 0]])), 1], [D.osc(2.2, 55.6, D.env([[0, 0], [.5, 1], [2.2, 0]])), 1]), 300), .35]), .6, s);
  });

  // —— 英雄：无双持续期间的脉冲 ——
  def('pulse0', { gap: .2, max: 2, vars: 3, pj: .8, send: .2 }, s => D.mix(
    [K.whoosh(.12, 4000, 1200, 1, s, .7, 'white'), .6], [K.thump(.25, 160, 60, .03, .08), .8, .1], [K.metal(.3, 1980, s, .15, .7), .25, .1]));
  def('pulse1', { gap: .2, max: 2, vars: 3, pj: .7, send: .2 }, s => D.mix(
    [K.whoosh(.3, 250, 1100, .9, s, .4), 1], [D.shape(K.fire(.3, s + 1, 180), D.ad(.01, .1)), .45], [K.thump(.25, 110, 55, .03, .1), .5, .05]));
  def('pulse2', { gap: .2, max: 2, vars: 3, pj: .5, send: .22 }, s => D.mix(
    [D.hp(D.noise(.08, D.ad(.0004, .02), 'white', s), 1200), .9], [D.shape(K.zap(.25, s + 1, 90, 260, 2000), D.ad(.001, .08)), .6], [D.lp(D.noise(.5, D.ad(.01, .15), 'brown', s + 2), 200), 1.2]));
  def('pulse3', { gap: .11, max: 3, vars: 3, pj: 1, send: .1 }, s => K.ticks(.12, 6, s, .8));
  def('pulse4', { gap: .2, max: 2, vars: 5, pj: 0, send: .35 }, s => D.mix(
    [K.thump(.3, 200, 90, .04, .1), .5], [K.ping(.5, penta(5 + (s % 5) * 2), .3, s, .3), .4], [K.whoosh(.3, 800, 1800, 1.2, s, .3), .4]));
  def('pulse5', { gap: .2, max: 2, vars: 3, pj: 1, send: .3 }, s => D.mix(
    [K.glass(.35, 2600 + (s % 5) * 300, s, .14), .55], [D.hp(D.noise(.1, D.ad(.0005, .02), 'white', s + 1), 2500), .6], [K.thump(.2, 140, 70, .03, .06), .4]));

  // —— 英雄：命中附色（叠在通用命中之上，轻）——
  def('tint0', { gap: .09, max: 2, vars: 3, pj: 1.5, send: .05 }, s => K.metal(.16, 3100, s, .075, .5));
  def('tint1', { gap: .09, max: 2, vars: 3, pj: 1, send: .05 }, s => D.mix([D.hp(D.noise(.16, D.ad(.002, .07), 'white', s), 3000), .7], [D.hp(D.crackle(.14, 70, 1, s + 1, .003), 2000), .45]));
  def('tint2', { gap: .09, max: 2, vars: 3, pj: 1, send: .05 }, s => D.shape(K.zap(.12, s, 120, 300, 3200), D.ad(.0005, .045)));
  def('tint3', { gap: .07, max: 2, vars: 3, pj: 2, send: .03 }, s => D.mix([K.click(.01, 5000, s), .4], [K.ping(.1, 6200, .04, s + 1, .2), .7], [K.ping(.1, 8300, .03, s + 2, .2), .35, .012]));
  def('tint4', { gap: .1, max: 2, vars: 5, pj: 0, send: .2 }, s => K.ping(.22, penta(12 + (s % 5)), .11, s));
  def('tint5', { gap: .09, max: 2, vars: 3, pj: 1.5, send: .12 }, s => K.glass(.18, 4300, s, .08));

  // —— 武器 / 招式附加事件 ——
  def('chain', { gap: .08, max: 2, vars: 3, pj: 1, send: .12 }, s => D.shape(K.zap(.24, s, 100, 320, 2800), D.ad(.001, .1)));
  def('drain', { gap: .35, max: 1, vars: 2, send: .3 }, s => D.mix([D.osc(.35, D.glide(700, 1400, .3), D.swell(.35, .3), 'sine'), .4], [K.sparkle(.2, 3, s, 12, 17, .08), .5]));
  def('shatter', { gap: .07, max: 3, vars: 4, pj: 1.2, send: .2 }, s => {
    const r = D.rng(s);
    return D.mix([K.glass(.3, 2400 + r() * 1500, s, .1), .5], [K.glass(.3, 3800 + r() * 2000, s + 1, .08), .35, .01], [D.hp(D.noise(.1, D.ad(.0005, .025), 'white', s + 2), 3000), .6]);
  });
  def('stun', { gap: .2, max: 2, send: .15 }, s => D.mix([D.bp(D.osc(.42, 118, D.ad(.005, .18), 'square'), 900, 1.4), .7], [D.hp(D.crackle(.4, 120, D.ad(.005, .2), s, .0015), 3000), .6]));
  def('freeze', { gap: .2, max: 2, send: .3 }, s => D.mix(...[0, 1, 2, 3, 4].map(k => [K.glass(.3, 1800 * 1.25 ** k, s + k, .12), .3, k * .035]), [D.hp(D.noise(.35, D.swell(.35, .2), 'white', s), 5000), .3]));
  def('bomb', { gap: .07, max: 3, vars: 3, pj: 1, send: .2 }, s => D.mix([K.thump(.3, 220, 80, .02, .09), .9], [K.click(.015, 1500, s), .5], [K.sparkle(.2, 4, s + 1, 14, 20, .06), .5, .01]));
  def('dash', { gap: .12, max: 2, vars: 3, pj: .6, send: .08 }, s => D.mix([K.whoosh(.24, 450, 2400, .8, s, .3), 1.1], [K.thump(.15, 90, 60, .04, .05), .25]));
  def('block', { gap: .2, max: 2, vars: 2, send: .1 }, s => D.mix([K.thump(.3, 110, 60, .03, .09), 1], [K.plate(.25, 380, s, .1), .35], [K.click(.01, 1200, s), .4]));

  // —— 通用命中 / 击杀 ——
  def('hit', { gap: .055, max: 4, vars: 4, pj: 1.2, send: .04 }, s => D.mix(
    [K.click(.006, 1500, s), .35], [D.bp(D.noise(.14, D.ad(.001, .05), 'white', s + 1), 900, .9), 1], [D.lp(D.noise(.14, D.ad(.002, .05), 'pink', s + 2), 500), .8], [K.thump(.14, 170, 75, .015, .06), .7]));
  def('armor', { gap: .07, max: 3, vars: 3, pj: 1, send: .08 }, s => D.mix([K.plate(.26, 760 + (s % 3) * 90, s, .13), .6], [K.click(.006, 1800, s + 1), .3], [K.thump(.14, 150, 80, .02, .05), .5]));
  def('bosshit', { gap: .11, max: 2, vars: 3, pj: .8, send: .12 }, s => D.mix([K.thump(.35, 100, 45, .03, .12), 1], [K.plate(.3, 300, s, .16), .35], [D.bp(D.noise(.15, D.ad(.001, .05), 'white', s + 1), 650, .8), .7]));
  def('crit', { gap: .18, max: 2, vars: 2, pj: 1, send: .1 }, s => D.mix([K.ping(.22, 2500, .12, s, .4), .7], [K.ping(.22, 3750, .08, s + 2, .3), .3], [K.click(.006, 3000, s + 1), .2]));
  def('kill', { gap: .065, max: 4, vars: 4, pj: 1.5, send: .1 }, s => D.mix(
    [D.filter(D.noise(.26, D.ad(.002, .1), 'white', s), 'bp', D.glide(3200, 600, .22), 1.2), 1], [D.lp(D.noise(.2, D.ad(.002, .06), 'pink', s + 2), 700), .5], [K.sparkle(.1, 2, s + 1, 13, 19, .05), .35]));
  def('elitekill', { gap: .15, max: 2, vars: 2, pri: 3, send: .25 }, s => K.stereo(D.mix(
    [K.boom(.7, s, 600, 80, .25), .9], [K.plate(.6, 520, s + 1, .3), .3], [D.hp(D.crackle(.5, 90, D.ad(.002, .15), s + 2, .002), 1500), .5], [K.sparkle(.3, 4, s + 3, 10, 16, .1), .4, .05]), .4, s));
  def('bossdie', { gap: 2, max: 1, pri: 8, send: .5, duck: .75 }, s => K.stereo(D.mix(
    [K.boom(3.2, s, 700, 35, 1.1), 1.5], [K.thump(2, 60, 28, .2, .9), .8],
    [D.shape(K.fire(3, s + 1, 120), D.ad(.03, 1)), .5], [K.gong(3.4, 110, s + 2), .45, .08],
    ...[0, 1, 2, 3].map(k => [K.plate(1.2, 400 + k * 230, s + 3 + k, .5), .15, .1 + k * .12])), .7, s));

  // —— 主角状态 ——
  def('hurt', { gap: .22, max: 1, pri: 5, send: .06 }, s => D.drive(D.mix([K.thump(.28, 140, 50, .03, .09), 1], [D.lp(D.noise(.12, D.ad(.001, .04), 'white', s), 1600), .8]), 2.2));
  def('shieldhit', { gap: .16, max: 1, pri: 4, vars: 2, send: .15 }, s => D.mix([D.fm(.25, 620, 1.5, D.ad(.001, .05), D.ad(.002, .08), s), .6], [K.glass(.25, 1850, s, .09), .3]));
  def('shieldbreak', { gap: .5, max: 1, pri: 5, send: .3, duck: .15 }, s => {
    const r = D.rng(s);
    return K.stereo(D.mix(...[0, 1, 2, 3, 4, 5, 6, 7].map(k => [K.glass(.5, 1500 + r() * 4500, s + k, .2), .25, r() * .06]), [D.hp(D.noise(.3, D.ad(.0005, .06), 'white', s + 9), 1800), .8], [D.osc(.4, D.glide(900, 200, .35), D.ad(.002, .12)), .25]), .5, s);
  });
  def('downed', { gap: 1, max: 1, pri: 7, send: .45, duck: .4 }, s => D.mix([D.lp(D.osc(1.3, D.glide(220, 52, 1.1), D.ad(.01, .5), 'saw'), 900), .6], [K.thump(.6, 90, 40, .08, .3), .9], [K.bell(2, 196, s, 1.4), .2, .1]));
  def('revive', { gap: .6, max: 1, pri: 6, send: .45, duck: .2 }, s => K.stereo(D.mix(
    [K.whoosh(.8, 500, 3000, 1, s, .8), .5], ...[0, 1, 2, 3, 4].map(k => [K.zheng(penta(5 + k * 2), 1.2, s + k, 1.4), .32, k * .07]), [K.sparkle(.6, 6, s + 9, 12, 20, .15), .4, .35]), .5, s));
  def('levelup', { gap: .4, max: 1, pri: 5, send: .38, duck: .15 }, s => K.stereo(D.mix(
    ...[0, 2, 4, 5, 7].map((k, i) => [K.zheng(penta(5 + k), 1.4, s + i, 1.6, .75), .35, i * .055]),
    [K.sparkle(.5, 7, s + 9, 14, 21, .12), .35, .2], [K.bell(1.6, 784, s + 10, 1), .12, .25]), .55, s));
  def('upgrade', { gap: .15, max: 1, pri: 4, send: .25 }, s => D.mix([K.zheng(penta(9), .7, s, 1, .8), .5], [K.zheng(penta(12), .8, s + 1, 1.2, .8), .5, .07], [K.sparkle(.2, 3, s + 2, 15, 20, .08), .3, .1]));
  def('ultready', { gap: 2, max: 1, pri: 5, send: .45 }, s => K.stereo(D.mix([K.bell(2.4, 392, s, 1.4), .45], [K.riser(.35, 1500, 6000, s + 1, 0), .25], [K.sparkle(.4, 5, s + 2, 15, 22, .1), .35, .3]), .5, s));
  def('breakout', { gap: 1, max: 1, pri: 5, send: .35, duck: .25 }, s => K.stereo(D.mix(
    [K.taiko(.8, s, 65), 1], [K.whoosh(.6, 400, 3500, .9, s + 1, .7), .6], ...[0, 2, 4].map((k, i) => [K.zheng(penta(10 + k), 1.2, s + 2 + i, 1.4), .3, .08 + i * .04])), .5, s));
  def('heartbeat', { gap: .3, max: 1, pri: 3, send: .04 }, s => D.lp(D.mix([K.thump(.3, 72, 40, .025, .07), 1], [K.thump(.3, 66, 38, .025, .06), .7, .17]), 400));
  def('heal', { gap: .12, max: 2, vars: 2, send: .25 }, s => D.mix([K.ping(.4, 1046.5, .22, s, .3), .5], [K.ping(.4, 1568, .2, s + 1, .3), .35, .05]));
  def('orb', { gap: .045, max: 5, vars: 1, send: .12 }, s => D.mix([K.ping(.16, 1318.5, .06, s, .3), 1], [K.click(.004, 6000, s), .2]));
  def('chest', { gap: .4, max: 1, pri: 5, send: .38, duck: .2 }, s => K.stereo(D.mix(
    [K.metal(.9, 1760, s, .5, .9), .35],                                   // 超频剑：剑鸣
    [D.osc(.6, D.glide(500, 2400, .5), D.swell(.6, .7), 'tri'), .18, .1],  // 蓄能棱晶：上扬
    [K.glass(1, 1200, s + 1, .5), .3, .12],
    [K.bell(1.6, 523, s + 2, 1.1), .25, .24],                              // 纹章盾：低钟
    [K.sparkle(.6, 8, s + 3, 12, 22, .12), .4, .05]), .6, s));

  // —— Boss：登场吼叫（每位一种）——
  const roar = (name, fn) => def(name, { gap: 1.5, max: 1, pri: 8, send: .5, duck: .6 }, fn);
  roar('roar0', s => K.stereo(D.mix(
    [D.shape(K.growl(2.2, D.env([[0, 62], [.4, 74], [2.2, 52]]), 34, [[600, 3, 1], [1000, 4, .6], [2400, 6, .2]], s, .4), D.swell(2.2, .25, 1)), 1],
    [D.shape(K.fire(2.2, s + 1, 110), D.swell(2.2, .3)), .5], [K.boom(1.4, s + 2, 300, 40, .6), .8, .05]), .5, s));
  roar('roar1', s => K.stereo(D.mix(
    [D.shape(K.growl(2.2, D.env([[0, 280], [.5, 520], [1.4, 380], [2.2, 240]]), 18, [[1200, 5, 1], [2600, 6, .6], [3800, 8, .3]], s, .5, 1.6), D.swell(2.2, .3, 1)), 1],
    [D.hp(D.noise(2.2, D.swell(2.2, .35), 'white', s + 1), 4000), .3],
    ...[0, 1, 2, 3].map(k => [K.glass(.8, 2500 + k * 900, s + 3 + k, .3), .15, .3 + k * .2])), .6, s));
  roar('roar2', s => K.stereo(D.mix(
    [D.shape(K.growl(2, D.env([[0, 88], [.3, 102], [2, 70]]), 27, [[500, 3, 1], [900, 4, .7], [2200, 6, .2]], s, .6, 2.4), D.swell(2, .2, 1)), 1],
    [D.lp(D.noise(2, D.swell(2, .25), 'pink', s + 1), 1800), .6], [K.thump(.8, 80, 35, .1, .4), .6]), .5, s));
  roar('roar3', s => K.stereo(D.mix(
    [K.wail(2.4, D.env([[0, 196], [.8, 220], [2.4, 165]]), 5, s, [[350, 4, 1], [700, 5, .5], [2500, 9, .15]], D.swell(2.4, .4)), 1],
    [D.lp(D.osc(2.4, 49, D.swell(2.4, .3), 'saw'), 300), .5],
    [D.bp(D.crackle(2, 40, D.swell(2, .5), s + 1, .008), 1400, 1.5), 1.2, .3]), .7, s));
  roar('roar4', s => K.stereo(D.mix(
    [D.lp(D.osc(1.8, D.env([[0, 180], [.6, 880], [1.8, 700]]), D.swell(1.8, .4), 'square'), 3000), .35],
    [D.lp(D.mix([D.osc(1.6, 233, 1, 'square'), 1], [D.osc(1.6, 277, 1, 'square'), 1], [D.osc(1.6, 349, 1, 'square'), .7]), 1600), .25, .4],
    [K.plate(1.2, 180, s, .6), .5], [D.hp(D.noise(1.4, D.ad(.3, .5), 'white', s + 1), 3000), .25, .6], [K.boom(1, s + 2, 300, 40, .4), .7]), .5, s));
  roar('roar5', s => K.stereo(D.mix(
    [K.wail(2.6, D.env([[0, 330], [1.2, 440], [2.6, 392]]), 6, s, [[500, 4, 1], [900, 5, .6], [2600, 8, .2]], D.swell(2.6, .55)), .9],
    [K.wail(2.6, D.env([[0, 247], [1.2, 294], [2.6, 262]]), 4, s + 1, [[400, 4, 1], [800, 5, .5]], D.swell(2.6, .6)), .6],
    [D.hp(D.noise(1.6, t => (t / 1.6) ** 3, 'pink', s + 2), 500), .5], [K.bell(2.6, 220, s + 3, 1.5), .35, 1.4]), .7, s));
  roar('roar6', s => K.stereo(D.mix(
    ...[0, 1, 2].map(k => [D.shape(K.growl(1.5, D.env([[0, 120 + k * 45], [.4, 150 + k * 50], [1.5, 100 + k * 40]]), 22 + k * 6, [[700 + k * 200, 3, 1], [1600 + k * 300, 5, .5]], s + k, .9, 1.8), D.swell(1.5, .3)), .55, k * .28]),
    [K.bubbles(2.2, 30, s + 5, 150, 600), .4]), .6, s));
  roar('roar7', s => K.stereo(D.mix(
    [D.shape(K.growl(2.4, D.env([[0, 700], [.5, 1250], [1.5, 1050], [2.4, 820]]), 14, [[1800, 4, 1], [3200, 6, .5], [5000, 8, .2]], s, .3, 1.5), D.swell(2.4, .3)), .9],
    [K.wail(2.4, D.mtof(57), 4, s + 1, [[730, 5, 1], [1090, 6, .5], [2440, 9, .2]], D.swell(2.4, .5)), .5],
    [D.shape(K.fire(2.4, s + 2, 120), D.swell(2.4, .35)), .4], [K.boom(1.6, s + 3, 500, 40, .7), .8, .1]), .6, s));

  // —— Boss：弹幕发射（每位元素不同）——
  const volley = (b, fn) => def('volley' + b, { gap: .14, max: 2, vars: 2, pj: .8, send: .2 }, fn);
  volley(0, s => D.mix([K.whoosh(.35, 300, 1500, .8, s, .3), .9], [D.shape(K.fire(.35, s + 1, 160), D.ad(.01, .12)), .5]));
  volley(1, s => D.mix([D.hp(K.whoosh(.35, 4000, 1500, 1, s, .25, 'white'), 1000), .7], [K.glass(.3, 2800, s + 1, .12), .3], [K.glass(.3, 3700, s + 2, .1), .2, .03]));
  volley(2, s => D.mix([K.whoosh(.3, 150, 600, .7, s, .4), 1.2], [K.thump(.3, 90, 50, .04, .1), .6]));
  volley(3, s => D.mix([K.whoosh(.4, 600, 1200, 2, s, .35), .6], [D.osc(.4, D.glide(660, 330, .35), D.swell(.4, .2), 'tri'), .2]));
  volley(4, s => D.mix([D.lp(D.osc(.25, D.glide(1600, 300, .2), D.ad(.002, .08), 'square'), 4000), .3], [D.osc(.25, D.glide(2200, 900, .15), D.ad(.001, .06)), .3]));
  volley(5, s => D.mix([K.wail(.4, D.glide(520, 440, .4), 2, s, [[600, 4, 1], [1100, 5, .5]], D.swell(.4, .3)), .4], [K.sparkle(.3, 3, s + 1, 12, 18, .08), .4]));
  volley(6, s => D.mix([D.shape(D.bp(D.noise(.35, 1, 'white', s), 900, 1.2), t => D.ad(.005, .1)(t) * (.6 + .4 * Math.sin(TAU * 40 * t))), 1], [K.bubbles(.35, 6, s + 1), .4]));
  volley(7, s => D.mix(...[0, 1, 2].map(k => [K.whoosh(.18, 1200, 3200, 1.2, s + k, .3), .6, k * .06]), [D.shape(K.fire(.4, s + 5, 120), D.ad(.01, .12)), .35]));

  // —— Boss：预警落地爆点（每位元素不同）——
  const boom = (b, fn) => def('boom' + b, { gap: .12, max: 3, vars: 2, pj: .6, pri: 3, send: .3 }, fn);
  boom(0, s => D.mix([K.boom(.9, s, 600, 60, .35), 1], [D.shape(K.fire(.8, s + 1, 140), D.ad(.005, .3)), .5], [K.whoosh(.4, 1500, 300, .8, s + 2, .1), .4]));
  boom(1, s => { const r = D.rng(s); return D.mix([K.thump(.5, 160, 60, .04, .15), .8], ...[0, 1, 2, 3, 4].map(k => [K.glass(.6, 1600 + r() * 3500, s + k, .22), .25, r() * .04]), [D.hp(D.noise(.4, D.ad(.001, .12), 'white', s + 9), 3000), .4]); });
  boom(2, s => D.mix([K.thump(.6, 90, 32, .06, .25), 1.2], [D.lp(D.crackle(.5, 160, D.ad(.002, .15), s, .01), 900), 1.4], [D.lp(D.noise(.6, D.ad(.002, .2), 'brown', s + 1), 400), 1.4]));
  boom(3, s => D.mix([K.boom(.8, s, 400, 50, .3), .8], [K.wail(.7, D.glide(300, 180, .6), 3, s + 1, [[400, 4, 1], [800, 5, .4]], D.ad(.01, .25)), .4]));
  boom(4, s => D.mix([D.shape(K.zap(.3, s, 100, 400, 2400), D.ad(.001, .1)), .5], [D.osc(.6, D.glide(900, 50, .4), D.ad(.002, .2)), .7], [K.click(.01, 1000, s + 1), .5], [K.plate(.5, 260, s + 2, .2), .3]));
  boom(5, s => D.mix([K.boom(.8, s, 450, 55, .3), .7], [K.wail(.8, D.glide(600, 400, .7), 3, s + 1, [[600, 4, 1], [1100, 5, .5]], D.ad(.005, .3)), .45], [K.sparkle(.4, 4, s + 2, 12, 18, .1), .3]));
  boom(6, s => D.mix([D.bp(D.noise(.6, D.ad(.002, .15), 'white', s), 700, .8), 1], [K.bubbles(.7, 14, s + 1, 200, 700), .5], [K.thump(.4, 110, 50, .04, .12), .6]));
  boom(7, s => D.mix([K.boom(.9, s, 700, 60, .35), .9], [D.shape(K.fire(.8, s + 1, 160), D.ad(.005, .3)), .45], [K.metal(.9, 1400, s + 2, .4, .6), .2]));
  boom('', s => D.mix([K.boom(.6, s, 500, 70, .25), 1], [K.click(.01, 1200, s + 1), .3]));

  // —— Boss / 敌方通用 ——
  def('warn', { gap: .14, max: 2, pri: 3, send: .15 }, s => D.mix([D.osc(.26, D.glide(520, 940, .24), D.swell(.26, .7), 'tri'), .45], [D.bp(D.noise(.26, D.swell(.26, .7), 'white', s), 1500, 2), .3]));
  def('warnlane', { gap: .16, max: 2, pri: 3, send: .15 }, s => D.mix([D.filter(D.osc(.45, 140, D.swell(.45, .8), 'saw'), 'bp', D.glide(400, 3200, .42), 3), .8], [D.osc(.45, 70, D.swell(.45, .8)), .25]));
  def('summon', { gap: .3, max: 1, pri: 4, send: .45 }, s => K.stereo(D.mix([D.lp(D.noise(.9, D.ad(.02, .3), 'brown', s), 300), 1.6], [K.wail(.9, D.glide(150, 300, .8), 3, s + 1, [[400, 4, 1], [800, 5, .4]], D.swell(.9, .6)), .4], [K.bell(1.2, 147, s + 2, .8), .2, .2]), .5, s));
  def('charge', { gap: .3, max: 1, pri: 4, send: .25 }, s => D.mix([K.whoosh(.7, 140, 650, .6, s, .55), 1.4], [D.lp(D.noise(.7, D.swell(.7, .5), 'brown', s + 1), 220), 1.4]));
  def('enrage', { gap: 2, max: 1, pri: 7, send: .45, duck: .55 }, s => K.stereo(D.mix([K.riser(1.1, 300, 4000, s, .35), .7], [K.boom(1.4, s + 1, 600, 40, .55), 1, 1.05], [K.taiko(1, s + 2, 55), .9, 1.05]), .6, s));
  def('zone', { gap: .25, max: 2, vars: 2, send: .25 }, s => D.mix([D.hp(D.noise(.8, D.ad(.03, .3), 'white', s), 1800), .35], [K.bubbles(.8, 10, s + 1, 150, 500), .5]));
  def('eshot', { gap: .1, max: 3, vars: 3, pj: 1.5, send: .08 }, s => D.mix([D.osc(.2, D.glide(950, 380, .16), D.ad(.002, .08), 'tri'), .8], [D.bp(D.noise(.15, D.ad(.002, .05), 'white', s), 1400, 1.5), .4], [K.click(.006, 2000, s), .15]));

  // —— 关卡节奏 ——
  def('stage', { gap: 2, max: 1, pri: 7, send: .5, duck: .5 }, s => K.stereo(D.mix([K.gong(3.2, 98, s), .9], [K.taiko(1.2, s + 1, 58), .9], [K.taiko(1.2, s + 2, 58), .6, .45]), .6, s));
  def('wave', { gap: 1.5, max: 1, pri: 5, send: .35, duck: .2 }, s => K.stereo(D.mix([K.taiko(.8, s, 66), .8], [K.taiko(.8, s + 1, 64), .7, .17], [K.taiko(1.1, s + 2, 56), 1, .36]), .5, s));

  // —— 界面 ——
  def('ui_click', { gap: .03, max: 2, send: .05 }, s => D.mix([K.ping(.14, 2100, .05, s, .2), .7], [K.ping(.14, 3150, .03, s + 2, .2), .25], [K.click(.004, 4000, s + 1), .15]));
  def('ui_select', { gap: .05, max: 2, vars: 5, send: .2 }, s => D.mix([K.zheng(penta(9 + (s % 5)), .8, s, 1.3, .8), .7], [K.ping(.3, penta(14 + (s % 5)), .14, s + 1), .25]));
  def('ui_confirm', { gap: .2, max: 1, pri: 4, send: .3 }, s => K.stereo(D.mix([K.zheng(penta(7), .9, s, 1.2, .8), .5], [K.zheng(penta(10), 1.1, s + 1, 1.4, .8), .5, .08], [K.whoosh(.5, 600, 3000, 1, s + 2, .7), .3], [K.taiko(.6, s + 3, 70), .35, .08]), .4, s));
  def('ui_back', { gap: .1, max: 1, send: .15 }, s => D.mix([K.zheng(penta(9), .5, s, .7, .7), .5], [K.zheng(penta(7), .6, s + 1, .8, .7), .5, .07]));
  def('ui_open', { gap: .1, max: 1, send: .2 }, s => D.mix([K.whoosh(.28, 700, 2400, 1.4, s, .6), .5], [K.ping(.3, penta(12), .12, s + 1, .3), .3, .12]));
  def('route', { gap: .15, max: 1, send: .3 }, s => D.mix([K.zheng(penta(5), .9, s, 1.2, .6), .5], [D.bp(D.mix([D.osc(.12, 620, D.ad(.001, .03)), 1], [K.click(.01, 800, s + 1), .4]), 620, 4), 1.4, .04]));
  def('camp', { gap: 1, max: 1, send: .45 }, s => K.stereo(D.mix(...[0, 4, 7, 9, 12].map((k, i) => [K.zheng(D.mtof(57 + k), 2, s + i, 2.2, .55), .3, i * .09]), [K.bell(2.4, 440, s + 9, 1.4), .1, .4]), .5, s));
  def('reward', { gap: .3, max: 1, send: .4 }, s => K.stereo(D.mix(...[0, 2, 4, 7].map((k, i) => [K.zheng(penta(7 + k), 1.3, s + i, 1.5, .75), .32, i * .06]), [K.sparkle(.5, 6, s + 8, 15, 22, .12), .3, .2]), .5, s));
  def('win', { gap: 2, max: 1, pri: 8, send: .5, duck: .9 }, s => K.stereo(D.mix(
    ...[0, 2, 4, 5, 7, 10].map((k, i) => [K.zheng(penta(5 + k), 1.8, s + i, 2, .8), .32, i * .085]),
    [K.taiko(1, s + 9, 62), .9, .5], [K.gong(3.4, 110, s + 10), .5, .5],
    [K.wail(2.6, D.mtof(55), 3, s + 11, [[730, 5, 1], [1090, 6, .5]], D.env([[0, 0], [.6, 1], [2.6, 0]])), .3, .5],
    [K.wail(2.6, D.mtof(62), 3, s + 12, [[730, 5, 1], [1090, 6, .5]], D.env([[0, 0], [.6, 1], [2.6, 0]])), .25, .5]), .6, s));
  def('fail', { gap: 2, max: 1, pri: 8, send: .6, duck: .9 }, s => {
    // 下行羽调式：E D B A E（笛声近似：正弦 + 气声）
    const notes = [76, 74, 71, 69, 64], parts = notes.map((m, i) => {
      const dur = i === 4 ? 1.8 : .5, f = D.mtof(m);
      const tone = D.mix([D.osc(dur, t => f * (1 + .006 * Math.sin(TAU * 5.2 * t) * Math.min(1, t * 3)), 1), 1], [D.osc(dur, f * 2, .18), 1], [D.bp(D.noise(dur, .25, 'white', s + i), f * 2, 3), 1]);
      return [D.shape(tone, D.env([[0, 0], [.05, 1], [dur * .7, .8], [dur, 0]])), .35, i * .42];
    });
    return K.stereo(D.mix(...parts, [K.taiko(1.4, s + 9, 48), .9, 0], [D.lp(D.osc(3.2, 41.2, D.ad(.05, 1.2), 'saw'), 200), .4]), .6, s);
  });

  // —— 环境点缀 ——
  def('amb_bell', { gap: 4, max: 1, pri: 1, send: .7 }, s => D.lp(K.bell(4.5, 330, s, 2.6), 2200));
  def('amb_drip', { gap: .05, max: 3, vars: 4, pj: 3, pri: 1, send: .4 }, s => D.mix([D.osc(.2, D.glide(900, 1900, .06), D.ad(.001, .06)), .8], [K.ping(.2, 2600, .05, s + 1, .2), .3, .02], [K.click(.004, 3000, s), .15]));
  def('amb_creak', { gap: 1, max: 1, vars: 2, pri: 1, send: .5 }, s => D.mix([D.bp(D.shape(D.osc(.9, D.glide(55, 70, .9), 1, 'saw'), t => D.swell(.9, .4)(t) * (.5 + .5 * Math.sin(TAU * 18 * t))), 700, 4), .8], [D.lp(D.crackle(.9, 40, D.swell(.9, .5), s, .006), 1500), .8]));
  def('amb_gust', { gap: 3, max: 1, vars: 2, pri: 1, send: .3 }, s => K.stereo(D.filter(D.noise(3, D.swell(3, .45), 'pink', s), 'bp', D.env([[0, 300], [1.4, 900], [3, 420]]), 1.2), .8, s));
  def('amb_ember', { gap: .15, max: 2, vars: 3, pri: 1, send: .2 }, s => D.mix([D.hp(D.crackle(.45, 90, D.ad(.002, .2), s, .004), 1200), 1], [D.bp(D.noise(.4, D.ad(.005, .15), 'pink', s + 1), 900, .8), .4]));
  def('amb_anvil', { gap: 3, max: 1, vars: 2, pri: 1, send: .7 }, s => D.lp(D.mix([K.plate(1.4, 640, s, .5), .6], [K.click(.01, 1500, s + 1), .3]), 2600));
  def('amb_whisper', { gap: 4, max: 1, vars: 2, pri: 1, send: .7 }, s => K.stereo(D.filter(D.noise(2.6, D.swell(2.6, .5), 'pink', s), 'bp', D.env([[0, 500], [1.3, 1200], [2.6, 700]]), 5), .9, s));
  def('amb_chime', { gap: 2, max: 1, vars: 3, pri: 1, send: .8 }, s => D.lp(K.bell(3, penta(17 + (s % 5)) / 2, s, 1.6), 5000));

  // 旧事件名 → 新配方（兼容其它模块的老调用）
  const ALIAS = { shot: 'shot0', skill: 'skill0', ultimate: 'ult0', heavy: 'bomb', level: 'levelup', pickup: 'ui_select', boss: 'roar0' };

  // 渲染一个变体：去直流、淡入淡出、按短时响度归一、裁掉尾部静音。返回 { data, wide, rate }
  function render(name, variant = 0) {
    const r = R[name];
    if (!r) throw new Error('Unknown sound: ' + name);
    return D.withRate(r.rate, () => {
      const out = r.render(D.hash(name) + variant * 7919), wide = out.wide || 0;
      return { data: D.trim(D.level(D.finish(out, 0), 10 ** (BASE / 20))), wide, rate: r.rate };
    });
  }
  return { recipes: R, alias: ALIAS, render, kit: K, penta };
})();
if (typeof module !== 'undefined') module.exports = NRSFX;
