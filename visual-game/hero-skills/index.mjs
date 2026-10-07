import aurelian from './aurelian.mjs';
import mordred from './mordred.mjs';
import volt from './volt.mjs';
import nyx from './nyx.mjs';
import seraph from './seraph.mjs';
import isolde from './isolde.mjs';

// 六份独立配方共用事件适配；米制换算只有这一处，不从表现层回写战斗。
export const HERO_SKILLS = Object.freeze([aurelian, mordred, volt, nyx, seraph, isolde]);
export function skillContext(event, scale = .028) {
  return { owner: event.owner, hero: event.hero, x: event.x * scale, z: event.y * scale,
    angle: event.angle, seed: event.id, age: event.age ?? 0,
    channelDuration: event.duration ?? 4.2,
    points: (event.points ?? []).map(p => ({ x: p.x * scale, z: p.y * scale,
      radius: (p.radius ?? p.r ?? 0) * scale, duration: p.duration,
      target: p.target, generation: p.generation, owner: p.owner })) };
}
export function heroRecipe(hero, kind, context) {
  const recipe = HERO_SKILLS[hero], make = recipe?.[kind];
  if (typeof make !== 'function') return { cues: [] };
  const definition = make(context);
  return { cues: definition.cues.map((cue, index) => ({ ...cue, effect: {
    hero, label: `${recipe.key}.${kind}.${index}`, cancelOnOwnerLoss: true,
    ...cue.effect,
  } })) };
}
