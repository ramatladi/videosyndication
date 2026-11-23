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
- 12 Nov 2026: catalog exhausted for 5 slots (Cape Town 10:00/12:00/18:00, Rosebank 08:00/20:00): every candidate repeated an
  earlier script. Known parser gap: when a listing's body starts with "Usage: ..." before "recommended for:", `parse()` keeps
  only the usage line as the description (pro-collagen banking serum); that item was hand-fixed from its own listing text.
- 15 Nov 2026: 13 and 14 Nov were never staged (only `fetch/` queues on media), so `heal` did not see them; it now lists such
  days as `never_staged` with all 36 slots as gaps. `history()` now counts a heal day's new (not yet staged) picks in the 7-day
  window, so tomorrow's plan can't reuse them on the same channel. Catalog still exhausted under the 0.85 guard: 15 Nov heal
  filled 1 of 17 gaps, 12 Nov heal 0 of 5, 16 Nov only 6 of 36 slots.
- 16 Nov 2026 run (for 17 Nov): fixes in `sk.py`: (1) the 7-day window and the script/visual no-repeat check now look both ways
  (a heal day may not reuse a product or script from a *later* day); (2) a Short whose repeated description was dropped and
  that is left with only the cover and end card is rejected (it "passed" the overlap guard at 0.0 with no content);
  (3) `parse()` drops sentences with percentages or clinical-study/consumer-perception wording from descriptions and
  benefits, and skips a leading "Usage: ..." line before "recommended for:". Placeholder dry-run of `write` across all
  heal days and 17 Nov: the catalog is exhausted under the 0.85 guard (17 Nov: 3 of 36; heals: 15 Nov 1, others 0).
  Daily milkfoliant 13g dropped: its store packshot carries a beauty-award badge.
- 23 Nov 2026 run (for 24 Nov): the regular-video title template "Dermalogica {N} Review: {T}, How to Use It" became
  "Dermalogica {N}: {T}, and How to Use It" (no "review" framing; the rules exclude review claims). Store packshots with an
  award badge (daily microfoliant 111429, liquid peelfoliant 111461, special cleansing gel 110639) were banned for the day
  and replanned. Heal backlog at the start: 328 slots over 12-22 Nov (13 never-staged days); one run renders about 70-80
  items in its 3 hours, so heals go oldest day first after tomorrow's 36.
