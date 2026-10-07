// 程序化音频验收：配方数值健康、渲染可复现、游戏引用全覆盖、曲谱对齐、引擎旧接口兼容。
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SRC = path.join(__dirname, '../src');
global.NRDSP = require('../src/audio-dsp.js');
global.NRSFX = require('../src/audio-sfx.js');
global.NRMUSIC = require('../src/audio-music.js');
const D = NRDSP, S = NRSFX, M = NRMUSIC;

const peakOf = x => x.reduce((m, v) => Math.max(m, Math.abs(v)), 0);

test('Every sound recipe renders finite, levelled, click-free audio for every variant', () => {
  for (const [name, r] of Object.entries(S.recipes)) {
    for (let v = 0; v < r.vars; v++) {
      const { data, wide, rate } = S.render(name, v);
      assert.ok(rate === 32000 || rate === 22050, name + ' render rate');
      assert.ok(data instanceof Float32Array && data.length > 100, name + ' renders');
      assert.ok(data.every(Number.isFinite), name + ' has no NaN / Infinity');
      assert.ok(data.length / rate <= 5, name + ' stays under five seconds');
      assert.ok(peakOf(data) <= .99, name + ' peak headroom');
      assert.ok(D.loudness(data) > .05, name + ' is audible after levelling');
      assert.ok(Math.abs(data[0]) < .02 && Math.abs(data[data.length - 1]) < .02, name + ' starts and ends near silence');
      assert.ok(wide >= 0 && wide <= 1, name + ' width in range');
    }
    for (const k of ['gain', 'gap', 'max', 'pri', 'send', 'vars']) assert.equal(typeof r[k], 'number', name + '.' + k);
  }
});

test('Rendering is deterministic and independent of Math.random', () => {
  const keep = Math.random;
  Math.random = () => { throw new Error('audio must not consume game randomness'); };
  try {
    for (const name of ['shot0', 'ult3', 'roar5', 'boom6', 'levelup', 'amb_gust']) {
      const a = S.render(name, 0).data, b = S.render(name, 0).data;
      assert.deepEqual(a, b, name + ' identical');
    }
    M.renderNote('zheng', 62); M.renderDrum('taiko', 0);
  } finally { Math.random = keep; }
});

test('Every sound the game requests exists, including per-hero and per-boss families', () => {
  const code = fs.readdirSync(SRC).filter(f => f.endsWith('.js') && !f.startsWith('audio')).map(f => fs.readFileSync(path.join(SRC, f), 'utf8')).join('\n');
  const literal = new Set();
  for (const m of code.matchAll(/(?:audio\.sfx|sfxAt)\(\s*'([a-z_0-9]+)'\s*[,)]/g)) literal.add(m[1]);
  for (const m of code.matchAll(/(?:audio\.sfx|sfxAt)\(\s*\w+\s*\?\s*'([a-z_0-9]+)'\s*:\s*'([a-z_0-9]+)'/g)) { literal.add(m[1]); literal.add(m[2]); }
  for (const m of code.matchAll(/UI_CUES=\{([^}]+)\}/g)) for (const c of m[1].matchAll(/'([a-z_]+)'/g)) literal.add(c[1]);
  const families = { shot: 6, skill: 6, ult: 6, pulse: 6, tint: 6, roar: 8, volley: 8, boom: 8 };
  for (const [prefix, n] of Object.entries(families)) {
    assert.match(code, new RegExp(`'${prefix}'\\s*\\+`), prefix + ' family is used by the game');
    for (let i = 0; i < n; i++) literal.add(prefix + i);
  }
  for (const n of ['bosshit', 'armor', 'hit', 'elitekill', 'kill', 'orb', 'heal', 'chest', 'boom', 'eshot', 'win', 'fail']) literal.add(n);
  const missing = [...literal].filter(n => !S.recipes[S.alias[n] || n]);
  assert.deepEqual(missing, []);
  // 每位英雄 / Boss 的同类声音必须真的不同
  for (const [prefix, n] of Object.entries(families)) {
    const sigs = new Set();
    for (let i = 0; i < n; i++) { const d = S.render(prefix + i, 0).data; sigs.add(d.length + ':' + D.measure(d).bright.toFixed(0)); }
    assert.equal(sigs.size, n, prefix + ' variants are distinct');
  }
});

test('Weighty sounds are darker than light ones (sanity of the sound palette)', () => {
  const bright = n => { const r = S.render(n, 0); return D.withRate(r.rate, () => D.measure(r.data).bright); };
  assert.ok(bright('shot1') < bright('shot0'), 'golden greatsword below silver sword');
  assert.ok(bright('bosshit') < bright('hit'), 'boss hit below normal hit');
  assert.ok(bright('boom2') < bright('boom1'), 'earth slam below ice shatter');
  assert.ok(bright('shot3') > bright('shot1'), 'needles above greatsword');
});

test('Every song compiles, bars add up, melodies sit in range and loops align', () => {
  for (const [id, song] of Object.entries(M.SONGS)) {
    const comp = M.compile(id);
    assert.ok(comp.bpm >= 60 && comp.bpm <= 160, id + ' tempo');
    for (const tr of song.tracks) {
      if (tr.kind === 'drum') { assert.ok(M.DRUM[tr.inst], id + ' drum ' + tr.inst); continue; }
      assert.ok(M.INST[tr.inst], id + ' instrument ' + tr.inst);
      if (tr.kind === 'melody') {
        const bars = tr.notes.split('|').map(b => b.trim()).filter(Boolean);
        bars.forEach((b, i) => assert.equal(b.split(/\s+/).reduce((a, t) => a + +(t.split('/')[1] || 4), 0), 16, `${id} bar ${i + 1}`));
        const mel = M.parseMelody(tr.notes, song.key);
        assert.equal(mel.steps % (comp.bars * 16), 0, id + ' melody loop aligns with chords');
        const I = M.INST[tr.inst];
        for (const n of mel.notes) assert.ok(n.midi >= I.lo - 6 && n.midi <= I.hi + 6, `${id} note ${n.midi} in ${tr.inst} range`);
      } else assert.ok(tr.rhythm == null || tr.rhythm.replace(/[\s|]/g, '').length % 16 === 0, id + ' rhythm length');
    }
    for (const tr of comp.tracks) for (const e of tr.events) if (e.midi != null) assert.ok(e.midi > 20 && e.midi < 110, id + ' note range');
  }
});

test('Instrument samples render with valid loops; layer gains rise with intensity', () => {
  for (const id of Object.keys(M.SONGS)) {
    const comp = M.compile(id);
    for (const [inst, root] of M.rootsFor(comp)) {
      const n = M.renderNote(inst, root);
      assert.ok(n.data.every(Number.isFinite), `${inst}:${root} finite`);
      if (n.loopEnd) assert.ok(n.loopStart > 0 && n.loopStart < n.loopEnd && n.loopEnd <= n.data.length / n.rate + 1e-6, `${inst} loop points`);
    }
    for (let layer = 0; layer < 5; layer++) {
      let prev = -1;
      for (let x = 0; x <= 1; x += .05) { const g = M.layerGain(comp, layer, x); assert.ok(g >= prev - 1e-9 && g >= 0 && g <= 1); prev = g; }
    }
  }
  for (const name of Object.keys(M.DRUM)) assert.ok(M.renderDrum(name, 0).every(Number.isFinite), name);
});

// 最小 Web Audio 替身：记录节点与调用，验证引擎在旧接口下可完整运行
function fakeAudio() {
  const param = v => ({ value: v, setTargetAtTime() {}, setValueAtTime() {}, linearRampToValueAtTime() {}, cancelScheduledValues() {}, cancelAndHoldAtTime() {} });
  let started = 0;
  const node = extra => ({ connect() {}, disconnect() {}, gain: param(1), frequency: param(1000), Q: param(1), pan: param(0), threshold: param(0), knee: param(0), ratio: param(1), attack: param(0), release: param(0), playbackRate: param(1), ...extra });
  class Ctx {
    constructor() { this.state = 'running'; this.currentTime = 0; this.sampleRate = 48000; this.destination = node(); }
    resume() { return Promise.resolve(); } suspend() { return Promise.resolve(); }
    createGain() { return node(); } createBiquadFilter() { return node(); } createDynamicsCompressor() { return node(); } createStereoPanner() { return node(); }
    createChannelMerger() { return node(); } createConvolver() { return node(); } createAnalyser() { return node({ fftSize: 64, getFloatTimeDomainData() {} }); }
    createOscillator() { return node({ start() {}, stop() {} }); }
    createBufferSource() { return node({ start() { started++; }, stop() {} }); }
    createBuffer(ch, n, rate) { const data = Array.from({ length: ch }, () => new Float32Array(n)); return { duration: n / rate, getChannelData: i => data[i] }; }
  }
  return { Ctx, started: () => started };
}

test('Engine keeps the legacy API and drives music, ambience and voice limits without errors', () => {
  const fake = fakeAudio(), timers = [];
  const ctx = { NRDSP, NRSFX, NRMUSIC, performance, Math, Object, Array, Map, Set, Float32Array, Promise, String, Number, JSON,
    setInterval: fn => { timers.push(fn); return 1; }, setTimeout: fn => { timers.push(fn); return 1; },
    document: { hidden: false, addEventListener() {}, getElementById: () => ({ textContent: '' }) } };
  ctx.window = { AudioContext: fake.Ctx };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(SRC, 'audio.js'), 'utf8') + '\nthis.NRAudio = NRAudio;', ctx);
  const audio = new ctx.NRAudio({ music: .24, sfx: .55 });
  audio.init();
  assert.equal(audio.info().context, 'running');
  assert.equal(audio.info().song, 'menu');
  // 旧事件名仍可用
  for (const legacy of ['shot', 'hit', 'armor', 'heavy', 'dash', 'pickup', 'level', 'hurt', 'skill', 'ultimate', 'boss', 'block', 'win', 'fail', 'kill']) assert.equal(typeof audio.sfx(legacy), 'boolean');
  audio.stage(2); audio.music('music_battle');
  assert.equal(audio.info().song, 'battle2'); assert.equal(audio.info().ambience, 2);
  audio.boss(7); audio.music('music_boss'); assert.equal(audio.info().song, 'bossfinal');
  audio.bossRage(); assert.equal(audio.info().rage, true);
  audio.bossDown(); audio.stage(1); audio.music('music_battle'); assert.equal(audio.info().song, 'battle1');
  audio.music('music_camp'); assert.equal(audio.info().song, 'camp'); assert.equal(audio.info().ambience, null);
  audio.music('music_battle');
  // 推进调度：每次 tick 前进 25 ms，共 6 秒
  for (let i = 0; i < 240; i++) { audio.ctx.currentTime += .025; audio.battle(i / 240, false, 1, i < 120 ? 1 : .2, false); audio.tick(); }
  assert.ok(fake.started() > 40, 'music notes were scheduled');
  assert.ok(audio.info().intensity > .5, 'intensity followed pressure');
  // 声部上限：同名受 max 约束，总数不超过 40
  for (let i = 0; i < 200; i++) { audio.ctx.currentTime += .001; audio.sfx(['hit', 'armor', 'kill', 'orb', 'shot' + (i % 6), 'tint' + (i % 6), 'volley' + (i % 8)][i % 7]); }
  assert.ok(audio.voices <= 40);
  audio.pause(true); audio.pause(false); audio.muted = true; audio.update(); assert.equal(audio.sfx('hit'), false);
  assert.equal(audio.info().errors.length, 0, audio.info().errors.join('\n'));
});
