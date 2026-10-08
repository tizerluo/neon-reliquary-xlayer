const {test} = require('node:test');
const assert = require('node:assert/strict');
const modules = Promise.all([
  import('../visual-game/presentation-actors.mjs'),
  import('../visual-game/presentation.mjs'),
  import('three'),
  import('three/addons/utils/SkeletonUtils.js'),
]);

async function fixture() {
  const [{createPresentationActors}, {HEROES}, THREE, {clone}] = await modules;
  const scene = new THREE.Scene(), source = new THREE.Group();
  const bone = new THREE.Bone(); bone.name = 'Joint'; source.add(bone);
  const mesh = new THREE.SkinnedMesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial());
  mesh.bind(new THREE.Skeleton([bone])); source.add(mesh);
  const clip = new THREE.AnimationClip('Idle', 1, [
    new THREE.NumberKeyframeTrack('Joint.position[y]', [0, 1], [0, 1]),
  ]);
  const created = [];
  function create(key) {
    const root = clone(source), mixer = new THREE.AnimationMixer(root);
    const skeleton = root.children.find(o => o.isSkinnedMesh).skeleton;
    skeleton.computeBoneTexture();
    mixer.clipAction(clip).play(); scene.add(root);
    const actor = {key, root, mixer, skeleton, disposed: 0, dispose() {
      this.disposed++; root.removeFromParent(); mixer.stopAllAction(); skeleton.dispose();
    }};
    created.push(actor); return actor;
  }
  return {cache: createPresentationActors(), scene, source, create, created, HEROES};
}

function live(actor, scene) {
  assert.equal(actor.disposed, 0, actor.key + ' disposed while cached');
  assert.equal(actor.root.parent, scene, actor.key + ' detached from scene');
  assert.equal(actor.root.visible, true, actor.key + ' stayed hidden');
  assert(actor.skeleton.boneTexture, actor.key + ' lost its skeleton texture');
  const before = actor.root.getObjectByName('Joint').position.y;
  actor.mixer.update(.1);
  assert.notEqual(actor.root.getObjectByName('Joint').position.y, before, actor.key + ' animation stopped');
}

test('All six heroes survive repeated battle → selection → home without losing their skeleton or animation', async () => {
  const {cache, scene, create, created, HEROES} = await fixture();
  const battle = create('battle-leader');
  for (const hero of HEROES) {
    const key = 'hero:' + hero.id;
    const selected = cache.show(key, () => create(key));
    const texture = selected.skeleton.boneTexture;
    for (let run = 0; run < 3; run++) {
      // Each battle frame hides menus; battle actors remain independent.
      for (let frame = 0; frame < 5; frame++) cache.hide();
      assert.equal(selected.root.visible, false);
      assert.equal(battle.root.visible, true);
      const returned = cache.show(key, () => assert.fail('same hero was recloned'));
      assert.equal(returned, selected);
      assert.equal(returned.skeleton.boneTexture, texture);
      live(returned, scene);
      assert.equal(cache.show(key, () => assert.fail('home recloned the selection')), selected);
      live(selected, scene);
    }
  }
  assert.equal(created.length, 7);
  assert.equal(cache.metrics().size, 4);
});

test('Hero/Boss revisits show only the active actor; eviction disposes once and later creates a fresh skeleton', async () => {
  const {cache, scene, create, source} = await fixture();
  const a = cache.show('hero:volt', () => create('hero:volt'));
  cache.show('boss-0', () => create('boss-0'));
  assert.equal(a.root.visible, false);
  assert.equal(cache.show('hero:volt', () => assert.fail('cached hero was recloned')), a);
  live(a, scene);
  for (const key of ['boss-1', 'boss-2', 'boss-3', 'boss-4']) cache.show(key, () => create(key));
  assert.equal(cache.metrics().size, 4);
  assert.equal(a.disposed, 1);
  assert.equal(a.root.parent, null);
  assert.equal(a.skeleton.boneTexture, null);
  cache.hide(); cache.hide();
  assert.equal(a.disposed, 1);
  const fresh = cache.show('hero:volt', () => create('hero:volt'));
  assert.notEqual(fresh, a); live(fresh, scene);
  assert.equal(scene.children.filter(root => root.visible).length, 1);
  assert.equal(source.visible, true, 'cache changed the shared source model');
});

test('A pending subject hides the previous actor and becomes reusable when preparation finishes', async () => {
  const {cache, scene, create} = await fixture();
  const first = cache.show('hero:volt', () => create('hero:volt'));
  assert.equal(cache.show('boss-7', () => null), null);
  assert.equal(first.root.visible, false);
  assert.deepEqual(cache.metrics(), {active: null, size: 1});
  const boss = cache.show('boss-7', () => create('boss-7')); live(boss, scene);
  assert.equal(cache.show('hero:volt', () => assert.fail('previous hero was destroyed')), first);
  live(first, scene); assert.equal(boss.root.visible, false);
});
