/* 仅在 ?test 验收页由 CDP 注入；普通游戏不加载本工具，也不改渲染命令。 */
(() => {
  if (!new URLSearchParams(location.search).has('test')) throw new Error('GPU probe requires ?test');
  const refs = window.__NR_GPU_REFS, bridge = window.__NR_VISUAL_BRIDGE;
  if (!refs?.native || !refs.env || !refs.renderer || !bridge) throw new Error('Capture render references first');
  const layers = ['native', 'arena', 'roster'];
  const contexts = layers.map((layer, i) => {
    const canvas = document.getElementById(['game', 'visualArena', 'visualRoster'][i]);
    const gl = canvas.getContext('webgl2');
    const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    if (!ext) throw new Error(`${layer}: GPU timer unavailable`);
    return { layer, canvas, gl, ext };
  });
  const original = { native: refs.native.render, arena: refs.env.render, bridge: bridge.render };
  let run = null, frame = null, bridgeDepth = 0, hdOpen = false, restored = false;
  let created = 0, deleted = 0, invalidated = 0, pollScheduled = false;
  const pending = [], errors = [], results = [];

  const quantile = (values, p) => {
    const a = [...values].sort((x, y) => x - y);
    return a[Math.max(0, Math.ceil(a.length * p) - 1)] ?? null;
  };
  const stats = a => ({ samples: a.length, median: quantile(a, .5), p95: quantile(a, .95),
    p99: quantile(a, .99), max: a.length ? Math.max(...a) : null,
    mean: a.length ? a.reduce((s, v) => s + v, 0) / a.length : null });

  function begin(i) {
    const c = contexts[i], q = c.gl.createQuery();
    created++;
    c.gl.beginQuery(c.ext.TIME_ELAPSED_EXT, q);
    frame.queries[i] = q;
    frame.order.push(c.layer);
  }
  function end(i) { contexts[i].gl.endQuery(contexts[i].ext.TIME_ELAPSED_EXT); }
  function discard(f) {
    for (let i = 0; i < contexts.length; i++) if (f.queries[i]) {
      contexts[i].gl.deleteQuery(f.queries[i]); deleted++; f.queries[i] = null;
    }
  }
  function complete() {
    if (!run || run.submitted < run.samples || pending.length) return;
    const r = run; run = null;
    clearTimeout(r.timeout);
    const rows = r.rows.sort((a, b) => a.index - b.index);
    const sums = rows.map(row => layers.reduce((s, k) => s + row.gpuNs[k], 0) / 1e6);
    const report = { label: r.label, valid: !r.disjoint && rows.length === r.samples && !r.errors.length,
      requested: r.samples, warmup: r.warmup, disjoint: r.disjoint, skippedBacklog: r.skipped,
      elapsedMs: performance.now() - r.started, units: 'nanoseconds (raw); milliseconds (summary)',
      gpuMs: Object.fromEntries(layers.map(k => [k, stats(rows.map(row => row.gpuNs[k] / 1e6))])),
      totalGpuMs: stats(sums), frameIntervalMs: stats(rows.map(row => row.frameIntervalMs).filter(v => v != null)),
      cpuSubmitMs: Object.fromEntries(layers.map(k => [k, stats(rows.map(row => row.cpuMs[k]))])),
      errors: r.errors, snapshotBefore: r.snapshotBefore, metricsBefore: r.metricsBefore,
      snapshot: window.__NR.snapshot(), metrics: bridge.metrics(), rows };
    results.push(report); r.resolve(report);
  }
  function poll() {
    pollScheduled = false;
    if (!run) return;
    // 任何上下文 disjoint 都使本次整组失效，不能把三个层的无效值相加。
    if (contexts.some(c => c.gl.getParameter(c.ext.GPU_DISJOINT_EXT))) {
      run.disjoint++; invalidated += pending.length;
      for (const f of pending) discard(f);
      pending.length = 0; run.submitted = run.samples;
    }
    for (let n = pending.length - 1; n >= 0; n--) {
      const f = pending[n];
      if (!f.queries.every((q, i) => q && contexts[i].gl.getQueryParameter(q, contexts[i].gl.QUERY_RESULT_AVAILABLE))) continue;
      const gpuNs = Object.fromEntries(layers.map((k, i) => [k, contexts[i].gl.getQueryParameter(f.queries[i], contexts[i].gl.QUERY_RESULT)]));
      run.rows.push({ index: f.index, gameTime: f.gameTime, load: f.load, gpuNs, cpuMs: f.cpuMs,
        frameIntervalMs: f.frameIntervalMs, order: f.order });
      discard(f); pending.splice(n, 1);
    }
    complete();
    if (pending.length) schedulePoll();
  }
  function schedulePoll() {
    if (!pollScheduled) { pollScheduled = true; setTimeout(poll, 0); }
  }

  refs.native.render = function (...args) {
    frame = null;
    if (run && run.submitted < run.samples) {
      if (run.warmLeft > 0) run.warmLeft--;
      else if (pending.length >= 48) run.skipped++;
      else {
        const t = performance.now();
        const d = args[0];
        frame = { index: run.submitted, gameTime: d.run?.time,
          load: { enemies: d.E.count, blades: d.B.count, hostiles: d.HB.count, pickups: d.O.count,
            warnings: d.warnings.length, skillEvents: d.skillEvents?.length, bossEvents: d.bossEvents?.length,
            pickupEvents: d.pickupEvents?.length }, queries: [], order: [], cpuMs: {},
          frameIntervalMs: run.lastStart == null ? null : t - run.lastStart };
        run.lastStart = t;
      }
    }
    if (!frame) return original.native.apply(this, args);
    const t = performance.now(); begin(0);
    try { return original.native.apply(this, args); }
    finally { end(0); frame.cpuMs.native = performance.now() - t; }
  };
  refs.env.render = function (...args) {
    if (!frame || !bridgeDepth || !args[0]) return original.arena.apply(this, args);
    const t = performance.now(); begin(1);
    try { return original.arena.apply(this, args); }
    finally {
      end(1); frame.cpuMs.arena = performance.now() - t;
      // 场地渲染（含 bloom / 热浪）全部结束后，才开启高清层，三个时间区间不重叠。
      begin(2); hdOpen = true; frame.hdCpuStart = performance.now();
    }
  };
  bridge.render = function (...args) {
    bridgeDepth++;
    try { return original.bridge.apply(this, args); }
    finally {
      bridgeDepth--;
      if (frame) {
        if (hdOpen) {
          end(2); hdOpen = false;
          frame.cpuMs.roster = performance.now() - frame.hdCpuStart;
        }
        if (frame.order.join(',') !== layers.join(',')) {
          const message = `Incomplete layer order: ${frame.order.join(',')}`;
          errors.push(message); run.errors.push(message); discard(frame);
        } else pending.push(frame);
        run.submitted++; frame = null; schedulePoll();
      }
    }
  };

  window.__NR_GPU_PROBE = {
    contexts: () => contexts.map(c => {
      const debug = c.gl.getExtension('WEBGL_debug_renderer_info');
      return { layer: c.layer, canvas: c.canvas.id, resolution: [c.canvas.width, c.canvas.height],
        attrs: c.gl.getContextAttributes(), timerBits: c.gl.getQuery(c.ext.TIME_ELAPSED_EXT, c.ext.QUERY_COUNTER_BITS_EXT),
        renderer: debug ? c.gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : c.gl.getParameter(c.gl.RENDERER) };
    }),
    measure(label, { samples = 180, warmup = 45, timeoutMs = 15000 } = {}) {
      if (restored || run || pending.length) return Promise.reject(new Error('GPU probe unavailable or busy'));
      return new Promise((resolve, reject) => {
        run = { label, samples, warmup, warmLeft: warmup, submitted: 0, lastStart: null, started: performance.now(),
          rows: [], skipped: 0, disjoint: 0, errors: [], snapshotBefore: window.__NR.snapshot(),
          metricsBefore: bridge.metrics(), resolve, reject };
        run.timeout = setTimeout(() => {
          const r = run; run = null;
          for (const f of pending) discard(f); pending.length = 0;
          reject(new Error(`${label}: timed out (${r.rows.length}/${samples})`));
        }, timeoutMs);
      });
    },
    status: () => ({ restored, measuring: run?.label ?? null, created, deleted, liveQueries: created - deleted,
      invalidated, errors: [...errors], activeQueries: contexts.map(c => !!c.gl.getQuery(c.ext.TIME_ELAPSED_EXT, c.gl.CURRENT_QUERY)),
      glErrors: contexts.map(c => c.gl.getError()) }),
    results,
    restore() {
      if (run || pending.length || frame) throw new Error('Finish GPU capture before restore');
      refs.native.render = original.native; refs.env.render = original.arena; bridge.render = original.bridge;
      restored = true; delete window.__NR_GPU_REFS;
      return this.status();
    },
  };
})();
