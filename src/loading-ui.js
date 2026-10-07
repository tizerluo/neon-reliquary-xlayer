/* 加载反馈独立于 WebGL：菜单局部提示、入场 / 转场遮罩和失败重试共用符文。 */
const NR_LOAD_COLORS = ['#86d8d2', '#b3dcf2', '#efad72', '#bda0ed'];
const NR_LOAD_RUNE = '<svg viewBox="0 0 120 120" aria-hidden="true"><circle class="rune-orbit" cx="60" cy="60" r="52"/><circle class="rune-inner" cx="60" cy="60" r="38"/><path class="rune-star" d="M60 24 91 78 29 78Z M60 96 29 42 91 42Z"/><path class="rune-cross" d="M60 4V13 M116 60H107 M60 116V107 M4 60H13"/><circle class="rune-heart" cx="60" cy="60" r="5"/></svg>';
class NRLoadingUI {
  constructor(app, actions) {
    this.app = app; this.actions = actions; this.menuKey = null; this.menuStart = 0; this.lastUpdate = 0;
    this.menu = document.createElement('div'); this.menu.id = 'presentationLoading'; this.menu.className = 'art-loading hidden';
    this.menu.innerHTML = '<div class="art-loading-rune">' + NR_LOAD_RUNE + '</div><div class="art-loading-copy"><strong></strong><span></span><div class="art-load-line"><i></i></div></div><button class="art-load-retry hidden"></button>';
    this.menu.setAttribute('role', 'status'); this.menu.setAttribute('aria-live', 'polite');
    this.menu.querySelector('button').onclick = () => actions.retry();
    this.battle = document.createElement('div'); this.battle.id = 'battleLoading'; this.battle.className = 'battle-loading hidden';
    this.battle.innerHTML = '<div class="battle-loading-veil"></div><div class="battle-loading-content"><small class="eyebrow"></small><div class="battle-loading-rune">' + NR_LOAD_RUNE + '</div><h2></h2><p class="battle-load-phase" role="status" aria-live="polite"></p><div class="art-load-line"><i></i></div><span class="battle-load-detail"></span><div class="battle-load-actions"><button class="art-load-retry hidden"></button><button class="art-load-continue hidden"></button><button class="art-load-back"></button></div></div>';
    this.battle.querySelector('.art-load-retry').onclick = () => actions.retry();
    this.battle.querySelector('.art-load-continue').onclick = () => actions.continue();
    this.battle.querySelector('.art-load-back').onclick = () => actions.back();
    app.append(this.menu, this.battle);
    this.wait = null; this.reduced = matchMedia('(prefers-reduced-motion: reduce)');
  }
  text(en, zh, lang) { return lang === 'zh' ? zh : en; }
  write(node, value) { if (node.textContent !== value) node.textContent = value; }
  line(panel, status) {
    const line = panel.querySelector('.art-load-line'), fill = line.firstElementChild;
    const determinate = status.phase === 'download' && status.progress != null;
    line.classList.toggle('indeterminate', !determinate && status.state === 'loading');
    fill.style.width = determinate ? Math.round(status.progress * 100) + '%' : status.state === 'loading' ? '32%' : '100%';
  }
  detail(status, lang, elapsed) {
    if (status.state === 'missing' || status.state === 'unavailable') return this.text('Your current preview is preserved. You can retry.', '已保留当前预览，可以重新尝试。', lang);
    if (elapsed > 8000) return this.text('Taking a little longer. Preparing your next view…', '载入时间较长，正在准备下一幕…', lang);
    if (status.phase === 'download' && status.total && status.progress != null) return (status.loaded / 1e6).toFixed(1) + ' / ' + (status.total / 1e6).toFixed(1) + ' MB';
    if (status.phase === 'prepare' || status.phase === 'frame') return this.text('Bringing the scene to life…', '正在点亮场景…', lang);
    return this.text('Gathering the knight and the realm…', '正在载入角色与场景…', lang);
  }
  begin(kind, stage, title) {
    this.wait = { kind, stage, title, start: performance.now() };
    this.battle.style.setProperty('--load-color', NR_LOAD_COLORS[stage] || NR_LOAD_COLORS[0]);
    this.battle.style.backgroundImage = 'url("' + NRAssets.url('ui/arena-' + ['cathedral', 'archive', 'foundry', 'throne'][stage] + '.png') + '")';
    this.battle.dataset.loadingState = 'loading'; this.battle.classList.remove('hidden');
    this.menu.classList.add('hidden');
  }
  end() { this.wait = null; this.battle.classList.add('hidden'); }
  updateBattle(status, lang, visible, title) {
    if (!this.wait) return;
    this.battle.classList.toggle('hidden', !visible);
    if (!visible) return;
    const elapsed = performance.now() - this.wait.start, failed = status.state === 'missing' || status.state === 'unavailable';
    this.battle.dataset.loadingState = failed ? 'missing' : status.state;
    this.write(this.battle.querySelector('small'), this.wait.kind === 'region' ? this.text('BEYOND THE NEXT GATE', '下一道门扉', lang) : this.text('YOUR OATH AWAITS', '誓约即将启程', lang));
    this.write(this.battle.querySelector('h2'), title || this.wait.title);
    this.write(this.battle.querySelector('.battle-load-phase'), failed ? this.text('The realm could not be fully prepared', '场景未能完整载入', lang) : status.phase === 'download' ? this.text('Opening the realm', '正在开启领域', lang) : this.text('Lighting the way', '正在点亮前路', lang));
    this.write(this.battle.querySelector('.battle-load-detail'), failed ? this.text('Retry, or continue with a compatible view. Combat is paused.', '可重试或使用兼容画面继续。战斗仍暂停。', lang) : this.detail(status, lang, elapsed));
    const retry = this.battle.querySelector('.art-load-retry'), proceed = this.battle.querySelector('.art-load-continue');
    retry.classList.toggle('hidden', !failed); proceed.classList.toggle('hidden', !failed);
    this.write(retry, this.text('RETRY', '重新载入', lang));
    this.write(proceed, this.text('CONTINUE · COMPATIBLE VIEW', '使用兼容画面继续', lang));
    this.write(this.battle.querySelector('.art-load-back'), this.text('← BACK TO SELECTION', '← 返回选角', lang));
    this.line(this.battle, status);
  }
  updateMenu(frame, info, status) {
    if (this.wait || !info || !['home', 'select', 'inspect'].includes(frame.state) || document.querySelector('.modal:not(.hidden)')) { this.menu.classList.add('hidden'); return; }
    const key = frame.state + ':' + info.key + ':' + info.stage;
    const now = performance.now();
    if (key !== this.menuKey) { this.menuKey = key; this.menuStart = now; this.lastUpdate = 0; }
    const ready = info.mode === 'live', capable = frame.options.backend !== 'canvas' && status.state !== 'unavailable';
    if (ready || !capable) { this.menu.classList.add('hidden'); return; }
    const failed = status.state === 'missing', elapsed = now - this.menuStart;
    if (!failed && elapsed < 150) { this.menu.classList.add('hidden'); return; }
    this.menu.classList.remove('hidden'); this.menu.dataset.loadingState = failed ? 'missing' : 'loading';
    this.menu.dataset.view = frame.state;
    this.menu.style.setProperty('--load-color', NR_LOAD_COLORS[info.stage]);
    const selector = frame.state === 'home' ? '.home-model-stage' : frame.state === 'inspect' ? '.inspect-reticle' : '.hero-stage';
    const base = this.app.getBoundingClientRect(), rect = document.querySelector(selector)?.getBoundingClientRect();
    let x = frame.state === 'home' ? .76 : frame.state === 'inspect' ? .31 : .26, y = frame.state === 'home' ? .71 : frame.state === 'select' ? .59 : .74;
    if (base.width < base.height && rect?.width) { x = (rect.left + rect.width / 2 - base.left) / base.width; y = (rect.bottom - base.top - (frame.state === 'select' ? 72 : 20)) / base.height; }
    this.menu.style.left = x * 100 + '%'; this.menu.style.top = y * 100 + '%';
    if (now - this.lastUpdate < 200 && this.lastLanguage === frame.language && this.lastState === status.state) return;
    this.lastUpdate = now; this.lastLanguage = frame.language; this.lastState = status.state;
    this.write(this.menu.querySelector('strong'), failed ? this.text('3D preview unavailable', '三维预览暂不可用', frame.language) : this.text('Revealing the sovereign', '正在呈现君王', frame.language));
    if (!failed && frame.state !== 'inspect') this.write(this.menu.querySelector('strong'), this.text('Revealing your knight', '正在呈现角色', frame.language));
    this.write(this.menu.querySelector('span'), this.detail(status, frame.language, elapsed));
    const retry = this.menu.querySelector('button'); retry.classList.toggle('hidden', !failed);
    this.write(retry, this.text('RETRY', '重试', frame.language)); this.line(this.menu, status);
  }
}
