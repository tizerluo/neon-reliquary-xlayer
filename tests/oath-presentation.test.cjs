const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createHash}=require('node:crypto');
const {inflateSync}=require('node:zlib');
const modules=Promise.all([import('../visual-game/presentation.mjs'),import('three')]);

test('UI portraits and scene stills are complete PNGs derived from the current game assets',()=>{
  const assets=path.join(__dirname,'../visual-lab/assets'),ui=path.join(assets,'ui');
  const manifest=JSON.parse(fs.readFileSync(path.join(ui,'manifest.json'),'utf8'));
  const sha=b=>createHash('sha256').update(b).digest('hex');
  assert.equal(Object.keys(manifest.assets).length,18);
  for(const entry of Object.values(manifest.assets)){
    const png=fs.readFileSync(path.join(ui,entry.file));
    assert.equal(png.length,entry.bytes,entry.file);
    assert.equal(sha(png),entry.SHA256,entry.file);
    assert.equal(sha(fs.readFileSync(path.join(assets,entry.source))),entry.sourceSHA256,entry.source);
    assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a',entry.file);
    assert.equal(png.subarray(-12).toString('hex'),'0000000049454e44ae426082',entry.file+' truncated');
    const chunks=[];
    for(let offset=8;offset<png.length;){
      const length=png.readUInt32BE(offset),type=png.toString('ascii',offset+4,offset+8);
      assert(offset+12+length<=png.length,entry.file+' incomplete '+type);
      if(type==='IDAT')chunks.push(png.subarray(offset+8,offset+8+length));
      offset+=length+12;
    }
    assert.equal(png[24],8);assert.equal(png[25],6);assert.equal(png[28],0);
    assert.equal(inflateSync(Buffer.concat(chunks)).length,(png.readUInt32BE(16)*4+1)*png.readUInt32BE(20),entry.file+' pixel data');
  }
});

test('Display contexts work before a run and retain the current battlefield through route, camp and result',async()=>{
  const [{presentationFor,HEROES}]=await modules;
  for(let selected=0;selected<6;selected++){
    assert.equal(presentationFor({state:'home',selected}).key,'hero:'+HEROES[selected].id);
    assert.equal(presentationFor({state:'home',selected}).stage,0);
    assert.equal(presentationFor({state:'select',selected,run:{stage:1}}).stage,HEROES[selected].region);
  }
  for(let id=0;id<8;id++)assert.deepEqual(presentationFor({state:'inspect',inspection:{id}}),{kind:'boss',key:'boss-'+id,boss:id,stage:Math.floor(id/2)});
  for(const state of ['play','paused','route','camp','result'])assert.deepEqual(presentationFor({state,P:{},run:{stage:3}}),{kind:'battle',stage:3});
  assert.equal(presentationFor({state:'inspect',inspection:{id:8}}),null);
  assert.equal(presentationFor({state:'play',run:{stage:3}}),null);
  assert.equal(presentationFor({state:'loading'}),null);
});

test('Rotated wide wings and tall heroes fit the available UI rectangle in landscape and portrait',async()=>{
  const [{fitPresentationCamera,presentationRect},THREE]=await modules;
  for(const aspect of [16/9,844/390,390/844])for(const state of ['home','select','inspect'])for(const size of [[2,8,2],[15,6,8],[11,4,12]])for(const yaw of [0,.71,1.57]){
    const box=new THREE.Box3(new THREE.Vector3(...size).multiplyScalar(-.5),new THREE.Vector3(...size).multiplyScalar(.5));
    box.applyMatrix4(new THREE.Matrix4().makeRotationY(yaw));
    const camera=new THREE.PerspectiveCamera(),rect=presentationRect(state,aspect);
    fitPresentationCamera(camera,box,aspect,rect);
    for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
      const p=new THREE.Vector3(x,y,z).project(camera),sx=(p.x+1)/2,sy=(1-p.y)/2;
      assert(sx>=rect.x-1e-6&&sx<=rect.x+rect.width+1e-6,`${state} wing clipped at ${aspect}`);
      assert(sy>=rect.y-1e-6&&sy<=rect.y+rect.height+1e-6,`${state} head or feet clipped at ${aspect}`);
      assert(p.z>-1&&p.z<1);
    }
  }
});
