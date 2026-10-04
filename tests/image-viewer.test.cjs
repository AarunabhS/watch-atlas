'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {higherResolutionUrl,canUpgrade,fit,clampPan,zoomAt}=require('../dist/image-viewer.js');
test('only verified Breguet resize URLs can request a larger copy of the same asset',()=>{
 assert.equal(higherResolutionUrl('https://www.breguet.com/sites/default/files/2026-03/watch.png?im=Resize,height=752'),'https://www.breguet.com/sites/default/files/2026-03/watch.png?im=Resize%2Cheight%3D2400');
 for(const src of ['javascript:alert(1)','http://www.breguet.com/sites/default/files/watch.png?im=Resize,height=752','https://example.com/sites/default/files/watch.png?im=Resize,height=752','https://www.breguet.com/sites/default/files/watch.png','https://www.breguet.com/sites/default/files/watch.png?im=Crop,width=500'])assert.equal(higherResolutionUrl(src),'');
});
const hash='707ef31566863dc95745cec4a27b3e6e3c072ed3.jpg';
test('IWC and JLC use documented larger presets while preserving the exact image identity',()=>{
 for(const preset of ['product-card-3','product-slideshow-1'])assert.equal(higherResolutionUrl(`https://img.iwc.com/${preset}/${hash}`),`https://img.iwc.com/product-slideshow-2xl-1/o-dpr-2/${hash}`);
 for(const preset of ['product-grid-hero-4','product-card-3'])assert.equal(higherResolutionUrl(`https://img.jaeger-lecoultre.com/${preset}/${hash}`),`https://img.jaeger-lecoultre.com/product-grid-hero-xl-4/o-dpr-2/${hash}`);
 assert.equal(higherResolutionUrl(`https://img.iwc.com/product-card-3/${hash}?keep=value`),`https://img.iwc.com/product-slideshow-2xl-1/o-dpr-2/${hash}?keep=value`);
 for(const url of [`https://img.iwc.com.evil.example/product-card-3/${hash}`,`https://img.iwc.com/product-card-3/not-an-asset.jpg`,`https://img.iwc.com/product-slideshow-2xl-1/o-dpr-2/${hash}`,`https://img.jaeger-lecoultre.com/product-grid-hero-xl-4/o-dpr-2/${hash}`,`https://user:pass@img.iwc.com/product-card-3/${hash}`,`https://img.iwc.com:444/product-card-3/${hash}`])assert.equal(higherResolutionUrl(url),'');
});
test('Omega raises the existing resize width without changing the original image path',()=>{
 assert.equal(higherResolutionUrl('https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=230'),'https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=2000');
 assert.equal(higherResolutionUrl('https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=640&keep=value'),'https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=2000&keep=value');
 for(const url of ['https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=2000','https://www.omegawatches.com/media/catalog/product/o/m/watch.png','https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=auto','https://example.com/media/catalog/product/o/m/watch.png?w=230'])assert.equal(higherResolutionUrl(url),'');
});
test('larger presets may have different canvas padding but must retain the same asset',()=>{
 const src=`https://img.iwc.com/product-card-3/${hash}`,hq=higherResolutionUrl(src);
 assert.equal(canUpgrade(src,hq,376,365,1854,2140),true);
 assert.equal(canUpgrade(src,hq.replace(hash,'f'.repeat(40)+'.jpg'),376,365,1854,2140),false);
 assert.equal(canUpgrade(src,hq,376,365,100,200),false);
 assert.equal(canUpgrade(src,hq,376,365,NaN,2140),false);
 const omega='https://www.omegawatches.com/media/catalog/product/o/m/watch.png?w=230',ohq=higherResolutionUrl(omega);
 assert.equal(canUpgrade(omega,ohq,230,230,2000,2000),true);assert.equal(canUpgrade(omega,ohq,230,230,2000,1000),false);
});
test('portrait and landscape images fit inside the available stage',()=>{
 assert.deepEqual(fit(526,752,600,800),{width:526,height:752});
 const p=fit(2688,3840,400,500);assert(p.width<=352&&p.height<=452);
 const l=fit(3840,2688,400,500);assert(l.width<=352&&l.height<=452);
});
test('panning stays within image edges and resets to center when the image fits',()=>{
 assert.deepEqual(clampPan(999,-999,300,450,400,500,1),{x:0,y:0});
 assert.deepEqual(clampPan(999,-999,300,450,400,500,3),{x:250,y:-425});
});
test('zoom preserves the point under the pointer or pinch midpoint',()=>{
 const p=zoomAt(1,3,20,10,80,50);assert.deepEqual(p,{x:-100,y:-70});
 assert.equal((80-p.x)/3,(80-20)/1);assert.equal((50-p.y)/3,(50-10)/1);
 assert.deepEqual(zoomAt(3,1,p.x,p.y,80,50),{x:20,y:10});
});
