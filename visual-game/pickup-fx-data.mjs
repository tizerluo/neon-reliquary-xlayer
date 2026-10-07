// 道具表现只读真实池：分档与尾迹不能反过来改变吸取速度、价值或释放时机。
export const PICKUP_TIERS = Object.freeze([
  Object.freeze({ scale: .7, emission: .64 }),
  Object.freeze({ scale: 1, emission: .88 }),
  Object.freeze({ scale: 1.6, emission: 1.16 }),
]);
export const pickupTier = value => value < 10 ? 0 : value < 50 ? 1 : 2;
export const pickupStyle = value => PICKUP_TIERS[pickupTier(value)];
export const PICKUP_TRAIL_LIFE = .18;
const EPSILON = 1e-7;

// 最多七个历史样本 / 槽位；只在游戏时间向前、真实位置发生移动时采样。
export function createPickupHistory() {
  let run = null, lastTime = null;
  const records = new Map();
  function reset() { records.clear(); run = null; lastTime = null; }
  function update(frame, time = frame.run?.time ?? 0) {
    if (frame.run !== run || lastTime !== null && time < lastTime) {
      records.clear(); run = frame.run;
    }
    const O = frame.O;
    if (!O || !Number.isFinite(time)) { reset(); return []; }
    const states = [];
    for (let i = 0; i < O.max; i++) {
      const x = O.x[i], y = O.y[i], age = O.age[i], value = O.value[i];
      if (!O.a[i] || O.kind[i] !== 0 || ![x, y, age, value].every(Number.isFinite)) {
        records.delete(i); continue;
      }
      let rec = records.get(i);
      // O 是优先复用释放槽位的池；同值新物的年龄甚至可能等于旧快照。
      // 校验年龄增量与游戏时间增量，容许 Float32 舍入，不仅依赖严格年龄回退。
      const reborn = rec && time > rec.time + EPSILON
        && Math.abs((age - rec.age) - (time - rec.time)) > Math.max(1e-5, Math.abs(age) * 1e-6);
      if (!rec || age + EPSILON < rec.age || value !== rec.value || reborn) {
        rec = { x, y, age, value, time, points: [] }; records.set(i, rec);
      } else if (time > rec.time + EPSILON) {
        const elapsed = time - rec.time, distance = Math.hypot(x - rec.x, y - rec.y);
        // 补帧跨度大或瞬移不连线；游戏正常吸取以位置连续变化为准。
        if (elapsed > .25 || distance > 140) rec.points.length = 0;
        else if (distance > .4) {
          if (!rec.points.length) rec.points.push({ x: rec.x, y: rec.y, time: rec.time });
          rec.points.push({ x, y, time });
          if (rec.points.length > 7) rec.points.shift();
        }
        rec.x = x; rec.y = y; rec.age = age; rec.time = time;
      }
      while (rec.points.length && rec.points[0].time < time - PICKUP_TRAIL_LIFE) rec.points.shift();
      states.push({ index: i, tier: pickupTier(value), ...pickupStyle(value),
        points: rec.points.map(p => ({ ...p })), age });
    }
    lastTime = time;
    return states;
  }
  return { update, reset, size: () => records.size };
}
