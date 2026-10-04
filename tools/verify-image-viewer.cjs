/* Optional browser QA: ATLAS_PLAYWRIGHT=/path/to/playwright node tools/verify-image-viewer.cjs [preview URL] */
const {chromium}=require(process.env.ATLAS_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const records=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/data.json'))).records;
const watch=records.find(r=>r.brand==='Breguet'&&r.image_url.includes('height=752'));
const reportDir=process.env.ATLAS_VIEWER_REPORTS||path.join(require('node:os').tmpdir(),'watch-atlas-viewer-qa');fs.mkdirSync(reportDir,{recursive:true});
const fixture=(w,h)=>`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 526 752"><rect x="205" y="8" width="116" height="736" rx="20" fill="#8f7050"/><circle cx="263" cy="376" r="180" fill="#cbbba0"/><circle cx="263" cy="376" r="166" fill="#e9e3d7"/><circle cx="263" cy="376" r="130" fill="none" stroke="#9c8b70" stroke-width="3"/><path d="M263 260V376L338 400" fill="none" stroke="#233651" stroke-width="8"/><text x="263" y="325" text-anchor="middle" font-size="22" fill="#333">BREGUET</text></svg>`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.ATLAS_CHROMIUM||chromium.executablePath()});
 try{
  for(const mobile of [false,true]){
   const context=await browser.newContext(mobile?{viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3}:{viewport:{width:1440,height:1000}});
   const page=await context.newPage(),errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
   let mode='success',release;
   await page.route('**/*',async route=>{
    const req=route.request(),url=req.url();if(url.startsWith('http://127.0.0.1:'))return route.continue();
    if(url.startsWith(watch.image_url.split('?')[0])){
     requests.push(url);const hq=!url.includes('height=752');
     if(hq&&mode==='failure')return route.abort();
     if(hq&&mode==='delayed')await new Promise(resolve=>release=resolve);
     return route.fulfill({contentType:'image/svg+xml',body:fixture(hq?2688:526,hq?3840:752)});
    }
    return route.abort();
   });
   await page.goto(process.argv[2]||'http://127.0.0.1:8790/');await page.waitForFunction(()=>document.querySelector('.atlas-hero'));
   await page.evaluate(async id=>{await ensureCatalog();await openRecord(id);},watch.id);
   const trigger=page.getByRole('button',{name:/Enlarge image of/});await trigger.waitFor();
   assert.equal(requests.filter(u=>!u.includes('height=752')).length,0,'HQ must not load before viewer opens');
   await trigger.click();await page.waitForFunction(()=>document.querySelector('.image-viewer-source')?.textContent.includes('3,840'));
   assert(await page.locator('#image-viewer').evaluate(e=>e.open));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'no horizontal page overflow');
   await page.getByRole('button',{name:'Zoom in',exact:true}).click();assert.equal(await page.locator('#image-viewer output').textContent(),'150%');
   await page.getByRole('button',{name:'Fit image',exact:true}).click();assert.equal(await page.locator('#image-viewer output').textContent(),'100%');
   const stage=page.locator('.image-viewer-stage'),b=await stage.boundingBox();
   if(!mobile){
    await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.wheel(0,-180);assert(Number.parseInt(await page.locator('#image-viewer output').textContent())>100);
    await stage.press('+');await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2+65,b.y+b.height/2+50,{steps:5});await page.mouse.up();
    assert(!await page.locator('.image-viewer-image').evaluate(e=>e.style.transform.startsWith('translate(0px, 0px)')));
    await stage.press('0');assert.equal(await page.locator('#image-viewer output').textContent(),'100%');
    await stage.dblclick();assert.equal(await page.locator('#image-viewer output').textContent(),'250%');
   }else{
    const cdp=await context.newCDPSession(page);
    const touch=(type,points)=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(([x,y,id])=>({x,y,id,radiusX:5,radiusY:5}))});
    const cx=b.x+b.width/2,cy=b.y+b.height/2;
    await touch('touchStart',[[cx-30,cy,1],[cx+30,cy,2]]);await touch('touchMove',[[cx-80,cy,1],[cx+80,cy,2]]);await touch('touchEnd',[]);
    assert(Number.parseInt(await page.locator('#image-viewer output').textContent())>150,'touch pinch zooms');
    await page.getByRole('button',{name:'Fit image',exact:true}).click();
    await page.touchscreen.tap(cx,cy);await page.touchscreen.tap(cx,cy);assert.equal(await page.locator('#image-viewer output').textContent(),'250%','double tap zooms');
    await touch('touchStart',[[cx,cy,1]]);await touch('touchMove',[[cx+45,cy+60,1]]);await touch('touchEnd',[]);assert(!await page.locator('.image-viewer-image').evaluate(e=>e.style.transform.startsWith('translate(0px, 0px)')),'touch drag pans a zoomed image');
   }
   await page.screenshot({path:path.join(reportDir,`image-viewer-${mobile?'mobile':'desktop'}-fixture.png`)});
   await page.keyboard.press('Escape');assert.equal(await page.locator('#image-viewer').evaluate(e=>e.open),false);assert.equal(await page.locator('#detail').evaluate(e=>e.open),true);
   assert.equal(await trigger.evaluate(e=>e===document.activeElement),true,'focus returns to image trigger');
   mode='failure';await page.evaluate(r=>AtlasImages.open(r,document.querySelector('.watch-image-trigger')),{...watch,image_url:watch.image_url+'&qa=failure'});await page.waitForFunction(()=>document.querySelector('.image-viewer-source')?.textContent.includes('752 px'));await page.waitForTimeout(100);assert.equal(await page.locator('.image-viewer-image').evaluate(e=>e.naturalHeight),752,'HQ failure keeps original');await page.getByRole('button',{name:'Close image viewer'}).click();
   mode='delayed';await page.evaluate(r=>AtlasImages.open(r,document.querySelector('.watch-image-trigger')),{...watch,image_url:watch.image_url+'&qa=delayed'});await page.waitForFunction(()=>document.querySelector('.image-viewer-source')?.textContent.includes('752 px'));await page.waitForTimeout(100);await page.getByRole('button',{name:'Close image viewer'}).click();
   const noImage={brand:'Test',specific_model:'Missing source',reference_number:'MISSING',image_url:'https://example.com/missing.png'};await page.evaluate(r=>AtlasImages.open(r),noImage);release?.();await page.waitForFunction(()=>document.querySelector('.image-viewer-status')?.textContent.includes('could not load'));
   assert.equal(await page.locator('.image-viewer-image').isVisible(),false,'late HQ from prior watch cannot replace a new watch');assert(await page.getByRole('button',{name:'Zoom in',exact:true}).isDisabled());await page.keyboard.press('Escape');
   assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('image-viewer-open')),false);assert.deepEqual(errors,[]);
   console.log(`${mobile?'Mobile':'Desktop'}: zoom, pan/gestures, fit, focus, Escape, HQ loading/fallback, stale load, missing image and overflow passed.`);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
