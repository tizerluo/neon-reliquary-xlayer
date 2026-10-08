// Menu actors keep their own skeletons while a battle uses separate instances.
// Only eviction disposes an actor; hiding a view must leave its cache reusable.
export function createPresentationActors(limit = 4) {
  const actors = new Map();
  let activeKey = null;

  function hide() {
    for (const actor of actors.values()) actor.root.visible = false;
    activeKey = null;
  }

  return {
    show(key, create) {
      if (activeKey !== key) hide();
      let actor = actors.get(key);
      if (!actor) actor = create();
      if (!actor) return null;
      actors.delete(key);
      actors.set(key, actor);
      actor.root.visible = true;
      activeKey = key;
      while (actors.size > limit) {
        const oldest = actors.keys().next().value;
        actors.get(oldest).dispose();
        actors.delete(oldest);
      }
      return actor;
    },
    hide,
    metrics: () => ({ active: activeKey, size: actors.size }),
  };
}
