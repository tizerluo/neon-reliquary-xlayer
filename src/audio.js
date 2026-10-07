/* 音频引擎：Web Audio 图、分轨混音、混响、配乐闪避、声部管理、配乐调度与区域环境声。
   声音全部来自 audio-sfx.js / audio-music.js 的程序化配方，空闲时预渲染，缺失时就地渲染。
   对外接口与旧版兼容：init / music / battle / pause / update / sfx / info / prepare / muted / voices；
   新增：stage(区域) / boss(编号) / bossRage() / bossDown() / duck()。 */
class NRAudio {
  constructor(options) {
    this.options = options; this.ctx = null; this.muted = false; this.paused = false; this.started = false;
    this.current = 'music_menu'; this.mix = 'musicCalm'; this.errors = [];
    this.last = {}; this.rr = {}; this.active = []; this.rand = NRDSP.rng(20261004);
    this.sfxCache = new Map(); this.noteCache = new Map(); this.drumCache = new Map(); this.compiled = new Map();
    this.queue = []; this.queued = new Set(); this.pumping = false;
    this.stageId = 0; this.bossType = -1; this.rage = false; this.hp = 1;
    this.intensity = .3; this.intensityTarget = .3; this.appliedIntensity = -1;
    this.song = null; this.fading = []; this.lastTick = 0;
    this.orbStreak = 0; this.lastOrb = -9; this.heartNext = 0; this.duckUntil = 0; this.duckLevel = 1;
    this.amb = null; this.ambOld = []; this.ambNext = {};
    this.stats = { sfx: 0, dropped: 0, renderMs: 0 }; this.requests = {};
  }
  get voices() { return this.active.length; }
  async prepare() { return true; }

  init() {
    try {
      if (!this.ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        this.ctx = new AC({ latencyHint: 'interactive' });
        this.build();
        this.started = true;
        this.timer = setInterval(() => this.tick(), 25);
        // 标签页隐藏时挂起，回来再恢复（游戏本身也会暂停）
        document.addEventListener('visibilitychange', () => {
          if (!this.ctx) return;
          if (document.hidden) this.ctx.suspend().catch(() => {});
          else this.ctx.resume().catch(() => {});
        });
        this.warm();
        this.route();
      }
      if (this.ctx.state === 'suspended' && !document.hidden) this.ctx.resume().catch(() => {});
      this.update();
    } catch (e) { this.fail(e); }
  }
  fail(e) { if (this.errors.length < 20) this.errors.push(String(e && e.stack || e).slice(0, 300)); }

  /* ---------- 音频图 ---------- */
  build() {
    const c = this.ctx, gain = v => { const n = c.createGain(); n.gain.value = v; return n; };
    // 主链：粘合压缩 → 限幅 → 输出
    this.glue = c.createDynamicsCompressor();
    this.glue.threshold.value = -18; this.glue.knee.value = 10; this.glue.ratio.value = 3; this.glue.attack.value = .006; this.glue.release.value = .25;
    this.limiter = c.createDynamicsCompressor();
    this.limiter.threshold.value = -2.5; this.limiter.knee.value = 0; this.limiter.ratio.value = 20; this.limiter.attack.value = .001; this.limiter.release.value = .12;
    this.master = gain(.95);
    this.master.connect(this.glue); this.glue.connect(this.limiter); this.limiter.connect(c.destination);
    // 电平表：并联在输出端，只供验收读数
    this.meterNode = c.createAnalyser(); this.meterNode.fftSize = 4096; this.limiter.connect(this.meterNode);
    // 配乐：音量 → 闪避 → 低通（暂停 / 濒死时发闷）
    this.musicBus = gain(0); this.musicDuck = gain(1);
    this.musicTone = c.createBiquadFilter(); this.musicTone.type = 'lowpass'; this.musicTone.frequency.value = 20000; this.musicTone.Q.value = .5;
    this.musicBus.connect(this.musicDuck); this.musicDuck.connect(this.musicTone); this.musicTone.connect(this.master);
    // 音效 / 界面 / 环境三条总线
    this.bus = gain(0); this.uiBus = gain(0); this.ambBus = gain(0);
    for (const b of [this.bus, this.uiBus, this.ambBus]) b.connect(this.master);
    // 混响：各声部按配方发送，卷积后回送主链
    this.revIn = gain(1); this.revOut = gain(.6); this.revOut.connect(this.master); this.verbs = new Map();
    // 音效发送也必须经过自己的音量控制，不能绕过音效 / 界面 / 环境总线。
    this.revSend = { sfx: gain(0), ui: gain(0), amb: gain(0) };
    for (const send of Object.values(this.revSend)) send.connect(this.revIn);
    const musicSend = gain(.16); this.musicTone.connect(musicSend); musicSend.connect(this.revIn);
    const ambSend = gain(.3); this.ambBus.connect(ambSend); ambSend.connect(this.revIn);
    // 扩宽：侧声道 = 全通去相关信号，左正右反；单声道相加时完全抵消
    const makeWide = dest => {
      const input = gain(1); let node = input;
      for (const [f, q] of [[540, .7], [1700, .8], [4200, .7]]) { const ap = c.createBiquadFilter(); ap.type = 'allpass'; ap.frequency.value = f; ap.Q.value = q; node.connect(ap); node = ap; }
      const inv = gain(-1), merge = c.createChannelMerger(2);
      node.connect(merge, 0, 0); node.connect(inv); inv.connect(merge, 0, 1); merge.connect(dest);
      return input;
    };
    this.wide = { sfx: makeWide(this.bus), ui: makeWide(this.uiBus), amb: makeWide(this.ambBus) };
    this.canPan = typeof c.createStereoPanner === 'function';
    // 环境声共用的噪声源
    const n = c.sampleRate * 4, nb = c.createBuffer(1, n, c.sampleRate), d = nb.getChannelData(0), r = NRDSP.rng(77);
    for (let i = 0; i < n; i++) d[i] = r() * 2 - 1;
    this.noiseBuf = nb;
  }
  // 各区域的混响：[秒, 亮, 暗]
  setVerb(key) {
    const VERB = { menu: [2.4, 6500, 1100], camp: [2, 5200, 1000], s0: [1.8, 6500, 1200], s1: [2.8, 9000, 1800], s2: [1.3, 4200, 700], s3: [3.6, 7500, 1000] };
    if (!this.ctx || this.verbKey === key || !VERB[key]) return;
    this.verbKey = key;
    try { this.buildVerb(key, VERB); } catch (e) { this.fail(e); }
  }
  buildVerb(key, VERB) {
    const c = this.ctx, now = c.currentTime;
    let v = this.verbs.get(key);
    if (!v) {
      // 卷积器要求脉冲响应与上下文采样率一致（常见 44.1 / 48 kHz）
      const [sec, bright, dark] = VERB[key], ir = NRDSP.withRate(c.sampleRate, () => NRDSP.impulse(sec, { seed: NRDSP.hash(key), bright, dark }));
      const b = c.createBuffer(2, ir[0].length, c.sampleRate);
      b.getChannelData(0).set(ir[0]); b.getChannelData(1).set(ir[1]);
      const conv = c.createConvolver(); conv.normalize = false; conv.buffer = b;
      const input = c.createGain(); input.gain.value = 0;
      this.revIn.connect(input); input.connect(conv); conv.connect(this.revOut);
      v = { input, conv }; this.verbs.set(key, v);
    }
    for (const [k, x] of this.verbs) x.input.gain.setTargetAtTime(k === key ? 1 : 0, now, .5);
  }

  /* ---------- 缓存与预渲染 ---------- */
  sound(name, variant) {
    const key = name + '#' + variant;
    let s = this.sfxCache.get(key);
    if (!s) {
      const t0 = performance.now(), { data, wide, rate } = NRSFX.render(name, variant);
      const buf = this.ctx.createBuffer(1, data.length, rate); buf.getChannelData(0).set(data);
      s = { buf, wide }; this.sfxCache.set(key, s);
      this.stats.renderMs += performance.now() - t0;
    }
    return s;
  }
  note(inst, root) {
    const key = inst + ':' + root;
    let s = this.noteCache.get(key);
    if (!s) {
      const t0 = performance.now(), n = NRMUSIC.renderNote(inst, root);
      const buf = this.ctx.createBuffer(1, n.data.length, n.rate); buf.getChannelData(0).set(n.data);
      s = { buf, loopStart: n.loopStart, loopEnd: n.loopEnd }; this.noteCache.set(key, s);
      this.stats.renderMs += performance.now() - t0;
    }
    return s;
  }
  drum(name, variant) {
    const key = name + '#' + variant;
    let b = this.drumCache.get(key);
    if (!b) {
      const t0 = performance.now(), data = NRMUSIC.renderDrum(name, variant);
      b = this.ctx.createBuffer(1, data.length, NRDSP.SR); b.getChannelData(0).set(data); this.drumCache.set(key, b);
      this.stats.renderMs += performance.now() - t0;
    }
    return b;
  }
  compile(id) { if (!this.compiled.has(id)) this.compiled.set(id, NRMUSIC.compile(id)); return this.compiled.get(id); }
  enqueue(key, fn, front = false) {
    if (this.queued.has(key)) return;
    this.queued.add(key);
    front ? this.queue.unshift(fn) : this.queue.push(fn);
  }
  warmSounds(names, front = false) {
    for (const name of names) { const r = NRSFX.recipes[name]; if (r) for (let v = 0; v < r.vars; v++) this.enqueue('s:' + name + v, () => this.sound(name, v), front); }
  }
  warmSong(id, front = false) {
    const comp = this.compile(id), jobs = [];
    for (const [inst, root] of NRMUSIC.rootsFor(comp)) jobs.push(['n:' + inst + root, () => this.note(inst, root)]);
    for (const tr of comp.tracks) if (tr.kind === 'drum') for (let v = 0; v < NRMUSIC.DRUM[tr.inst].vars; v++) jobs.push(['d:' + tr.inst + v, () => this.drum(tr.inst, v)]);
    (front ? jobs.reverse() : jobs).forEach(([k, fn]) => this.enqueue(k, fn, front));
    this.pump();
  }
  // 预渲染顺序：界面 → 菜单曲 → 英雄与常用战斗音 → 第一境与 Boss 曲 → 大招 / Boss 音 → 其余曲目 → 环境
  warm() {
    const all = Object.keys(NRSFX.recipes), pick = re => all.filter(n => re.test(n));
    this.warmSounds(pick(/^(ui_|route$|camp$|reward$)/));
    this.warmSong('menu');
    this.warmSounds(pick(/^(shot|tint|pulse|skill)\d$|^(hit|armor|bosshit|crit|kill|dash|block|hurt|orb|heal|shieldhit|chain|drain|shatter|stun|freeze|bomb|warn|warnlane|eshot|boom)$/));
    this.warmSong('battle0'); this.warmSong('boss'); this.warmSong('camp');
    this.warmSounds(pick(/^ult\d$|^(levelup|upgrade|chest|ultready|breakout|elitekill|wave|stage|heartbeat|shieldbreak|downed|revive)$/));
    this.warmSounds(pick(/^(roar|volley|boom)\d$|^(summon|charge|enrage|zone|bossdie)$/));
    this.warmSounds(pick(/^amb_|^(win|fail)$/));
    this.pump();
  }
  // 空闲时分片渲染，每片约 8 ms
  pump() {
    if (this.pumping || !this.queue.length) return;
    this.pumping = true;
    const later = typeof requestIdleCallback === 'function' ? cb => requestIdleCallback(cb, { timeout: 400 }) : cb => setTimeout(cb, 30);
    const run = () => {
      const t0 = performance.now();
      while (this.queue.length && performance.now() - t0 < 8) { const fn = this.queue.shift(); try { fn(); } catch (e) { this.fail(e); } }
      if (this.queue.length) later(run); else this.pumping = false;
    };
    later(run);
  }

  /* ---------- 音效 ---------- */
  // pan -1..1；power 额外音量；opt.rate 音高倍率，opt.when 定时
  sfx(name, pan = 0, power = 1, opt = {}) {
    name = NRSFX.alias[name] || name;
    this.requests[name] = (this.requests[name] || 0) + 1; // 验收用：记录游戏请求过的音效（与是否发声无关）
    const c = this.ctx, r = NRSFX.recipes[name];
    if (!c || !r || c.state !== 'running' || this.muted || !(power > 0)) return false;
    try {
      const now = c.currentTime;
      if (now - (this.last[name] ?? -99) < r.gap) { this.stats.dropped++; return false; }
      let same = 0;
      for (const v of this.active) if (v.name === name) same++;
      if (same >= r.max) { this.stats.dropped++; return false; }
      // 声部上限：挤掉优先级最低、最早开始的一个；新声音优先级更低则放弃
      if (this.active.length >= 40) {
        let victim = null;
        for (const v of this.active) if (!victim || v.pri < victim.pri || (v.pri === victim.pri && v.t < victim.t)) victim = v;
        if (victim.pri > r.pri) { this.stats.dropped++; return false; }
        this.release(victim, now);
      }
      this.last[name] = now;
      const variant = r.vars > 1 ? (this.rr[name] = ((this.rr[name] || 0) + 1) % r.vars) : 0;
      const { buf, wide } = this.sound(name, variant);
      let rate = opt.rate || 1;
      if (r.pj) rate *= 2 ** ((this.rand() * 2 - 1) * r.pj / 12);
      // 连续拾取经验：音高沿五声音阶上行
      if (name === 'orb') {
        this.orbStreak = now - this.lastOrb < .45 ? Math.min(this.orbStreak + 1, 14) : 0; this.lastOrb = now;
        const k = this.orbStreak, steps = [0, 2, 4, 7, 9];
        rate *= 2 ** ((steps[k % 5] + 12 * Math.floor(k / 5)) / 12) * .75;
      }
      const route = name.startsWith('amb_') ? 'amb' : /^(ui_|route$|camp$|reward$)/.test(name) ? 'ui' : 'sfx';
      const src = c.createBufferSource(), g = c.createGain(), nodes = [g];
      src.buffer = buf; src.playbackRate.value = rate;
      g.gain.value = Math.min(2, r.gain * power);
      src.connect(g);
      let out = g;
      // 统一经过声像器（居中也走），避免 pan=0 与微小偏移之间出现 3 dB 跳变
      if (this.canPan) { const p = c.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, pan)); g.connect(p); out = p; nodes.push(p); }
      out.connect(route === 'amb' ? this.ambBus : route === 'ui' ? this.uiBus : this.bus);
      if (r.send > 0) { const s = c.createGain(); s.gain.value = r.send; out.connect(s); s.connect(this.revSend[route]); nodes.push(s); }
      if (wide > 0) { const w = c.createGain(); w.gain.value = wide * .85; g.connect(w); w.connect(this.wide[route]); nodes.push(w); }
      if (r.duck) this.duck(r.duck, Math.min(1.6, buf.duration * .45));
      const voice = { name, pri: r.pri, src, g, t: now, nodes };
      this.active.push(voice);
      src.onended = () => {
        const i = this.active.indexOf(voice); if (i >= 0) this.active.splice(i, 1);
        try { src.disconnect(); } catch {} for (const n of nodes) try { n.disconnect(); } catch {}
      };
      src.start(Math.max(now, opt.when || 0));
      this.stats.sfx++;
      return true;
    } catch (e) { this.fail(e); return false; }
  }
  release(v, now) {
    const i = this.active.indexOf(v); if (i >= 0) this.active.splice(i, 1);
    try { v.g.gain.setTargetAtTime(0, now, .015); v.src.stop(now + .08); } catch {}
  }
  // 压低配乐：amount 0..1，hold 秒后缓慢回升
  duck(amount, hold = .6) {
    if (!this.ctx) return;
    const now = this.ctx.currentTime, target = 1 - Math.min(.8, amount * .75);
    if (now < this.duckUntil && target >= this.duckLevel) return;
    const p = this.musicDuck.gain;
    if (p.cancelAndHoldAtTime) p.cancelAndHoldAtTime(now); else { const v = p.value; p.cancelScheduledValues(now); p.setValueAtTime(v, now); }
    p.setTargetAtTime(target, now, .03); p.setTargetAtTime(1, now + hold, .45);
    this.duckLevel = target; this.duckUntil = now + hold;
  }

  /* ---------- 配乐 ---------- */
  songFor(name) {
    if (name === 'music_menu') return 'menu';
    if (name === 'music_camp') return 'camp';
    if (name === 'music_boss') return this.bossType === 7 || this.stageId === 3 ? 'bossfinal' : 'boss';
    return 'battle' + this.stageId;
  }
  music(name) {
    this.paused = false;
    this.current = name;
    if (name !== 'music_boss') { this.rage = false; this.mix = name === 'music_menu' || name === 'music_camp' ? 'musicCalm' : 'musicRise'; }
    else this.mix = 'musicBoss';
    this.route();
    this.update();
  }
  // 按当前曲名切换曲目、环境声与混响
  route() {
    if (!this.ctx) return;
    const name = this.current, battle = name === 'music_battle' || name === 'music_boss';
    this.playSong(this.songFor(name));
    this.setAmbience(battle ? this.stageId : null);
    this.setVerb(battle ? 's' + this.stageId : name === 'music_camp' ? 'camp' : 'menu');
  }
  playSong(id) {
    if (!this.ctx || this.song?.id === id) return;
    try {
      const c = this.ctx, now = c.currentTime;
      if (this.song) { const old = this.song; old.out.gain.setTargetAtTime(0, now, .45); old.dying = now + 2.4; this.fading.push(old); }
      const comp = this.compile(id), out = c.createGain();
      out.gain.value = 0; out.gain.setTargetAtTime(comp.gain ?? 1, now + .05, .2); out.connect(this.musicBus);
      const level = this.levelFor(comp);
      const layers = [0, 1, 2, 3, 4].map(k => { const g = c.createGain(); g.gain.value = NRMUSIC.layerGain(comp, k, level); g.connect(out); return g; });
      // Boss 曲按 Boss 编号小幅移调，八位妖王不完全同调
      const transpose = id === 'boss' ? [0, 2, -2, 3, -1, 1, -3, 0][Math.max(0, this.bossType)] || 0 : 0;
      this.song = { id, comp, out, layers, target: layers.map(g => g.gain.value), step: 0, next: now + .1, bpm: comp.bpm * (this.rage ? 1.05 : 1), transpose };
      this.appliedIntensity = level;
      this.warmSong(id, true);
    } catch (e) { this.fail(e); }
  }
  levelFor(comp) {
    if (comp.fixed != null) return comp.fixed;
    if (this.rage && comp.base) return 1;
    return comp.base ? Math.max(comp.base, this.intensity) : this.intensity;
  }
  applyLayers(force = false) {
    const s = this.song; if (!s) return;
    const level = this.levelFor(s.comp);
    if (!force && Math.abs(level - this.appliedIntensity) < .03) return;
    this.appliedIntensity = level;
    const now = this.ctx.currentTime;
    s.layers.forEach((g, k) => { const v = NRMUSIC.layerGain(s.comp, k, level); s.target[k] = v; g.gain.setTargetAtTime(v, now, v > g.gain.value ? .8 : 1.6); });
  }
  // 每帧由战斗循环调用：p 包围压力，boss 是否在场，phase 关卡段，hp 主角血量比，ult 无双中
  battle(p, boss, phase, hp, ult) {
    this.mix = boss ? 'musicBoss' : p > .55 || hp < .25 || ult ? 'musicDanger' : p > .18 || phase === 2 ? 'musicRise' : 'musicCalm';
    let v = .2 + p * .78;
    if (phase === 2) v = Math.max(v, .46);
    if (ult) v = Math.max(v, .9);
    if (hp < .3) v = Math.max(v, .72);
    this.intensityTarget = Math.min(1, v);
    const low = hp > 0 && hp < .3;
    if (low !== this.lowHp) { this.lowHp = low; this.update(); }
    this.hp = hp;
  }
  stage(z) {
    z = ((z | 0) % 4 + 4) % 4;
    // 本境与下一境的曲子提前预热；第三境起把终局 Boss 曲也备好
    if (this.ctx) { this.warmSong('battle' + z); this.warmSong('battle' + Math.min(3, z + 1)); if (z >= 2) this.warmSong('bossfinal'); }
    if (z === this.stageId) return;
    this.stageId = z;
    if (this.ctx && this.current === 'music_battle') this.music('music_battle');
  }
  boss(type) { this.bossType = type; this.rage = false; if (this.ctx) this.warmSong(type === 7 || this.stageId === 3 ? 'bossfinal' : 'boss', true); }
  bossRage() {
    this.rage = true;
    if (this.song && this.song.comp.base) { this.song.bpm = this.song.comp.bpm * 1.05; this.applyLayers(true); }
    this.sfx('enrage');
  }
  bossDown() { this.rage = false; this.bossType = -1; }

  playStep(s, step, time) {
    const sd = 60 / s.bpm / 4;
    for (const e of NRMUSIC.eventsAt(s.comp, step)) {
      const lg = s.layers[e.layer];
      if (s.target[e.layer] < .01 && lg.gain.value < .01) continue;
      if (e.drum) this.playDrum(e.drum, time, e.vel, lg);
      else this.playNote(e.inst, e.midi + s.transpose, time, e.len * sd, e.vel, lg);
    }
  }
  playNote(inst, midi, time, dur, vel, dest) {
    const I = NRMUSIC.INST[inst], { root, rate } = NRMUSIC.rootFor(inst, midi), smp = this.note(inst, root), c = this.ctx;
    const src = c.createBufferSource(), g = c.createGain();
    src.buffer = smp.buf; src.playbackRate.value = rate;
    if (smp.loopEnd) { src.loop = true; src.loopStart = smp.loopStart; src.loopEnd = smp.loopEnd; }
    const peak = vel * I.gain, a = Math.max(.004, I.attack), hold = Math.max(time + a, time + (I.ring ? Math.max(dur, I.ring) : dur));
    g.gain.setValueAtTime(0, time); g.gain.linearRampToValueAtTime(peak, time + a);
    g.gain.setValueAtTime(peak, hold); g.gain.setTargetAtTime(0, hold, I.release / 3);
    src.connect(g); g.connect(dest);
    src.start(time); src.stop(hold + I.release * 1.6 + .05);
    src.onended = () => { try { src.disconnect(); g.disconnect(); } catch {} };
  }
  playDrum(name, time, vel, dest) {
    const D = NRMUSIC.DRUM[name], v = D.vars > 1 ? (this.rr['d' + name] = ((this.rr['d' + name] || 0) + 1) % D.vars) : 0, c = this.ctx;
    const src = c.createBufferSource(), g = c.createGain();
    src.buffer = this.drum(name, v); src.playbackRate.value = 1 + (this.rand() - .5) * .02;
    g.gain.value = vel * D.gain;
    src.connect(g); g.connect(dest); src.start(time);
    src.onended = () => { try { src.disconnect(); g.disconnect(); } catch {} };
  }

  /* ---------- 环境声 ---------- */
  // beds：[滤波类型, 频率, Q, 音量, LFO 频率, LFO 深度, 扫频深度 Hz]；drones：[频率, 音量]；events：[音效, 平均间隔秒]
  // 垫底电平目标约 -35 LUFS（默认音效音量），比战斗配乐低约 10 dB
  static AMB = [
    { beds: [['highpass', 2600, .5, .015, .13, .3, 0], ['bandpass', 380, .7, .05, .07, .5, 120]], events: [['amb_drip', 1.4], ['amb_bell', 26], ['amb_gust', 15]] },
    { beds: [['bandpass', 650, 4, .06, .09, .6, 260], ['lowpass', 300, .5, .1, .05, .4, 0]], events: [['amb_creak', 7], ['amb_gust', 9], ['amb_chime', 13]] },
    { beds: [['lowpass', 170, .7, .17, .11, .3, 0], ['bandpass', 1100, .6, .025, .4, .5, 0]], events: [['amb_ember', .5], ['amb_anvil', 11], ['amb_gust', 21]] },
    { beds: [['bandpass', 220, 2, .028, .04, .6, 80]], drones: [[55, .017], [55.4, .017], [82.4, .007]], events: [['amb_whisper', 11], ['amb_chime', 7], ['amb_bell', 24]] }
  ];
  setAmbience(z) {
    if (!this.ctx || (this.amb && this.amb.z === z) || (!this.amb && z == null)) return;
    const c = this.ctx, now = c.currentTime;
    if (this.amb) { const old = this.amb; old.out.gain.setTargetAtTime(0, now, .8); old.until = now + 4; this.ambOld.push(old); this.amb = null; }
    if (z == null) return;
    try {
      const def = NRAudio.AMB[z], out = c.createGain(), nodes = [];
      out.gain.value = 0; out.gain.setTargetAtTime(1, now, 1.2); out.connect(this.ambBus);
      for (const [type, f, q, vol, lr, ld, sweep] of def.beds) {
        const src = c.createBufferSource(); src.buffer = this.noiseBuf; src.loop = true;
        const fl = c.createBiquadFilter(); fl.type = type; fl.frequency.value = f; fl.Q.value = q;
        const g = c.createGain(); g.gain.value = vol;
        src.connect(fl); fl.connect(g); g.connect(out);
        const lfo = c.createOscillator(), depth = c.createGain(); lfo.frequency.value = lr; depth.gain.value = vol * ld;
        lfo.connect(depth); depth.connect(g.gain); lfo.start(now);
        if (sweep) { const sd = c.createGain(); sd.gain.value = sweep; lfo.connect(sd); sd.connect(fl.frequency); }
        src.start(now, this.rand() * 3.5);
        nodes.push(src, lfo);
      }
      for (const [f, vol] of def.drones || []) { const o = c.createOscillator(), g = c.createGain(); o.frequency.value = f; g.gain.value = vol; o.connect(g); g.connect(out); o.start(now); nodes.push(o); }
      this.amb = { z, out, nodes, def };
      this.ambNext = {};
      for (const [name, mean] of def.events) this.ambNext[name] = now + mean * (.3 + this.rand());
    } catch (e) { this.fail(e); }
  }
  ambTick(now) {
    for (const old of this.ambOld) if (now > old.until) { for (const n of old.nodes) try { n.stop(); } catch {} try { old.out.disconnect(); } catch {} old.done = true; }
    this.ambOld = this.ambOld.filter(o => !o.done);
    if (!this.amb || this.paused) return;
    for (const [name, mean] of this.amb.def.events) {
      if (now < this.ambNext[name]) continue;
      this.sfx(name, (this.rand() * 2 - 1) * .8, .55 + this.rand() * .5);
      this.ambNext[name] = now + mean * (.45 + this.rand() * 1.1);
    }
  }

  /* ---------- 调度 ---------- */
  tick() {
    const c = this.ctx;
    if (!c || c.state !== 'running') return;
    try {
      const now = c.currentTime, dt = Math.min(.2, Math.max(0, now - (this.lastTick || now)));
      this.lastTick = now;
      // 强度：上升快、回落慢，避免层级来回闪烁
      const d = this.intensityTarget - this.intensity;
      this.intensity += Math.max(-.07 * dt, Math.min(.45 * dt, d));
      if (this.current === 'music_battle' || this.current === 'music_boss') this.applyLayers();
      const ahead = now + .2;
      for (const s of [this.song, ...this.fading]) {
        if (!s) continue;
        const sd = 60 / s.bpm / 4;
        // 后台节流造成的积压直接跳过，不补发
        if (s.next < now - .1) { const lag = Math.ceil((now - s.next) / sd); s.step += lag; s.next += lag * sd; }
        while (s.next < ahead) { this.playStep(s, s.step, s.next); s.step++; s.next += 60 / s.bpm / 4; }
      }
      this.fading = this.fading.filter(s => { if (now < s.dying) return true; try { s.out.disconnect(); } catch {} return false; });
      this.ambTick(now);
      // 濒死心跳
      const battle = this.current === 'music_battle' || this.current === 'music_boss';
      if (battle && !this.paused && this.lowHp && now >= this.heartNext) {
        this.sfx('heartbeat', 0, .7 + (.3 - this.hp) * 1.5);
        this.heartNext = now + 60 / (70 + (.3 - this.hp) * 160);
      }
    } catch (e) { this.fail(e); }
  }
  pause(v) { this.paused = v; this.update(); }
  update() {
    if (!this.ctx) return;
    const now = this.ctx.currentTime, o = this.options, sfx = this.muted ? 0 : o.sfx ?? .55;
    const battle = this.current === 'music_battle' || this.current === 'music_boss';
    // 主静音同时切断已在卷积器中的尾音。
    this.master.gain.setTargetAtTime(this.muted ? 0 : .95, now, .015);
    this.musicBus.gain.setTargetAtTime(this.muted ? 0 : (o.music ?? .24) * 1 * (this.paused ? .5 : 1), now, .08);
    this.bus.gain.setTargetAtTime(sfx, now, .03);
    this.uiBus.gain.setTargetAtTime(sfx, now, .03);
    this.ambBus.gain.setTargetAtTime(battle ? sfx * (this.paused ? .3 : 1) : 0, now, .5);
    this.revSend.sfx.gain.setTargetAtTime(sfx, now, .03);
    this.revSend.ui.gain.setTargetAtTime(sfx, now, .03);
    this.revSend.amb.gain.setTargetAtTime(battle ? sfx * (this.paused ? .3 : 1) : 0, now, .5);
    this.musicTone.frequency.setTargetAtTime(this.paused ? 900 : battle && this.lowHp ? 1700 : 20000, now, .25);
    const el = document.getElementById('muteBtn'); if (el) el.textContent = this.muted ? '♪̸' : '♫';
  }
  // 输出电平（dBFS）：最近约 85 ms 的 RMS 与峰值
  meter() {
    if (!this.meterNode) return null;
    const a = new Float32Array(this.meterNode.fftSize); this.meterNode.getFloatTimeDomainData(a);
    let sum = 0, peak = 0; for (const v of a) { sum += v * v; peak = Math.max(peak, Math.abs(v)); }
    const db = v => v > 0 ? +(20 * Math.log10(v)).toFixed(1) : -120;
    return { rms: db(Math.sqrt(sum / a.length)), peak: db(peak) };
  }
  info() {
    return {
      context: this.ctx?.state || 'not-started', mix: this.mix, voices: this.voices, muted: this.muted, playing: this.started, errors: this.errors.slice(-5),
      song: this.song?.id || null, intensity: +this.intensity.toFixed(2), stage: this.stageId, boss: this.bossType, rage: this.rage, ambience: this.amb?.z ?? null,
      cached: { sfx: this.sfxCache.size, notes: this.noteCache.size, drums: this.drumCache.size }, queue: this.queue.length,
      played: this.stats.sfx, dropped: this.stats.dropped, renderMs: Math.round(this.stats.renderMs)
    };
  }
}
