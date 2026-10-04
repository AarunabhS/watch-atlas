const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require.resolve('../dist/finder.js'),'utf8');
function autocomplete(fetch){
 const attributes=new Map(),input={value:'Rolex',setAttribute:(k,v)=>attributes.set(k,v),removeAttribute:k=>attributes.delete(k),blur(){document.activeElement=null;},focus(){document.activeElement=input;},select(){}};
 const popup={hidden:true,innerHTML:'',querySelectorAll:()=>[]},form={contains:()=>false},timers=new Map(),navigation=[];
 const elements={'#universal-query':input,'#universal-search':form,'#universal-suggestions':popup};
 const document={activeElement:input,querySelector:s=>elements[s]||null,addEventListener(){}};
 let id=0;const ctx={document,fetch,URLSearchParams,AbortController,AtlasFinderModel:require('../dist/finder-model.js'),setTimeout(fn){timers.set(++id,fn);return id;},clearTimeout:id=>timers.delete(id),AtlasWorkspace:{}};
 ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(source,ctx);ctx.AtlasFinder.configure({metadata:{facets:{}},navigate:(view,state)=>navigation.push({view,state})});
 return {input,popup,form,attributes,navigation,api:ctx.AtlasFinder,run(){const [key,fn]=timers.entries().next().value;timers.delete(key);return fn();}};
}
const body={groups:[{label:'Brands',items:[{label:'Rolex',state:{brand:['Rolex']}}]}]};
test('a dismissed search cannot reopen from a late autocomplete response',async()=>{
 let finish;const ui=autocomplete(()=>new Promise(resolve=>{finish=resolve;}));ui.input.oninput();const pending=ui.run();ui.api.dispose();finish({ok:true,json:async()=>body});await pending;
 assert.equal(ui.popup.hidden,true);assert.equal(ui.attributes.get('aria-expanded'),'false');
});
test('keyboard autocomplete selects the structured entity and closes its popup',async()=>{
 const ui=autocomplete(async()=>({ok:true,json:async()=>body}));ui.input.oninput();await ui.run();assert.equal(ui.popup.hidden,false);ui.input.onkeydown({key:'ArrowDown',preventDefault(){}});ui.form.onsubmit({preventDefault(){}});
 assert.equal(ui.navigation.length,1);assert.equal(ui.navigation[0].view,'finder');assert.equal(ui.navigation[0].state.brand[0],'Rolex');assert.equal(ui.popup.hidden,true);assert.equal(ui.attributes.get('aria-expanded'),'false');
});
