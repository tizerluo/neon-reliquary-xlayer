const {test}=require('node:test');
const assert=require('node:assert/strict');
const {simulation}=require('./sim_harness.cjs');

function fixture(){
  const s=simulation();s.startFull();s.chooseRoute(s.options()[0]);s.clear();s.bindInputs();
  return s;
}
function advance(s,n=30){for(let i=0;i<n;i++)s.tick(1/60);}

test('Held joystick pointer moves the human; release stops movement',()=>{
  const s=fixture(),p=s.raw().P,x=p.x,y=p.y;
  s.inputEvent('joystick','pointerdown',{pointerId:7,clientX:90,clientY:55});
  advance(s);assert(p.x>x+60);assert(Math.abs(p.y-y)<1);
  s.inputEvent('joystick','pointerup',{pointerId:7});
  const stopped=p.x;advance(s,10);assert.equal(p.x,stopped);assert.equal(s.input().pointer,null);
});

test('Joystick clamps diagonal input and ignores a different pointer release',()=>{
  const s=fixture();s.inputEvent('joystick','pointerdown',{pointerId:7,clientX:90,clientY:55});
  s.inputEvent('joystick','pointermove',{pointerId:8,clientX:0,clientY:0});assert(s.input().x>0);assert.equal(s.input().y,0);
  s.inputEvent('joystick','pointermove',{pointerId:7,clientX:180,clientY:-100});
  assert(Math.abs(Math.hypot(s.input().x,s.input().y)-1)<1e-9);
  s.inputEvent('joystick','pointerup',{pointerId:8});assert.equal(s.input().pointer,7);
  s.inputEvent('joystick','pointercancel',{pointerId:7});assert.equal(s.input().x,0);assert.equal(s.input().y,0);
});

test('Blur pauses and clears held movement; a completed gesture between frames does not move',()=>{
  const s=fixture(),p=s.raw().P,x=p.x;
  s.inputEvent('joystick','pointerdown',{pointerId:7,clientX:90,clientY:55});
  s.inputEvent('joystick','pointerup',{pointerId:7});advance(s,1);assert.equal(p.x,x);
  s.inputEvent('joystick','pointerdown',{pointerId:7,clientX:90,clientY:55});
  s.inputEvent('window','blur');assert.equal(s.raw().state,'paused');assert.equal(s.input().x,0);assert.equal(s.input().pointer,null);
  advance(s);assert.equal(p.x,x);
});
