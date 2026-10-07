"""Desktop/touch UI regression and actual WebGL2 screenshots; no external LLM called."""
import json,os,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'previews'; OUT.mkdir(exist_ok=True)
html=(ROOT/'Neon_Reliquary_v3.html').read_text().replace("if(!new URLSearchParams(location.search).has('test'))return;",'')
html=html.replace('<body>','<body><script>window.requestAnimationFrame=()=>1;window.__NR_MANUAL_TEST=true;</script>')
checks=[]
x=subprocess.Popen(['Xvfb',':100','-screen','0','1600x1000x24'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=False,env={'DISPLAY':':100'},args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
  p=b.new_page(viewport={'width':1440,'height':810});p.set_default_timeout(6000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(html);p.wait_for_function('!!window.__NR')
  def shot(name):
   p.evaluate('__NR.render()');p.screenshot(path=str(OUT/(name+'.png')))
  shot('home');p.click('#enterBtn');shot('selection');p.click('#partyOpen');p.click('#partyTry');shot('party')
  assert p.locator('.party-row select').nth(0).input_value()=='bot'; checks.append({'test':'Desktop party button, fill local bots and dismissal panel','passed':True})
  p.click('#partyDone');p.click('#startBtn');p.evaluate('__NR.advance(4)');shot('battle')
  a=p.evaluate('NRCoop.call("nr_observe")');assert len(a['units'])==4
  # 玩家键盘与三位队友可同时工作。
  p.evaluate('__NR.coop.clear()');prev=p.evaluate('__NR.snapshot().position');p.keyboard.down('d');p.evaluate('__NR.advance(.35)');p.keyboard.up('d');curr=p.evaluate('__NR.snapshot().position');assert curr['x']>prev['x']
  checks.append({'test':'Human keyboard movement while three companions remain active','passed':True})
  p.click('#partyHudOpen');assert p.evaluate('__NR.snapshot().state')=='paused';p.click('#partyClose');assert p.evaluate('__NR.snapshot().state')=='paused';p.click('#resumeBtn');assert p.evaluate('__NR.snapshot().state')=='play'
  checks.append({'test':'Party modal pauses and requires explicit human resume','passed':True})
  p.evaluate('__NR.spawnBoss(1);__NR.saturate(150);__NR.advance(.35)');shot('battle')
  p.evaluate('__NR.home()');p.click('#codexBtn');p.locator('[data-boss="0"]').click();shot('boss1')
  for i in range(1,8):
   p.click('#inspectNext');shot('boss'+str(i+1))
  p.locator('#inspectRotation').fill('125');p.locator('#inspectRotation').dispatch_event('input');assert p.evaluate('document.querySelector("#inspectAuto").textContent').endswith('OFF')
  p.click('#inspectClose');assert p.locator('#codexModal').is_visible();p.click('#codexClose')
  checks.append({'test':'All eight native boss models via real archive UI, rotation and return','passed':True})
  (ROOT/'tool_schemas.json').write_text(json.dumps(p.evaluate('NRCoop.listTools()'),ensure_ascii=False,indent=2))
  # 横屏手机：触摸点击、滚动、中文热切换和摇杆。
  c=b.new_context(viewport={'width':844,'height':390},device_scale_factor=1,is_mobile=True,has_touch=True)
  m=c.new_page();m.set_default_timeout(6000);m.on('pageerror',lambda e:errors.append(str(e)));m.set_content(html);m.wait_for_function('!!window.__NR');m.tap('#enterBtn');m.evaluate('__NR.render()');m.screenshot(path=str(OUT/'mobile_selection.png'));m.tap('#partyOpen');m.tap('#partyTry');m.evaluate('__NR.lang("zh");__NR.render()');m.screenshot(path=str(OUT/'mobile_party.png'))
  bound=m.locator('.party-card').evaluate('(e)=>({width:e.clientWidth,scroll:e.scrollWidth,height:e.clientHeight,content:e.scrollHeight})');assert bound['scroll']<=bound['width']+2;assert '誓约' in m.locator('.party-card').inner_text();m.tap('#partyDone');m.tap('#startBtn');m.evaluate('__NR.advance(2)');assert len(m.evaluate('NRCoop.call("nr_observe")')['units'])==4
  rect=m.locator('#joystick').bounding_box();assert rect;cx=rect['x']+rect['width']*.5;cy=rect['y']+rect['height']*.5
  # dispatch pointer events checks same touch handlers; not a physical device measurement.
  pos=m.evaluate('__NR.snapshot().position');m.locator('#joystick').dispatch_event('pointerdown',{'pointerId':1,'clientX':cx,'clientY':cy,'pointerType':'touch'});m.locator('#joystick').dispatch_event('pointermove',{'pointerId':1,'clientX':cx+28,'clientY':cy,'pointerType':'touch'});m.evaluate('__NR.advance(.25)');m.locator('#joystick').dispatch_event('pointerup',{'pointerId':1,'clientX':cx+28,'clientY':cy,'pointerType':'touch'});newpos=m.evaluate('__NR.snapshot().position');assert newpos['x']>pos['x'];m.evaluate('__NR.render()');m.screenshot(path=str(OUT/'mobile_battle.png'))
  checks.append({'test':'844x390 touch simulation: bilingual party panel, scroll, four units and joystick','passed':True,'details':bound})
  assert not errors;checks.append({'test':'No desktop/touch uncaught JavaScript errors','passed':True})
  (ROOT/'tests/ui_results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(json.dumps(checks,ensure_ascii=False,indent=2),flush=True);b.close()
finally:x.terminate()
