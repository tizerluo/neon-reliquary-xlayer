/* 程序化配乐：乐器采样渲染 + 简谱曲目 + 自适应分层。
   旋律用简谱写：1–7 为调内音级，' 升八度，, 降八度，#/b 变音，0 为休止，/n 为时值（十六分音符个数），每小节 16。
   和弦：音级 + 性质（m 小三、M 大三、s 挂四、2 挂二、5 空五度；省略时按调内默认）。
   节奏串（每小节 16 格）：X 重音、x 普通、g 轻、- 延续、. 休止；低音里 o 为高八度、5 为五度。
   层级：0 底垫 / 1 旋律 / 2 律动 / 3 鼓组 / 4 高潮；强度越高，越多层淡入。 */
const NRMUSIC = (() => {
  const D = NRDSP, K = NRSFX.kit, TAU = Math.PI * 2;

  /* ---------- 乐器 ---------- */
  // lo/hi 音域，step 采样根音间距（半音），rate 渲染采样率，loop 持续音循环区间，attack/release 运行时包络
  const vib = (rate, depth, delay = .25) => t => 1 + depth * Math.sin(TAU * rate * t) * Math.min(1, Math.max(0, (t - delay) / .4));
  const INST = {
    // 古筝：拨弦 + 琴体共鸣
    zheng: { lo: 50, hi: 88, step: 4, rate: 32000, attack: 0, release: .5, ring: 2.2, gain: .55, render: (m, s) => {
      const f = D.mtof(m), x = D.pluck(2.4, f, 2.6 - (m - 50) * .035, .72, s);
      return D.filter(D.mix([x, 1], [D.filter(x, 'bp', f * 2, 6), .25]), 'peak', 280, 1, 4);
    } },
    // 笛：正弦 + 少量泛音 + 气声，延迟颤音
    dizi: { lo: 58, hi: 93, step: 4, rate: 32000, attack: .05, release: .14, gain: .42, render: (m, s) => {
      const f = D.mtof(m), v = vib(5.6, .005), dur = 1.8;
      const tone = D.mix([D.osc(dur, t => f * v(t), 1), 1], [D.osc(dur, t => 2 * f * v(t), .22), 1], [D.osc(dur, t => 3 * f * v(t), .08), 1]);
      const breath = D.filter(D.noise(dur, t => .08 + .12 * Math.exp(-t * 8), 'white', s), 'bp', f * 1.5, 1.2);
      return D.loopify(D.mix([tone, 1], [breath, 1]), .6, 1.75, .25);
    } },
    // 二胡：锯齿 + 共振峰，较深的颤音
    erhu: { lo: 52, hi: 86, step: 4, rate: 32000, attack: .09, release: .18, gain: .4, render: (m, s) => {
      const f = D.mtof(m), v = vib(6.1, .009, .2), dur = 1.8;
      let x = D.osc(dur, t => f * v(t), 1, 'saw');
      x = D.mix([D.filter(x, 'peak', 950, 1.4, 7), 1], [D.bp(D.noise(dur, .04, 'white', s), 2600, 2), 1]);
      x = D.filter(D.lp(x, 3600), 'peak', 2500, 2, 4);
      return D.loopify(x, .6, 1.75, .25);
    } },
    // 唢呐：鼻音明亮，轻失真
    suona: { lo: 60, hi: 88, step: 4, rate: 32000, attack: .03, release: .12, gain: .32, render: (m, s) => {
      const f = D.mtof(m), v = vib(5.4, .007, .15), dur = 1.8;
      let x = D.mix([D.osc(dur, t => f * v(t), 1, 'square'), .6], [D.osc(dur, t => f * v(t), 1, 'saw'), .6]);
      x = D.mix([D.bp(x, 1250, 2), 1], [D.bp(x, 2900, 3), .6], [D.lp(x, 700), .5]);
      return D.loopify(D.drive(x, 1.6), .6, 1.75, .25);
    } },
    // 弦乐垫：五条失谐锯齿
    pad: { lo: 40, hi: 80, step: 5, rate: 22050, attack: .5, release: 1, gain: .26, render: (m, s) => {
      const f = D.mtof(m), r = D.rng(s), dur = 2.4;
      const x = D.mix(...[-13, -6, 0, 7, 12].map(c => [D.osc(dur, f * 2 ** (c / 1200), 1, 'saw', r()), .2]));
      return D.loopify(D.filter(D.lp(x, Math.min(2400, f * 6), .5), 'peak', 600, .8, 2), .5, 2.3, .5);
    } },
    // 合唱：元音 a 的共振峰
    choir: { lo: 45, hi: 79, step: 5, rate: 22050, attack: .45, release: .9, gain: .3, render: (m, s) => D.loopify(K.wail(2.4, D.mtof(m), 3, s, [[730, 5, 1], [1090, 6, .55], [2440, 9, .22]]), .5, 2.3, .5) },
    // 管风琴：叠加谐波 + 轻微合唱
    organ: { lo: 36, hi: 79, step: 5, rate: 22050, attack: .07, release: .35, gain: .24, render: (m, s) => {
      const f = D.mtof(m), dur = 2.2;
      const x = D.mix(...[[1, 1], [2, .6], [3, .35], [4, .3], [6, .16], [8, .12]].map(([k, a]) => [D.osc(dur, t => f * k * (1 + .0015 * Math.sin(TAU * .8 * t + k)), a), 1]));
      return D.loopify(D.lp(x, 5000), .4, 2.1, .4);
    } },
    // 钟琴 / 冰晶
    bell: { lo: 64, hi: 100, step: 5, rate: 32000, attack: 0, release: .6, ring: 1.6, gain: .26, render: (m, s) => { const f = D.mtof(m); return D.modal(2, [[f, 1, 1.1], [f * 2, .32, .5], [f * 3, .1, .3], [f * 4.07, .1, .22], [f * 5.4, .05, .15]], s); } },
    // 合成贝斯
    bass: { lo: 28, hi: 55, step: 5, rate: 22050, attack: .005, release: .09, gain: .5, render: (m, s) => {
      const f = D.mtof(m), dur = 1.5;
      return D.mix([D.osc(dur, f, D.ad(.004, .9)), 1], [D.filter(D.osc(dur, f, D.ad(.004, .5), 'saw'), 'lp', D.drop(f * 9, f * 2.5, .08), 1.2), .45]);
    } },
    // 失真贝斯（赤烬废城 / Boss）
    dbass: { lo: 28, hi: 55, step: 5, rate: 22050, attack: .004, release: .07, gain: .38, render: (m, s) => {
      const f = D.mtof(m), dur = 1.2;
      const x = D.mix([D.osc(dur, f, 1, 'saw'), .7], [D.osc(dur, f * 1.004, 1, 'square'), .4], [D.osc(dur, f / 2, 1), .6]);
      return D.shape(D.filter(D.drive(x, 2.8), 'lp', D.drop(f * 14, f * 4, .12), 1.1), D.ad(.003, .7));
    } },
    // 合成铜管齐奏
    brass: { lo: 43, hi: 76, step: 5, rate: 32000, attack: .03, release: .16, gain: .3, render: (m, s) => {
      const f = D.mtof(m), r = D.rng(s), dur = 1.4;
      const x = D.mix(...[-8, 0, 9].map(c => [D.osc(dur, f * 2 ** (c / 1200), 1, 'saw', r()), .33]));
      return D.filter(x, 'lp', D.env([[0, f * 1.2], [.06, f * 7], [.4, f * 4], [dur, f * 3.5]]), .9);
    } },
    // 霓虹脉冲琶音
    pulse: { lo: 52, hi: 91, step: 5, rate: 32000, attack: .002, release: .05, ring: .35, gain: .2, render: (m, s) => {
      const f = D.mtof(m);
      return D.filter(D.osc(.4, f, D.ad(.002, .14), 'square'), 'lp', D.drop(f * 8, f * 2, .05), 2);
    } }
  };
  // 打击乐：无音高，单个样本（可多个变体）
  const DRUM = {
    taiko: { gain: .7, vars: 2, render: s => K.taiko(1.2, s, 60) },
    tanggu: { gain: .45, vars: 2, render: s => D.mix([K.thump(.5, 260, 150, .015, .12), 1], [D.bp(D.noise(.2, D.ad(.001, .04), 'white', s), 1800, 1), .5]) },
    kick: { gain: .6, vars: 1, render: s => D.mix([K.thump(.45, 150, 48, .03, .2), 1], [K.click(.006, 2500, s), .25]) },
    snare: { gain: .38, vars: 2, render: s => D.mix([D.osc(.2, D.drop(260, 185, .02), D.ad(.001, .05)), .6], [D.hp(D.noise(.25, D.ad(.001, .08), 'white', s), 1500), .8]) },
    clap: { gain: .32, vars: 2, render: s => D.bp(D.mix(...[0, .011, .022].map((o, k) => [D.noise(.2, D.ad(.0005, k === 2 ? .06 : .008), 'white', s + k), 1, o])), 1300, .9) },
    hat: { gain: .16, vars: 3, render: s => D.hp(D.noise(.06, D.ad(.0005, .018), 'white', s), 7500) },
    ohat: { gain: .14, vars: 2, render: s => D.hp(D.noise(.3, D.ad(.001, .1), 'white', s), 7000) },
    shaker: { gain: .14, vars: 3, render: s => D.bp(D.noise(.09, D.swell(.09, .4), 'white', s), 6500, 1.2) },
    block: { gain: .3, vars: 2, render: s => D.mix([D.bp(D.osc(.12, 880, D.ad(.0008, .025)), 880, 6), 2], [K.click(.006, 1500, s), .3]) },
    rim: { gain: .22, vars: 2, render: s => D.mix([K.ping(.06, 1700, .018, s, .2), .7], [K.click(.005, 3000, s), .5]) },
    bo: { gain: .26, vars: 2, render: s => D.mix([D.hp(D.noise(1.4, D.ad(.002, .45), 'white', s), 3500), .7], [K.plate(1.4, 430, s + 1, .5), .3]) },
    gong: { gain: .42, vars: 1, render: s => K.gong(3.4, 92, s) },
    anvil: { gain: .22, vars: 2, render: s => D.mix([K.plate(.6, 980, s, .22), .6], [K.click(.006, 2000, s + 1), .4]) },
    boom: { gain: .6, vars: 1, render: s => K.boom(1.8, s, 400, 35, .7) }
  };

  /* ---------- 记谱解析 ---------- */
  const DEG = { 1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11 };
  const DEFAULT_Q = { 1: 'M', 2: 'm', 3: 'm', 4: 'M', 5: 'M', 6: 'm', 7: 'm' };
  // 简谱旋律 → [{ step, len, midi }]（midi 为 null 表示休止）
  function parseMelody(text, key) {
    const out = [];
    let step = 0;
    for (const tok of text.trim().split(/\s+/)) {
      if (tok === '|') continue;
      const m = /^([#b]?)([0-7])([',]*)(?:\/(\d+))?$/.exec(tok);
      if (!m) throw new Error('Bad note: ' + tok);
      const len = +(m[4] || 4);
      if (m[2] !== '0') {
        const oct = [...m[3]].reduce((a, c) => a + (c === "'" ? 12 : -12), 0);
        out.push({ step, len, midi: key + DEG[m[2]] + (m[1] === '#' ? 1 : m[1] === 'b' ? -1 : 0) + oct });
      }
      step += len;
    }
    return { notes: out, steps: step };
  }
  // 和弦记号 → { root（相对调主音的半音）, third, quality }
  function parseChord(tok) {
    const m = /^([#b]?)([1-7])([mMs25]?)$/.exec(tok);
    if (!m) throw new Error('Bad chord: ' + tok);
    const q = m[3] || DEFAULT_Q[m[2]];
    return { root: DEG[m[2]] + (m[1] === '#' ? 1 : m[1] === 'b' ? -1 : 0), q };
  }
  const THIRD = { m: 3, M: 4, s: 5, 2: 2, 5: 7 };
  // 把根音收进 [low, low+12)
  const wrap = (midi, low) => { while (midi >= low + 12) midi -= 12; while (midi < low) midi += 12; return midi; };
  // 节奏串 → [{ step, len, vel, ch }]，按小节拼接
  function parseRhythm(text) {
    const cells = text.replace(/[\s|]/g, ''), out = [];
    for (let i = 0; i < cells.length; i++) {
      const ch = cells[i];
      if (ch === '.' || ch === '-') continue;
      let len = 1; while (cells[i + len] === '-') len++;
      out.push({ step: i, len, ch, vel: ch === 'X' ? 1 : ch === 'g' ? .42 : .76 });
    }
    return { hits: out, steps: cells.length };
  }

  /* ---------- 曲目 ----------
     key：简谱 1 对应的 MIDI 音高；gain：整曲音量（菜单 / 营地没有音效竞争，略响；Boss 曲音效最密，略轻）；chords：每小节一个和弦，整首按和弦长度循环；
     tracks：kind = chord / bass / arp / drum / melody；layer 层级；low 根音下限；every / on 控制隔小节出现。 */
  const SONGS = {
    // 主菜单 · 青岚序（D 宫，B 羽）
    menu: { name: '青岚序', bpm: 72, key: 62, fixed: .62, reverb: 2.4, gain: 1.7,
      chords: '6m 4 1 5 6m 4 5 5',
      tracks: [
        { kind: 'chord', inst: 'choir', layer: 0, low: 50, vel: .55 },
        { kind: 'chord', inst: 'pad', layer: 0, low: 47, vel: .4 },
        { kind: 'bass', inst: 'bass', layer: 2, low: 35, vel: .55, rhythm: 'x---------------' },
        { kind: 'arp', inst: 'zheng', layer: 2, low: 59, vel: .5, rhythm: 'x...x...x...x.x.', pattern: [0, 2, 1, 3, 4] },
        { kind: 'arp', inst: 'bell', layer: 4, low: 71, vel: .3, rhythm: '........x.......', pattern: [3, 4] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .55, rhythm: 'X...............', every: 2 },
        { kind: 'melody', inst: 'dizi', layer: 1, vel: .75, notes: `
          3/8 2/4 1/4 | 2/12 3/4 | 5/6 3/2 2/4 1/4 | 2/16 |
          6,/4 1/4 2/4 3/4 | 5/8 6/4 5/4 | 3/6 2/2 1/4 2/4 | 6,/16 |
          6/8 1'/4 6/4 | 5/6 6/2 5/4 3/4 | 2'/8 1'/4 6/4 | 5/16 |
          3'/6 2'/2 1'/4 6/4 | 5/4 6/4 1'/8 | 6/4 5/4 3/4 2/4 | 6,/12 0/4 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 营地 / 路线 · 篝火（A 宫）
    camp: { name: '篝火', bpm: 66, key: 69, fixed: .55, reverb: 2, gain: 1.9,
      chords: '1 6m 4 5 1 6m 2m 5',
      tracks: [
        { kind: 'chord', inst: 'pad', layer: 0, low: 50, vel: .42 },
        { kind: 'bass', inst: 'bass', layer: 2, low: 33, vel: .5, rhythm: 'x-------x-------' },
        { kind: 'arp', inst: 'zheng', layer: 0, low: 57, vel: .45, rhythm: 'x.x.x.x.x.x.x.x.', pattern: [0, 1, 2, 3, 4, 3, 2, 1] },
        { kind: 'drum', inst: 'block', layer: 3, vel: .4, rhythm: 'x.......x...x...' },
        { kind: 'melody', inst: 'dizi', layer: 1, vel: .7, notes: `
          3/6 5/2 6/4 5/4 | 3/8 2/4 1/4 | 2/4 3/4 5/4 6/4 | 5/12 0/4 |
          1'/6 6/2 5/4 3/4 | 5/4 3/4 2/8 | 2/4 3/2 2/2 1/4 6,/4 | 1/12 0/4 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 第一境 · 青岚古庭（G 宫，E 羽）：古筝快速琶音 + 太鼓 + 笛
    battle0: { name: '青岚古庭', bpm: 122, key: 67, reverb: 1.8,
      chords: '6m 6m 4 5 6m 6m 4 3M',
      tracks: [
        { kind: 'chord', inst: 'pad', layer: 0, low: 50, vel: .45 },
        { kind: 'arp', inst: 'zheng', layer: 0, low: 59, vel: .42, rhythm: 'x.x.x.x.x.x.x.x.', pattern: [0, 1, 2, 1, 3, 2, 4, 2] },
        { kind: 'bass', inst: 'bass', layer: 2, low: 35, vel: .75, rhythm: 'x..x..x.x..x.x..' },
        { kind: 'arp', inst: 'zheng', layer: 2, low: 71, vel: .3, rhythm: '..x...x...x...xx', pattern: [2, 3, 4, 3] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .9, rhythm: 'X.......X..x....', fill: 'X..x..x.X.x.xxxx', fillEvery: 4 },
        { kind: 'drum', inst: 'tanggu', layer: 3, vel: .7, rhythm: '..g.x..g....x.g.' },
        { kind: 'drum', inst: 'shaker', layer: 3, vel: .6, rhythm: 'x.x.x.x.x.x.x.x.' },
        { kind: 'chord', inst: 'brass', layer: 4, low: 52, vel: .5, rhythm: 'X.....x.........' },
        { kind: 'drum', inst: 'taiko', layer: 4, vel: .45, rhythm: '..x...x...x...x.' },
        { kind: 'drum', inst: 'bo', layer: 4, vel: .7, rhythm: 'X...............', every: 4 },
        { kind: 'melody', inst: 'dizi', layer: 1, vel: .8, notes: `
          6,/4 1/2 2/2 3/4 2/2 1/2 | 6,/6 5,/2 6,/8 | 3/4 5/4 6/2 5/2 3/4 | 2/6 3/2 2/4 1/4 |
          6,/4 1/2 2/2 3/4 5/4 | 6/8 5/4 3/4 | 5/4 3/2 2/2 1/4 2/4 | 3/12 0/4 |
          6/2 6/2 5/2 6/2 1'/4 6/4 | 5/4 3/4 5/2 6/6 | 1'/4 2'/4 3'/4 2'/2 1'/2 | 6/6 5/2 2'/8 |
          3'/4 2'/2 1'/2 6/4 5/4 | 6/2 5/2 3/4 2/2 3/6 | 5/4 6/4 1'/4 6/4 | 7/8 6/4 #5/4 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 第二境 · 寒渊雪境（E 宫，C# 羽）：二胡 + 冰晶钟琴 + 慢太鼓
    battle1: { name: '寒渊雪境', bpm: 112, key: 64, reverb: 2.8,
      chords: '6m 4 1 5 6m 4 2m 3M',
      tracks: [
        { kind: 'chord', inst: 'pad', layer: 0, low: 49, vel: .5 },
        { kind: 'arp', inst: 'bell', layer: 0, low: 73, vel: .3, rhythm: 'x..x..x.x..x..x.', pattern: [0, 2, 1, 3, 2, 4] },
        { kind: 'bass', inst: 'bass', layer: 2, low: 33, vel: .7, rhythm: 'x.......x...x...' },
        { kind: 'arp', inst: 'zheng', layer: 2, low: 61, vel: .32, rhythm: 'x.x.x.x.x.x.x.x.', pattern: [0, 2, 3, 2, 4, 3, 2, 1] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .85, rhythm: 'X.......x.......', fill: 'X...x...X.x.x.xx', fillEvery: 4 },
        { kind: 'drum', inst: 'rim', layer: 3, vel: .6, rhythm: '....x.......x...' },
        { kind: 'drum', inst: 'shaker', layer: 3, vel: .55, rhythm: 'g.x.g.x.g.x.g.x.' },
        { kind: 'chord', inst: 'choir', layer: 4, low: 52, vel: .45 },
        { kind: 'drum', inst: 'taiko', layer: 4, vel: .4, rhythm: '....x.......x.x.' },
        { kind: 'drum', inst: 'bo', layer: 4, vel: .6, rhythm: 'X...............', every: 4 },
        { kind: 'melody', inst: 'erhu', layer: 1, vel: .8, notes: `
          6,/8 1/4 2/4 | 3/12 2/2 1/2 | 2/8 1/4 6,/4 | 5,/16 |
          6,/4 1/4 3/4 5/4 | 6/8 5/4 3/4 | 2/6 3/2 2/4 1/4 | 3/8 7,/8 |
          6/6 1'/2 6/4 5/4 | 3/8 5/4 6/4 | 1'/6 2'/2 1'/4 6/4 | 5/16 |
          3'/4 2'/4 1'/4 6/4 | 5/6 6/2 1'/8 | 2'/8 1'/4 6/4 | 7/16 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 第三境 · 赤烬废城（F 宫，D 羽带弗里几亚色彩）：失真贝斯 + 铁砧 + 唢呐
    battle2: { name: '赤烬废城', bpm: 134, key: 65, reverb: 1.3,
      chords: '6m b7 6m 5 6m b7 4 3M',
      tracks: [
        { kind: 'chord', inst: 'pad', layer: 0, low: 46, vel: .45 },
        { kind: 'bass', inst: 'dbass', layer: 0, low: 38, vel: .55, rhythm: 'x---------------' },
        { kind: 'bass', inst: 'dbass', layer: 2, low: 38, vel: .8, rhythm: 'x.xox.x.x.xox.x.' },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .95, rhythm: 'X..x..X.x.x..x..', fill: 'X..x..X.x.xxxxxx', fillEvery: 4 },
        { kind: 'drum', inst: 'clap', layer: 3, vel: .8, rhythm: '....X.......X...' },
        { kind: 'drum', inst: 'hat', layer: 3, vel: .6, rhythm: 'x.x.x.x.x.x.x.x.' },
        { kind: 'chord', inst: 'brass', layer: 4, low: 50, vel: .6, rhythm: 'X..X..X.........' },
        { kind: 'drum', inst: 'anvil', layer: 4, vel: .7, rhythm: '....x.......x..x' },
        { kind: 'drum', inst: 'bo', layer: 4, vel: .65, rhythm: 'X...............', every: 4 },
        { kind: 'melody', inst: 'suona', layer: 1, vel: .78, notes: `
          6,/2 6,/2 1/2 6,/2 2/4 1/4 | b7,/6 6,/2 5,/8 | 6,/2 1/2 2/2 3/2 5/4 3/4 | 2/12 0/4 |
          6/2 6/2 5/2 6/2 1'/4 6/4 | b7/8 6/4 5/4 | 4/4 5/4 6/4 1'/4 | 3/4 #5/4 7/8 |
          6/4 0/2 6/2 5/2 6/2 1'/4 | 2'/4 1'/4 b7/8 | 6/2 5/2 3/2 5/2 6/8 | 5/8 3/4 2/4 |
          3/2 5/2 6/4 1'/2 6/2 5/4 | b7/6 1'/2 b7/4 6/4 | 4/4 2/4 1/4 7,/4 | 3/16 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 第四境 · 冥月天阙（D 宫，B 羽）：管风琴 + 合唱 + 二胡，终章气势
    battle3: { name: '冥月天阙', bpm: 126, key: 62, reverb: 3.4,
      chords: '6m 4 1 5 6m 4 2m 3M',
      tracks: [
        { kind: 'chord', inst: 'organ', layer: 0, low: 47, vel: .45 },
        { kind: 'bass', inst: 'bass', layer: 2, low: 35, vel: .75, rhythm: 'x.....x.x.....x.' },
        { kind: 'arp', inst: 'zheng', layer: 2, low: 59, vel: .34, rhythm: 'x.x.x.x.x.x.x.x.', pattern: [0, 1, 2, 3, 4, 3, 2, 1] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .9, rhythm: 'X...x...X...x.x.', fill: 'X.x.x.x.X.xxx.xx', fillEvery: 4 },
        { kind: 'drum', inst: 'tanggu', layer: 3, vel: .6, rhythm: '..g...x...g...x.' },
        { kind: 'drum', inst: 'ohat', layer: 3, vel: .5, rhythm: '..x...x...x...x.' },
        { kind: 'chord', inst: 'choir', layer: 4, low: 54, vel: .5 },
        { kind: 'drum', inst: 'taiko', layer: 4, vel: .4, rhythm: 'x.x.x.x.x.x.x.x.' },
        { kind: 'drum', inst: 'gong', layer: 4, vel: .6, rhythm: 'X...............', every: 8 },
        { kind: 'melody', inst: 'erhu', layer: 1, vel: .82, notes: `
          6,/4 3/4 2/4 1/4 | 2/8 1/4 2/4 | 3/6 5/2 3/4 2/4 | 2/12 1/2 2/2 |
          6,/4 3/4 5/4 6/4 | 1'/8 6/4 5/4 | 5/6 3/2 2/4 3/4 | 3/8 7,/8 |
          6/8 1'/4 2'/4 | 3'/8 2'/4 1'/4 | 2'/6 1'/2 6/4 5/4 | 3/12 0/4 |
          6/4 1'/4 3'/4 2'/4 | 1'/8 2'/4 1'/4 | 6/6 5/2 3/4 2/4 | 3/16 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // Boss · 妖王（C 宫，A 羽）：失真贝斯 + 霓虹脉冲 + 合唱铜管
    boss: { name: '妖王', bpm: 140, key: 60, reverb: 2, base: .72, gain: .8,
      chords: '6m 6m 4 3M 6m b7 4 3M',
      tracks: [
        { kind: 'chord', inst: 'pad', layer: 0, low: 45, vel: .5 },
        { kind: 'chord', inst: 'organ', layer: 0, low: 33, vel: .35, rhythm: 'x---------------' },
        { kind: 'bass', inst: 'dbass', layer: 2, low: 33, vel: .8, rhythm: 'x.x.o.x.x.x.o.x.' },
        { kind: 'arp', inst: 'pulse', layer: 2, low: 57, vel: .5, rhythm: 'xxxxxxxxxxxxxxxx', pattern: [0, 2, 1, 3, 2, 4, 3, 2] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: .95, rhythm: 'X..x..x.X..x..x.', fill: 'X.x.x.x.xxxxXXXX', fillEvery: 4 },
        { kind: 'drum', inst: 'snare', layer: 3, vel: .75, rhythm: '....X.......X...' },
        { kind: 'drum', inst: 'hat', layer: 3, vel: .55, rhythm: 'xxxxxxxxxxxxxxxx' },
        { kind: 'chord', inst: 'choir', layer: 4, low: 52, vel: .55, rhythm: 'X.......X.......' },
        { kind: 'chord', inst: 'brass', layer: 4, low: 45, vel: .55, rhythm: 'X..X..X...X.....' },
        { kind: 'drum', inst: 'bo', layer: 4, vel: .7, rhythm: 'X...............', every: 4 },
        { kind: 'melody', inst: 'erhu', layer: 1, vel: .8, notes: `
          6,/2 6,/2 3/4 2/2 1/2 7,/4 | 6,/12 0/4 | 1/2 2/2 3/4 4/4 3/4 | #5,/8 7,/8 |
          6/2 6/2 5/4 3/2 2/2 3/4 | 4/8 2/4 b7,/4 | 1/4 2/4 3/4 6/4 | #5/8 3/8 |
          6/2 6/2 3'/4 2'/2 1'/2 7/4 | 6/12 0/4 | 1'/2 2'/2 3'/4 4'/4 3'/4 | #5/8 7/8 |
          6'/2 6'/2 5'/4 3'/2 2'/2 3'/4 | 4'/8 2'/4 b7/4 | 1'/4 7/4 6/4 #5/4 | 6/16 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] },
    // 终局 Boss · 终焉（降 B 宫，G 羽）：管风琴 + 合唱 + 锣
    bossfinal: { name: '终焉', bpm: 132, key: 58, reverb: 3.6, base: .72, gain: .8,
      chords: '6m 4 1 5 6m 4 2m 3M',
      tracks: [
        { kind: 'chord', inst: 'organ', layer: 0, low: 43, vel: .5 },
        { kind: 'chord', inst: 'choir', layer: 0, low: 50, vel: .35 },
        { kind: 'bass', inst: 'dbass', layer: 2, low: 31, vel: .75, rhythm: 'x..x..x.x..x..x.' },
        { kind: 'arp', inst: 'zheng', layer: 2, low: 55, vel: .36, rhythm: 'xxxxxxxxxxxxxxxx', pattern: [0, 1, 2, 3, 4, 3, 2, 1] },
        { kind: 'drum', inst: 'taiko', layer: 3, vel: 1, rhythm: 'X..x..x.X.x.x...', fill: 'X.x.x.x.X.x.xxxx', fillEvery: 4 },
        { kind: 'drum', inst: 'tanggu', layer: 3, vel: .7, rhythm: '....X.......X...' },
        { kind: 'drum', inst: 'ohat', layer: 3, vel: .5, rhythm: '..x...x...x...x.' },
        { kind: 'chord', inst: 'brass', layer: 4, low: 46, vel: .55, rhythm: 'X.....X...X.....' },
        { kind: 'drum', inst: 'boom', layer: 4, vel: .6, rhythm: 'X...............', every: 4 },
        { kind: 'drum', inst: 'gong', layer: 4, vel: .55, rhythm: 'X...............', every: 8 },
        { kind: 'melody', inst: 'erhu', layer: 1, vel: .82, notes: `
          6/8 3'/8 | 1'/4 2'/4 3'/8 | 5'/6 3'/2 2'/4 1'/4 | 2'/16 |
          6/4 1'/4 3'/4 6'/4 | 5'/4 3'/4 1'/8 | 2'/6 3'/2 5'/4 3'/4 | 3'/8 7/8 |
          6'/8 5'/4 3'/4 | 5'/6 6'/2 5'/4 3'/4 | 2'/8 1'/4 6/4 | 5/12 0/4 |
          6/4 1'/4 2'/4 3'/4 | 5'/8 3'/8 | 2'/4 1'/4 7/4 #5/4 | 3'/16 |
          0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16 | 0/16` }
      ] }
  };
  const LAYER_AT = [0, .12, .34, .54, .8];

  /* ---------- 编译：把每条轨道展开成循环内的事件表 ---------- */
  function compile(id) {
    const song = SONGS[id];
    if (!song) throw new Error('Unknown song: ' + id);
    const chords = song.chords.trim().split(/\s+/).map(parseChord), bars = chords.length;
    const tracks = song.tracks.map((tr, ti) => {
      let period = bars * 16;
      const ev = [];
      const chordAt = bar => chords[bar % bars];
      const tones = (c, kind) => {
        const third = THIRD[c.q], root = wrap(song.key + c.root, tr.low ?? 48);
        if (kind === 'chord') return [0, 7, 12, third + 12].map(k => root + (c.q === '5' && k === third + 12 ? 19 : k));
        return [0, 7, 12, third + 12, 19, 24].map(k => root + k);
      };
      if (tr.kind === 'melody') {
        const m = parseMelody(tr.notes, song.key);
        period = m.steps;
        for (const n of m.notes) ev.push({ step: n.step, len: n.len, midi: n.midi, vel: tr.vel });
      } else {
        const rhythm = tr.rhythm ? parseRhythm(tr.rhythm) : { hits: [{ step: 0, len: 16, ch: 'x', vel: 1 }], steps: 16 };
        const fill = tr.fill ? parseRhythm(tr.fill) : null;
        for (let bar = 0; bar < bars * (tr.every && bars % tr.every ? tr.every : 1); bar++) {
          if (tr.every && bar % tr.every) continue;
          const pat = fill && bar % tr.fillEvery === tr.fillEvery - 1 ? fill : rhythm;
          const c = chordAt(bar);
          let k = 0;
          for (const h of pat.hits) {
            const step = bar * 16 + h.step, vel = tr.vel * h.vel;
            if (tr.kind === 'drum') ev.push({ step, len: h.len, drum: tr.inst, vel });
            else if (tr.kind === 'chord') for (const midi of tones(c, 'chord')) ev.push({ step, len: tr.rhythm ? Math.max(h.len, 6) : 16, midi, vel: vel * .7 });
            else if (tr.kind === 'bass') {
              const root = wrap(song.key + c.root, tr.low ?? 33);
              ev.push({ step, len: h.len, midi: root + (h.ch === 'o' ? 12 : h.ch === '5' ? 7 : 0), vel });
            } else if (tr.kind === 'arp') {
              const t = tones(c, 'arp');
              ev.push({ step, len: h.len, midi: t[tr.pattern[k++ % tr.pattern.length] % t.length], vel });
            }
          }
        }
        period = bars * 16 * (tr.every && bars % tr.every ? tr.every : 1);
      }
      // 按步建索引
      const byStep = new Map();
      for (const e of ev) { e.track = ti; e.layer = tr.layer; e.inst = tr.inst; if (!byStep.has(e.step)) byStep.set(e.step, []); byStep.get(e.step).push(e); }
      return { ...tr, period, events: ev, byStep };
    });
    return { id, ...song, bars, tracks, layerAt: song.layerAt || LAYER_AT };
  }
  // 某一步（全曲绝对步数）要发出的事件
  function eventsAt(comp, step) {
    const out = [];
    for (const tr of comp.tracks) { const list = tr.byStep.get(step % tr.period); if (list) out.push(...list); }
    return out;
  }
  // 层增益：阈值附近平滑过渡
  function layerGain(comp, layer, intensity) {
    const at = comp.layerAt[layer] ?? 0;
    if (at <= 0) return 1;
    const u = D.clamp((intensity - at + .07) / .14, 0, 1);
    return u * u * (3 - 2 * u);
  }

  /* ---------- 采样 ---------- */
  // 选离目标最近的采样根音，返回 { root, rate }
  function rootFor(inst, midi) {
    const I = INST[inst], m = D.clamp(midi, I.lo - 6, I.hi + 6);
    const k = Math.round((m - I.lo) / I.step), root = D.clamp(I.lo + k * I.step, I.lo, I.lo + Math.floor((I.hi - I.lo) / I.step) * I.step);
    return { root, rate: 2 ** ((midi - root) / 12) };
  }
  // 渲染一个乐器根音：返回 { data, rate, loopStart?, loopEnd? }
  function renderNote(inst, root) {
    const I = INST[inst];
    return D.withRate(I.rate, () => {
      let out = I.render(root, D.hash(inst) + root);
      const loop = out && out.data ? out : null;
      let data = loop ? loop.data : out;
      data = D.finish(data, 0, .001, loop ? 0 : .02);
      D.level(data, .2);
      return { data, rate: I.rate, loopStart: loop?.loopStart, loopEnd: loop?.loopEnd };
    });
  }
  function renderDrum(name, variant = 0) {
    const out = DRUM[name].render(D.hash(name) + variant * 131);
    return D.trim(D.level(D.finish(out, 0), .22));
  }
  // 曲目需要的全部 [乐器, 根音]
  function rootsFor(comp) {
    const set = new Set();
    for (const tr of comp.tracks) for (const e of tr.events) if (e.midi != null) set.add(e.inst + ':' + rootFor(e.inst, e.midi).root);
    return [...set].map(k => { const [inst, root] = k.split(':'); return [inst, +root]; });
  }

  return { INST, DRUM, SONGS, compile, eventsAt, layerGain, rootFor, renderNote, renderDrum, rootsFor, parseMelody, parseRhythm, parseChord };
})();
if (typeof module !== 'undefined') module.exports = NRMUSIC;
