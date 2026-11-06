import assert from 'node:assert/strict';
import {webcrypto,timingSafeEqual} from 'node:crypto';
import worker,{seal,unseal,validateConfig,validateJob,tick} from './worker.mjs';
Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
crypto.subtle.timingSafeEqual=(a,b)=>timingSafeEqual(Buffer.from(a),Buffer.from(b));
const env={VAULT_KEY:Buffer.alloc(32,7).toString('base64url'),ADMIN_TOKEN:'test-admin-token'};
let checks=0;
const check=(fn)=>{fn();checks++;};
const encrypted=await seal(env,{refresh_token:'sensitive-test-value'});
check(()=>assert.ok(!encrypted.includes('sensitive-test-value')));
assert.deepEqual(await unseal(env,encrypted),{refresh_token:'sensitive-test-value'});checks++;
await assert.rejects(()=>unseal({...env,VAULT_KEY:Buffer.alloc(32,8).toString('base64url')},encrypted));checks++;
const origin='https://unit.example';
const web={web:{project_id:'globalnewsflix-video',client_id:'unit.apps.googleusercontent.com',client_secret:'secret',redirect_uris:[origin+'/oauth/callback']}};
check(()=>assert.equal(validateConfig(web,origin).client_id,web.web.client_id));
check(()=>assert.throws(()=>validateConfig({installed:{}},origin),/Desktop/));
check(()=>assert.throws(()=>validateConfig({web:{...web.web,redirect_uris:['http://localhost']}},origin),/exact callback/));
check(()=>assert.throws(()=>validateConfig({web:{...web.web,project_id:'other'}},origin),/globalnewsflix/));
const job={id:'amj001',title:'Product facts',description:'We earn a commission if you buy through our link.',privacy:'public',paid_promotion:true,contains_synthetic_media:false};
check(()=>assert.equal(validateJob(job).id,'amj001'));
check(()=>assert.throws(()=>validateJob({...job,description:'No disclosure'}),/disclosure/));
check(()=>assert.throws(()=>validateJob({...job,id:'../other'}),/Invalid post/));
check(()=>assert.throws(()=>validateJob({...job,privacy:'typo'}),/visibility/));
check(()=>assert.throws(()=>validateJob({...job,paid_promotion:undefined}),/flags/));
let res=await worker.fetch(new Request(origin+'/config',{method:'POST',headers:{Origin:'https://evil.example'},body:'{}'}),env);
check(()=>assert.equal(res.status,403));
res=await worker.fetch(new Request(origin+'/status'),env);check(()=>assert.equal(res.status,401));
res=await worker.fetch(new Request(origin+'/session',{method:'POST',headers:{Origin:origin},body:JSON.stringify({key:'wrong'})}),env);check(()=>assert.equal(res.status,401));
res=await worker.fetch(new Request(origin+'/session',{method:'POST',headers:{Origin:origin},body:JSON.stringify({key:env.ADMIN_TOKEN})}),env);
check(()=>assert.equal(res.status,200));
check(()=>assert.match(res.headers.get('set-cookie'),/HttpOnly; Secure; SameSite=Lax/));
const authCookie=res.headers.get('set-cookie').split(';')[0];
let consumed=0;
const callbackEnv={...env,DB:{prepare(sql){return{bind(){return this;},async first(){consumed++;return null;}};}}};
res=await worker.fetch(new Request(origin+'/oauth/callback?state=replayed&code=not-logged',{headers:{Cookie:authCookie}}),callbackEnv);
check(()=>assert.equal(res.status,403));check(()=>assert.equal(consumed,1));
// No refresh token means cron must not make a Google request or claim a post.
const oldFetch=globalThis.fetch;globalThis.fetch=()=>{throw new Error('unexpected network');};
await tick({...env,DB:{prepare(sql){return{bind(){return this;},async run(){return{};},async first(){return null;}};}}});checks++;
globalThis.fetch=oldFetch;
// Wrong-channel consent must never write a token to the vault.
let vaultWrites=0;
const configCipher=await seal(env,{client_id:'unit.apps.googleusercontent.com',client_secret:'unit-secret'});
const verifierCipher=await seal(env,'pkce-verifier');
const wrongEnv={...env,DB:{prepare(sql){return{bind(){return this;},async first(){if(sql.startsWith('DELETE'))return{client:'unit.apps.googleusercontent.com',verifier:verifierCipher};if(sql.startsWith('SELECT'))return{value:configCipher};throw Error('Unexpected SQL');},async run(){vaultWrites++;}};}}};
globalThis.fetch=async url=>Response.json(url.includes('/token')?{access_token:'test-access',refresh_token:'test-refresh',scope:'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'}:{items:[{id:'WRONG_CHANNEL',snippet:{title:'Other channel'}}]});
res=await worker.fetch(new Request(origin+'/oauth/callback?state=fresh&code=one-use',{headers:{Cookie:authCookie}}),wrongEnv);
check(()=>assert.equal(res.status,403));check(()=>assert.equal(vaultWrites,0));
globalThis.fetch=oldFetch;
console.log(`${checks} checks passed`);

{
  const { launch2Resource } = await import('./worker.mjs');
  const r = launch2Resource({ title: 'Dermalogica calm water gel #shorts', description: 'x\n\nWe earn a commission if you buy through our link.', tags: ['a', 'b'] }, Date.parse('2026-11-07T10:00:00Z'));
  check(() => { assert.equal(r.status.privacyStatus, 'private'); assert.equal(r.status.publishAt, '2026-11-07T10:00:00.000Z');
    assert.equal(r.status.containsSyntheticMedia, false); assert.equal(r.paidProductPlacementDetails.hasPaidProductPlacement, true); });
  check(() => assert.throws(() => launch2Resource({ title: 't', description: 'no disclosure' }, 0)));
  console.log('launch v2 checks passed');
}
