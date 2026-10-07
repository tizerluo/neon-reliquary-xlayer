#!/usr/bin/env node
// 离线审听：渲染全部程序化音效与配乐预览，输出 WAV / MP3、频谱图与数值报告。
// 音效与游戏逐样本一致；配乐用同一乐谱与乐器采样在 Node 中混音（混响用 ffmpeg 卷积近似引擎的混响总线）。
// 用法：node tools/audio_review.cjs [输出目录，默认 art/review/audio]
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

global.NRDSP = require('../src/audio-dsp.js');
global.NRSFX = require('../src/audio-sfx.js');
global.NRMUSIC = require('../src/audio-music.js');
const D = NRDSP, S = NRSFX, M = NRMUSIC, SR = 44100;
const OUT = path.resolve(process.argv[2] || path.join(__dirname, '../art/review/audio'));
const TMP = path.join(OUT, '.tmp');
fs.mkdirSync(TMP, { recursive: true });

function wav(file, chans, rate = SR) {
  const n = chans[0].length, ch = chans.length, buf = Buffer.alloc(44 + n * ch * 2);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * ch * 2, 4); buf.write('WAVEfmt ', 8); buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20); buf.writeUInt16LE(ch, 22); buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * ch * 2, 28); buf.writeUInt16LE(ch * 2, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(n * ch * 2, 40);
  for (let i = 0, o = 44; i < n; i++) for (let c = 0; c < ch; c++, o += 2) buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, chans[c][i])) * 32767), o);
  fs.writeFileSync(file, buf);
}
function resample(x, from, to) {
  if (from === to) return x;
  const n = Math.floor(x.length * to / from), out = new Float32Array(n), k = from / to;
  for (let i = 0; i < n; i++) { const p = i * k, i0 = Math.floor(p), f = p - i0; out[i] = x[i0] * (1 - f) + (x[i0 + 1] || 0) * f; }
  return out;
}
const ff = args => execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...args]);
// EBU R128 整体响度与响度范围
function loudness(file) {
  const text = execFileSync('sh', ['-c', `ffmpeg -hide_banner -nostats -i "${file}" -af ebur128 -f null - 2>&1`]).toString().split('Summary:').pop();
  return { I: +(/I:\s+(-?[\d.]+) LUFS/.exec(text) || [0, NaN])[1], LRA: +(/LRA:\s+([\d.]+) LU/.exec(text) || [0, NaN])[1] };
}

/* ---------- 音效：按类别拼成试听卷 ---------- */
const GROUPS = {
  heroes: n => /^(shot|tint|skill|ult|pulse)\d$/.test(n),
  bosses: n => /^(roar|volley|boom)\d$/.test(n),
  combat: n => /^(hit|armor|bosshit|crit|kill|elitekill|bossdie|chain|drain|shatter|stun|freeze|bomb|dash|block)$/.test(n),
  player: n => /^(hurt|shieldhit|shieldbreak|downed|revive|heartbeat|levelup|upgrade|ultready|breakout|heal|orb|chest)$/.test(n),
  enemy: n => /^(warn|warnlane|boom|summon|charge|enrage|zone|eshot|stage|wave|win|fail)$/.test(n),
  ui: n => /^(ui_|route$|camp$|reward$)/.test(n),
  ambience: n => /^amb_/.test(n)
};
const report = { generated: new Date().toISOString(), sfx: {}, music: {} };
const names = Object.keys(S.recipes);
for (const [group, test] of Object.entries(GROUPS)) {
  const list = group === 'heroes'
    ? ['shot', 'tint', 'skill', 'ult', 'pulse'].flatMap(p => [0, 1, 2, 3, 4, 5].map(i => p + i))
    : group === 'bosses' ? ['roar', 'volley', 'boom'].flatMap(p => [0, 1, 2, 3, 4, 5, 6, 7].map(i => p + i)) : names.filter(test);
  const gap = D.len(.35), parts = [], index = [];
  let t = 0;
  for (const name of list) {
    const r = S.recipes[name], rendered = S.render(name, 0), wide = rendered.wide;
    // 游戏内缓冲为 32 / 22.05 kHz，这里线性插值到 44.1 kHz 拼卷
    const data = resample(rendered.data, rendered.rate, SR);
    // 按引擎增益（并含 -3 dB 居中声像）回放，宽度用全通扩宽近似
    const g = r.gain * Math.SQRT1_2 * .55, [L, R] = wide ? D.widen(data, wide * .85, 3) : [data, data];
    parts.push([L.map(v => v * g), R.map(v => v * g)]);
    const m = D.measure(data);
    report.sfx[name] = { group, rate: rendered.rate, seconds: +m.seconds.toFixed(3), targetLU: r.lu, gain: +r.gain.toFixed(3), bright: Math.round(m.bright), width: wide };
    index.push(`${t.toFixed(2)}s  ${name}`);
    t += data.length / SR + .35;
  }
  const total = parts.reduce((a, [l]) => a + l.length + gap, 0), L = new Float32Array(total), R = new Float32Array(total);
  let o = 0;
  for (const [l, r] of parts) { L.set(l, o); R.set(r, o); o += l.length + gap; }
  // 整卷线性提升到峰值 -1 dBFS，卷内相对电平保持游戏内比例
  let pk = 0; for (const c of [L, R]) for (const v of c) pk = Math.max(pk, Math.abs(v));
  const lift = .89 / (pk || 1); for (const c of [L, R]) for (let i = 0; i < c.length; i++) c[i] *= lift;
  const file = path.join(TMP, `sfx-${group}.wav`);
  wav(file, [L, R]);
  ff(['-i', file, '-codec:a', 'libmp3lame', '-q:a', '3', path.join(OUT, `sfx-${group}.mp3`)]);
  ff(['-i', file, '-lavfi', 'showspectrumpic=s=1600x420:legend=1:scale=log:fscale=log:color=magma', path.join(OUT, `sfx-${group}-spectrum.png`)]);
  fs.writeFileSync(path.join(OUT, `sfx-${group}.txt`), index.join('\n') + '\n');
  console.log(`sfx-${group}: ${list.length} sounds, ${(total / SR).toFixed(1)} s`);
}

/* ---------- 配乐：强度三段 0.2 → 0.55 → 0.9，每段 16 小节 ---------- */
const sampleCache = new Map();
function sample(inst, root) {
  const k = inst + root;
  if (!sampleCache.has(k)) sampleCache.set(k, M.renderNote(inst, root));
  return sampleCache.get(k);
}
const drumCache = new Map();
function drum(name, v) { const k = name + v; if (!drumCache.has(k)) drumCache.set(k, M.renderDrum(name, v)); return drumCache.get(k); }
// 采样回放：线性插值变调；带循环区间；包络与引擎一致（线性起音、保持、指数释放）
function addNote(out, smp, rate, start, dur, peak, I) {
  const ratio = rate * smp.rate / SR, a = Math.max(.004, I.attack), hold = Math.max(a, I.ring ? Math.max(dur, I.ring) : dur), rel = I.release / 3;
  const end = hold + I.release * 1.6, n = Math.ceil(end * SR), s0 = Math.round(start * SR), d = smp.data;
  const ls = smp.loopStart ? smp.loopStart * smp.rate : 0, le = smp.loopEnd ? smp.loopEnd * smp.rate : 0;
  let pos = 0;
  for (let i = 0; i < n && s0 + i < out.length; i++) {
    if (le && pos >= le) pos = ls + (pos - le);
    if (!le && pos >= d.length - 1) break;
    const p0 = Math.floor(pos), f = pos - p0, v = d[p0] * (1 - f) + (d[p0 + 1] || 0) * f, t = i / SR;
    const e = t < a ? t / a * peak : t < hold ? peak : peak * Math.exp(-(t - hold) / rel);
    out[s0 + i] += v * e;
    pos += ratio;
  }
}
function renderSong(id, segments = [.2, .55, .9]) {
  const comp = M.compile(id), sd = 60 / comp.bpm / 4, segSteps = 16 * 16;
  const levels = comp.fixed != null ? [comp.fixed] : segments, steps = segSteps * levels.length;
  const out = new Float32Array(Math.ceil((steps * sd + 4) * SR));
  for (let step = 0; step < steps; step++) {
    const level = levels[Math.floor(step / segSteps)], time = step * sd;
    for (const e of M.eventsAt(comp, step)) {
      const lg = M.layerGain(comp, e.layer, comp.base ? Math.max(comp.base, level) : level);
      if (lg < .01) continue;
      if (e.drum) {
        const Dm = M.DRUM[e.drum], d = drum(e.drum, step % Dm.vars), s0 = Math.round(time * SR), g = e.vel * Dm.gain * lg;
        for (let i = 0; i < d.length && s0 + i < out.length; i++) out[s0 + i] += d[i] * g;
      } else {
        const I = M.INST[e.inst], { root, rate } = M.rootFor(e.inst, e.midi);
        addNote(out, sample(e.inst, root), rate, time, e.len * sd, e.vel * I.gain * lg, I);
      }
    }
  }
  // 与引擎相同的配乐总线增益（默认音量 0.24 × 整曲增益）
  const g = .24 * (comp.gain ?? 1);
  for (let i = 0; i < out.length; i++) out[i] *= g;
  return { out, levels, seconds: out.length / SR };
}
const REVERB = { menu: 2.4, camp: 2, battle0: 1.8, battle1: 2.8, battle2: 1.3, battle3: 3.6, boss: 1.8, bossfinal: 3.6 };
for (const id of Object.keys(M.SONGS)) {
  const t0 = Date.now(), { out, levels, seconds } = renderSong(id);
  const dry = path.join(TMP, `music-${id}-dry.wav`), irFile = path.join(TMP, `ir-${id}.wav`);
  wav(dry, [out, out]);
  wav(irFile, D.impulse(REVERB[id], { seed: D.hash(id) }));
  // 干声 + 卷积湿声（约 -10 dB 发送），近似引擎的混响总线；记下干混电平（不含环境声与主链，仅供对比），再把试听版线性提升到 -16 LUFS
  const mix = path.join(TMP, `music-${id}-mix.wav`), mp3 = path.join(OUT, `music-${id}.mp3`);
  ff(['-i', dry, '-i', irFile, '-filter_complex', '[0:a]asplit=2[d][w];[w][1:a]afir=gtype=none[r];[r]volume=0.3[rv];[d][rv]amix=inputs=2:normalize=0', mix]);
  const inGame = loudness(mix);
  ff(['-i', mix, '-af', `volume=${(-16 - inGame.I).toFixed(2)}dB,alimiter=limit=0.89:level=false`, '-codec:a', 'libmp3lame', '-q:a', '3', mp3]);
  ff(['-i', mp3, '-lavfi', 'showspectrumpic=s=1600x420:legend=1:scale=log:fscale=log:color=magma', path.join(OUT, `music-${id}-spectrum.png`)]);
  report.music[id] = { name: M.SONGS[id].name, bpm: M.SONGS[id].bpm, levels, seconds: +seconds.toFixed(1), renderMs: Date.now() - t0, dryMixLUFS: inGame.I, loudnessRangeLU: inGame.LRA, previewLUFS: -16 };
  console.log(`music-${id}: ${seconds.toFixed(1)} s, levels ${levels.join(' → ')}`);
}
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2) + '\n');
fs.rmSync(TMP, { recursive: true, force: true });
console.log('written', OUT);
