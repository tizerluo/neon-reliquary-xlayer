// 下载有并发上限；解析 / 模型准备串行进行，给界面留下绘制机会。
export const yieldForPaint = () => new Promise(resolve => setTimeout(resolve, 16));

export function describeAssets(records, keys, rendered = false) {
  const list = [...new Set(keys)].map(key => ({ ...(records.get(key) || { state: 'loading', phase: 'download' }), key }));
  const failed = list.filter(r => r.state === 'missing').map(r => r.key);
  const pending = list.filter(r => r.state !== 'ready' && r.state !== 'missing');
  const known = list.length > 0 && list.every(r => r.total > 0);
  const total = list.reduce((n, r) => n + (r.total || 0), 0);
  const loaded = list.reduce((n, r) => n + Math.min(r.loaded || 0, r.total || Infinity), 0);
  const phase = pending.some(r => r.phase === 'download' || r.phase === 'queued') ? 'download' : 'prepare';
  return { state: failed.length ? 'missing' : pending.length ? 'loading' : rendered ? 'ready' : 'loading',
    phase: failed.length ? 'failed' : pending.length ? phase : rendered ? 'ready' : 'frame',
    failed, pending: pending.length, count: list.length, ready: list.filter(r => r.state === 'ready').length,
    loaded, total, progress: known ? Math.min(1, loaded / total) : null };
}

export function createAssetStore({ loader, url, fetcher = globalThis.fetch, concurrency = 3, timeout = 90000,
  verify = async () => {}, clock = () => performance.now(), yieldPaint = yieldForPaint, discard = () => {} } = {}) {
  const records = new Map(), queue = [];
  let active = 0, scheduled = false, preparation = Promise.resolve();

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(() => { scheduled = false; pump(); }, 0);
  }
  function pump() {
    queue.sort((a, b) => a.priority - b.priority || a.started - b.started);
    while (active < concurrency && queue.length) {
      const rec = queue.shift();
      if (rec.state !== 'loading' || rec.phase !== 'queued') continue;
      active++;
      run(rec).finally(() => { active--; schedule(); });
    }
  }
  async function run(rec) {
    const generation = rec.generation, controller = new AbortController();
    const current = () => generation === rec.generation && rec.state !== 'missing';
    rec.abort = () => controller.abort();
    rec.phase = 'download';
    const timer = setTimeout(() => { if (current()) { rec.state = 'missing'; rec.error = 'timeout'; controller.abort(); } }, timeout);
    try {
      const path = url(rec.path), request = rec.attempt ? path + (path.includes('?') ? '&' : '?') + 'retry=' + rec.attempt : path;
      const response = await fetcher(request, { signal: controller.signal });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const encoding = response.headers.get('content-encoding');
      rec.total = encoding && encoding !== 'identity' ? 0 : Number(response.headers.get('content-length')) || 0;
      let buffer;
      if (response.body?.getReader) {
        const reader = response.body.getReader(), chunks = [];
        while (true) {
          const { value, done } = await reader.read();
          if (!current()) { await reader.cancel(); return; }
          if (done) break;
          chunks.push(value); rec.loaded += value.byteLength;
        }
        const bytes = new Uint8Array(rec.loaded); let offset = 0;
        for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
        buffer = bytes.buffer;
      } else {
        buffer = await response.arrayBuffer(); rec.loaded = buffer.byteLength;
      }
      if (!current()) return;
      // 无 Content-Length 的响应也只在下载结束后获得分母，不编造百分比。
      rec.total = buffer.byteLength;
      await verify(rec.path, buffer);
      if (!current()) return;
      rec.phase = 'prepare'; rec.state = 'preparing';
      const job = async () => {
        if (!current()) return;
        await yieldPaint();
        const start = clock(), gltf = await loader.parseAsync(buffer, new URL('.', request).href);
        if (!current()) { discard(null, gltf); return; }
        const result = await rec.prepare(gltf, rec.key);
        if (!current()) { discard(result, gltf); return; }
        Object.assign(rec, result); rec.prepareMs = clock() - start;
        rec.state = 'ready'; rec.phase = 'ready'; rec.ms = clock() - rec.started;
      };
      // 失败不阻断后面的准备任务；取消等待时也能继续处理下一个角色。
      const aborted = new Promise(resolve => controller.signal.addEventListener('abort', resolve, { once: true }));
      const ready = preparation.then(job);
      preparation = Promise.race([ready.catch(() => {}), aborted]);
      await Promise.race([ready, aborted]);
    } catch (error) {
      if (generation === rec.generation) { rec.state = 'missing'; rec.phase = 'failed'; if (rec.error !== 'timeout') rec.error = String(error); }
    } finally { clearTimeout(timer); if (generation === rec.generation) rec.abort = null; }
  }

  function load(key, path, prepare, priority = 0) {
    let rec = records.get(key);
    if (rec) { rec.priority = Math.min(rec.priority, priority); return rec; }
    rec = { key, path, prepare, priority, state: 'loading', phase: 'queued', loaded: 0, total: 0,
      started: clock(), generation: 0, attempt: 0 };
    records.set(key, rec); queue.push(rec); schedule(); return rec;
  }
  function retry(keys) {
    for (const key of new Set(keys)) {
      const rec = records.get(key);
      if (!rec || rec.state === 'ready') continue;
      rec.generation++; rec.abort?.();
      Object.assign(rec, { state: 'loading', phase: 'queued', loaded: 0, total: 0, error: null,
        started: clock(), attempt: rec.attempt + 1, priority: 0 });
      queue.push(rec);
    }
    schedule();
  }
  return { records, load, retry, prioritize(keys) {
      const current = new Set(keys);
      for (const rec of queue) rec.priority = current.has(rec.key) ? 0 : 2;
    }, describe: (keys, rendered) => describeAssets(records, keys, rendered),
    metrics: () => ({ active, queued: queue.length,
      assets: Object.fromEntries([...records].map(([key, r]) => [key, { state: r.state, phase: r.phase,
        loaded: r.loaded, total: r.total, ms: r.ms, prepareMs: r.prepareMs, attempt: r.attempt, error: r.error }])) }) };
}
