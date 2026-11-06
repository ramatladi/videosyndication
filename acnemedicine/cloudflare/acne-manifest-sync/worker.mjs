// acne-manifest-sync: queues each day's Acne Medicine Johannesburg posts for the existing uploader worker
// (acne-youtube-automation). Every 10 minutes it reads today's and tomorrow's (SAST) manifest from the media branch
// of ramatladi/videosyndication, verifies each video against the manifest's SHA-256, copies it into the shared R2
// bucket and inserts a QUEUED job (due = publish_at) into the shared D1 `jobs` table. The uploader's own cron then
// publishes it at the due time, exactly as for posts queued by hand. Nothing here talks to YouTube.
// Bindings (same resources as acne-youtube-automation): DB = D1 acne-youtube-automation, MEDIA = R2 acne-youtube-media.
const BASE = 'https://raw.githubusercontent.com/ramatladi/videosyndication/media/';
const CHANNEL = 'UCtwhnWNVzoS6MR0SkvZIDHQ';
const MAX_MEDIA = 90 * 1024 * 1024;
const MAX_NEW_PER_RUN = 2;           // keep each run well inside Worker limits
const ID = /^[a-z0-9][a-z0-9_-]{2,40}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function sastDates(now = Date.now()) {
  const d = new Date(now + 2 * 3600e3);                 // SAST = UTC+2, no DST
  const t = new Date(d.getTime() + 864e5);
  return [d.toISOString().slice(0, 10), t.toISOString().slice(0, 10)];
}

async function get(url, as) {
  const r = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(60000) });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url.slice(BASE.length)}`);
  return as === 'json' ? r.json() : r.arrayBuffer();
}

const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');

// Same checks as acne-youtube-automation's validateJob, plus the fields this channel always needs.
export function checkMeta(m, id) {
  if (m.id !== id) throw new Error('metadata id mismatch');
  if (typeof m.title !== 'string' || !m.title.trim() || m.title.length > 100 || /[<>]/.test(m.title)) throw new Error('bad title');
  if (typeof m.description !== 'string' || !m.description.trim() || new TextEncoder().encode(m.description).length > 5000) throw new Error('bad description');
  if (!['public', 'unlisted', 'private'].includes(m.privacy)) throw new Error('bad privacy');
  if (typeof m.paid_promotion !== 'boolean' || typeof m.contains_synthetic_media !== 'boolean') throw new Error('flags missing');
  if (m.paid_promotion && !/earn a commission/i.test(m.description)) throw new Error('commission disclosure missing');
  if (m.tags && (!Array.isArray(m.tags) || m.tags.some(x => typeof x !== 'string') || m.tags.join(',').length > 400)) throw new Error('bad tags');
  return { id, title: m.title, description: m.description, tags: m.tags || [], privacy: m.privacy,
           paid_promotion: m.paid_promotion, contains_synthetic_media: m.contains_synthetic_media, category_id: '26',
           kind: 'post', source: 'manifest' };
}

export async function sync(env, now = Date.now()) {
  const log = [];
  let added = 0;
  for (const date of sastDates(now)) {
    if (!DATE.test(date)) continue;
    const man = await get(`${BASE}acnemedicine/${date}/manifest.json`, 'json');
    if (!man) { log.push(`${date}: no manifest`); continue; }
    if (man.channel_id !== CHANNEL || man.date !== date || !Array.isArray(man.items)) throw new Error(`${date}: manifest rejected`);
    for (const it of man.items.slice(0, 12)) {
      if (added >= MAX_NEW_PER_RUN) return log.concat('limit reached; rest next run');
      if (!ID.test(it.id || '')) { log.push(`skip bad id`); continue; }
      const prefix = `acnemedicine/${date}/${it.id}`;
      if (it.video !== `${prefix}.mp4` || it.metadata !== `${prefix}.json` || !/^[0-9a-f]{64}$/.test(it.video_sha256 || '')) {
        log.push(`${it.id}: paths/hash rejected`); continue;
      }
      if (await env.DB.prepare('SELECT 1 FROM jobs WHERE id=?').bind(it.id).first()) continue;   // already queued or done
      const due = Date.parse(it.publish_at);
      if (!Number.isFinite(due)) { log.push(`${it.id}: bad publish_at`); continue; }
      const meta = checkMeta(await get(BASE + it.metadata, 'json'), it.id);
      const buf = await get(BASE + it.video);
      if (!buf || buf.byteLength < 10000 || buf.byteLength > MAX_MEDIA) { log.push(`${it.id}: video missing or size out of range`); continue; }
      if (new TextDecoder().decode(new Uint8Array(buf, 4, 4)) !== 'ftyp') { log.push(`${it.id}: not an MP4`); continue; }
      if (hex(await crypto.subtle.digest('SHA-256', buf)) !== it.video_sha256) { log.push(`${it.id}: SHA-256 mismatch`); continue; }
      const key = `manifest/${it.id}.mp4`;
      await env.MEDIA.put(key, buf, { httpMetadata: { contentType: 'video/mp4' } });
      const t = Date.now();
      const r = await env.DB.prepare("INSERT OR IGNORE INTO jobs(id,metadata,media_key,kind,status,due,created,updated,note) VALUES(?,?,?,'post','QUEUED',?,?,?,?)")
        .bind(it.id, JSON.stringify(meta), key, due, t, t, `queued from ${date} manifest`).run();
      if (r.meta?.changes) { added++; log.push(`${it.id}: queued for ${it.publish_at}`); }
    }
  }
  return log;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(sync(env).then(l => l.length && console.log(JSON.stringify({ event: 'manifest_sync', log: l })))
      .catch(e => console.error(JSON.stringify({ event: 'manifest_sync_failed', error: String(e.message || e) }))));
  },
  async fetch() {                    // no public interface
    return new Response('Not found', { status: 404 });
  },
};
