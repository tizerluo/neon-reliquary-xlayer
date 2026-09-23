'use strict';
(() => {
    const $ = id => document.getElementById(id), TAU = Math.PI * 2, W = 1280, H = 720;
    const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), rand = (a, b) => a + Math.random() * (b - a), ri = (a, b) => Math.floor(rand(a, b + 1)), dist2 = (x, y) => x * x + y * y;
    const rgba = (hex, a) => { let s = hex.slice(1); return `rgba(${parseInt(s.slice(0, 2), 16)},${parseInt(s.slice(2, 4), 16)},${parseInt(s.slice(4, 6), 16)},${a})`; };
    const HEROES = [
        { name: '晓斌', tag: '天枢剑主 · 攻守兼备', color: '#8cdcff', quote: '一剑开天，万剑归心。', desc: '以银蓝天枢剑织成双重剑流。精准追击与稳固剑阵，让他能从正面撕开妖潮。', weapon: '天枢流光', weaponDesc: '双螺旋御剑，飞剑出阵后追击敌人。', skill: '天枢破阵', skillDesc: '向瞄准方向劈开扇形缺口，击退并获得护盾。', ult: '万剑归宗', ultDesc: '巨剑沿指定方向连续落下，凿开一条突围通道。', symbol: '阵', hp: 120, speed: 235, damage: 23, count: 12, interval: .29, shotSpeed: 600, orbit: .46, turn: 4.8, skillMax: 7, passive: '剑阵护体' },
        { name: '阿喵', tag: '金焰刀客 · 重剑破阵', color: '#ffbf60', quote: '本喵出手，寸草不留。', desc: '宽刃重剑沿弧线斩入敌阵，再回旋收割。攻速稍慢，但每一剑都足够沉重。', weapon: '金焰重阙', weaponDesc: '宽刃穿透，回旋剑势能再次切入妖潮。', skill: '裂地重斩', skillDesc: '狭长重斩破甲推开敌阵，留下灼烧通道。', ult: '赤阳开天', ultDesc: '向前连续开山重斩，金焰集中撕开阵线。', symbol: '斩', hp: 148, speed: 214, damage: 45, count: 7, interval: .38, shotSpeed: 430, orbit: .26, turn: 2.5, skillMax: 6, passive: '重剑破甲' },
        { name: '旺财', tag: '奔雷剑卫 · 雷链突进', color: '#8bbaff', quote: '你守住方向，我守住你。', desc: '雷剑高速贯穿敌群，命中时向邻近妖兵传导闪电。灵活而有韧性的护卫。', weapon: '逐电雷牙', weaponDesc: '高速雷剑，命中后概率连锁闪电。', skill: '奔雷裂隙', skillDesc: '雷剑沿直线贯穿并短暂麻痹，获得护盾。', ult: '天狼逐电', ultDesc: '在前方扇面连续落雷，而不是全屏清场。', symbol: '雷', hp: 132, speed: 255, damage: 20, count: 13, interval: .26, shotSpeed: 720, orbit: .33, turn: 4.4, skillMax: 8, passive: '雷链连击' },
        { name: '吱吱', tag: '千机剑匠 · 极密剑雨', color: '#cfadff', quote: '别看我小，剑可不少。', desc: '轻巧剑针高速成群飞出，织成密集的紫色旋流。靠机动与数量持续压制。', weapon: '千机飞星', weaponDesc: '小型飞剑数量最多，双向旋流追击。', skill: '千机星爆', skillDesc: '沿瞄准方向排布四枚星爆，逐段炸开通道。', ult: '千机暴雨', ultDesc: '密集剑针向指定方向集中喷涌，持续凿穿敌阵。', symbol: '机', hp: 94, speed: 266, damage: 13, count: 19, interval: .22, shotSpeed: 700, orbit: .37, turn: 5.8, skillMax: 6, passive: '御剑疾行' },
        { name: '柳如烟', tag: '花影剑仙 · 花雨续战', color: '#f6a7d7', quote: '花开时，剑已穿过烟雨。', desc: '花瓣般的粉色剑气绕身流转，分散后向敌人汇聚。回春与花影让她能持久作战。', weapon: '烟雨花影', weaponDesc: '花瓣剑流，命中时少量恢复生命。', skill: '莲心回春', skillDesc: '向前推出花刃，挤开敌阵并恢复少量生命。', ult: '花开万剑', ultDesc: '莲华沿前方路径逐层绽放，边突围边续战。', symbol: '花', hp: 108, speed: 233, damage: 19, count: 14, interval: .28, shotSpeed: 520, orbit: .64, turn: 5.2, skillMax: 9, passive: '花影汲取' },
        { name: '小蓝', tag: '寒魄灵狐 · 冰封控场', color: '#82ecf8', quote: '冰封千里，只留一线生机。', desc: '冰晶剑锋在妖兵间穿梭，持续减缓追击。控场稳固，善于瓦解高速冲锋。', weapon: '霜华冰魄', weaponDesc: '冰晶飞剑附带减速与额外穿透。', skill: '冰封领域', skillDesc: '冻结前方扇面；踏风可穿过失衡或冻结的妖兵。', ult: '绝对零度', ultDesc: '冰晶暴雨持续压制前方，冻结并撕开逃生口。', symbol: '霜', hp: 112, speed: 242, damage: 24, count: 11, interval: .30, shotSpeed: 570, orbit: .50, turn: 4.8, skillMax: 8, passive: '冰魄迟滞' }
    ];
    const BOSSES = [
        { name: '赤焰魔尊', sub: '焚天之怒', color: '#ff8969', desc: '裂地重击、冲锋与火刃扇阵。狂暴后连发。' },
        { name: '玄冰骨龙', sub: '寒渊之主', color: '#91e6ff', desc: '冰陨追踪、螺旋冰弹与冰封环。' },
        { name: '啸岳妖王', sub: '万兽之王', color: '#efcf8c', desc: '三连扑击与近身震波，必须及时闪避。' },
        { name: '九幽尸将', sub: '不灭之军', color: '#c5a1f4', desc: '召唤亡灵军阵，释放环形魂弹。' },
        { name: '天机巨神', sub: '古代兵器', color: '#f4c76c', desc: '交叉光束、锁定轰击与旋转弹幕。' },
        { name: '万魂神坛', sub: '幽冥祭祀', color: '#eba1f6', desc: '多重魂井、灵体增援与远程魂雨。' },
        { name: '碧厄三首', sub: '瘴海龙王', color: '#8ceab9', desc: '三头喷毒、毒池封路与密集扇射。' },
        { name: '烬天凰皇', sub: '终焉之翼', color: '#ffad8c', desc: '飞羽旋雨、连续火陨与终焉冲击。' }
    ];
    const DIFFS = [
        {name:'入门',hp:.70,dmg:.60,speed:.86,initial:125,target:270,spawn:.83,note:'熟悉破阵：小股合围，有较长的脱身窗口。'},
        {name:'江湖',hp:1,dmg:1,speed:1,initial:225,target:450,spawn:1,note:'标准突围：妖兵成层推进，先打薄一侧，再踏风冲出。'},
        {name:'炼狱',hp:1.28,dmg:1.55,speed:1.15,initial:300,target:610,spawn:1.28,note:'妖将压阵、侧翼截路；单靠站桩御剑难以活下来。'},
        {name:'修罗',hp:1.65,dmg:2.20,speed:1.29,initial:380,target:780,spawn:1.55,note:'近身包围更早形成，护甲更厚；破阵技与闪避缺一不可。'}
    ];
    const STAGES = [{ name: '青岚古庭', sub: '雨过山门，妖影初现', color: '#85c9ba', rune: '#adc594' }, { name: '寒渊雪境', sub: '风雪封关，万骨争鸣', color: '#abcbe4', rune: '#b6dceb' }, { name: '赤烬废城', sub: '烽火照夜，群魔压境', color: '#d08f76', rune: '#e3b277' }, { name: '冥月天阙', sub: '八王齐现，剑定人间', color: '#bf9ccf', rune: '#c9b7df' }];
    const MOB_HP = [180, 135, 450, 155, 215, 310, 210, 560], MOB_SPEED = [90, 132, 64, 125, 78, 75, 76, 70], MOB_RADIUS = [14, 16, 19, 15, 18, 17, 16, 22];
    let storageOK = true;
    let saved = { best: 0, totalKills: 0, runs: 0, wins: 0, bosses: [], settings: { music: .32, sfx: .55, quality: 'auto', shake: true, numbers: true }, hero: 0, diff: 1 };
    try {
        const s = JSON.parse(localStorage.getItem('neon-reliquary.v3') || localStorage.getItem('neon-reliquary.v2') || 'null');
        if (s) {
            saved = { ...saved, ...s, settings: { ...saved.settings, ...s.settings } };
        }
    }
    catch (_) {
        storageOK = false;
    }
    function save() { try {
        localStorage.setItem('neon-reliquary.v3', JSON.stringify(saved));
        storageOK = true;
    }
    catch (_) {
        storageOK = false;
        $('saveState').textContent = tx('private');
    } }
    if(saved.perfVersion!=='1.1'){saved.settings.quality='auto';saved.settings.backend='auto';saved.perfVersion='1.1';}
    let selected = clamp(saved.hero | 0, 0, 5), difficulty = clamp(saved.diff | 0, 0, 3), mode = 'campaign', state = 'loading', hero = HEROES[selected], options = saved.settings;
    let canvas = $('game'); const mini = $('minimap').getContext('2d', { alpha: true });
    const images = {}, whiteSprites = {}, swordSprites = [], glows = [], atlasRects = {};
    let actorAtlas = null, whiteAtlas = null, shadowSprite = null;
    let patterns = [], runeSprites = [], props = [], propImages = [], bgVignette;
    let ready = false, renderScale = 1, qualityFactor = 1, lowFrameTime = 0, fps = 60, uiClock = 0, miniClock = 0, frameNo = 0;
    const camera = { x: 0, y: 0 }, pointer = { x: 640, y: 360, held: false, inside: false }, keys = new Set();
    let joy = { x: 0, y: 0 }, joyPointer = null;
    let run = null, P = null, announcementTime = 0, toastTime = 0, shake = 0, flash = 0, phaseFlash = 0;
    function show(id) { $(id).classList.remove('hidden'); }
    function hide(id) { $(id).classList.add('hidden'); }
    function toast(text, duration = 2) { $('toast').textContent = trLegacy(text); show('toast'); toastTime = duration; }
    function announce(top, title, desc, duration = 2.6) { $('announcementTop').textContent = trLegacy(top); $('announcementTitle').textContent = trLegacy(title); $('announcementDesc').textContent = trLegacy(desc); hide('announcement'); void $('announcement').offsetWidth; show('announcement'); announcementTime = duration; }
    function setAccent() { hero = HEROES[selected]; document.documentElement.style.setProperty('--accent', hero.color); document.documentElement.style.setProperty('--aura', rgba(hero.color, .18)); }
    const audio = new NRAudio(options);
    function createCanvas(w, h) { let c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
    function mulberry(a) { return function(){let t=a+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return ((t^t>>>14)>>>0)/4294967296;};}
    function makePool(max, floatFields, intFields = []) { const p = { max, count: 0, free: [], a: new Uint8Array(max) }; for (let i = max - 1; i >= 0; i--)
        p.free.push(i); for (const n of floatFields)
        p[n] = new Float32Array(max); for (const n of intFields)
        p[n] = new Int32Array(max); p.alloc = () => { if (!p.free.length)
        return -1; const i = p.free.pop(); p.a[i] = 1; p.count++; return i; }; p.release = i => { if (p.a[i]) {
        p.a[i] = 0;
        p.free.push(i);
        p.count--;
    } }; p.clear = () => { p.a.fill(0); p.free.length = 0; for (let i = max - 1; i >= 0; i--)
        p.free.push(i); p.count = 0; }; return p; }
    const E = makePool(1450, ['x', 'y', 'hp', 'maxhp', 'speed', 'radius', 'age', 'timer', 'hit', 'slow', 'freeze', 'kx', 'ky', 'charge', 'dx', 'dy', 'cool', 'stagger', 'born'], ['type', 'tier', 'phase', 'gen']);
    const B = makePool(2600, ['x', 'y', 'px', 'py', 'vx', 'vy', 'angle', 'age', 'life', 'damage', 'speed', 'orbit', 'turn', 'seed', 'tx1', 'ty1', 'tx2', 'ty2', 'tx3', 'ty3', 'tx4', 'ty4', 'trailClock'], ['target', 'targetGen', 'pierce', 'lastHit', 'flags','owner','hero']);
    const F = makePool(420, ['x', 'y', 'vx', 'vy', 'life', 'age', 'size'], ['color', 'kind']);
    const O = makePool(700, ['x', 'y', 'value', 'age'], ['kind']);
    const HB = makePool(950, ['x', 'y', 'vx', 'vy', 'life', 'radius', 'damage', 'age', 'turn'], ['kind']);
    const hashHead = new Int32Array(64 * 64), hashNext = new Int32Array(E.max);
    const CELL = 96, HALF = 3072;
    const rings = [], lines = [], warnings = [], numbers = [], traces = [], zones = [];
    let renderEnemies = [], targetScratch = [];
    function buildHash() { hashHead.fill(-1); for (let i = 0; i < E.max; i++) {
        if (!E.a[i])
            continue;
        const gx = clamp(Math.floor((E.x[i] + HALF) / CELL), 0, 63), gy = clamp(Math.floor((E.y[i] + HALF) / CELL), 0, 63), k = gx + gy * 64;
        hashNext[i] = hashHead[k];
        hashHead[k] = i;
    } }
    function queryCircle(x, y, r, callback) { const minx = clamp(Math.floor((x - r + HALF) / CELL), 0, 63), maxx = clamp(Math.floor((x + r + HALF) / CELL), 0, 63), miny = clamp(Math.floor((y - r + HALF) / CELL), 0, 63), maxy = clamp(Math.floor((y + r + HALF) / CELL), 0, 63); for (let cy = miny; cy <= maxy; cy++)
        for (let cx = minx; cx <= maxx; cx++) {
            let i = hashHead[cx + cy * 64], guard = 0;
            while (i !== -1 && guard++ < E.max) {
                const next = hashNext[i];
                if (E.a[i] && dist2(E.x[i] - x, E.y[i] - y) < (r + E.radius[i]) ** 2)
                    callback(i);
                i = next;
            }
        } }
    function nearest(x, y, range = 900) { let best = -1, d = range * range; for (let i = 0; i < E.max; i++) {
        if (!E.a[i])
            continue;
        let q = dist2(E.x[i] - x, E.y[i] - y);
        if (E.tier[i] === 2)
            q *= .7;
        if (q < d) {
            d = q;
            best = i;
        }
    } return best; }
    function particle(x, y, vx, vy, life, size, color = selected, kind = 0) { let i = F.alloc(); if (i < 0)
        return; F.x[i] = x; F.y[i] = y; F.vx[i] = vx; F.vy[i] = vy; F.life[i] = life; F.age[i] = 0; F.size[i] = size; F.color[i] = color; F.kind[i] = kind; }
    function burst(x, y, count = 8, color = selected, scale = 1) { count = Math.round(count * (options.quality === 'low' ? .45 : qualityFactor)); for (let j = 0; j < count; j++) {
        let a = rand(0, TAU), s = rand(30, 150) * scale;
        particle(x, y, Math.cos(a) * s, Math.sin(a) * s, rand(.18, .48), rand(1.5, 4), color, j % 4 === 0 ? 1 : 0);
    } }
    function ring(x, y, r, color = hero.color, life = .6, type = 0) { if (rings.length >= 36)
        rings.shift(); rings.push({ x, y, r, color, life, age: 0, type }); }
    function line(x1, y1, x2, y2, color = hero.color, width = 2, life = .18, kind = 0) { if (lines.length >= 56)
        lines.shift(); lines.push({ x1, y1, x2, y2, color, width, life, age: 0, kind, seed: Math.random() * 100 }); }
    function number(x, y, text, color = '#dfebf1', large = false) { if (!options.numbers || !visible(x,y,80) || numbers.length >= 18)
        return; numbers.push({ x: x + rand(-8, 8), y: y - 20, text: String(text), color, large, age: 0, life: large ? .9 : .65 }); }
    function spawnOrb(x, y, value, kind = 0) { let i = O.alloc(); if (i < 0) {
        if (kind === 0 && P)
            P.xp += value;
        return;
    } O.x[i] = x + rand(-12, 12); O.y[i] = y + rand(-10, 10); O.value[i] = value; O.kind[i] = kind; O.age[i] = 0; }
    function spawnEnemy(type = 0, tier = 0, x = null, y = null) {
        if(tier!==2 && E.count>=E.max-8)return -1;
        let i = E.alloc();
        if (i < 0)
            return -1;
        const d = DIFFS[difficulty];
        if (x === null) {
            const a = rand(0, TAU), r = rand(.9, 1.13);
            x = P.x + Math.cos(a) * 640 * r;
            y = P.y + Math.sin(a) * 385 * r;
        }
        E.x[i] = clamp(x, -1650, 1650);
        E.y[i] = clamp(y, -1480, 1480);
        PREV.E.x[i]=E.x[i]; PREV.E.y[i]=E.y[i];
        E.type[i] = type;
        E.tier[i] = tier;
        E.age[i] = rand(0, 3);
        E.timer[i] = rand(1, 3);
        E.hit[i] = 0; E.stagger[i]=0; E.born[i]=run.time;
        E.slow[i] = 0;
        E.freeze[i] = 0;
        E.kx[i] = E.ky[i] = 0;
        E.charge[i] = 0;
        E.cool[i] = 0;
        E.phase[i] = 0;
        E.gen[i]++;
        let scale = (1 + (run.wave - 1) * .11) * d.hp;
        if (tier === 2) {
            E.maxhp[i] = (14500 + type * 7800) * (1 + P.level * .035) * (mode === 'bossrush' ? 1.12 : 1) * d.hp * (mode === 'endless' ? 1 + Math.floor((run.wave - 1) / 16) * .5 : 1);
            E.radius[i] = type === 4 ? 67 : 58;
            E.speed[i] = (type === 2 ? 54 : 33) * d.speed;
            E.timer[i] = 2;
            run.bossId = i;
            run.bossBorn = run.time;
            audio.music('music_boss');
            audio.sfx('boss');
            show('bossHud');
            $('bossTitle').textContent = BOSSES[type].name;
            $('bossPhase').textContent = tx('phase1') + ' · ' + BOSSES[type].sub;
            announce('妖王降临 · ' + BOSSES[type].sub, BOSSES[type].name, '躲开红色预警，寻找反击空隙', 2.7);
            ring(x, y, 180, BOSSES[type].color, 1.5, 3);
            shake = 5;
        }
        else if (tier === 1) {
            E.maxhp[i] = (1100 + type * 135) * scale;
            E.radius[i] = 28;
            E.speed[i] = (60 + type * 5) * d.speed;
            E.timer[i] = rand(2.2, 4);
        }
        else {
            E.maxhp[i] = MOB_HP[type] * scale;
            E.radius[i] = MOB_RADIUS[type];
            E.speed[i] = (MOB_SPEED[type] + run.wave * 1.3) * d.speed;
        }
        E.maxhp[i]*=tier===2?(run.scaling?.bossHP||1):(run.scaling?.mobHP||1);
        if(run.expedition&&tier===2)E.maxhp[i]*=2.6;
        E.hp[i] = E.maxhp[i];
        return i;
    }
    function spawnPack(count, initial = false) {
      // Advance as four offset fronts, not an isolated random target every frame.
      if(!run.fronts)run.fronts={angle:rand(0,TAU),serial:0};
      for(let j=0;j<count;j++){
        const id=run.fronts.serial++,wing=Math.floor(id/12)%4;
        const a=run.fronts.angle+wing*Math.PI/2+rand(-.34,.34);
        const rad=initial?rand(.83,1.24):rand(1.03,1.21);
        const forward=P.moving?Math.min(90,(run.wave+2)*9):0;
        const x=P.x+Math.cos(a)*625*rad+Math.cos(P.moveAim||0)*forward;
        const y=P.y+Math.sin(a)*375*rad+Math.sin(P.moveAim||0)*forward;
        const heavy=id%11===0,type=heavy?(id%22===0?7:2):Math.random()<.40?0:ri(0,Math.min(7,3+run.wave));
        const tier=!initial&&id%(Math.max(15,31-run.wave))===0?1:0;
        spawnEnemy(tier?id%6:type,tier,x,y);
      }
    }
    function playerHurt(amount,x,y){hurtActor(P,amount,x,y);}

    function damageEnemy(i, amount, kick = 0, critical = true, actor = P) {
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
        if (!E.a[i] || run.ended)
            return;
        let crit = critical && Math.random() < P.crit;
        let dmg = amount * (crit ? 1.75 : 1);
        if(run.expedition&&E.tier[i]===2)dmg*=run.expedition.bossWindow?1.6:.70;
        if (E.tier[i] === 0 && E.type[i] === 2 && selected !== 1)
            dmg *= .78;
        E.hp[i] -= dmg;
        run.damageDealt += dmg; P.damageDealt=(P.damageDealt||0)+dmg;
        if (E.hit[i] <= 0) {
            E.hit[i] = .10;
            if (E.tier[i] > 0 || Math.random() < .1)
                number(E.x[i], E.y[i], Math.ceil(dmg), crit ? '#fbd184' : '#dee6df', crit);
            if (Math.random() < .13)
                burst(E.x[i], E.y[i], 3);
            audio.sfx((E.type[i]===2||E.type[i]===7||E.tier[i]>0)?'armor':'hit',clamp((E.x[i]-P.x)/430,-.8,.8));
        }
        if(kick>180){E.stagger[i]=E.tier[i]===2?.07:.40;run.heavyHits++;}
        if (kick) {
            let dx = E.x[i] - P.x, dy = E.y[i] - P.y, d = Math.hypot(dx, dy) || 1;
            E.kx[i] += dx / d * kick * (E.tier[i] === 2 ? .2 : 1);
            E.ky[i] += dy / d * kick * (E.tier[i] === 2 ? .2 : 1);
        }
        if (selected === 5)
            E.slow[i] = 1.35;
        if (selected === 4 && !P.downed && Math.random() < .08)
            P.hp = Math.min(P.maxhp, P.hp + .16);
        if (E.hp[i] <= 0)
            killEnemy(i,actor);
    }
    function killEnemy(i, actor=P) {
        if (!E.a[i])
            return;
        let tier = E.tier[i], type = E.type[i], x = E.x[i], y = E.y[i];
        E.release(i);
        run.kills++; run.lifetimeSum+=run.time-E.born[i];
        run.combo++;
        run.comboClock = 3.2;
        run.maxCombo = Math.max(run.maxCombo, run.combo);
        for(const unit of partyActors()) unit.ult=Math.min(100,unit.ult+(tier===2?35:(tier===1?3:.5)*(unit.ultTime>0?.18:1)));
        run.coins += tier === 2 ? 160 : tier === 1 ? 14 : 1;
        actor.kills++;
        burst(x, y, tier === 2 ? 72 : tier === 1 ? 18 : 5, selected, tier === 2 ? 2.6 : 1);
        if (tier > 0 || run.kills % 4 === 0)
            ring(x, y, tier === 2 ? 230 : tier === 1 ? 60 : 20, hero.color, tier === 2 ? 1.2 : .3);
        spawnOrb(x, y, tier === 2 ? 90 : tier === 1 ? 16 : 3.5, 0);
        if (Math.random() < .028 || tier === 2)
            spawnOrb(x + 16, y, 12, 1);
        if (Math.random() < .009 || tier === 2)
            spawnOrb(x - 13, y, 1, 2);
        if (tier === 2) {
            run.bosses++; coopBossClear(type);
            run.bossId = -1;
            hide('bossHud');
            audio.sfx('level');
            audio.music('music_battle');
            P.hp = Math.min(P.maxhp, P.hp + P.maxhp * .2);
            P.shield = Math.min(P.maxhp * .65, P.shield + 20);
            saved.bosses = Array.from(new Set([...saved.bosses, type]));
            save();
            announce('妖王已斩 · 剑意更盛', BOSSES[type].name + ' · 陨落', '生命回复 · 获得剑匣 · 无双蓄能', 2);
            if (mode === 'bossrush') {
                run.bossNextAt = run.time + 3.5;
                if (run.bosses >= 8)
                    finish(true);
            }
            else if (mode === 'campaign' && run.wave >= 16)
                finish(true);
        }
        else if (run.kills % 5 === 0)
            audio.sfx('kill');
    }
    function areaDamage(x, y, r, amount, kick = 50, freeze = 0, actor=P) {
        const P=actor,selected=P.heroId??0,hero=HEROES[selected]; queryCircle(x, y, r, i => { damageEnemy(i, amount, kick,true,actor); if (E.a[i] && freeze)
        E.freeze[i] = E.tier[i] === 2 ? Math.min(freeze, .4) : freeze; }); }
    function shootSword(x, y, angle, target, damage = P.damage, flags = 0, life = 2.25, orbit = -1, actor=P) {
        const P=actor,selected=P.heroId??0,hero=HEROES[selected]; let i = B.alloc(); if (i < 0)
        return -1; B.x[i] = B.px[i] = B.tx1[i] = B.tx2[i] = B.tx3[i] = B.tx4[i] = x; B.y[i] = B.py[i] = B.ty1[i] = B.ty2[i] = B.ty3[i] = B.ty4[i] = y; PREV.B.x[i]=x;PREV.B.y[i]=y;B.age[i] = 0; B.life[i] = life; B.angle[i] = angle; B.seed[i] = rand(-1, 1); B.speed[i] = hero.shotSpeed * (flags ? 1.1 : 1); B.vx[i] = Math.cos(angle) * B.speed[i]; B.vy[i] = Math.sin(angle) * B.speed[i]; B.damage[i] = damage; B.orbit[i] = orbit >= 0 ? orbit : hero.orbit; B.turn[i] = hero.turn; B.target[i] = target; B.targetGen[i] = target >= 0 ? E.gen[target] : 0; B.pierce[i] = P.pierce + (selected === 1 || selected === 5 ? 2 : 1) + (flags ? 1 : 0); B.lastHit[i] = -1; B.flags[i] = flags; B.owner[i]=P.uid; B.hero[i]=selected; B.trailClock[i] = 0; return i; }
    function salvo(extra = 0, actor=P) {
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
        P.attackAnim=.16; let target = (P.uid||P.controller==='external')?coopCombatTarget(P):nearest(P.x, P.y, 1000), n = P.swords + extra;
        let aim = (P.uid===0&&P.controller!=='external'&&pointer.held) ? Math.atan2(pointer.y - H / 2 + camera.y - P.y, pointer.x - W / 2 + camera.x - P.x) : target >= 0 ? Math.atan2(E.y[target] - P.y, E.x[target] - P.x) : run.time * .5;
        if ((P.uid===0&&P.controller!=='external'&&pointer.held))
            target = -1;
        P.aim = aim;
        for (let j = 0; j < n; j++) {
            const a = run.time * (selected === 4 ? 1.6 : selected === 3 ? -3 : 2) + j * TAU / n;
            const i = shootSword(P.x + Math.cos(a) * 42, P.y + Math.sin(a) * 29, a, target, P.damage*.61,0,2.25,-1,actor);
            if (i >= 0) {
                B.seed[i] = j % 2 ? 1 : -1;
                B.angle[i] = a;
                B.vx[i] = Math.cos(aim + (j - (n - 1) / 2) * .035) * B.speed[i];
                B.vy[i] = Math.sin(aim + (j - (n - 1) / 2) * .035) * B.speed[i];
            }
        }
        audio.sfx('shot');
    }
    function enemyBullet(x, y, angle, speed = 170, damage = 10, r = 5, kind = 0, turn = 0) { const i = HB.alloc(); if (i < 0)
        return; HB.x[i] = x; HB.y[i] = y;PREV.HB.x[i]=x;PREV.HB.y[i]=y; HB.vx[i] = Math.cos(angle) * speed; HB.vy[i] = Math.sin(angle) * speed; HB.radius[i] = r; HB.life[i] = 6; HB.age[i] = 0; HB.damage[i] = damage; HB.kind[i] = kind; HB.turn[i] = turn; }
    function warnCircle(x, y, r, delay = .9, damage = 18, color = '#fa837d', zone = false) { if (warnings.length >= 80)
        return; warnings.push({ type: 0, x, y, r, delay, age: 0, damage, color, zone }); }
    function warnLine(x, y, angle, len = 900, width = 42, delay = 1, damage = 20, color = '#ffae79') { if (warnings.length >= 80)
        return; warnings.push({ type: 1, x, y, angle, len, width, delay, age: 0, damage, color }); }
    function dash() { if (state !== 'play' || P.downed || P.dashCD > 0)
        return; let x = (keys.has('d') || keys.has('arrowright') ? 1 : 0) - (keys.has('a') || keys.has('arrowleft') ? 1 : 0) + joy.x, y = (keys.has('s') || keys.has('arrowdown') ? 1 : 0) - (keys.has('w') || keys.has('arrowup') ? 1 : 0) + joy.y; let l = Math.hypot(x, y); if (l < .15) {
        x = pointer.x - W / 2 + camera.x - P.x;
        y = pointer.y - H / 2 + camera.y - P.y;
        l = Math.hypot(x, y) || 1;
    } if (Math.hypot(x, y) < .1) {
        x = Math.cos(P.aim);
        y = Math.sin(P.aim);
        l = 1;
    } P.dashX = x / l; P.dashY = y / l; P.dashTime = .24; P.dashCD = P.dashMax; P.inv = .29; P.magnet = 2.5; ring(P.x, P.y, 80, hero.color, .35); audio.sfx('dash'); P.dashPierced=0; }
    function skillAim(actor=P){return (actor.uid||actor.controller==='external')?actor.aim:(pointer.held?Math.atan2(pointer.y-H/2+camera.y-actor.y,pointer.x-W/2+camera.x-actor.x):(actor.moving?actor.moveAim:actor.aim));}

    function arcDamage(a,range,half,damage,kick=400,freeze=0,actor=P){
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      let hits=0;const co=Math.cos(a),si=Math.sin(a),threshold=Math.cos(half);
      queryCircle(P.x,P.y,range,i=>{const dx=E.x[i]-P.x,dy=E.y[i]-P.y,d=Math.hypot(dx,dy)||1;
        if(d<48||(dx*co+dy*si)/d>=threshold){damageEnemy(i,damage,kick,true,actor);if(E.a[i]&&freeze)E.freeze[i]=E.tier[i]===2?Math.min(.35,freeze):freeze;hits++;}
      });return hits;
    }
    function laneDamage(a,length,width,damage,kick=400,freeze=0,actor=P){
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      const co=Math.cos(a),si=Math.sin(a);let hits=0;
      queryCircle(P.x,P.y,length,i=>{const dx=E.x[i]-P.x,dy=E.y[i]-P.y,t=dx*co+dy*si,perp=Math.abs(-dx*si+dy*co);
        if(t>-25&&t<length&&perp<width+E.radius[i]){damageEnemy(i,damage,kick,true,actor);if(E.a[i]&&freeze)E.freeze[i]=E.tier[i]===2?.22:freeze;hits++;}
      });return hits;
    }
    function attackArcFX(a,range,half,actor=P){
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      let ax=P.x+Math.cos(a-half)*range,ay=P.y+Math.sin(a-half)*range;
      for(let j=1;j<=9;j++){let t=a-half+half*2*j/9,x=P.x+Math.cos(t)*range,y=P.y+Math.sin(t)*range;line(ax,ay,x,y,hero.color,j%2?9:6,.24,0);ax=x;ay=y;}
      line(P.x,P.y,P.x+Math.cos(a)*range,P.y+Math.sin(a)*range,hero.color,13,.28,2);
    }
    function castSkill(actor=P) {
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      if(state!=='play'||P.downed||P.skillCD>0)return;
      const a=skillAim(actor),co=Math.cos(a),si=Math.sin(a),d=P.damage;
      P.aim=a;P.skillCD=hero.skillMax;P.castAnim=.52;P.inv=Math.max(P.inv,.30);P.magnet=2;P.hitPulse=.16;
      audio.sfx('skill');shake=options.shake?3.6:0;
      let hits=0;
      if(selected===0){
        hits=arcDamage(a,355,.58,d*10,510,0,actor);P.shield=Math.min(P.maxhp*.5,P.shield+24);attackArcFX(a,330,.58,actor);
        for(let j=0;j<12;j++)shootSword(P.x,P.y,a+(j-5.5)*.07,-1,d*.85,1,1.15,0,actor);
      }else if(selected===1){
        hits=laneDamage(a,435,68,d*11,580,0,actor);attackArcFX(a,280,.38,actor);
        line(P.x,P.y,P.x+co*440,P.y+si*440,hero.color,30,.38,2);
        for(let k=0;k<3;k++)addZone({x:P.x+co*(100+k*120),y:P.y+si*(100+k*120),r:62,life:2.5,age:0,tick:.3,friendly:true,damage:d*.62,color:hero.color},actor);
      }else if(selected===2){
        hits=laneDamage(a,430,79,d*10,430,1.0,actor);P.shield=Math.min(P.maxhp*.55,P.shield+32);
        for(let k=-1;k<=1;k++)line(P.x-si*k*25,P.y+co*k*25,P.x+co*430-si*k*25,P.y+si*430+co*k*25,hero.color,4,.32,1);
      }else if(selected===3){
        hits=arcDamage(a,140,.62,d*4.0,390,0,actor);
        for(let k=0;k<4;k++)addZone({x:P.x+co*(85+k*82),y:P.y+si*(85+k*82),r:80,life:1.4,age:0,tick:.12+k*.12,friendly:true,damage:d*9.8,color:hero.color,bomb:true},actor);
        line(P.x,P.y,P.x+co*405,P.y+si*405,hero.color,7,.30,1);
      }else if(selected===4){
        hits=arcDamage(a,325,.68,d*10.3,560,0,actor);P.hp=Math.min(P.maxhp,P.hp+P.maxhp*.17);P.shield=Math.min(P.maxhp*.50,P.shield+10);
        attackArcFX(a,290,.68,actor);number(P.x,P.y-45,'+'+Math.round(P.maxhp*.17),'#b8ecc7',true);
      }else{
        hits=arcDamage(a,340,.78,d*6.3,350,2.3,actor);attackArcFX(a,325,.78,actor);
        for(let k=0;k<7;k++){let t=a+(k-3)*.19;line(P.x+Math.cos(t)*55,P.y+Math.sin(t)*55,P.x+Math.cos(t)*340,P.y+Math.sin(t)*340,hero.color,4,.35,2);}
      }
      if(selected===4)coopHealNearby(actor);
      if(hits>0&&P.uid===0){audio.sfx('heavy',0,.8);toast('破阵命中 '+hits+' · 立即踏风冲出缺口',1.15);}
    }
    function ultimate(actor=P){
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      if(state!=='play'||P.downed||P.ult<99.9||P.ultTime>0)return;
      P.ult=0;P.ultTime=4.2;P.ultTick=0;P.ultAim=skillAim(actor);P.aim=P.ultAim;P.inv=.70;P.shield=Math.min(P.maxhp*.6,P.shield+22);P.magnet=5;run.ults++;
      audio.sfx('ultimate');if(P.uid===0)announce('无双破阵 · '+hero.name,hero.ult,'向指定方向持续凿穿 · 包围圈不会全屏消失',1.6);
      shake=options.shake?6:0;P.hitPulse=.16;
      const a=P.ultAim;attackArcFX(a,400,.6,actor);arcDamage(a,460,.62,P.damage*7,510,selected===5?1.3:0,actor);
      // Protect the immediate escape lane, rather than erasing every hostile projectile.
      for(let i=0;i<HB.max;i++)if(HB.a[i]){let dx=HB.x[i]-P.x,dy=HB.y[i]-P.y,d=Math.hypot(dx,dy)||1;if(d<85||(d<430&&(dx*Math.cos(a)+dy*Math.sin(a))/d>.74))HB.release(i);}
    }
    function updateUltimate(dt,actor=P){
        const P=actor,selected=P.heroId??0,hero=HEROES[selected];
      if(P.ultTime<=0)return;P.ultTime=Math.max(0,P.ultTime-dt);P.ultTick-=dt;if(P.ultTick>0)return;
      P.ultTick=selected===3?.17:.36;
      // Player can steer by deliberately holding the aim button; otherwise keep the original breach.
      if(P.uid===0&&P.controller!=='external'&&pointer.held){let want=skillAim(actor),delta=Math.atan2(Math.sin(want-P.ultAim),Math.cos(want-P.ultAim));P.ultAim+=clamp(delta,-.18,.18);}
      const a=P.ultAim,d=P.damage,co=Math.cos(a),si=Math.sin(a);P.aim=a;
      if(selected===0||selected===5){
        for(let j=0;j<3;j++){const along=120+((Math.floor(run.time*9)+j*3)%9)*38,side=rand(-65,65),x=P.x+co*along-si*side,y=P.y+si*along+co*side;
          line(x-35,y-190,x,y,hero.color,5,.26,2);areaDamage(x,y,72,d*(selected===5?3.8:4.5),240,selected===5?.7:0,actor);burst(x,y,5,selected,1.1);
        }
      }else if(selected===1){
        let sweep=a+Math.sin(run.time*12)*.18;laneDamage(sweep,455,68,d*4.3,310,0,actor);line(P.x,P.y,P.x+Math.cos(sweep)*480,P.y+Math.sin(sweep)*480,hero.color,24,.23,2);
      }else if(selected===2){
        let n=0;queryCircle(P.x,P.y,470,i=>{let dx=E.x[i]-P.x,dy=E.y[i]-P.y,di=Math.hypot(dx,dy)||1;if(n<10&&(dx*co+dy*si)/di>.74){n++;line(P.x,P.y,E.x[i],E.y[i],hero.color,3,.21,1);damageEnemy(i,d*4.5,220,true,actor);if(E.a[i])E.stagger[i]=.2;}});
      }else if(selected===3){
        for(let j=0;j<16;j++){let t=a+(j-7.5)*.045;shootSword(P.x-si*(j-7.5)*5,P.y+co*(j-7.5)*5,t,-1,d*1.05,1,1.1,0,actor);}
      }else{
        let along=140+(Math.floor(run.time*8)%4)*70;
        let x=P.x+co*along,y=P.y+si*along;ring(x,y,95,hero.color,.55,4);areaDamage(x,y,98,d*3.1,300,0,actor);P.hp=Math.min(P.maxhp,P.hp+.5);
      }
    }

    function bossAttack(i,actor=P) {
        const P=actor;
        const type = E.type[i], rage = E.phase[i], seq = Math.floor(E.cool[i]++), x = E.x[i], y = E.y[i], a = Math.atan2(P.y - y, P.x - x), dd = DIFFS[difficulty];
        E.timer[i] = (rage ? 1.8 : 2.65) / (run.scaling?.tempo||1) / (1 + (difficulty * .08));
        const fan = (n, arc, speed = 190, offset = a, kind = 0) => { for (let j = 0; j < n; j++)
            enemyBullet(x, y, offset + (j - (n - 1) / 2) * arc / Math.max(1, n - 1), speed, 13 + type * 1.3, 5.5, kind); };
        const nova = (n, speed = 140, offset = run.time, kind = 0) => { for (let j = 0; j < n; j++)
            enemyBullet(x, y, offset + j * TAU / n, speed, 12 + type * 1.1, 5.5, kind); };
        if (type === 0) {
            if (seq % 3 === 0) {
                warnCircle(x, y, 190 + rage * 50, .85, 26);
                fan(9 + rage * 6, 1.5, 205);
            }
            else if (seq % 3 === 1) {
                warnLine(x, y, a, 650, 66, .75, 28);
                E.dx[i] = Math.cos(a);
                E.dy[i] = Math.sin(a);
                E.charge[i] = -.8;
            }
            else {
                nova(20 + rage * 12, 165);
                for (let k = 0; k < 3 + rage; k++)
                    warnCircle(P.x + rand(-110, 110), P.y + rand(-90, 90), 60, .85 + k * .14, 19);
            }
        }
        else if (type === 1) {
            if (seq % 2 === 0) {
                for (let k = 0; k < 7 + rage * 4; k++)
                    warnCircle(P.x + rand(-240, 240), P.y + rand(-170, 170), 53, .8 + k * .08, 18, '#9ecbee');
                nova(16, 135, run.time, 2);
            }
            else {
                for (let k = 0; k < 3; k++)
                    fan(7 + rage * 3, .75, 170 + k * 35, a + (k - 1) * .65, 2);
                warnCircle(x, y, 245, 1.1, 23, '#9acde6');
            }
        }
        else if (type === 2) {
            if (seq % 3 < 2) {
                warnLine(x, y, a, 720, 78, .58, 30, '#e0b37a');
                E.dx[i] = Math.cos(a);
                E.dy[i] = Math.sin(a);
                E.charge[i] = -.65;
                E.timer[i] = 1.25;
                warnCircle(P.x, P.y, 92, 1.25, 28, '#e5b180');
            }
            else {
                warnCircle(x, y, 260 + rage * 55, .85, 30, '#edbd90');
                nova(24 + rage * 12, 200, run.time, 1);
            }
        }
        else if (type === 3) {
            nova(24 + rage * 16, 140, run.time, 3);
            if (seq % 2 === 0) {
                for (let k = 0; k < 12 + rage * 8; k++) {
                    let a = k * TAU / (12 + rage * 8);
                    spawnEnemy(k % 3 === 0 ? 6 : 0, 0, x + Math.cos(a) * 170, y + Math.sin(a) * 140);
                }
                ring(x, y, 185, '#c7a2ef', 1, 3);
            }
            else {
                for (let k = 0; k < 5 + rage * 3; k++)
                    warnCircle(P.x + rand(-240, 240), P.y + rand(-180, 180), 76, 1 + k * .1, 20, '#bc89ef');
            }
        }
        else if (type === 4) {
            if (seq % 2 === 0) {
                const offset = seq * .32;
                for (let k = 0; k < 4 + rage * 2; k++)
                    warnLine(x, y, offset + k * TAU / (4 + rage * 2), 1000, 43, .95, 29, '#f6be69');
                warnCircle(x, y, 125, .85, 24, '#efbe74');
            }
            else {
                nova(32 + rage * 16, 155, run.time, 1);
                for (let k = 0; k < 5; k++)
                    warnCircle(P.x + rand(-200, 200), P.y + rand(-130, 130), 70, .75 + k * .13, 24, '#f1b96e');
            }
        }
        else if (type === 5) {
            for (let k = 0; k < 4 + rage * 2; k++)
                warnCircle(P.x + rand(-250, 250), P.y + rand(-180, 180), 86, 1 + k * .13, 19, '#d99cfa', true);
            nova(20 + rage * 12, 120, run.time, 3);
            if (seq % 3 === 0)
                for (let k = 0; k < 8; k++) {
                    let a = k * TAU / 8;
                    spawnEnemy(6, 0, x + Math.cos(a) * 160, y + Math.sin(a) * 100);
                }
        }
        else if (type === 6) {
            for (let k = -1; k <= 1; k++)
                fan(6 + rage * 3, .64, 160 + Math.abs(k) * 40, a + k * .65, 4);
            for (let k = 0; k < 4 + rage * 2; k++)
                warnCircle(P.x + rand(-220, 220), P.y + rand(-150, 150), 74, 1 + k * .1, 18, '#98dcb0', true);
            if (seq % 3 === 0)
                nova(30, 125, run.time, 4);
        }
        else {
            nova(36 + rage * 24, 170, run.time, 1);
            for (let k = 0; k < 8 + rage * 6; k++)
                warnCircle(P.x + rand(-330, 330), P.y + rand(-220, 220), 57, .85 + k * .055, 22, '#ff9c80');
            if (seq % 3 === 2) {
                warnLine(x, y, a, 900, 100, .85, 36, '#ffb79a');
                E.dx[i] = Math.cos(a);
                E.dy[i] = Math.sin(a);
                E.charge[i] = -.9;
            }
        }
    }
    function updateEnemies(dt) {
        for (let i = 0; i < E.max; i++) {
            if (!E.a[i])
                continue;
            const P=partyTarget(E.x[i],E.y[i],i);
            E.age[i] += dt;
            E.hit[i] = Math.max(0, E.hit[i] - dt); E.stagger[i]=Math.max(0,E.stagger[i]-dt);
            E.slow[i] = Math.max(0, E.slow[i] - dt);
            E.freeze[i] = Math.max(0, E.freeze[i] - dt);
            E.timer[i] -= dt;
            let dx = P.x - E.x[i], dy = P.y - E.y[i], distance = Math.hypot(dx, dy) || 1, nx = dx / distance, ny = dy / distance, speed = E.speed[i] * (E.slow[i] > 0 ? .52 : 1), type = E.type[i], tier = E.tier[i];
            if (tier === 2 && E.phase[i] === 0 && E.hp[i] < E.maxhp[i] * .5) {
                E.phase[i] = 1;
                E.timer[i] = 1.1;
                $('bossPhase').textContent = '第二式 · 狂暴';
                announce('剑锋触怒妖王', BOSSES[type].name + ' · 狂暴', '攻击节奏加快，预留踏风闪避', 1.8);
                ring(E.x[i], E.y[i], 310, BOSSES[type].color, 1, 3);
                for (let j = 0; j < 3; j++)
                    spawnEnemy(j % 6, 1, E.x[i] + rand(-200, 200), E.y[i] + rand(-130, 130));
            }
            if(E.stagger[i]>0)speed*=.18;
            if (E.freeze[i] > 0) {
                speed *= tier === 2 ? .26 : 0;
                E.timer[i] += dt * .75;
            }
            if (E.charge[i] < 0) {
                E.charge[i] += dt;
                speed = 0;
                if (E.charge[i] >= 0) {
                    E.charge[i] = tier === 2 ? .62 : .5;
                    burst(E.x[i], E.y[i], 8, 1, 1.5);
                }
            }
            else if (E.charge[i] > 0) {
                E.charge[i] = Math.max(0, E.charge[i] - dt);
                E.x[i] += E.dx[i] * (tier === 2 ? 580 : 390) * dt;
                E.y[i] += E.dy[i] * (tier === 2 ? 580 : 390) * dt;
                speed = 0;
                if (frameNo % 4 === 0)
                    particle(E.x[i], E.y[i], 0, 0, .24, 8, 1, 1);
            }
            if (tier === 2) {
                if (E.timer[i] <= 0 && E.charge[i] === 0)
                    bossAttack(i,P);
                if (distance < 210)
                    speed *= .28;
            }
            else if (tier === 1) {
                if (E.timer[i] <= 0 && distance < 720) {
                    E.timer[i] = rand(3, 4.8) / (1 + difficulty * .12);
                    if (type === 1 || type === 0) {
                        warnLine(E.x[i], E.y[i], Math.atan2(dy, dx), 460, 40, .65, 16);
                        E.dx[i] = nx;
                        E.dy[i] = ny;
                        E.charge[i] = -.7;
                    }
                    else if (type === 4 || type === 3) {
                        warnCircle(P.x + rand(-35, 35), P.y + rand(-35, 35), 78, .8, 16, type === 4 ? '#9fdda8' : '#d39ce9', type === 4);
                    }
                    else {
                        for (let j = -2; j <= 2; j++)
                            enemyBullet(E.x[i], E.y[i], Math.atan2(dy, dx) + j * .22, 165, 13, 5);
                    }
                }
            }
            else if ((type === 6 || type === 4) && distance < 720) {
                if (distance < 340) {
                    nx = -ny;
                    ny = dx / distance;
                    speed *= .55;
                }
                if (E.timer[i] <= 0) {
                    E.timer[i] = rand(2.5, 4.2);
                    enemyBullet(E.x[i], E.y[i], Math.atan2(dy, dx), type === 6 ? 135 : 165, type === 6 ? 10 : 8, 4, type === 6 ? 3 : 4);
                }
            }
            else if (type === 1 && E.timer[i] <= 0 && distance < 360 && E.charge[i] === 0) {
                E.dx[i] = nx;
                E.dy[i] = ny;
                E.charge[i] = -.36;
                E.timer[i] = rand(3.5, 6);
            }
            if(tier!==2 && E.freeze[i]<=0 && E.charge[i]===0){
              if(distance>560)speed*=1.28;
              if(type!==4&&type!==6){
                if((type===1||type===3||i%6===1)&&distance>135&&P.moving){
                  const lead=.85+(i%3)*.16,tx=P.x+Math.cos(P.moveAim)*P.speed*lead,ty=P.y+Math.sin(P.moveAim)*P.speed*lead;
                  let ax=tx-E.x[i],ay=ty-E.y[i],al=Math.hypot(ax,ay)||1;nx=ax/al;ny=ay/al;
                } else if((type===2||type===7)&&distance>90&&distance<480){
                  const side=(i&1)?1:-1,angle=Math.atan2(E.y[i]-P.y,E.x[i]-P.x)+side*.21;
                  const shell=72+Math.max(0,155-(run.waveClock%40)*5);
                  let ax=P.x+Math.cos(angle)*shell-E.x[i],ay=P.y+Math.sin(angle)*shell-E.y[i],al=Math.hypot(ax,ay)||1;
                  nx=ax/al;ny=ay/al;if(al<15)speed*=.28;
                }
              }
            }
            if (tier !== 2 && E.freeze[i] <= 0 && ((i + frameNo) & 1) === 0) {
                let gx = clamp(Math.floor((E.x[i] + HALF) / CELL), 1, 62), gy = clamp(Math.floor((E.y[i] + HALF) / CELL), 1, 62), rx = 0, ry = 0, seen = 0, visits=0;
                for (let yy = gy - 1; yy <= gy + 1 && seen < 7 && visits<48; yy++)
                    for (let xx = gx - 1; xx <= gx + 1 && seen < 7 && visits<48; xx++) {
                        let j = hashHead[xx + yy * 64], guard = 0;
                        while (j !== -1 && seen < 7 && guard++ < 32 && visits++<48) {
                            if (j !== i && E.a[j]) {
                                let qx = E.x[i] - E.x[j], qy = E.y[i] - E.y[j], q = qx * qx + qy * qy, m = (E.radius[i] + E.radius[j])*.84;
                                if (q < m * m && q > .01) {
                                    let d = Math.sqrt(q), f = (m - d) * 4;
                                    rx += qx / d * f;
                                    ry += qy / d * f;
                                    seen++;
                                }
                            }
                            j = hashNext[j];
                        }
                    }
                E.x[i] += clamp(rx, -160, 160) * dt * 2;
                E.y[i] += clamp(ry, -160, 160) * dt * 2;
            }
            let weave = Math.sin(E.age[i] * 1.7 + i) * .17;
            E.x[i] += (nx - ny * weave) * speed * dt + E.kx[i] * dt;
            E.y[i] += (ny + nx * weave) * speed * dt + E.ky[i] * dt;
            E.kx[i] *= Math.exp(-8 * dt);
            E.ky[i] *= Math.exp(-8 * dt);
            if (E.charge[i] < .001 && E.charge[i] > 0)
                E.charge[i] = 0;
            if (distance < E.radius[i] + 15) {
                hurtActor(P,tier === 2 ? 30 : tier === 1 ? 17 : 7 + type * .35, E.x[i], E.y[i]);
                if (tier !== 2) {
                    E.x[i] -= nx * dt * 36;
                    E.y[i] -= ny * dt * 36;
                }
            }
            E.x[i] = clamp(E.x[i], -1720, 1720);
            E.y[i] = clamp(E.y[i], -1540, 1540);
            if (distance > 1700 && tier === 0) {
                E.x[i] = P.x + rand(-700, 700);
                E.y[i] = P.y + (Math.random() < .5 ? -440 : 440);
            }
        }
    }
    // Shortest distance to a movement segment prevents fast swords from tunnelling through targets.
    function pointSegmentSq(x, y, ax, ay, bx, by) { let dx = bx - ax, dy = by - ay, t = clamp(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1), 0, 1); return dist2(x - ax - dx * t, y - ay - dy * t); }
    function collideSword(b,actor=P) {
        const selected=B.hero[b],hero=HEROES[selected];
        const ax = B.px[b], ay = B.py[b], bx = B.x[b], by = B.y[b], minx = clamp(Math.floor((Math.min(ax, bx) - 78 + HALF) / CELL), 0, 63), maxx = clamp(Math.floor((Math.max(ax, bx) + 78 + HALF) / CELL), 0, 63), miny = clamp(Math.floor((Math.min(ay, by) - 78 + HALF) / CELL), 0, 63), maxy = clamp(Math.floor((Math.max(ay, by) + 78 + HALF) / CELL), 0, 63);
        for (let cy = miny; cy <= maxy; cy++)
            for (let cx = minx; cx <= maxx; cx++) {
                let e = hashHead[cx + cy * 64], guard = 0;
                while (e !== -1 && guard++ < E.max) {
                    let next = hashNext[e];
                    if (E.a[e] && B.lastHit[b] !== e && pointSegmentSq(E.x[e], E.y[e], ax, ay, bx, by) < (E.radius[e] + (selected === 1 ? 8 : 4)) ** 2) {
                        B.lastHit[b] = e;
                        let ex = E.x[e], ey = E.y[e];
                        damageEnemy(e, B.damage[b], selected === 1 ? 42 : 8,true,actor);
                        if (selected === 2 && Math.random() < .22) {
                            let chain = -1, best = 120 ** 2;
                            queryCircle(ex, ey, 120, k => { if (k !== e) {
                                let d = dist2(E.x[k] - ex, E.y[k] - ey);
                                if (d < best) {
                                    best = d;
                                    chain = k;
                                }
                            } });
                            if (chain >= 0 && E.a[chain]) {
                                line(ex, ey, E.x[chain], E.y[chain], hero.color, 1.5, .18, 1);
                                damageEnemy(chain, B.damage[b] * .55, 0, false,actor);
                            }
                        }
                        if (--B.pierce[b] <= 0) {
                            B.release(b);
                            return;
                        }
                    }
                    e = next;
                }
            }
    }
    function updateSwords(dt) {
        for (let i = 0; i < B.max; i++) {
            if (!B.a[i])
                continue;
            const actor=actorByUid(B.owner[i]); if(!actor){B.release(i);continue;}
            const P=actor,selected=B.hero[i];
            B.age[i] += dt;
            if (B.age[i] >= B.life[i]) {
                B.release(i);
                continue;
            }
            B.px[i] = B.x[i];
            B.py[i] = B.y[i];
            let target = B.target[i];
            if (target >= 0 && (!E.a[target] || E.gen[target] !== B.targetGen[i]))
                target = B.target[i] = -1;
            if (B.age[i] < B.orbit[i]) {
                let ratio = B.age[i] / B.orbit[i], angle = B.angle[i] + B.age[i] * (selected === 1 ? 4 : 7.5) * B.seed[i], r = 40 + ratio * (selected === 4 ? 118 : 98);
                B.x[i] = P.x + Math.cos(angle) * r;
                B.y[i] = P.y + Math.sin(angle) * r * .83;
            }
            else {
                if (B.age[i] - dt < B.orbit[i]) {
                    let a = target >= 0 ? Math.atan2(E.y[target] - B.y[i], E.x[target] - B.x[i]) : (P.uid===0&&P.controller!=='external'&&pointer.held) ? P.aim : Math.atan2(B.vy[i], B.vx[i]);
                    B.vx[i] = Math.cos(a) * B.speed[i];
                    B.vy[i] = Math.sin(a) * B.speed[i];
                }
                if (target >= 0) {
                    let dx = E.x[target] - B.x[i], dy = E.y[target] - B.y[i], l = Math.hypot(dx, dy) || 1, t = 1 - Math.exp(-B.turn[i] * dt);
                    B.vx[i] += (dx / l * B.speed[i] - B.vx[i]) * t;
                    B.vy[i] += (dy / l * B.speed[i] - B.vy[i]) * t;
                }
                if (selected === 1 && B.age[i] > 1.06) {
                    let dx = P.x - B.x[i], dy = P.y - B.y[i], d = Math.hypot(dx, dy) || 1, t = 1 - Math.exp(-3 * dt);
                    B.vx[i] += (dx / d * B.speed[i] - B.vx[i]) * t;
                    B.vy[i] += (dy / d * B.speed[i] - B.vy[i]) * t;
                    if (d < 25 && B.age[i] > 1.4) {
                        B.release(i);
                        continue;
                    }
                }
                B.x[i] += B.vx[i] * dt;
                B.y[i] += B.vy[i] * dt;
            }
            B.trailClock[i] += dt;
            if (B.trailClock[i] > .027) {
                B.trailClock[i] = 0;
                B.tx4[i] = B.tx3[i];
                B.ty4[i] = B.ty3[i];
                B.tx3[i] = B.tx2[i];
                B.ty3[i] = B.ty2[i];
                B.tx2[i] = B.tx1[i];
                B.ty2[i] = B.ty1[i];
                B.tx1[i] = B.px[i];
                B.ty1[i] = B.py[i];
            }
            if(B.age[i]>=B.orbit[i]*.92)collideSword(i,actor);
        }
    }
    function updateHostiles(dt) {
        for (let i = 0; i < HB.max; i++) {
            if (!HB.a[i])
                continue;
            HB.age[i] += dt;
            if (HB.age[i] > HB.life[i]) {
                HB.release(i);
                continue;
            }
            let ax = HB.x[i], ay = HB.y[i];
            if (HB.turn[i]) {
                const target=partyTarget(ax,ay,i);let dx = target.x - ax, dy = target.y - ay, d = Math.hypot(dx, dy) || 1, s = Math.hypot(HB.vx[i], HB.vy[i]), t = dt * HB.turn[i];
                HB.vx[i] += (dx / d * s - HB.vx[i]) * t;
                HB.vy[i] += (dy / d * s - HB.vy[i]) * t;
            }
            HB.x[i] += HB.vx[i] * dt;
            HB.y[i] += HB.vy[i] * dt;
            for(const unit of partyActors()){if(!unit.downed&&pointSegmentSq(unit.x, unit.y, ax, ay, HB.x[i], HB.y[i]) < (HB.radius[i] + 12) ** 2) {
                hurtActor(unit,HB.damage[i], ax, ay);
                burst(HB.x[i], HB.y[i], 4, 1);
                HB.release(i); break;
            }}
        }
    }
    function addZone(z,actor=P){if(z.friendly)z.owner=actor.uid;if(zones.length>=128)zones.shift();zones.push(z);}
    function updateWarnings(dt) {
        for (let k = warnings.length - 1; k >= 0; k--) {
            let a = warnings[k];
            a.age += dt;
            if (a.age < a.delay)
                continue;
            if (a.type === 0) {
                for(const unit of partyActors())if(dist2(unit.x-a.x,unit.y-a.y)<(a.r+9)**2)hurtActor(unit,a.damage,a.x,a.y);
                ring(a.x, a.y, a.r, a.color, .5, 2);
                burst(a.x, a.y, 16, 1, 1.8);
                if (a.zone)
                    addZone({ x: a.x, y: a.y, r: a.r, life: 3.4, age: 0, tick: 0, friendly: false, damage: a.damage * .34, color: a.color });
            }
            else {
                let bx = a.x + Math.cos(a.angle) * a.len, by = a.y + Math.sin(a.angle) * a.len;
                for(const unit of partyActors())if(pointSegmentSq(unit.x,unit.y,a.x,a.y,bx,by)<(a.width/2+10)**2)hurtActor(unit,a.damage,a.x,a.y);
                line(a.x, a.y, bx, by, a.color, a.width, .42, 3);
                burst(bx, by, 16, 1, 1.6);
            }
            warnings.splice(k, 1);
        }
        for (let k = zones.length - 1; k >= 0; k--) {
            let z = zones[k];
            z.age += dt;
            z.tick -= dt;
            if (z.tick <= 0) {
                z.tick = z.bomb ? 100 : .42;
                if (z.friendly) {
                    const owner=actorByUid(z.owner??0);if(owner)areaDamage(z.x, z.y, z.r, z.damage, z.bomb ? 230 : 15,0,owner);
                    if (z.bomb) {
                        ring(z.x, z.y, z.r, z.color, .7, 3);
                        burst(z.x, z.y, 24, selected, 1.5);
                        z.life = z.age + .16;
                    }
                }
                else {for(const unit of partyActors())if(dist2(unit.x-z.x,unit.y-z.y)<(z.r+5)**2)hurtActor(unit,z.damage,z.x,z.y);}
            }
            if (z.age >= z.life)
                zones.splice(k, 1);
        }
    }
    function levelUp() { P.level++; P.damage *= 1.025; P.maxhp += 2; if(!P.downed)P.hp = Math.min(P.maxhp, P.hp + 7); P.nextXP = run.expedition?110+P.level*90:44+P.level*24; P.pending++; if (P.pending === 1 && P.controller!=='external') {
        P.chooseTime = 8;
        show('upgradePanel');
    } P.crit = Math.min(.28, P.crit + .003); if (P.level % 5 === 0) {
        P.pierce=Math.min(3,P.pierce+1);
        P.formation++;
        toast('剑境突破 · 穿透 +1 · 护体剑阵扩展');
    } ring(P.x, P.y, 220, hero.color, .7, 3); audio.sfx('level'); coopLevelUp(); if(P.controller==='external'){while(P.pending)chooseUpgrade(P.path);}
    }
    function chooseUpgrade(path) { if (!P || P.pending <= 0 || state !== 'play')
        return; P.path = path; P.upgrades[path]++; if (path === 0)
        P.damage *= run.expedition?1.04:1.08;
    else if (path === 1) {
        if (P.swords < (run.expedition?24:36))
            P.swords = Math.min(run.expedition?24:36, P.swords + 2);
        else
            P.damage *= run.expedition?1.04:1.08;
    }
    else {
        P.maxhp += run.expedition?8:16;
        if(!P.downed)P.hp = Math.min(P.maxhp, P.hp + 28);
        P.regen += .12;
        P.speed = Math.min(330, P.speed + 4);
    } P.pending--; P.chooseTime = 8; if (P.pending <= 0)
        hide('upgradePanel'); audio.sfx('pickup'); updateHUD(); }
    function updateOrbs(dt) {
        for (let i = 0; i < O.max; i++) {
            if (!O.a[i])
                continue;
            O.age[i] += dt;
            const unit=partyTarget(O.x[i],O.y[i]);let dx = unit.x - O.x[i], dy = unit.y - O.y[i], d = Math.hypot(dx, dy) || 1;
            if (d < 150 + unit.formation * 14 || unit.magnet > 0) {
                let s = (unit.magnet > 0 ? 480 : 210) + 500 * clamp(1 - d / 170, 0, 1);
                O.x[i] += dx / d * s * dt;
                O.y[i] += dy / d * s * dt;
            }
            if (d < 24 || O.age[i] > 85) {
                if (O.kind[i] === 0)
                    P.xp += O.value[i];
                else if (O.kind[i] === 1) {
                    if(!unit.downed)unit.hp=Math.min(unit.maxhp,unit.hp+O.value[i]);
                    number(unit.x, unit.y - 40, '+' + O.value[i], '#b3efc0');
                }
                else {
                    unit.boost=8;
                    unit.ult=Math.min(100,unit.ult+20);
                    unit.shield=Math.min(unit.maxhp*.8,unit.shield+12);
                    toast('拾获剑匣 · 8 秒剑意激荡 · 无双蓄能 +20');
                    ring(P.x, P.y, 180, '#f3d287', .65, 3);
                }
                audio.sfx('pickup');
                O.release(i);
            }
        }
        let guard = 0;
        while (P.xp >= P.nextXP && guard++ < 10) {
            P.xp -= P.nextXP;
            levelUp();
        }
    }
    function updateEffects(dt) { for (let i = 0; i < F.max; i++) {
        if (!F.a[i])
            continue;
        F.age[i] += dt;
        if (F.age[i] >= F.life[i]) {
            F.release(i);
            continue;
        }
        F.x[i] += F.vx[i] * dt;
        F.y[i] += F.vy[i] * dt;
        F.vx[i] *= Math.exp(-2 * dt);
        F.vy[i] *= Math.exp(-2 * dt);
    } for (const list of [rings, lines, numbers, traces])
        for (let k = list.length - 1; k >= 0; k--) {
            list[k].age += dt;
            if (list[k].age >= list[k].life)
                list.splice(k, 1);
        } shake *= Math.exp(-12 * dt); flash = Math.max(0, flash - dt); phaseFlash = Math.max(0, phaseFlash - dt); }
    function setStage(z, silent = false) { run.stage = z % 4; props.length = 0; let rng = mulberry(2496 + z); for (let i = 0; i < 105; i++) {
        let a = rng() * TAU, r = 350 + rng() * 1300, x = Math.cos(a) * r, y = Math.sin(a) * r * .9;
        props.push({ x, y, type: i % 7 === 0 ? 1 : i % 3 === 0 ? 0 : 2, scale: .58 + rng() * .7 });
    } props.sort((a, b) => a.y - b.y); phaseFlash = 1.2; if (!silent) {
        if(!P.downed)P.hp = Math.min(P.maxhp, P.hp + P.maxhp * .2);
        announce('第 ' + (z + 1) + ' 境 · 剑路渐深', STAGES[run.stage].name, STAGES[run.stage].sub, 2.8);
    } }
    function startWave(w, initial = false) { run.wave = w; run.waveClock = 0;coopWaveStart(); run.bossSpawned = false; const stage = Math.floor((w - 1) / 4) % 4; if (stage !== run.stage)
        setStage(stage);
    else if (!initial)
        toast('第 ' + w + ' 潮 · 妖潮再起', 1.5); if (!initial)
        spawnPack(Math.round(Math.min(65+w*4,155)*(run.scaling?.density||1))); }
    function director(dt){
      if(run.expedition){expeditionDirector(dt);return;}
      run.waveClock+=dt;
      const cycle=run.waveClock%40;run.phase=cycle<8?0:cycle<23?1:cycle<34?2:3;
      if(mode==='bossrush'){
        if(run.bossId<0&&run.bosses<8&&run.time>=run.bossNextAt){run.wave=run.bosses*2+2;coopWaveStart();const z=Math.floor(run.bosses/2);if(z!==run.stage)setStage(z,true);spawnEnemy(run.bosses,2,P.x+340,P.y-120);run.bossNextAt=Infinity;}
        run.spawnAccumulator+=dt*(5+run.bosses*1.2)*DIFFS[difficulty].spawn*(run.scaling?.density||1);
        let budget=6;while(run.spawnAccumulator>=1&&E.count<(120+run.bosses*14)*(run.scaling?.density||1)&&budget-->0){spawnPack(1);run.spawnAccumulator--;}
        run.spawnAccumulator=Math.min(6,run.spawnAccumulator);return;
      }
      const mult=[.80,1.18,1.48,.42][run.phase],d=DIFFS[difficulty],target=Math.min(E.max-8,(d.target+run.wave*18)*(run.scaling?.density||1));
      run.spawnAccumulator+=dt*(21+run.wave*1.30)*d.spawn*mult*(run.scaling?.density||1);
      let budget=7;while(run.spawnAccumulator>=1&&E.count<target&&budget-->0){spawnPack(1);run.spawnAccumulator--;}
      run.spawnAccumulator=Math.min(7,run.spawnAccumulator);
      if(run.wave%2===0&&!run.bossSpawned&&run.waveClock>3){run.bossSpawned=true;let b=(Math.floor(run.wave/2)-1)%8;spawnEnemy(b,2,clamp(P.x+(Math.random()<.5?360:-360),-1500,1500),clamp(P.y-135,-1400,1400));}
      if(run.waveClock>=run.waveLength&&run.bossId<0){if(mode==='campaign'&&run.wave>=16)finish(true);else startWave(run.wave+1);}
    }
    function resolveBodies(dt){
      if(!P||!run)return;let contacts=0;
      queryCircle(P.x,P.y,85,i=>{
        if(contacts>=12||!E.a[i]||E.stagger[i]>.06||(E.freeze[i]>0&&E.tier[i]!==2))return;
        const dx=P.x-E.x[i],dy=P.y-E.y[i],dist=Math.hypot(dx,dy)||.1,m=11+E.radius[i]*(E.tier[i]===2?.80:.69);
        if(dist>=m)return;contacts++;
        if(P.dashTime>0){
          const armor=E.tier[i]>0||E.type[i]===2||E.type[i]===7;
          if(!armor&&(P.dashPierced||0)<1){P.dashPierced=(P.dashPierced||0)+1;E.stagger[i]=.18;damageEnemy(i,P.damage*.9,130,false);return;}
          P.dashTime=0;run.blocked++;audio.sfx('block',clamp((E.x[i]-P.x)/330,-.8,.8));
          if(run.time-(run.lastBlockTip||-10)>3){toast('阵线尚厚 · 先 E 打开缺口，再踏风',1.25);run.lastBlockTip=run.time;}
        }
        const push=Math.min(m-dist,5.8);P.x+=dx/dist*push;P.y+=dy/dist*push;
      });
    }
    function updatePressure(dt){
      run.pressureClock+=dt;if(run.pressureClock<.2)return;run.pressureClock=0;
      const sectors=run.sectors;sectors.fill(0);let near=0,near80=0;
      for(let i=0;i<E.max;i++)if(E.a[i]){
        const dx=E.x[i]-P.x,dy=E.y[i]-P.y,d=Math.hypot(dx,dy);
        if(d<190)near++;if(d<80)near80++;
        if(d<430){let a=(Math.atan2(dy,dx)+TAU)%TAU,k=Math.floor(a/TAU*12)%12;sectors[k]+=(1-d/480)*(E.tier[i]>0?2:E.type[i]===2||E.type[i]===7?1.5:1);}
      }
      let occupied=0,min=Infinity,gap=0;
      for(let k=0;k<12;k++){if(sectors[k]>2.4)occupied++;const n=sectors[k]+sectors[(k+11)%12]*.45+sectors[(k+1)%12]*.45;if(n<min){min=n;gap=k;}}
      run.near=near;run.near80=near80;run.gap=(gap+.5)*TAU/12;
      run.pressure=clamp((occupied/12)*.55+(near/34)*.45,0,1);run.peakPressure=Math.max(run.peakPressure,run.pressure);
      if(run.pressure>.77&&near>18&&!run.trapped){run.trapped=true;run.trapX=P.x;run.trapY=P.y;run.trapAt=run.time;}
      if(run.trapped&&near<9&&dist2(P.x-run.trapX,P.y-run.trapY)>170*170){
        run.trapped=false;run.breakouts++;P.ult=Math.min(100,P.ult+9);audio.sfx('level',0,.65);toast('冲出重围！ · 无双蓄能 +9',1.5);
      }
      audio.battle(run.pressure,run.bossId>=0,run.phase,P.hp/P.maxhp,P.ultTime>0);
    }

    function startGame() {
        if (!ready)
            return;
        if(!oathPreflight())return;
        if(run?.expedition&&!run.ended)finish(false);
        selected = clamp(selected, 0, 5);
        setAccent();
        saved.hero = selected;
        saved.diff = difficulty;
        save();
        for (const pool of [E, B, F, O, HB])
            pool.clear();
        for (const list of [rings, lines, warnings, numbers, traces, zones])
            list.length = 0;
        hashHead.fill(-1);
        keys.clear();
        pointer.held = false;
        joy.x = joy.y = 0;
        run = { time: 0, wave: 1, waveClock: 0, waveLength: 40, stage: 0, bossId: -1, bossSpawned: false, bosses: 0, bossBorn: 0, bossNextAt: 1.8, kills: 0, maxCombo: 0, combo: 0, comboClock: 0, coins: 0, damageTaken: 0, damageDealt: 0, ults: 0, spawnAccumulator: 0, invincible: false, ended: false,pressure:0,near:0,near80:0,phase:0,breakouts:0,heavyHits:0,blocked:0,lifetimeSum:0,sectors:new Float32Array(12),gap:0,pressureClock:0,trapped:false,trapX:0,trapY:0,peakPressure:0 };
        P = { uid:0,heroId:selected,downed:false,revive:0,damageDealt:0,damageTaken:0,x: 0, y: 0, hp: hero.hp, maxhp: hero.hp, shield: 0, speed: hero.speed, damage: hero.damage, swords: hero.count, attack: 0, ringTick: 0, inv: 1.5, dashCD: 0, dashMax: 1.65, dashTime: 0, dashX: 1, dashY: 0, skillCD: 0, ult: 60, ultTime: 0, ultTick: 0, level: 1, xp: 0, nextXP: 42, pending: 0, chooseTime: 0, path: 1, pierce: 0, formation: 0, crit: .11, regen: difficulty === 0 ? 1.05 : difficulty === 1 ? .26 : .07, upgrades: [0, 0, 0], kills: 0, aim: 0, moving: false, moveAim:0, hitPulse:0, walk: 0, magnet: 1.6, boost: 0, face: 1 };
        if (mode === 'bossrush') {
            P.ult=100;
            P.level = 12;
            P.damage *= 2.4;
            P.swords += 12;
            P.maxhp *= 1.4;
            P.hp = P.maxhp;
            P.pierce = 3;
            P.formation = 2;
            P.nextXP = 230;
            P.upgrades = [5, 6, 2];
        }
        coopStartRun();
        oathStartRun();
        camera.x = P.x;
        camera.y = P.y;
        simAccumulator=0;interpolation=1;previousPX=P.x;previousPY=P.y;previousCX=camera.x;previousCY=camera.y;
        perfLog.windowFrames=0;perfLog.windowTime=0;perfLog.windowWork=0;perfLog.windowMax=0;
        shake = flash = 0;
        fps = 0;
        workAvg = 0;
        peakEnemies = 0;
        peakSwords = 0;
        framesMeasured = 0;
        lowFrameTime = 0;
        setStage(0, true);
        for(const id of ['partyModal','inspect','codexModal','helpModal'])hide(id);
        hide('home');
        hide('select');
        hide('result');
        hide('pauseModal');
        hide('bossHud');
        hide('upgradePanel');
        hide('toast');
        show('hud');
        state = 'play';
        audio.init();
        audio.music('music_battle');
        $('hudName').textContent = hero.name;
        $('hudPortrait').innerHTML = crest(selected);
        $('skillSymbol').textContent = hero.symbol;
        $('skillLabel').textContent = hero.skill;
        $('ultLabel').textContent = hero.ult;
        if (mode !== 'bossrush') {
            spawnPack(Math.round(DIFFS[difficulty].initial*(run.scaling?.density||1)), true);
            announce(tx(mode).toUpperCase() + ' · ' + DIFFS[difficulty].name, STAGES[0].name, '鼠标按住瞄准 → E 打开缺口 → 空格冲出包围', 3.5);
        }
        else
            announce('八王试剑 · ' + DIFFS[difficulty].name, '剑试八荒', '十二阶剑修 · 连战八大妖王', 2.5);
        buildHash();snapPrevious();
        renderer?.resetRun();
        updateHUD();
        if(run.expedition)expeditionRoute();
    }
    function step(dt) {
        if (state !== 'play' || !P || run.ended)
            return;
        frameNo++;
        run.time += dt;
        director(dt);
        if (state !== 'play')
            return;
        oathTick(dt);
        if(!P.downed){
        P.attackAnim=Math.max(0,(P.attackAnim||0)-dt);P.castAnim=Math.max(0,(P.castAnim||0)-dt);
        P.inv = Math.max(0, P.inv - dt);
        P.dashCD = Math.max(0, P.dashCD - dt);
        P.skillCD = Math.max(0, P.skillCD - dt);
        P.magnet = Math.max(0, P.magnet - dt);
        P.boost = Math.max(0, P.boost - dt);
        P.shield = clamp(P.shield - dt * .65, 0, P.maxhp * .8);
        P.hp = Math.min(P.maxhp, P.hp + P.regen * dt);
        P.ult = Math.min(100, P.ult + dt * .48);
        let dx = (keys.has('d') || keys.has('arrowright') ? 1 : 0) - (keys.has('a') || keys.has('arrowleft') ? 1 : 0) + joy.x, dy = (keys.has('s') || keys.has('arrowdown') ? 1 : 0) - (keys.has('w') || keys.has('arrowup') ? 1 : 0) + joy.y, l = Math.hypot(dx, dy);
        const externalMove=oathLeaderMove(dt);if(externalMove){dx=externalMove.x;dy=externalMove.y;l=Math.hypot(dx,dy);}
        P.moving = l > .1;
        P.hitPulse=Math.max(0,(P.hitPulse||0)-dt);
        if(l>.1)P.moveAim=Math.atan2(dy,dx);
        P.walk += dt * (P.moving ? 13 : 3);
        if (l > 1) {
            dx /= l;
            dy /= l;
        }
        if (dx !== 0)
            P.face = dx < 0 ? -1 : 1;
        if (P.dashTime > 0) {
            P.dashTime = Math.max(0, P.dashTime - dt);
            P.x += P.dashX * 850 * dt;
            P.y += P.dashY * 850 * dt;
            if (frameNo % 2 === 0 && traces.length < 10)
                traces.push({ x: P.x, y: P.y, age: 0, life: .3 });
            P.moving = true;
        }
        else {
            P.x += dx * P.speed * dt;
            P.y += dy * P.speed * dt;
        }
        resolveBodies(dt);
        P.x = clamp(P.x, -1490, 1490);
        P.y = clamp(P.y, -1310, 1310);
        }
        camera.x += (P.x - camera.x) * (1 - Math.exp(-8 * dt));
        camera.y += (P.y - camera.y) * (1 - Math.exp(-8 * dt));
        buildHash();
        updateEnemies(dt);
        if (state !== 'play')
            return;
        buildHash();
        if(!P.downed){P.attack -= dt;
        if (P.attack <= 0) {
            salvo();
            P.attack = hero.interval * 1.35 / (1 + P.level * .009) * (P.boost > 0 ? .7 : 1);
        }
        P.ringTick -= dt;
        if (P.ringTick <= 0) {
            P.ringTick = .55;
            areaDamage(P.x, P.y, 65 + P.formation * 4, P.damage * .20, 8);
        }
        }
        coopTick(dt);
        updateSwords(dt);
        if (state !== 'play')
            return;
        if(!P.downed)updateUltimate(dt);
        if (state !== 'play')
            return;
        updateHostiles(dt);
        if (state !== 'play')
            return;
        updateWarnings(dt);
        if (state !== 'play')
            return;
        coopRescue(dt);
        updateOrbs(dt);
        updatePressure(dt);
        updateEffects(dt);
        if (P.pending > 0) {
            P.chooseTime -= dt;
            if (P.chooseTime <= 0)
                chooseUpgrade(P.path);
        }
        if (run.comboClock > 0)
            run.comboClock -= dt;
        else
            run.combo = 0;
        uiClock += dt;
        miniClock += dt;
        if (uiClock > .1) {
            uiClock = 0;
            updateHUD();
        }
        if (miniClock > .14) {
            miniClock = 0;
            drawMinimap();
        }
    }
