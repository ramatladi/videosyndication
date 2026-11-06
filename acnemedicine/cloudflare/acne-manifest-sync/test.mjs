import fs from 'node:fs'; import crypto from 'node:crypto';
// node test.mjs — runs sync() against an in-memory D1/R2 and a local copy of the media branch.
import { sync, sastDates, checkMeta } from './worker.mjs';
import os from 'node:os'; import path from 'node:path';
// Work on a scratch copy of the media-branch checkout (argv[2]) holding only 2026-11-07, so the real folder is untouched.
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'amjsync-'));
fs.cpSync(`${process.argv[2]}/acnemedicine/2026-11-07`, `${ROOT}/acnemedicine/2026-11-07`, { recursive: true });
let fails = 0; const ok = (n, c, d) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) { fails++; if (d) console.log('   ', d); } };
const jobs = new Map(), r2 = new Map(); let fetched = [];
const env = {
  DB: { prepare(sql) { return { bind(...a) { return {
    async first() { return jobs.has(a[0]) ? { 1: 1 } : null; },
    async run() { if (jobs.has(a[0])) return { meta: { changes: 0 } };
      jobs.set(a[0], { id: a[0], metadata: a[1], media_key: a[2], due: a[3], status: 'QUEUED' }); return { meta: { changes: 1 } }; } }; } }; } },
  MEDIA: { async put(k, b) { r2.set(k, Buffer.from(b)); } },
};
let tamper = null;
globalThis.fetch = async (url) => {
  const p = url.replace('https://raw.githubusercontent.com/ramatladi/videosyndication/media/', ''); fetched.push(p);
  const f = `${ROOT}/${p}`; if (!fs.existsSync(f)) return new Response('nf', { status: 404 });
  let b = fs.readFileSync(f); if (tamper && p.endsWith(tamper)) b = Buffer.concat([b, Buffer.from('x')]);
  return new Response(b, { status: 200 });
};
const NOW = Date.parse('2026-11-06T18:30:00Z');    // 20:30 SAST on 6 Nov
ok('SAST dates are today and tomorrow', JSON.stringify(sastDates(NOW)) === '["2026-11-06","2026-11-07"]');
let log = await sync(env, NOW);
ok('two new posts per run, queued with manifest due times', jobs.size === 2 && [...jobs.values()].every(j => j.status === 'QUEUED'), log);
const man = JSON.parse(fs.readFileSync(`${ROOT}/acnemedicine/2026-11-07/manifest.json`));
const j1 = jobs.get(man.items[0].id);
ok('due time = publish_at', j1 && j1.due === Date.parse(man.items[0].publish_at));
ok('R2 copy is byte-identical to the verified video', j1 && crypto.createHash('sha256').update(r2.get(j1.media_key)).digest('hex') === man.items[0].video_sha256);
const meta = JSON.parse(j1.metadata);
ok('metadata carries title, commission disclosure, paid promotion, privacy', meta.title === man.items[0].title && /earn a commission/i.test(meta.description) && meta.paid_promotion === true && meta.privacy === 'public');
for (let i = 0; i < 3; i++) log = await sync(env, NOW);
ok('later runs queue the rest, all six once', jobs.size === 6, [...jobs.keys()]);
fetched = []; await sync(env, NOW);
ok('already-queued posts are not downloaded again', !fetched.some(p => p.endsWith('.mp4')), fetched);
// tampered video is refused
jobs.clear(); r2.clear(); tamper = man.items[0].id + '.mp4';
log = await sync(env, NOW);
ok('video whose SHA-256 differs from the manifest is refused', !jobs.has(man.items[0].id) && log.some(l => l.includes('SHA-256 mismatch')), log);
tamper = null;
// missing disclosure refused
let threw = false; try { checkMeta({ id: 'abc', title: 't', description: 'no disclosure', privacy: 'public', paid_promotion: true, contains_synthetic_media: false }, 'abc'); } catch { threw = true; }
ok('paid post without the commission line is refused', threw);
// wrong channel manifest refused
const bad = `${ROOT}/acnemedicine/2026-11-06`; fs.mkdirSync(bad, { recursive: true });
fs.writeFileSync(`${bad}/manifest.json`, JSON.stringify({ date: '2026-11-06', channel_id: 'UCother', items: [] }));
threw = false; try { await sync(env, NOW); } catch { threw = true; } ok('manifest for another channel is rejected', threw);
fs.rmSync(`${bad}/manifest.json`);
fs.rmSync(ROOT, { recursive: true, force: true });
console.log(fails ? `${fails} FAILED` : 'ALL PASSED'); process.exit(fails ? 1 : 0);
