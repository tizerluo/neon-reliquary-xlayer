// 六种武器的运动语言。只读战斗状态：不改飞剑位置、目标、伤害、吸血概率或冰冻判定。
import * as THREE from 'three';
import { ADDITIVE, radialTexture } from './glow.js';

export const WEAPON_STYLES = ['aurelian', 'mordred', 'volt', 'nyx', 'seraph', 'isolde'];
const COLORS = ['#70e5dc', '#ffab52', '#79adff', '#c293f4', '#f477b5', '#c2f4ff'].map(c => new THREE.Color(c));
const WHITE = new THREE.Color('#e3f3ff');
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const turn = a => Math.atan2(Math.sin(a), Math.cos(a));

function ribbonTexture() {
  const canvas = document.createElement('canvas'); canvas.width = 16; canvas.height = 64;
  const g = canvas.getContext('2d'), gradient = g.createLinearGradient(0, 0, 0, 64);
  for (const [t, a] of [[0, 0], [.25, .45], [.5, 1], [.75, .45], [1, 0]]) gradient.addColorStop(t, `rgba(255,255,255,${a})`);
  g.fillStyle = gradient; g.fillRect(0, 0, 16, 64);
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace; return texture;
}

// 共用一张小图集，但轮廓独立：六角碎片、熔渣、花瓣、分面冰片、四芒闪光、针。
function fragmentAtlas() {
  const canvas = document.createElement('canvas'); canvas.width = 384; canvas.height = 64;
  const g = canvas.getContext('2d');
  const polygon = points => { g.beginPath(); points.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); };
  for (let tile = 0; tile < 6; tile++) {
    g.setTransform(1, 0, 0, 1, tile * 64, 0); g.lineWidth = 2;
    g.fillStyle = 'rgba(255,255,255,.55)'; g.strokeStyle = 'rgba(255,255,255,.95)';
    if (tile === 0) {
      polygon(Array.from({ length: 6 }, (_, i) => [32 + Math.cos(i * Math.PI / 3) * 23, 32 + Math.sin(i * Math.PI / 3) * 23]));
      g.fill(); g.stroke(); polygon([[10, 32], [32, 12], [32, 52]]); g.fillStyle = 'rgba(255,255,255,.75)'; g.fill();
    } else if (tile === 1) {
      polygon([[7, 33], [21, 18], [57, 30], [39, 43]]); g.fill(); g.stroke();
      polygon([[8, 33], [53, 30], [32, 36]]); g.fillStyle = '#fff'; g.fill();
    } else if (tile === 2) {
      g.beginPath(); g.moveTo(9, 32); g.bezierCurveTo(25, 3, 45, 6, 56, 30); g.bezierCurveTo(38, 54, 23, 55, 9, 32);
      g.fill(); g.stroke(); g.beginPath(); g.moveTo(10, 32); g.quadraticCurveTo(35, 24, 55, 30); g.stroke();
    } else if (tile === 3) {
      polygon([[5, 32], [25, 13], [59, 28], [36, 53]]); g.fill(); g.stroke();
      polygon([[5, 32], [25, 13], [32, 32], [36, 53]]); g.fillStyle = 'rgba(255,255,255,.9)'; g.fill();
    } else if (tile === 4) {
      polygon([[32, 4], [37, 26], [60, 32], [37, 37], [32, 60], [27, 37], [4, 32], [27, 26]]); g.fillStyle = '#fff'; g.fill();
    } else {
      polygon([[3, 32], [45, 27], [60, 32], [45, 37]]); g.fillStyle = '#fff'; g.fill();
    }
  }
  const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
  texture.generateMipmaps = false; texture.minFilter = THREE.LinearFilter; return texture;
}

// 动态四边形合批：三张几何 / 三次基础绘制，数量有上限，避免每条细尾都是一个 Mesh。
function makeBatch(scene, name, map, capacity, noGlow = false, atlas = false) {
  const positions = new Float32Array(capacity * 18), colors = new Float32Array(capacity * 18), uv = new Float32Array(capacity * 12);
  const geometry = new THREE.BufferGeometry();
  for (const [key, array, size] of [['position', positions, 3], ['color', colors, 3], ['uv', uv, 2]])
    geometry.setAttribute(key, new THREE.BufferAttribute(array, size).setUsage(THREE.DynamicDrawUsage));
  geometry.setDrawRange(0, 0);
  const material = new THREE.MeshBasicMaterial({ map, vertexColors: true, transparent: true, depthWrite: false,
    side: THREE.DoubleSide, toneMapped: false, ...ADDITIVE });
  material.userData.glowSelf = true;
  const mesh = new THREE.Mesh(geometry, material); mesh.name = name; mesh.frustumCulled = false;
  mesh.renderOrder = 2; mesh.userData.noGlow = noGlow; mesh.visible = false; scene.add(mesh);
  let count = 0, limit = capacity;
  function quad(points, color, gain, tile) {
    if (count >= limit) return false;
    const u0 = atlas ? (tile * 64 + 2) / 384 : 0, u1 = atlas ? (tile * 64 + 62) / 384 : 1;
    const v0 = atlas ? 2 / 64 : 0, v1 = atlas ? 62 / 64 : 1;
    const order = [0, 1, 2, 2, 1, 3], tex = [[u1, v0], [u1, v1], [u0, v0], [u0, v1]];
    for (let k = 0; k < 6; k++) {
      const dst = count * 18 + k * 3, point = points[order[k]];
      positions[dst] = point[0]; positions[dst + 1] = point[1]; positions[dst + 2] = point[2];
      colors[dst] = color.r * gain; colors[dst + 1] = color.g * gain; colors[dst + 2] = color.b * gain;
      uv[count * 12 + k * 2] = tex[order[k]][0]; uv[count * 12 + k * 2 + 1] = tex[order[k]][1];
    }
    count++; return true;
  }
  return {
    mesh, get count() { return count; },
    begin(max = capacity) { count = 0; limit = Math.min(capacity, max); },
    beam(ax, ay, az, bx, by, bz, width, color, gain, tailWidth = width) {
      const dx = bx - ax, dz = bz - az, length = Math.hypot(dx, dz);
      if (length < .005 || count >= limit) return false;
      const nx = -dz / length / 2, nz = dx / length / 2;
      return quad([[ax + nx * width, ay, az + nz * width], [ax - nx * width, ay, az - nz * width],
        [bx + nx * tailWidth, by, bz + nz * tailWidth], [bx - nx * tailWidth, by, bz - nz * tailWidth]], color, gain, 0);
    },
    stamp(x, y, z, length, width, angle, color, gain, tile = 0) {
      const c = Math.cos(angle) / 2, s = Math.sin(angle) / 2;
      return quad([[x + c * length - s * width, y, z + s * length + c * width],
        [x + c * length + s * width, y, z + s * length - c * width],
        [x - c * length - s * width, y, z - s * length + c * width],
        [x - c * length + s * width, y, z - s * length - c * width]], color, gain, tile);
    },
    finish() {
      geometry.setDrawRange(0, count * 6); mesh.visible = count > 0;
      for (const [key, size] of [['position', 18], ['color', 18], ['uv', 12]]) {
        const attribute = geometry.getAttribute(key); attribute.clearUpdateRanges();
        if (count) attribute.addUpdateRange(0, count * size); attribute.needsUpdate = true;
      }
    },
    dispose() { mesh.removeFromParent(); geometry.dispose(); material.dispose(); map.dispose(); },
  };
}

export function createHeroWeaponFX(scene) {
  const ribbons = makeBatch(scene, 'Hero weapon ribbons', ribbonTexture(), 6400);
  const glyphs = makeBatch(scene, 'Hero weapon fragments', fragmentAtlas(), 1800, false, true);
  const mist = makeBatch(scene, 'Frost mist', radialTexture([[0, 'rgba(255,255,255,.65)'], [.4, 'rgba(255,255,255,.24)'], [1, 'rgba(255,255,255,0)']]), 900, true);
  const particles = [], impacts = [], heading = new Float32Array(2600).fill(NaN), age = new Float32Array(2600), emberTick = new Int32Array(2600).fill(-1);
  const actorMap = new Map(), lists = Array.from({ length: 6 }, () => []), squads = new Map();
  let run = null, cursor = 0, clock = 0, stats;
  const totals = { hit: 0, chain: 0, drain: 0, shatter: 0 };
  function reset(nextRun = null, nextCursor = 0) {
    run = nextRun; cursor = nextCursor; clock = nextRun?.time || 0;
    particles.length = impacts.length = 0; heading.fill(NaN); emberTick.fill(-1);
    ribbons.begin(); glyphs.begin(); mist.begin(); ribbons.finish(); glyphs.finish(); mist.finish();
    for (const k in totals) totals[k] = 0;
    stats = { perHero: WEAPON_STYLES.map(id => ({ id, blades: 0, trailSegments: 0 })), events: { ...totals }, particles: 0, impacts: 0, links: 0, swarmGroups: 0, frosted: 0, returns: [], quads: { ribbons: 0, fragments: 0, mist: 0 } };
  }
  reset();
  function particle(kind, x, y, z, h, seed, size = .15, angle = 0, elapsed = 0) {
    if (particles.length >= 400) return;
    const a = angle + (hash(seed) - .5) * 3, speed = 2 + hash(seed + 9) * 3;
    const p = { kind, x, y, z, h, seed, angle: a, vx: Math.cos(a) * speed, vz: Math.sin(a) * speed,
      vy: kind === 'ember' ? 2.1 : .8, age: elapsed, life: kind === 'ember' ? .52 : .32 + hash(seed + 4) * .18, size };
    const travel = (1 - Math.exp(-5 * elapsed)) / 5;
    p.x += p.vx * travel; p.z += p.vz * travel; p.y += p.vy * elapsed - 1.5 * elapsed * elapsed;
    p.vx *= Math.exp(-5 * elapsed); p.vz *= Math.exp(-5 * elapsed); p.vy -= 3 * elapsed;
    particles.push(p);
  }
  function hit(event, S, elapsed) {
    const { hero: h, id, angle = 0 } = event, x = event.x * S, z = event.y * S;
    if (impacts.length < 48) impacts.push({ kind: h === 1 ? 'crack' : h === 2 ? 'zap' : 'flash', h, x, z,
      age: elapsed, life: h === 1 ? .48 : .18, seed: id, angle });
    const kinds = ['hex', 'ember', 'glint', 'needle', 'petal', 'ice'];
    const n = h === 0 ? 5 : h === 1 ? 4 : 2;
    for (let j = 0; j < n; j++) particle(kinds[h], x, .68, z, h, id * 7 + j, h === 0 ? .19 : .13, angle + j * Math.PI * 2 / n, elapsed);
  }
  function lightning(x, z, x2, z2, seed, gain, width = .055, branches = true) {
    const dx = x2 - x, dz = z2 - z, distance = Math.hypot(dx, dz);
    if (distance < .1 || distance > 8) return;
    let ax = x, az = z;
    for (let j = 1; j <= 5; j++) {
      const t = j / 5, offset = j === 5 ? 0 : (hash(seed + j) - .5) * Math.min(.5, distance * .16);
      const bx = x + dx * t - dz / distance * offset, bz = z + dz * t + dx / distance * offset;
      ribbons.beam(ax, .72, az, bx, .72, bz, width, COLORS[2], gain);
      ribbons.beam(ax, .73, az, bx, .73, bz, width * .28, WHITE, gain * .9);
      if (branches && j === 3) ribbons.beam(bx, .72, bz, bx - dz / distance * .32, .73, bz + dx / distance * .32, width * .4, COLORS[2], gain * .55, .005);
      ax = bx; az = bz;
    }
  }
  function frost(frame, S, inView, low) {
    const E = frame.E;
    for (let i = 0; i < E.max && stats.frosted < (low ? 12 : 28); i++) {
      if (!E.a[i] || !(E.slow[i] > 0 || E.freeze[i] > 0) || !inView(E.x[i], E.y[i])) continue;
      stats.frosted++;
      const r = E.radius[i] * S * .8;
      for (let j = 0; j < 3; j++) {
        const a = i * .7 + j * Math.PI * 2 / 3;
        glyphs.stamp(E.x[i] * S + Math.cos(a) * r, .45 + j * .27, E.y[i] * S + Math.sin(a) * r,
          .23, .13, a, COLORS[5], .45 + (E.freeze[i] > 0 ? .25 : 0), 3);
      }
    }
  }
  function update(frame, native, S, dt, ready) {
    if (frame.run !== run) reset(frame.run);
    clock += dt;
    const low = frame.options.quality === 'low', B = frame.B;
    ribbons.begin(low ? 2500 : 6400); glyphs.begin(low ? 700 : 1800); mist.begin(low ? 250 : 900);
    for (const list of lists) list.length = 0; actorMap.clear(); squads.clear();
    for (const unit of [frame.P, ...(frame.agents || [])]) actorMap.set(unit.uid, unit);
    stats = { perHero: WEAPON_STYLES.map(id => ({ id, blades: 0, trailSegments: 0 })), events: { ...totals }, particles: 0, impacts: 0, links: 0, swarmGroups: 0, frosted: 0, returns: [] };
    const halfW = native.viewWidth / 2 + 100, halfH = native.viewHeight / (2 * native.sinElev) + 100;
    const inView = (x, y) => Math.abs(x - frame.camera.x) < halfW && Math.abs(y - frame.camera.y) < halfH;
    // 每条事件消费一次；先保留吸血 / 碎冰 / 雷链，普通命中按英雄轮换限流。
    const fresh = (frame.weaponEvents || []).filter(e => e.id > cursor);
    if (fresh.length) cursor = fresh[fresh.length - 1].id;
    let hitBudget = low ? 6 : 14, specialBudget = low ? 5 : 10;
    const hits = Array.from({ length: 6 }, () => []), ordered = fresh.filter(e => e.kind !== 'hit');
    for (const e of fresh) if (e.kind === 'hit') hits[e.hero]?.push(e);
    for (let n = 0; hits.some(list => list.length > n); n++)
      for (let h = 0; h < 6; h++) if (hits[h][n]) ordered.push(hits[h][n]);
    for (const event of ordered) {
      if (frame.run.time - event.time > .3 || !inView(event.x, event.y) || !ready[event.hero]) continue;
      const elapsed = Math.max(0, frame.run.time - event.time);
      if (event.kind === 'hit') {
        if (hitBudget-- <= 0) continue; hit(event, S, elapsed);
      } else {
        if (specialBudget-- <= 0) continue;
        if (event.kind === 'chain' && impacts.length < 48) impacts.push({ kind: 'chain', h: 2, x: event.x * S, z: event.y * S,
          x2: event.x2 * S, z2: event.y2 * S, seed: event.id, age: elapsed, life: .18 });
        if (event.kind === 'shatter') for (let j = 0; j < (low ? 4 : 8); j++)
          particle('ice', event.x * S, .7, event.y * S, 5, event.id * 13 + j, .18 + hash(event.id + j) * .08, j * Math.PI / 4, elapsed);
        if (event.kind === 'drain') {
          const owner = actorMap.get(event.owner);
          if (!owner || owner.downed || particles.length > 396) continue;
          for (let j = 0; j < 3; j++) particles.push({ kind: 'return', h: 4, owner: event.owner,
            x: event.x * S, y: .75, z: event.y * S, seed: event.id, age: elapsed - j * .05, life: .68, size: j ? .10 : .19 });
        }
      }
      if (event.kind in totals) totals[event.kind]++;
    }
    // 先画短时命中，给每名英雄留同等的尾迹份额；满屏飞剑也不会把后出场英雄全部挤掉。
    drawImpacts(dt);
    drawParticles(dt, S);
    const active = new Set();
    for (let i = 0; i < B.max; i++) {
      if (!B.a[i]) { heading[i] = NaN; continue; }
      const h = B.hero[i] ?? frame.selected;
      if (!ready[h] || !inView(B.x[i], B.y[i])) continue;
      lists[h].push(i); active.add(h); stats.perHero[h].blades++;
      if (h === 3) {
        const key = `${B.owner[i]}:${B.target[i]}`, group = squads.get(key) || { x: 0, z: 0, n: 0 };
        const angle = Math.atan2(B.y[i] - B.ty1[i], B.x[i] - B.tx1[i]);
        group.x += Math.cos(angle); group.z += Math.sin(angle); group.n++; squads.set(key, group);
      }
    }
    stats.swarmGroups = squads.size;
    for (const i of lists[3]) {
      const group = squads.get(`${B.owner[i]}:${B.target[i]}`), groupAngle = Math.atan2(group.z, group.x);
      const wanted = B.angle[i] + Math.max(-.16, Math.min(.16, turn(groupAngle - B.angle[i]) * .2));
      heading[i] = Number.isNaN(heading[i]) || B.age[i] < age[i] ? wanted : heading[i] + turn(wanted - heading[i]) * Math.min(1, dt * 14);
      age[i] = B.age[i];
    }
    let embers = low ? 3 : 8;
    const quota = Math.max(24, Math.floor((low ? 1900 : 5200) / Math.max(1, active.size)));
    for (let h = 0; h < 6; h++) {
      const list = lists[h], cost = h === 0 ? (low ? 8 : 12) : h === 2 ? 8 : 5;
      const stride = Math.max(1, Math.ceil(list.length * cost / quota));
      for (let at = 0; at < list.length; at += stride) {
        const i = list[at], before = ribbons.count + mist.count, s = (B.flags[i] ? 1.15 : .58) * 1.2;
        const points = [[B.x[i] * S, B.y[i] * S], [B.tx1[i] * S, B.ty1[i] * S], [B.tx2[i] * S, B.ty2[i] * S],
          [B.tx3[i] * S, B.ty3[i] * S], [B.tx4[i] * S, B.ty4[i] * S]];
        if (Math.hypot(points[0][0] - points[1][0], points[0][1] - points[1][1]) > 150 * S) continue;
        if (h === 0) helix(points, s, B.age[i] * 17 + hash(i) * 6, low);
        else for (let j = 0; j < (low ? 2 : 4); j++) {
          const a = points[j], b = points[j + 1], fade = 1 - j / 4;
          if (Math.hypot(a[0] - b[0], a[1] - b[1]) > 150 * S) break;
          if (h === 1) ribbons.beam(a[0], .64, a[1], b[0], .64, b[1], .22 * s * fade, COLORS[h], .8 * fade, .14 * s * fade);
          if (h === 2) {
            const mx = (a[0] + b[0]) / 2 + (hash(i + j + Math.floor(clock * 12)) - .5) * .16;
            const mz = (a[1] + b[1]) / 2 + (hash(i * 3 + j) - .5) * .16;
            ribbons.beam(a[0], .66, a[1], mx, .66, mz, .055 * s, COLORS[h], .9 * fade);
            ribbons.beam(mx, .66, mz, b[0], .66, b[1], .045 * s, COLORS[h], .7 * fade);
          }
          if (h === 3) ribbons.beam(a[0], .67, a[1], b[0], .67, b[1], .058 * s * fade, COLORS[h], .7 * fade, .008);
          if (h === 4) ribbons.beam(a[0], .65, a[1], b[0], .65, b[1], .14 * s * fade, COLORS[h], .55 * fade, .025);
          if (h === 5) {
            mist.beam(a[0], .53, a[1], b[0], .53, b[1], .56 * s, COLORS[h], .12 * fade, .8 * s);
            if (j < 2) glyphs.stamp(b[0], .64, b[1], .17 * s, .09 * s, B.angle[i] + j, COLORS[h], .42 * fade, 3);
          }
        }
        if (h === 1 && B.age[i] > Math.max(1.06, B.orbit?.[i] || 0)) {
          const tick = Math.floor(B.age[i] * 16);
          if (tick !== emberTick[i] && embers > 0 && dt > 0) { particle('ember', points[1][0], .7, points[1][1], h, i + tick * 7, .11, B.angle[i] + Math.PI); embers--; }
          emberTick[i] = tick;
        }
        if (h === 3) {
          // 两枚暗一些的卫星针依附真实剑身，共享朝向，读成同组收束而非粗紫光束。
          for (const side of [-1, 1]) glyphs.stamp(points[0][0] - Math.cos(heading[i]) * .2 - Math.sin(heading[i]) * side * .13,
            .66, points[0][1] - Math.sin(heading[i]) * .2 + Math.cos(heading[i]) * side * .13,
            .34 * s, .055 * s, heading[i], COLORS[h], .46, 5);
        }
        stats.perHero[h].trailSegments += ribbons.count + mist.count - before;
      }
    }
    const volt = lists[2];
    // 邻接只查后续四枚剑，同一主人且距离接近才连；固定预算，不做 O(n²) 全剑配对。
    for (let n = 0; n < volt.length && stats.links < (low ? 3 : 8); n++) {
      const a = volt[n];
      if ((Math.floor(clock * 11) + a) % 3 === 0) continue;
      let closest = -1, distance = 3.2;
      for (let k = n + 1; k < Math.min(volt.length, n + 5); k++) {
        const b = volt[k]; if (B.owner[b] !== B.owner[a]) continue;
        const d = Math.hypot(B.x[a] - B.x[b], B.y[a] - B.y[b]) * S;
        if (d > .4 && d < distance) { distance = d; closest = b; }
      }
      if (closest < 0) continue;
      lightning(B.x[a] * S, B.y[a] * S, B.x[closest] * S, B.y[closest] * S, a + Math.floor(clock * 11), .5, .04, false);
      stats.links++;
    }
    frost(frame, S, inView, low);
    stats.events = { ...totals }; stats.particles = particles.length; stats.impacts = impacts.length;
    stats.quads = { ribbons: ribbons.count, fragments: glyphs.count, mist: mist.count };
    ribbons.finish(); glyphs.finish(); mist.finish();
  }
  function helix(points, scale, phase, low) {
    const n = low ? 4 : 6, a = points[0], b = points[points.length - 1], dx = b[0] - a[0], dz = b[1] - a[1];
    const distance = Math.hypot(dx, dz); if (distance < .04 || distance > 150 * .028) return;
    const nx = -dz / distance, nz = dx / distance;
    for (const side of [-1, 1]) {
      let prev;
      for (let j = 0; j <= n; j++) {
        const t = j / n, slot = t * 4, index = Math.min(3, Math.floor(slot)), u = slot - index;
        const x = points[index][0] * (1 - u) + points[index + 1][0] * u, z = points[index][1] * (1 - u) + points[index + 1][1] * u;
        const p = phase + t * Math.PI * 2.7, offset = Math.sin(p) * .18 * scale * side;
        const next = [x + nx * offset, .65 + Math.cos(p) * .12 * scale * side, z + nz * offset];
        if (prev) ribbons.beam(prev[0], prev[1], prev[2], next[0], next[1], next[2], .078 * scale * (1 - t * .65), COLORS[0], .9 * (1 - t * .75));
        prev = next;
      }
    }
  }
  function drawImpacts(dt) {
    for (let i = impacts.length - 1; i >= 0; i--) {
      const p = impacts[i]; p.age += dt;
      if (p.age >= p.life) { impacts.splice(i, 1); continue; }
      const fade = 1 - p.age / p.life;
      if (p.kind === 'chain') lightning(p.x, p.z, p.x2, p.z2, p.seed, fade * 1.2);
      else if (p.kind === 'crack') {
        for (let j = 0; j < 3; j++) {
          const angle = p.angle + (j - 1) * 1.15, radius = .8 + hash(p.seed + j) * .45;
          let ax = p.x, az = p.z;
          for (let k = 1; k <= 3; k++) {
            const r = radius * k / 3, zig = (k % 2 ? 1 : -1) * .1;
            const bx = p.x + Math.cos(angle) * r - Math.sin(angle) * zig, bz = p.z + Math.sin(angle) * r + Math.cos(angle) * zig;
            ribbons.beam(ax, .07, az, bx, .07, bz, .075 * fade, COLORS[1], .75 * fade, .016);
            ax = bx; az = bz;
          }
        }
      } else if (p.kind === 'zap') {
        for (let j = 0; j < 3; j++) {
          const a = p.angle + j * 2.1;
          lightning(p.x, p.z, p.x + Math.cos(a) * .7, p.z + Math.sin(a) * .7, p.seed + j, fade * .8, .04, false);
        }
      } else glyphs.stamp(p.x, .69, p.z, .36 * (1.3 - fade * .3), .36, p.angle, COLORS[p.h], fade * .75, 4);
    }
  }
  function drawParticles(dt, S) {
    const tiles = { hex: 0, ember: 1, petal: 2, ice: 3, glint: 4, needle: 5 };
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i]; p.age += dt;
      if (p.age >= p.life) { particles.splice(i, 1); continue; }
      if (p.age < 0) continue;
      const t = p.age / p.life, fade = 1 - t;
      if (p.kind === 'return') {
        const owner = actorMap.get(p.owner);
        if (!owner || owner.downed) { particles.splice(i, 1); continue; }
        const x2 = owner.x * S, z2 = owner.y * S, dx = x2 - p.x, dz = z2 - p.z;
        const distance = Math.hypot(dx, dz) || 1, bend = .8 * (hash(p.seed) > .5 ? 1 : -1);
        const x = p.x + dx * t - dz / distance * Math.sin(Math.PI * t) * bend;
        const z = p.z + dz * t + dx / distance * Math.sin(Math.PI * t) * bend, y = .75 + Math.sin(Math.PI * t) * .9;
        glyphs.stamp(x, y, z, p.size * 1.8, p.size, Math.atan2(dz, dx), COLORS[4], .85 * Math.sin(Math.PI * Math.min(.95, t) + .18), 2);
        if (stats.returns.length < 4) stats.returns.push({ owner: p.owner, progress: t, target: [x2, z2] });
        continue;
      }
      p.x += p.vx * dt; p.z += p.vz * dt; p.y += p.vy * dt;
      const drag = Math.exp(-5 * dt); p.vx *= drag; p.vz *= drag; p.vy -= 3 * dt;
      const length = p.kind === 'needle' ? p.size * 2.5 : p.size;
      glyphs.stamp(p.x, Math.max(.12, p.y), p.z, length, p.kind === 'needle' ? p.size * .3 : p.size * .65,
        p.angle + t * (p.kind === 'ember' ? 3 : 1), COLORS[p.h], fade * (p.kind === 'ice' ? 1 : .8), tiles[p.kind]);
    }
  }
  return { update, reset,
    bladeHeading: (i, fallback) => Number.isNaN(heading[i]) ? fallback : heading[i],
    metrics: () => ({ ...stats, mode: 'hero', capacities: { ribbons: 6400, fragments: 1800, mist: 900, particles: 400, impacts: 48 } }),
    dispose() { reset(); ribbons.dispose(); glyphs.dispose(); mist.dispose(); },
  };
}
