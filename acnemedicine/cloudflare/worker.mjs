const FIRST_POST = {"id": "amj001", "title": "Dermalogica Breakout Clearing Foaming Wash: what's in it and how to use it #shorts", "description": "What's in Dermalogica's Breakout Clearing Foaming Wash, and how Dermalogica says to use it.\n\nWe earn a commission if you buy through our link.\n\n\u2022 Active ingredient: salicylic acid 0.5%\n\u2022 8 botanicals including tea tree, lavender and camellia, plus orange peel extract\n\u2022 Morning and night: a pea-sized amount lathered in wet hands, on face, neck, chest or back; avoid the eyes; rinse with warm water\n\u2022 Patch test first if you have a known sensitivity to an ingredient\n\nProduct information from Dermalogica South Africa's product page (checked 4 Nov 2026). General product information, not medical advice. For severe or painful acne, see a doctor or pharmacist.\n\nShop: https://acnemedicine.co.za/\n\n#skincare #dermalogica #salicylicacid", "tags": ["dermalogica", "breakout clearing foaming wash", "salicylic acid", "skincare", "cleanser", "johannesburg"], "privacy": "public", "short": true, "contains_synthetic_media": false, "category_id": "26", "language": "en", "publish_at": null, "paid_promotion": true};
const CHANNEL = 'UCtwhnWNVzoS6MR0SkvZIDHQ';
const PROJECT = 'globalnewsflix-video';
const SCOPES = ['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly'];
const encoder = new TextEncoder();
const MAX_MEDIA = 90 * 1024 * 1024;
const headers = {'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Strict-Transport-Security':'max-age=31536000'};
class SafeError extends Error { constructor(message,status=400){super(message);this.status=status;} }
const b64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
const un64 = s => Uint8Array.from(atob(s.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));
const random = () => b64(crypto.getRandomValues(new Uint8Array(32)));
const digest = s => crypto.subtle.digest('SHA-256',encoder.encode(s));
const hash = async s => b64(await digest(s));
async function equal(a,b){return crypto.subtle.timingSafeEqual(await digest(a),await digest(b));}
async function key(env){return crypto.subtle.importKey('raw',un64(env.VAULT_KEY),'AES-GCM',false,['encrypt','decrypt']);}
export async function seal(env,value){const iv=crypto.getRandomValues(new Uint8Array(12));const data=await crypto.subtle.encrypt({name:'AES-GCM',iv},await key(env),encoder.encode(JSON.stringify(value)));return b64(iv)+'.'+b64(data);}
export async function unseal(env,value){const [iv,data]=value.split('.');return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:un64(iv)},await key(env),un64(data))));}
const json = (data,status=200,extra={}) => Response.json(data,{status,headers:{...headers,...extra}});
const cookie = (name,value,age) => `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
const getCookie = (r,name) => (r.headers.get('cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(name+'='))?.slice(name.length+1);
async function session(r,env){try{const s=await unseal(env,getCookie(r,'__Host-amj')||'');if(s.expires>Date.now())return s;}catch{}return null;}
async function boundedJSON(r){if(Number(r.headers.get('content-length'))>24000)throw new SafeError('Request too large',413);const reader=r.body?.getReader();let total=0,parts=[];if(!reader)throw new SafeError('Missing request');for(;;){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>24000){await reader.cancel();throw new SafeError('Request too large',413);}parts.push(value);}const bytes=new Uint8Array(total);let off=0;for(const p of parts){bytes.set(p,off);off+=p.length;}try{return JSON.parse(new TextDecoder().decode(bytes));}catch{throw new SafeError('Invalid JSON');}}
async function readVault(env,name){const row=await env.DB.prepare('SELECT value FROM vault WHERE name=?').bind(name).first();return row?unseal(env,row.value):null;}
async function writeVault(env,name,value){await env.DB.prepare('INSERT INTO vault(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value').bind(name,await seal(env,value)).run();}
export function validateConfig(data,origin){const c=data.web;if(!c||data.installed)throw new SafeError('Choose a Web application JSON. The Desktop JSON cannot use a hosted callback.');if(c.project_id!==PROJECT||!c.client_id?.endsWith('.apps.googleusercontent.com')||typeof c.client_secret!=='string'||!c.client_secret)throw new SafeError('Use a Web client from globalnewsflix-video.');if(!c.redirect_uris?.includes(origin+'/oauth/callback'))throw new SafeError('Register the exact callback address shown above in Google Cloud, then download the Web client JSON.');return {client_id:c.client_id,client_secret:c.client_secret};}
export function validateJob(j){if(!/^[a-z0-9][a-z0-9_-]{2,40}$/.test(j.id))throw new SafeError('Invalid post ID');if(typeof j.title!=='string'||!j.title.trim()||j.title.length>100||/[<>]/.test(j.title))throw new SafeError('Title must be 1–100 characters without angle brackets');if(typeof j.description!=='string'||!j.description.trim()||encoder.encode(j.description).length>5000)throw new SafeError('Description must be 1–5000 bytes');if(!['public','unlisted','private'].includes(j.privacy))throw new SafeError('Choose a visibility');if(typeof j.paid_promotion!=='boolean'||typeof j.contains_synthetic_media!=='boolean')throw new SafeError('Specify promotion and synthetic-media flags');if(j.paid_promotion&&!/earn a commission/i.test(j.description))throw new SafeError('Include the commission disclosure in the description');if(j.tags&&(!Array.isArray(j.tags)||j.tags.some(x=>typeof x!=='string')||j.tags.join(',').length>400))throw new SafeError('Invalid tags');return {...j,category_id:'26',tags:j.tags||[]};}
async function google(url,options={}){const res=await fetch(url,{...options,redirect:'manual',signal:AbortSignal.timeout(30000)});if(!res.ok)throw new SafeError('Google request failed (HTTP '+res.status+'). Reconnect or check the publishing status.',502);return res.json();}
async function channel(token){const d=await google('https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',{headers:{Authorization:'Bearer '+token}});if(d.items?.length!==1||d.items[0].id!==CHANNEL)throw new SafeError('Wrong YouTube channel. Choose Acne Medicine Johannesburg; no connection was saved.',403);return d.items[0];}
async function access(env){const [c,t]=await Promise.all([readVault(env,'config'),readVault(env,'youtube')]);if(!c||!t)throw new SafeError('Connect YouTube first',409);const d=await google('https://oauth2.googleapis.com/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({...c,grant_type:'refresh_token',refresh_token:t.refresh_token})});if(!d.access_token)throw new SafeError('Google did not return an access token',502);await channel(d.access_token);return d.access_token;}
async function updateJob(env,id,status,note=null){await env.DB.prepare('UPDATE jobs SET status=?,note=?,updated=? WHERE id=?').bind(status,note,Date.now(),id).run();}
async function verifyJob(env,j,token){const data=await google('https://www.googleapis.com/youtube/v3/videos?part=snippet,status,paidProductPlacementDetails&id='+encodeURIComponent(j.video_id),{headers:{Authorization:'Bearer '+token}});const v=data.items?.[0];if(!v)return;const want=JSON.parse(j.metadata);if(v.snippet.channelId!==CHANNEL||['failed','rejected','deleted'].includes(v.status.uploadStatus))return updateJob(env,j.id,'NEEDS_REVIEW','Channel or processing validation failed');if(v.status.privacyStatus!==want.privacy||Boolean(v.paidProductPlacementDetails?.hasPaidProductPlacement)!==want.paid_promotion)return updateJob(env,j.id,'NEEDS_REVIEW','Visibility or paid-promotion setting differs; inspect YouTube Studio');if(v.status.uploadStatus==='processed')await updateJob(env,j.id,'VERIFIED');}
export async function tick(env){
  // Claim at most one job. Interrupted uploads never restart automatically.
  await env.DB.prepare("UPDATE jobs SET status='NEEDS_REVIEW',note='Interrupted upload; inspect YouTube before retrying',updated=? WHERE status='UPLOADING' AND updated<?").bind(Date.now(),Date.now()-3600000).run();
  if(!await readVault(env,'youtube'))return;
  const token=await access(env);
  const pending=await env.DB.prepare("SELECT * FROM jobs WHERE status='PROCESSING' LIMIT 5").all();
  for(const j of pending.results)await verifyJob(env,j,token);
  // Require a verified unlisted test before any public post.
  const test=await env.DB.prepare("SELECT id FROM jobs WHERE status='VERIFIED' AND kind='test' LIMIT 1").first();
  const j=await env.DB.prepare("UPDATE jobs SET status='UPLOADING',updated=? WHERE id=(SELECT id FROM jobs WHERE status='QUEUED' AND due<=? AND (kind='test' OR ?=1) ORDER BY due LIMIT 1) AND status='QUEUED' RETURNING *").bind(Date.now(),Date.now(),test?1:0).first();
  if(!j)return;
  try{
    const item=JSON.parse(j.metadata), obj=await env.MEDIA.get(j.media_key);
    if(!obj)throw new SafeError('Video file is missing');
    const resource={snippet:{title:item.title,description:item.description,tags:[...item.tags,'amjref'+j.id],categoryId:'26',defaultLanguage:'en'},status:{privacyStatus:item.privacy,selfDeclaredMadeForKids:false,containsSyntheticMedia:item.contains_synthetic_media},paidProductPlacementDetails:{hasPaidProductPlacement:item.paid_promotion}};
    const start=await fetch('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,paidProductPlacementDetails',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json','X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':String(obj.size)},body:JSON.stringify(resource),redirect:'manual',signal:AbortSignal.timeout(30000)});
    if(!start.ok)throw new SafeError('YouTube refused upload session (HTTP '+start.status+')');
    const location=start.headers.get('location');const sessionURL=new URL(location||'https://invalid');if(sessionURL.protocol!=='https:'||sessionURL.hostname!=='www.googleapis.com')throw new SafeError('Unexpected Google upload destination');
    await env.DB.prepare('UPDATE jobs SET upload_session=?,updated=? WHERE id=?').bind(await seal(env,location),Date.now(),j.id).run();
    const sent=await fetch(location,{method:'PUT',headers:{'Content-Type':'video/mp4','Content-Length':String(obj.size)},body:obj.body,redirect:'manual',signal:AbortSignal.timeout(180000)});
    if(!sent.ok)throw new SafeError('Upload needs review (HTTP '+sent.status+'); it will not be repeated automatically');
    const result=await sent.json();if(!/^[A-Za-z0-9_-]{11}$/.test(result.id))throw new SafeError('No valid YouTube video ID returned');
    await env.DB.prepare("UPDATE jobs SET status='PROCESSING',video_id=?,updated=? WHERE id=?").bind(result.id,Date.now(),j.id).run();
  }catch(e){await updateJob(env,j.id,'NEEDS_REVIEW',e instanceof SafeError?e.message:'Upload interrupted; inspect YouTube before retrying');}
}
async function handle(r,env){
  const u=new URL(r.url), path=u.pathname;
  if(path==='/health')return json({ok:true,channel:CHANNEL,version:'1.0.0'});
  if(path==='/'&&r.method==='GET')return page();
  if(path==='/app.js'&&r.method==='GET')return new Response(APP,{headers:{...headers,'Content-Type':'text/javascript'}});
  if(r.method!=='GET'&&r.headers.get('origin')!==u.origin)throw new SafeError('Origin rejected',403);
  if(path==='/session'&&r.method==='POST'){
    const d=await boundedJSON(r);if(typeof d.key!=='string'||!await equal(d.key,env.ADMIN_TOKEN))throw new SafeError('Invalid access link',401);
    return json({ok:true},200,{'Set-Cookie':cookie('__Host-amj',await seal(env,{id:random(),expires:Date.now()+86400000}),86400)});
  }
  const owner=await session(r,env);if(!owner)throw new SafeError('Open your private access link to sign in',401);
  if(path==='/launch'&&r.method==='GET')return launchPage(env);
  if(path.startsWith('/launch/start/')&&r.method==='POST')return launchStart(env,u.origin,owner,path.slice('/launch/start/'.length));
  if(path.startsWith('/launch/v2/start/')&&r.method==='POST')return launch2Start(env,u.origin,owner,path.slice('/launch/v2/start/'.length));
  if(path==='/status'&&r.method==='GET'){const c=await readVault(env,'config'),t=await readVault(env,'youtube');const jobs=await env.DB.prepare('SELECT id,status,video_id,note,due,kind FROM jobs ORDER BY created DESC LIMIT 50').all();return json({configured:!!c,connected:!!t,channel:CHANNEL,channelTitle:t?.title,callback:u.origin+'/oauth/callback',jobs:jobs.results});}
  if(path==='/draft'&&r.method==='GET')return json(FIRST_POST);
  if(path==='/config'&&r.method==='POST'){if(await readVault(env,'youtube'))throw new SafeError('A channel is already connected; configuration is locked',409);const c=validateConfig(await boundedJSON(r),u.origin);await writeVault(env,'config',c);return json({ok:true});}
  if(path==='/oauth/start'&&r.method==='POST'){
    const c=await readVault(env,'config');if(!c)throw new SafeError('Upload the Web client JSON first',409);
    const state=random(),verifier=random();await env.DB.prepare('DELETE FROM oauth_states WHERE expires<?').bind(Date.now()).run();
    await env.DB.prepare('INSERT INTO oauth_states(state,owner,verifier,client,expires) VALUES(?,?,?,?,?)').bind(await hash(state),await hash(owner.id),await seal(env,verifier),c.client_id,Date.now()+600000).run();
    const params=new URLSearchParams({client_id:c.client_id,redirect_uri:u.origin+'/oauth/callback',response_type:'code',scope:SCOPES.join(' '),state,code_challenge:await hash(verifier),code_challenge_method:'S256',access_type:'offline',prompt:'consent select_account'});
    return json({url:'https://accounts.google.com/o/oauth2/v2/auth?'+params});
  }
  if(path==='/oauth/callback'&&r.method==='GET'){
    const state=u.searchParams.get('state')||'';
    const row=await env.DB.prepare('DELETE FROM oauth_states WHERE state=? AND owner=? AND expires>? RETURNING *').bind(await hash(state),await hash(owner.id),Date.now()).first();
    if(!row)throw new SafeError('Sign-in expired or was already used. Start again.',403);
    if(u.searchParams.has('error'))throw new SafeError('Google sign-in was cancelled. No connection changed.');
    const c=await readVault(env,'config');if(c.client_id!==row.client)throw new SafeError('Configuration changed. Start sign-in again.');
    const token=await google('https://oauth2.googleapis.com/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({...c,grant_type:'authorization_code',code:u.searchParams.get('code')||'',redirect_uri:u.origin+'/oauth/callback',code_verifier:await unseal(env,row.verifier)})});
    if(state.startsWith('launch.'))return scheduleLaunch(env,state,token);
    if(state.startsWith('launch2.'))return scheduleLaunch2(env,state,token);
    if(!token.refresh_token||!SCOPES.every(s=>(token.scope||'').split(' ').includes(s)))throw new SafeError('Both YouTube permissions and offline access are required. Start sign-in again.');
    const ch=await channel(token.access_token);await writeVault(env,'youtube',{refresh_token:token.refresh_token,title:ch.snippet.title,connected:Date.now()});
    return new Response(null,{status:303,headers:{...headers,Location:'/'}});
  }
  if(path==='/media'&&r.method==='POST'){
    const size=Number(r.headers.get('content-length'));if(!Number.isFinite(size)||size<10000||size>MAX_MEDIA)throw new SafeError('Choose an MP4 between 10 KB and 90 MB',413);
    if(r.headers.get('content-type')!=='video/mp4')throw new SafeError('MP4 required');
    const reader=r.body.getReader();const first=await reader.read();if(first.done||first.value.length<12||new TextDecoder().decode(first.value.slice(4,8))!=='ftyp')throw new SafeError('Invalid MP4 file');
    let count=first.value.length;const stream=new ReadableStream({start(c){c.enqueue(first.value);},async pull(c){const next=await reader.read();if(next.done){if(count!==size){c.error(new Error('Length mismatch'));return;}c.close();return;}count+=next.value.length;if(count>size||count>MAX_MEDIA){await reader.cancel();c.error(new Error('Too large'));return;}c.enqueue(next.value);},cancel(){return reader.cancel();}});
    const id=crypto.randomUUID();const fixed=new FixedLengthStream(size);await Promise.all([stream.pipeTo(fixed.writable),env.MEDIA.put(id,fixed.readable,{httpMetadata:{contentType:'video/mp4'}})]);return json({media_key:id});
  }
  if(path==='/jobs'&&r.method==='POST'){
    const input=await boundedJSON(r),j=validateJob(input);if(!await readVault(env,'youtube'))throw new SafeError('Connect YouTube first',409);
    const kind=j.kind==='test'?'test':'post';if(kind==='test'&&(j.privacy!=='unlisted'||j.paid_promotion))throw new SafeError('Connection test must be unlisted without paid promotion');
    const media=await env.MEDIA.head(j.media_key);if(!media)throw new SafeError('Upload a video first');
    const due=j.due?Date.parse(j.due):Date.now();if(!Number.isFinite(due))throw new SafeError('Invalid publication time');
    try{await env.DB.prepare("INSERT INTO jobs(id,metadata,media_key,kind,status,due,created,updated) VALUES(?,?,?,?,'QUEUED',?,?,?)").bind(j.id,JSON.stringify(j),j.media_key,kind,due,Date.now(),Date.now()).run();}catch{throw new SafeError('Post ID or media already queued; use the status list to check it',409);}return json({queued:true,id:j.id});
  }
  throw new SafeError('Not found',404);
}
export default {async fetch(r,env){try{return await handle(r,env);}catch(e){if(!(e instanceof SafeError))console.error(JSON.stringify({event:'request_failed',path:new URL(r.url).pathname}));return json({error:e instanceof SafeError?e.message:'Request failed; please retry'},e instanceof SafeError?e.status:500);}},async scheduled(event,env,ctx){ctx.waitUntil(tick(env).catch(()=>console.error(JSON.stringify({event:'scheduler_failed'}))));}};
function page(){return new Response(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Acne Medicine · Publishing</title><style>body{font:16px system-ui;background:#f3f6f6;color:#143b3c;margin:0}main{max-width:900px;margin:auto;padding:40px 24px}h1{font-size:38px;letter-spacing:-1px}section{background:white;border:1px solid #d8e4e2;border-radius:18px;padding:24px;margin:20px 0}button{background:#14685f;color:white;border:0;padding:13px 19px;border-radius:8px;cursor:pointer}input,textarea,select{display:block;box-sizing:border-box;width:100%;margin:8px 0 18px;padding:10px;border:1px solid #abc3bf;border-radius:7px;font:inherit}input[type=checkbox]{display:inline;width:auto}code{overflow-wrap:anywhere}small{color:#536b68}#notice{white-space:pre-wrap}li{padding:8px 0}a{color:#14685f}</style><main><small>ROYAL RS · CHANNEL PUBLISHING</small><h1>Acne Medicine Johannesburg</h1><p>Connect once. Queue approved videos. Track verified uploads.</p><p id="notice" role="status">Opening your secure workspace…</p><div id="workspace" hidden><section><h2>1. Connect Google</h2><p id="connection"></p><div id="setup"><p>Create a <strong>Web application</strong> client in <a href="https://console.cloud.google.com/auth/clients?project=globalnewsflix-video" target="_blank" rel="noreferrer">GlobalNewsFlix Video</a>. Add this exact authorised redirect URI:</p><code id="callback"></code><p>Download the new client JSON and select it below. The existing Desktop JSON cannot be used here.</p><label>Web client JSON<input id="config" type="file" accept="application/json,.json"></label><button id="save">Save connection settings</button></div><p><button id="connect">Connect YouTube</button></p><small>Choose ecstacyspiritlifestyle@gmail.com and Acne Medicine Johannesburg. Only the expected channel is accepted.</small></section><section><h2>2. Queue a video</h2><button id="draft">Load prepared first post</button><p>First queue an unlisted connection test. Public posts wait until a test is verified.</p><label>Post ID<input id="postid" placeholder="amj001"></label><label>MP4 file (up to 90 MB)<input id="video" type="file" accept="video/mp4"></label><label>Title<input id="title" maxlength="100"></label><label>Description<textarea id="description" rows="5">We earn a commission if you buy through our link.</textarea></label><label>Post type<select id="kind"><option value="post">Product post</option><option value="test">Connection test</option></select></label><label>Visibility<select id="privacy"><option value="public">Public</option><option value="unlisted">Unlisted</option><option value="private">Private</option></select></label><label><input id="paid" type="checkbox" checked> Paid promotion / commission</label><p><label><input id="synthetic" type="checkbox"> Realistic altered or synthetic content requiring disclosure</label></p><label>Publish after (your local time; blank means next queue run)<input id="due" type="datetime-local"></label><button id="queue">Upload and queue</button></section><section><h2>Publishing status</h2><button id="refresh">Refresh</button><ul id="jobs"></ul><small>The queue runs every five minutes. Interrupted uploads stop for review to prevent duplicates. Uploaded media stays private in Cloudflare.</small></section></div></main><script src="/app.js"></script></html>`,{headers:{...headers,'Content-Type':'text/html;charset=utf-8','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}});}
const APP = `const $=id=>document.getElementById(id);const note=s=>$('notice').textContent=s;async function api(path,body){const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error);return d;}async function refresh(){const s=await api('/status');$('workspace').hidden=false;$('callback').textContent=s.callback;$('connection').textContent=s.connected?'Connected: '+s.channelTitle:s.configured?'Settings saved. Google approval is still required.':'Google Web client setup is required.';$('setup').hidden=s.connected;$('connect').disabled=!s.configured;$('jobs').replaceChildren();for(const j of s.jobs){const li=document.createElement('li');li.textContent=j.id+' — '+j.status+(j.note?' · '+j.note:'');if(j.video_id){const a=document.createElement('a');a.href='https://www.youtube.com/watch?v='+j.video_id;a.textContent=' View video';a.target='_blank';a.rel='noreferrer';li.append(a);}$('jobs').append(li);}}function act(id,fn){$(id).onclick=async()=>{const b=$(id);b.disabled=true;try{await fn();}catch(e){note(e.message);}finally{b.disabled=false;}};}act('draft',async()=>{const j=await api('/draft');$('postid').value=j.id;$('title').value=j.title;$('description').value=j.description;$('privacy').value=j.privacy;$('paid').checked=j.paid_promotion;$('synthetic').checked=j.contains_synthetic_media;note('First-post details loaded. Select the disclosed amj001.mp4 prepared by Claude.');});act('save',async()=>{const f=$('config').files[0];if(!f)throw Error('Select a Web client JSON');await api('/config',JSON.parse(await f.text()));$('config').value='';note('Connection settings saved securely.');await refresh();});act('connect',async()=>{const d=await api('/oauth/start',{});location.assign(d.url);});act('refresh',refresh);act('queue',async()=>{const f=$('video').files[0];if(!f)throw Error('Choose the MP4');if(f.size>94371840)throw Error('Maximum size is 90 MB');note('Uploading video to private storage…');const r=await fetch('/media',{method:'POST',headers:{'Content-Type':'video/mp4'},body:f});const m=await r.json();if(!r.ok)throw Error(m.error);await api('/jobs',{id:$('postid').value.trim(),title:$('title').value,description:$('description').value,media_key:m.media_key,kind:$('kind').value,privacy:$('privacy').value,paid_promotion:$('paid').checked,contains_synthetic_media:$('synthetic').checked,due:$('due').value?new Date($('due').value).toISOString():null});note('Queued. Publishing starts after channel and connection-test checks pass.');await refresh();});(async()=>{try{const fragment=location.hash;history.replaceState(null,'',location.pathname);if(fragment.startsWith('#key='))await api('/session',{key:decodeURIComponent(fragment.slice(5))});await refresh();note('Private publishing workspace.');}catch(e){note(e.message);}})();`;
const launchHandles = {
  'skincare.joburg':'SkincareJoburgRosebank',
  'skincare.durban':'SkincareDurbanWestville',
  'dermatologist.joburg':'DermatologistJoburgMidrand',
  'dermatology.joburg':'DermatologyJoburgBedfordview',
  'dermatology.durban':'DermatologyDurbanUmhlanga',
  'dermatology.capetown':'DermatologyCapeTown'
};
async function launchPage(env) {
  const rows = (await env.DB.prepare('SELECT domain,due,status FROM skincare_launch ORDER BY due').all()).results;
  const entries = rows.filter(x=>Object.hasOwn(launchHandles,x.domain)).map(x=>{
    const time = new Date(x.due).toLocaleString('en-ZA',{timeZone:'Africa/Johannesburg'});
    const action = x.status==='READY' ? '<form method="post" action="/launch/start/'+x.domain+'"><button>Connect @'+launchHandles[x.domain]+' and schedule</button></form>' : '';
    return '<section><h2>'+x.domain+'</h2><p>'+time+' SAST · '+x.status+'</p>'+action+'</section>';
  });
  entries.push(...await launch2Entries(env));
  return new Response('<!doctype html><meta name="viewport" content="width=device-width"><title>Skincare launch schedule</title><style>body{font:16px system-ui;max-width:48rem;margin:3rem auto;padding:1rem;color:#183631}section{border-top:1px solid #ccc;padding:1rem 0}button{padding:.8rem;background:#164e44;color:white;border:0;border-radius:.4rem}</style><h1>Skincare launch schedule</h1><p>Choose the matching YouTube channel at Google to schedule its launch video.</p>'+entries.join(''),{headers:{...headers,'Referrer-Policy':'same-origin','Content-Type':'text/html; charset=utf-8','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://accounts.google.com; frame-ancestors 'none'"}});
}
async function launchStart(env,origin,owner,domain) {
  if (!Object.hasOwn(launchHandles,domain)) throw new SafeError('Unknown channel');
  const row = await env.DB.prepare('SELECT status FROM skincare_launch WHERE domain=?').bind(domain).first();
  if(row?.status!=='READY') throw new SafeError('This launch has already started');
  const c=await readVault(env,'config'), state='launch.'+domain+'.'+random(), verifier=random();
  await env.DB.prepare('INSERT INTO oauth_states(state,owner,verifier,client,expires) VALUES(?,?,?,?,?)').bind(await hash(state),await hash(owner.id),await seal(env,verifier),c.client_id,Date.now()+600000).run();
  const p=new URLSearchParams({client_id:c.client_id,redirect_uri:origin+'/oauth/callback',response_type:'code',scope:SCOPES.join(' '),state,code_challenge:await hash(verifier),code_challenge_method:'S256',access_type:'online',prompt:'select_account consent'});
  return new Response(null,{status:303,headers:{...headers,Location:'https://accounts.google.com/o/oauth2/v2/auth?'+p}});
}
async function scheduleLaunch(env,state,token) {
  const domain=state.slice(7,state.lastIndexOf('.'));
  if(!Object.hasOwn(launchHandles,domain)||!SCOPES.every(s=>(token.scope||'').split(' ').includes(s)))throw new SafeError('Select the requested permissions and try again.');
  const auth={Authorization:'Bearer '+token.access_token};
  const channels=await google('https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',{headers:auth});
  const ch=channels.items?.[0];
  if(channels.items?.length!==1||ch?.snippet?.customUrl?.toLowerCase()!=='@'+launchHandles[domain].toLowerCase())throw new SafeError('Select @'+launchHandles[domain]+' for this launch.');
  const row=await env.DB.prepare('SELECT * FROM skincare_launch WHERE domain=?').bind(domain).first();
  if(!row||row.status!=='READY')throw new SafeError('Already handled; check the launch schedule.');
  if(row.due<Date.now()+300000)throw new SafeError('This slot has passed; select a new future time.');
  const obj=await env.MEDIA.get(row.media_key);
  if(!obj)throw new SafeError('Staged media missing');
  const item=JSON.parse(row.metadata),publishAt=new Date(row.due).toISOString();
  const resource={snippet:{title:item.title,description:item.description,categoryId:'26',defaultLanguage:'en'},status:{privacyStatus:'private',publishAt,selfDeclaredMadeForKids:false},paidProductPlacementDetails:{hasPaidProductPlacement:true}};
  const claim=await env.DB.prepare("UPDATE skincare_launch SET status='UPLOADING' WHERE domain=? AND status='READY'").bind(domain).run();
  if(!claim.meta.changes)throw new SafeError('Already started');
  try {
    const start=await fetch('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,paidProductPlacementDetails',{method:'POST',headers:{...auth,'Content-Type':'application/json','X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':String(obj.size)},body:JSON.stringify(resource),redirect:'manual'});
    if(!start.ok)throw new SafeError('YouTube upload setup failed (HTTP '+start.status+')');
    const dest=new URL(start.headers.get('location'));if(dest.origin!=='https://www.googleapis.com')throw new SafeError('Unexpected upload destination');
    const v=await google(dest.href,{method:'PUT',headers:{'Content-Type':'video/mp4','Content-Length':String(obj.size)},body:obj.body});
    if(!/^[\w-]{11}$/.test(v.id))throw new SafeError('Missing video ID');
    await env.DB.prepare('UPDATE skincare_launch SET video_id=? WHERE domain=?').bind(v.id,domain).run();
    const data=await google('https://www.googleapis.com/youtube/v3/videos?part=snippet,status,paidProductPlacementDetails&id='+v.id,{headers:auth});
    const itemRead=data.items?.[0];
    if(itemRead?.snippet.channelId!==ch.id||Date.parse(itemRead?.status.publishAt)!==row.due||itemRead?.status.privacyStatus!=='private'||itemRead?.paidProductPlacementDetails?.hasPaidProductPlacement!==true)throw new SafeError('Review scheduling details in YouTube Studio.');
    await env.DB.prepare("UPDATE skincare_launch SET status='SCHEDULED' WHERE domain=?").bind(domain).run();
  } catch(e) {await env.DB.prepare("UPDATE skincare_launch SET status='REVIEW' WHERE domain=?").bind(domain).run();throw e;}
  return new Response(null,{status:303,headers:{...headers,Location:'/launch'}});
}

// ---- Launch v2 (7 Nov 2026): one regular video + one Short per skincare channel, staged on the media branch under
// skincare-launch/v2/. Rows live in skincare_launch_v2 (one per video). One Google consent per channel schedules both
// of its rows: the worker fetches each MP4 and thumbnail from GitHub, checks the SHA-256 from the row, uploads it
// private with publishAt = due, sets the thumbnail, then reads the video back. Nothing is retried automatically.
const RAW = 'https://raw.githubusercontent.com/ramatladi/videosyndication/media/';
const hexOf = buf => [...new Uint8Array(buf)].map(b=>b.toString(16).padStart(2,'0')).join('');
async function rawGet(path, sha, max) {
  if (!/^skincare-launch\/v2\/[a-z.]+\/[a-z0-9-]+\.(mp4|jpg)$/.test(path)) throw new SafeError('Unexpected media path');
  const r = await fetch(RAW + path, {redirect:'manual', signal:AbortSignal.timeout(60000)});
  if (!r.ok) throw new SafeError('Staged file missing (HTTP '+r.status+')');
  const buf = await r.arrayBuffer();
  if (buf.byteLength < 1000 || buf.byteLength > max) throw new SafeError('Staged file size out of range');
  if (hexOf(await crypto.subtle.digest('SHA-256', buf)) !== sha) throw new SafeError('Staged file failed its SHA-256 check');
  return buf;
}
async function launch2Entries(env) {
  let rows;
  try { rows = (await env.DB.prepare('SELECT domain,format,due,status,video_id FROM skincare_launch_v2 ORDER BY domain,due').all()).results; }
  catch { return []; }
  const by = {};
  for (const x of rows) if (Object.hasOwn(launchHandles,x.domain)) (by[x.domain] ||= []).push(x);
  return Object.entries(by).map(([domain,list]) => {
    const lines = list.map(x => x.format+' · '+(x.due===0?'Immediate release':new Date(x.due).toLocaleString('en-ZA',{timeZone:'Africa/Johannesburg'})+' SAST')+' · '+x.status).join('<br>');
    const ready = list.some(x => x.status==='READY');
    const action = ready ? '<form method="post" action="/launch/v2/start/'+domain+'"><button>Connect @'+launchHandles[domain]+(list.every(x=>x.due===0)?' and publish now':' and schedule its video + Short')+'</button></form>' : '';
    return '<section><h2>'+domain+' · launch v2</h2><p>'+lines+'</p>'+action+'</section>';
  });
}
async function launch2Start(env,origin,owner,domain) {
  if (!Object.hasOwn(launchHandles,domain)) throw new SafeError('Unknown channel');
  const row = await env.DB.prepare("SELECT 1 FROM skincare_launch_v2 WHERE domain=? AND status='READY' LIMIT 1").bind(domain).first();
  if (!row) throw new SafeError('Nothing ready for this channel');
  const c=await readVault(env,'config'), state='launch2.'+domain+'.'+random(), verifier=random();
  await env.DB.prepare('INSERT INTO oauth_states(state,owner,verifier,client,expires) VALUES(?,?,?,?,?)').bind(await hash(state),await hash(owner.id),await seal(env,verifier),c.client_id,Date.now()+600000).run();
  const p=new URLSearchParams({client_id:c.client_id,redirect_uri:origin+'/oauth/callback',response_type:'code',scope:SCOPES.join(' '),state,code_challenge:await hash(verifier),code_challenge_method:'S256',access_type:'online',prompt:'select_account consent'});
  return new Response(null,{status:303,headers:{...headers,Location:'https://accounts.google.com/o/oauth2/v2/auth?'+p}});
}
export function launch2Resource(item, due) {
  if (typeof item.title!=='string'||!item.title.trim()||item.title.length>100||/[<>]/.test(item.title)) throw new SafeError('Bad title');
  if (typeof item.description!=='string'||!/earn a commission/i.test(item.description)||new TextEncoder().encode(item.description).length>5000) throw new SafeError('Bad description');
  const tags = Array.isArray(item.tags) ? item.tags.filter(t=>typeof t==='string') : [];
  if (tags.join(',').length > 500) throw new SafeError('Too many tags');
  return {snippet:{title:item.title,description:item.description,tags,categoryId:'26',defaultLanguage:'en',defaultAudioLanguage:'en'},
          status:{...(due===0?{privacyStatus:'public'}:{privacyStatus:'private',publishAt:new Date(due).toISOString()}),selfDeclaredMadeForKids:false,containsSyntheticMedia:false},
          paidProductPlacementDetails:{hasPaidProductPlacement:true}};
}
async function scheduleLaunch2(env,state,token) {
  const domain=state.slice(8,state.lastIndexOf('.'));
  if(!Object.hasOwn(launchHandles,domain)||!SCOPES.every(s=>(token.scope||'').split(' ').includes(s)))throw new SafeError('Select the requested permissions and try again.');
  const auth={Authorization:'Bearer '+token.access_token};
  const channels=await google('https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',{headers:auth});
  const ch=channels.items?.[0];
  if(channels.items?.length!==1||ch?.snippet?.customUrl?.toLowerCase()!=='@'+launchHandles[domain].toLowerCase())throw new SafeError('Select @'+launchHandles[domain]+' for this launch.');
  const rows=(await env.DB.prepare("SELECT * FROM skincare_launch_v2 WHERE domain=? AND status='READY' ORDER BY due").bind(domain).all()).results;
  for (const row of rows) {
    if(row.due!==0 && row.due<Date.now()+600000){await env.DB.prepare("UPDATE skincare_launch_v2 SET status='REVIEW',note='Slot passed; set a new future due time' WHERE id=?").bind(row.id).run();continue;}
    const claim=await env.DB.prepare("UPDATE skincare_launch_v2 SET status='UPLOADING' WHERE id=? AND status='READY'").bind(row.id).run();
    if(!claim.meta.changes)continue;
    try {
      const item=JSON.parse(row.metadata), resource=launch2Resource(item,row.due);
      const video=await rawGet(row.media_path,row.sha256,MAX_MEDIA);
      const jpg=await rawGet(row.thumbnail_path,row.thumbnail_sha256,2*1024*1024);
      const start=await fetch('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,paidProductPlacementDetails',{method:'POST',headers:{...auth,'Content-Type':'application/json','X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':String(video.byteLength)},body:JSON.stringify(resource),redirect:'manual',signal:AbortSignal.timeout(30000)});
      if(!start.ok)throw new SafeError('YouTube upload setup failed (HTTP '+start.status+')');
      const dest=new URL(start.headers.get('location')||'https://invalid');if(dest.origin!=='https://www.googleapis.com')throw new SafeError('Unexpected upload destination');
      const v=await google(dest.href,{method:'PUT',headers:{'Content-Type':'video/mp4','Content-Length':String(video.byteLength)},body:video});
      if(!/^[\w-]{11}$/.test(v.id))throw new SafeError('Missing video ID');
      await env.DB.prepare('UPDATE skincare_launch_v2 SET video_id=? WHERE id=?').bind(v.id,row.id).run();
      let note=null;
      try{
        await google('https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId='+v.id,{method:'POST',headers:{...auth,'Content-Type':'image/jpeg','Content-Length':String(jpg.byteLength)},body:jpg});}
      catch{note='Thumbnail not set; upload it in YouTube Studio';}
      const data=await google('https://www.googleapis.com/youtube/v3/videos?part=snippet,status,paidProductPlacementDetails&id='+v.id,{headers:auth});
      const got=data.items?.[0];
      if(got?.snippet.channelId!==ch.id||(row.due===0 ? got?.status.privacyStatus!=='public' : (Date.parse(got?.status.publishAt)!==row.due||got?.status.privacyStatus!=='private'))||got?.paidProductPlacementDetails?.hasPaidProductPlacement!==true)throw new SafeError('Review scheduling details in YouTube Studio.');
      await env.DB.prepare("UPDATE skincare_launch_v2 SET status=?,note=? WHERE id=?").bind(row.due===0?'PUBLISHED':'SCHEDULED',note,row.id).run();
    } catch(e) {
      await env.DB.prepare("UPDATE skincare_launch_v2 SET status='REVIEW',note=? WHERE id=?").bind(e instanceof SafeError?e.message:'Upload interrupted; check YouTube Studio before retrying',row.id).run();
    }
  }
  return new Response(null,{status:303,headers:{...headers,Location:'/launch'}});
}
