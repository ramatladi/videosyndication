# skincare-daily

Daily production for the six skincare channels. Read `DAILY_TASK.md`; the code is `sk.py`.

## Catalog snapshot JS (run in the built-in browser on https://dermalogica.co.za/collections/all)

```js
let all=[];for(let p=1;p<6;p++){const r=await fetch('/products.json?limit=250&page='+p).then(r=>r.json());if(!r.products.length)break;all=all.concat(r.products)}
const out=[];async function one(p){try{const html=await fetch('/products/'+p.handle).then(r=>r.text());const d=new DOMParser().parseFromString(html,'text/html');d.querySelectorAll('script,style,header,footer,nav').forEach(e=>e.remove());let t=(d.querySelector('main')||d.body).innerText.replace(/\s+/g,' ');
out.push({handle:p.handle,title:p.title,type:p.product_type,tags:p.tags,variants:p.variants.map(v=>({id:v.id,title:v.title,sku:v.sku,available:v.available,price:v.price,img:v.featured_image&&v.featured_image.src})),images:p.images.map(i=>({src:i.src,w:i.width,h:i.height,variant_ids:i.variant_ids})),body:p.body_html.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(),text:t.slice(0,6000)})}catch(e){out.push({handle:p.handle,error:String(e)})}}
for(let i=0;i<all.length;i+=8){await Promise.all(all.slice(i,i+8).map(one))}
const blob=new Blob([JSON.stringify({fetched:new Date().toISOString(),products:out})],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='catalog.json';document.body.appendChild(a);a.click();a.remove();
out.length+' products'
```

## History
- 7 Nov: launch (12 items, `skincare-launch/v2.1`). 8-9 Nov: hand-written batches. 10-11 Nov onward: `sk.py`.
- 11 Nov 2026: fallback tiers + rolling 7-day window, kit-contents check, self-healing ledger, Downloads clean-up (Sello).
