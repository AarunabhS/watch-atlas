/* Remote images only. Original-resolution requests happen when the viewer opens. */
(function(root){
'use strict';
const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=u=>{try{const url=new URL(u);return url.protocol==='https:'?url.href:'';}catch{return '';}};
function higherResolutionUrl(src){
 try{
  const u=new URL(src);if(u.protocol!=='https:'||u.username||u.password||u.port)return '';
  const iwc=/^\/(?:product-card-3|product-slideshow-1)\/(?:o-dpr-2\/)?([a-f0-9]{40}\.(?:jpg|png|webp))$/i;
  const jlc=/^\/(?:product-grid-hero-4|product-card-3)\/(?:o-dpr-2\/)?([a-f0-9]{40}\.(?:jpg|png|webp))$/i;
  if(u.hostname==='www.breguet.com'&&u.pathname.startsWith('/sites/default/files/')&&/^Resize,height=\d+$/.test(u.searchParams.get('im')||'')&&Number((u.searchParams.get('im')||'').split('=')[1])<2400)u.searchParams.set('im','Resize,height=2400');
  else if(u.hostname==='www.omegawatches.com'&&u.pathname.startsWith('/media/catalog/product/')&&/^\d+$/.test(u.searchParams.get('w')||'')&&Number(u.searchParams.get('w'))<2000)u.searchParams.set('w','2000');
  else if(u.hostname==='img.iwc.com'&&iwc.test(u.pathname))u.pathname='/product-slideshow-2xl-1/o-dpr-2/'+u.pathname.match(iwc)[1];
  else if(u.hostname==='img.jaeger-lecoultre.com'&&jlc.test(u.pathname))u.pathname='/product-grid-hero-xl-4/o-dpr-2/'+u.pathname.match(jlc)[1];
  else return '';
  return u.href===src?'':u.href;
 }catch{return '';}
}
function canUpgrade(src,candidate,w,h,ow,oh){
 if(!candidate||candidate!==higherResolutionUrl(src)||![w,h,ow,oh].every(n=>Number.isFinite(n)&&n>0)||ow<=w||oh<=h)return false;
 // These official presets change canvas padding while retaining the exact asset hash.
 const host=new URL(src).hostname;
 return ['img.iwc.com','img.jaeger-lecoultre.com'].includes(host)||Math.abs((ow/oh)/(w/h)-1)<.02;
}
function fit(width,height,viewportWidth,viewportHeight){const ratio=Math.min(Math.max(1,viewportWidth-48)/width,Math.max(1,viewportHeight-48)/height);return {width:width*ratio,height:height*ratio};}
function clampPan(x,y,width,height,viewportWidth,viewportHeight,scale){const bx=Math.max(0,(width*scale-viewportWidth)/2),by=Math.max(0,(height*scale-viewportHeight)/2);return {x:Math.max(-bx,Math.min(bx,x))||0,y:Math.max(-by,Math.min(by,y))||0};}
function zoomAt(scale,next,x,y,anchorX,anchorY){return {x:anchorX-(anchorX-x)*next/scale,y:anchorY-(anchorY-y)*next/scale};}
const api={higherResolutionUrl,canUpgrade,fit,clampPan,zoomAt};
if(typeof module==='object'&&module.exports)module.exports=api;
if(!root.document)return;
let dialog,stage,img,zoomLabel,status,sourceLink,recordLabel,opener,resizeObserver;
let scale=1,x=0,y=0,width=0,height=0,naturalWidth=0,naturalHeight=0,sequence=0,ready=false,previousTouch=null,lastTouchAt=0,dragged=false;
const pointers=new Map(),pending=new Set();
function teardown(){
 if(dialog.open||!document.documentElement.classList.contains('image-viewer-open'))return;
 sequence++;for(const cancel of [...pending])cancel();pointers.clear();previousTouch=null;document.documentElement.classList.remove('image-viewer-open');img.removeAttribute('src');img.hidden=true;opener?.isConnected&&opener.focus({preventScroll:true});
}
const close=()=>{dialog.close();teardown();};
function paint(){
 const bounds=clampPan(x,y,width,height,stage.clientWidth,stage.clientHeight,scale);x=bounds.x;y=bounds.y;
 img.style.width=width+'px';img.style.height=height+'px';img.style.transform=`translate(${x}px, ${y}px) scale(${scale})`;
 zoomLabel.textContent=Math.round(scale*100)+'%';dialog.querySelector('[data-image-out]').disabled=!ready||scale<=1;dialog.querySelector('[data-image-in]').disabled=!ready||scale>=6;
 dialog.querySelector('[data-image-fit]').disabled=!ready;stage.classList.toggle('is-zoomed',scale>1);stage.classList.toggle('is-dragging',pointers.size>0);
}
function resize(){if(!ready)return;({width,height}=fit(naturalWidth,naturalHeight,stage.clientWidth,stage.clientHeight));paint();}
function reset(){scale=1;x=y=0;paint();}
function zoom(next,anchorX=0,anchorY=0){if(!ready)return;next=Math.max(1,Math.min(6,next));({x,y}=zoomAt(scale,next,x,y,anchorX,anchorY));scale=next;paint();}
function localPoint(e){const b=stage.getBoundingClientRect();return {x:e.clientX-b.left-b.width/2,y:e.clientY-b.top-b.height/2};}
function gesture(){const p=[...pointers.values()];if(p.length>=2)return {x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2,distance:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)};return p[0]||null;}
function initialize(){
 if(dialog)return;
 dialog=document.createElement('dialog');dialog.id='image-viewer';dialog.className='image-viewer';dialog.setAttribute('aria-labelledby','image-viewer-title');dialog.setAttribute('aria-describedby','image-viewer-help');
 dialog.innerHTML=`<div class="image-viewer-shell"><header class="image-viewer-header"><div><p class="eyebrow">A CLOSER LOOK</p><h2 id="image-viewer-title"></h2><p class="image-viewer-reference"></p></div><button class="image-viewer-close" aria-label="Close image viewer" autofocus>×</button></header><div class="image-viewer-stage" tabindex="0" role="region" aria-label="Watch image; zoom and pan"><img class="image-viewer-image" alt="" draggable="false" referrerpolicy="no-referrer" hidden><p class="image-viewer-status" role="status" aria-live="polite"></p></div><footer class="image-viewer-footer"><div class="image-viewer-controls" role="group" aria-label="Image zoom controls"><button data-image-out aria-label="Zoom out">−</button><output aria-label="Zoom level">100%</output><button data-image-in aria-label="Zoom in">+</button><button data-image-fit>Fit image</button></div><p id="image-viewer-help">Scroll or pinch to zoom · Drag to explore · Double-tap to zoom</p><a class="image-viewer-source" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">Open source image ↗</a></footer></div>`;
 document.body.append(dialog);stage=dialog.querySelector('.image-viewer-stage');img=stage.querySelector('img');status=stage.querySelector('[role="status"]');zoomLabel=dialog.querySelector('output');sourceLink=dialog.querySelector('a');recordLabel=dialog.querySelector('.image-viewer-reference');
 dialog.querySelector('.image-viewer-close').onclick=close;
 dialog.querySelector('[data-image-in]').onclick=()=>zoom(scale*1.5);
 dialog.querySelector('[data-image-out]').onclick=()=>zoom(scale/1.5);
 dialog.querySelector('[data-image-fit]').onclick=reset;
 dialog.addEventListener('close',teardown);
 dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
 dialog.addEventListener('keydown',e=>{
  if(e.key==='Escape')return;let handled=true;
  if(['+','='].includes(e.key))zoom(scale*1.5);else if(e.key==='-')zoom(scale/1.5);else if(['0','Home'].includes(e.key))reset();
  else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)&&ready){x+=e.key==='ArrowLeft'?60:e.key==='ArrowRight'?-60:0;y+=e.key==='ArrowUp'?60:e.key==='ArrowDown'?-60:0;paint();}else handled=false;
  if(handled)e.preventDefault();
 });
 stage.addEventListener('wheel',e=>{if(!ready)return;e.preventDefault();const p=localPoint(e);const delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?stage.clientHeight:1);zoom(scale*Math.exp(-Math.max(-200,Math.min(200,delta))*.003),p.x,p.y);},{passive:false});
 stage.addEventListener('dblclick',e=>{if(Date.now()-lastTouchAt<600)return;const p=localPoint(e);if(scale>1)reset();else zoom(2.5,p.x,p.y);});
 stage.addEventListener('pointerdown',e=>{if(!ready||e.button!==0)return;stage.setPointerCapture(e.pointerId);const p=localPoint(e);pointers.set(e.pointerId,{...p,startX:p.x,startY:p.y});if(pointers.size>1){previousTouch=null;dragged=true;}else dragged=false;paint();});
 stage.addEventListener('pointermove',e=>{
  if(!pointers.has(e.pointerId))return;const before=gesture();const p=localPoint(e),old=pointers.get(e.pointerId);if(Math.hypot(p.x-old.startX,p.y-old.startY)>3)dragged=true;pointers.set(e.pointerId,{...p,startX:old.startX,startY:old.startY});const after=gesture();
  x+=after.x-before.x;y+=after.y-before.y;
  if(pointers.size>=2&&before.distance>0)zoom(scale*after.distance/before.distance,after.x,after.y);else paint();
 });
 const end=e=>{if(!pointers.has(e.pointerId))return;const p=pointers.get(e.pointerId);const tap=e.type==='pointerup'&&e.pointerType==='touch'&&!dragged&&pointers.size===1;
  if(e.pointerType==='touch')lastTouchAt=Date.now();
  if(tap){const now=Date.now();if(previousTouch&&now-previousTouch.time<320&&Math.hypot(p.x-previousTouch.x,p.y-previousTouch.y)<30){if(scale>1)reset();else zoom(2.5,p.x,p.y);previousTouch=null;}else previousTouch={...p,time:now};}else previousTouch=null;
  pointers.delete(e.pointerId);paint();};
 for(const event of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(event,end);
 resizeObserver=new ResizeObserver(resize);resizeObserver.observe(stage);
}
function load(src,ticket,done,fail){
 const probe=new Image();probe.referrerPolicy='no-referrer';let timer;
 const cancel=()=>{clearTimeout(timer);probe.onload=probe.onerror=null;pending.delete(cancel);probe.removeAttribute('src');};pending.add(cancel);
 probe.onload=()=>{const w=probe.naturalWidth,h=probe.naturalHeight;cancel();if(ticket===sequence&&dialog.open&&w&&h)done(w,h);};
 probe.onerror=()=>{cancel();if(ticket===sequence&&dialog.open)fail();};timer=setTimeout(()=>{cancel();if(ticket===sequence&&dialog.open)fail();},20000);probe.src=src;
}
function open(r,trigger){
 const src=safe(r.image_url);if(!src)return;initialize();opener=trigger||document.activeElement;for(const cancel of [...pending])cancel();const ticket=++sequence;ready=false;scale=1;x=y=0;naturalWidth=naturalHeight=0;pointers.clear();previousTouch=null;
 dialog.querySelector('h2').textContent=[r.brand,r.specific_model].filter(Boolean).join(' · ');recordLabel.textContent=r.reference_number||'';
 img.alt=[r.brand,r.specific_model,r.reference_number].filter(Boolean).join(' ');img.hidden=true;status.hidden=false;status.textContent='Loading watch image…';sourceLink.href=src;sourceLink.textContent='Open source image ↗';document.documentElement.classList.add('image-viewer-open');if(!dialog.open)dialog.showModal();paint();
 const show=(url,w,h)=>{naturalWidth=w;naturalHeight=h;img.src=url;img.hidden=false;status.hidden=true;ready=true;sourceLink.href=url;sourceLink.textContent=`Open source image ↗ · ${w.toLocaleString()} × ${h.toLocaleString()} px`;resize();};
 load(src,ticket,(w,h)=>{show(src,w,h);const original=higherResolutionUrl(src);if(original)load(original,ticket,(ow,oh)=>{if(canUpgrade(src,original,w,h,ow,oh))show(original,ow,oh);},()=>{});},()=>{status.textContent='This watch image could not load. You can try opening the source image.';});
}
function detail(r,visual){return safe(r.image_url)?`<button class="watch-image-trigger" type="button" aria-label="Enlarge image of ${escape([r.brand,r.specific_model,r.reference_number].filter(Boolean).join(' '))}">${visual}<span class="watch-image-hint"><span aria-hidden="true">⤢</span> Enlarge image</span></button>`:visual;}
function bindDetail(r){const trigger=document.querySelector('#detail .watch-image-trigger');if(!trigger)return;trigger.onclick=()=>open(r,trigger);const preview=trigger.querySelector('img');const unavailable=()=>{trigger.disabled=true;trigger.querySelector('.watch-image-hint').textContent='Image unavailable';};if(preview){preview.addEventListener('error',unavailable,{once:true});if(preview.complete&&!preview.naturalWidth)unavailable();}else unavailable();}
root.AtlasImages={...api,open,detail,bindDetail};
})(globalThis);
