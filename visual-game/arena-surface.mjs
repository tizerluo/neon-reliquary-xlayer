// 氛围出生面：按真实世界面积取样；裁剪活动范围，避免大地面把粒子浪费在远处。
import * as THREE from 'three';

export function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value + 0x6D2B79F5) >>> 0;
    let n = Math.imul(value ^ (value >>> 15), 1 | value);
    n ^= n + Math.imul(n ^ (n >>> 7), 61 | n);
    return ((n ^ (n >>> 14)) >>> 0) / 4294967296;
  };
}

export function collectSurface(root, { from, bounds = null, yRange = null } = {}) {
  const tris = [], sums = [];
  let total = 0;
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const ab = new THREE.Vector3(), ac = new THREE.Vector3();
  const add = (p, q, r) => {
    const ux = q[0] - p[0], uy = q[1] - p[1], uz = q[2] - p[2];
    const vx = r[0] - p[0], vy = r[1] - p[1], vz = r[2] - p[2];
    const area = Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2;
    if (area < 1e-6) return;
    total += area;
    tris.push(...p, ...q, ...r);
    sums.push(total);
  };
  // Sutherland–Hodgman：在世界坐标裁剪三角形，保留边缘的正确面积权重。
  function clip(poly, axis, limit, sign) {
    const result = [];
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      const insideP = sign * (p[axis] - limit) >= 0;
      const insideQ = sign * (q[axis] - limit) >= 0;
      if (insideP) result.push(p);
      if (insideP !== insideQ) {
        const t = (limit - p[axis]) / (q[axis] - p[axis]);
        result.push(p.map((v, k) => v + (q[k] - v) * t));
      }
    }
    return result;
  }
  root.updateMatrixWorld(true);
  root.traverse(o => {
    if (!o.isMesh || !o.geometry.attributes.position) return;
    const geo = o.geometry, pos = geo.attributes.position, idx = geo.index;
    const materials = [].concat(o.material);
    const orientation = o.matrixWorld.determinant() < 0 ? -1 : 1;
    const groups = Array.isArray(o.material) ? geo.groups : [{ start: 0, count: idx ? idx.count : pos.count, materialIndex: 0 }];
    for (const group of groups) {
      const material = materials[group.materialIndex];
      if (!material) continue;
      if (from) { from.lastIndex = 0; if (!from.test(material.name || '')) continue; }
      const start = Math.max(group.start, geo.drawRange.start);
      const end = Math.min(group.start + group.count, geo.drawRange.start + geo.drawRange.count, idx ? idx.count : pos.count);
      for (let k = start; k + 2 < end; k += 3) {
        a.fromBufferAttribute(pos, idx ? idx.getX(k) : k).applyMatrix4(o.matrixWorld);
        b.fromBufferAttribute(pos, idx ? idx.getX(k + 1) : k + 1).applyMatrix4(o.matrixWorld);
        c.fromBufferAttribute(pos, idx ? idx.getX(k + 2) : k + 2).applyMatrix4(o.matrixWorld);
        ab.subVectors(b, a).cross(ac.subVectors(c, a));
        // 只取朝上的有效面；排除侧墙、底面和退化三角形。
        if (ab.lengthSq() < 4e-12 || ab.normalize().y * orientation < 0.5) continue;
        let poly = [a.toArray(), b.toArray(), c.toArray()];
        if (bounds) {
          for (const [axis, limit, sign] of [[0, bounds[0], 1], [0, bounds[1], -1], [2, bounds[2], 1], [2, bounds[3], -1]]) {
            poly = clip(poly, axis, limit, sign);
            if (poly.length < 3) break;
          }
        }
        if (yRange && poly.length >= 3) {
          poly = clip(poly, 1, yRange[0], 1);
          poly = clip(poly, 1, yRange[1], -1);
        }
        for (let i = 1; i + 1 < poly.length; i++) add(poly[0], poly[i], poly[i + 1]);
      }
    }
  });
  const triangles = new Float32Array(tris), cumulative = new Float64Array(sums);
  return {
    triangles, cumulative, total,
    sample(rng = Math.random, target = new THREE.Vector3()) {
      if (!total) return null;
      const r = rng() * total;
      let lo = 0, hi = cumulative.length - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (cumulative[mid] < r) lo = mid + 1; else hi = mid; }
      let u = rng(), v = rng();
      if (u + v > 1) { u = 1 - u; v = 1 - v; }
      const t = lo * 9;
      return target.set(
        triangles[t] + u * (triangles[t + 3] - triangles[t]) + v * (triangles[t + 6] - triangles[t]),
        triangles[t + 1] + u * (triangles[t + 4] - triangles[t + 1]) + v * (triangles[t + 7] - triangles[t + 1]),
        triangles[t + 2] + u * (triangles[t + 5] - triangles[t + 2]) + v * (triangles[t + 8] - triangles[t + 2]),
      );
    },
  };
}
