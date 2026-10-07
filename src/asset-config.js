'use strict';
globalThis.NRAssets = (() => {
  const config = /*__NR_ASSET_CONFIG__*/ { base: null, files: {} };
  function key(path) { return String(path).replace(/^.*visual-lab\/assets\//, '').split(/[?#]/)[0]; }
  function url(path) {
    const name = key(path);
    if (config.base && !config.files[name]) throw Error('UNLISTED_ASSET: ' + name);
    return new URL(name, config.base || new URL('visual-lab/assets/', document.baseURI)).href;
  }
  async function verify(path, bytes) {
    if (!config.base) return;
    const name = key(path), expected = config.files[name];
    if (!expected || bytes.byteLength !== expected.bytes) throw Error('ASSET_SIZE_MISMATCH: ' + name);
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const hash = [...new Uint8Array(digest)].map(n => n.toString(16).padStart(2, '0')).join('');
    if (hash !== expected.sha256) throw Error('ASSET_HASH_MISMATCH: ' + name);
  }
  return Object.freeze({ url, verify, version: config.version || 'local', files: config.files });
})();
