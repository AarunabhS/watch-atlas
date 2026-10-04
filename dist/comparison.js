(function(root){
'use strict';
const M=root.AtlasCompare,escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=u=>{try{const x=new URL(u);return x.protocol==='https:'?x.href:'';}catch{return '';}};
const labels={lte:'At most',gte:'At least',eq:'Exactly',between:'Between',contains:'Contains',equals:'Equals',excludes:'Does not contain',known:'Must be recorded'};
const storageKey='watch-atlas-comparison-v1',maxWatches=6;
let rows=[],index=new Map(),fields=[],ids=[],selected=[...M.defaults],rules=[],unknown=false,differences=false,hideEmpty=false,query='',shown=12,callbacks={},toastTimer;
const $=s=>document.querySelector(s);
function notify(text){const el=$('#atlas-status');if(el){el.textContent=text;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{el.textContent='';},4500);}}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify({ids,selected,rules,unknown,differences,hideEmpty}));}catch{}refreshSelection();}
function sanitize(value){
 const v=value&&typeof value==='object'?value:{};
 ids=[...new Set(Array.isArray(v.ids)?v.ids:[])].filter(id=>index.has(id)).slice(0,maxWatches);
 selected=[...new Set(Array.isArray(v.selected)?v.selected:M.defaults)].filter(id=>fields.some(f=>f.id===id));
 rules=(Array.isArray(v.rules)?v.rules:[]).slice(0,12).filter(r=>r&&fields.some(f=>f.id===r.field)&&typeof r.value==='string'&&r.value.length<=200).map(r=>({field:r.field,op:M.operators(fields.find(f=>f.id===r.field)).includes(r.op)?r.op:'known',value:r.value,value2:String(r.value2||'').slice(0,30),currency:/^[A-Z]{3}$/.test(r.currency||'')?r.currency:'USD'}));
 unknown=v.unknown===true;differences=v.differences===true;hideEmpty=v.hideEmpty===true;
}
function initialize(data){
 rows=root.AtlasModel.curatedOrder(data.records.filter(r=>r.is_watch),data.brandOrder||[]);index=new Map(rows.map(r=>[r.id,r]));fields=M.allFields(rows);
 try{sanitize(JSON.parse(localStorage.getItem(storageKey)||'{}'));}catch{sanitize({});}
 if(location.hash.startsWith('#compare?')){
  try{const p=new URLSearchParams(location.hash.split('?')[1]);if(location.hash.length<14000)sanitize({ids:(p.get('ids')||'').split(','),selected:p.has('fields')?JSON.parse(p.get('fields')):M.defaults,rules:JSON.parse(p.get('rules')||'[]'),unknown:p.get('unknown')==='1',differences:p.get('diff')==='1',hideEmpty:p.get('hide')==='1'});persist();}catch{notify('This comparison link could not be read. Your saved shortlist is still available.');}
 }
 refreshSelection();
}
function isSelected(id){return ids.includes(id);}
function toggle(id){
 if(!index.has(id))return;
 if(ids.includes(id))ids=ids.filter(x=>x!==id);
 else if(ids.length<maxWatches)ids.push(id);
 else{notify('Your shortlist has six watches. Remove one to add another.');return;}
 persist();notify(`${ids.length} of ${maxWatches} watches shortlisted.`);
 if($('#comparison-table'))renderTable();
}
function refreshSelection(){
 document.querySelectorAll('[data-compare]').forEach(b=>{const on=ids.includes(b.dataset.compare);b.textContent=on?'✓ Shortlisted':'+ Compare';b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});
 const count=$('#compare-count');if(count)count.textContent=ids.length||'';
 const matchCount=$('#compare-matches .results-info span:last-child');if(matchCount)matchCount.textContent=`Shortlist ${ids.length} / ${maxWatches}`;
 const tray=$('#compare-tray');if(tray){tray.hidden=!ids.length;tray.innerHTML=`<span><strong>${ids.length} / ${maxWatches}</strong> watches shortlisted</span><button class="button primary" data-open-compare>Compare watches →</button><button class="text-button" data-clear-shortlist>Clear</button>`;tray.querySelector('[data-open-compare]').onclick=()=>{if($('#comparison-table'))$('.comparison-panel').scrollIntoView({block:'start'});else callbacks.navigate?.('compare');};tray.querySelector('[data-clear-shortlist]').onclick=clear;}
}
function selectionButton(r){return `<button class="compare-toggle ${isSelected(r.id)?'selected':''}" data-compare="${escape(r.id)}" aria-pressed="${isSelected(r.id)}" aria-label="Compare ${escape(r.brand+' '+r.specific_model+' '+r.reference_number)}">${isSelected(r.id)?'✓ Shortlisted':'+ Compare'}</button>`;}
function bindSelection(){document.querySelectorAll('[data-compare]').forEach(b=>b.onclick=()=>toggle(b.dataset.compare));refreshSelection();}
function clear(){ids=[];persist();notify('Shortlist cleared.');if($('#comparison-table'))renderTable();}
function fieldOptions(value){return [...new Set(fields.map(f=>f.group))].map(group=>`<optgroup label="${escape(group)}">${fields.filter(f=>f.group===group&&!['url'].includes(f.type)).map(f=>`<option value="${escape(f.id)}" ${f.id===value?'selected':''}>${escape(f.label)}${f.unit?' ('+escape(f.unit)+')':''}</option>`).join('')}</optgroup>`).join('');}
function render(){return `<div class="view-intro compare-intro"><p class="eyebrow">YOUR WATCH, YOUR CRITERIA</p><h1>Find what fits. Compare what matters.</h1><p>Set your requirements, shortlist up to six references, and choose the details you want to see side by side.</p></div><div class="compare-steps"><span><b>01</b> Define your requirements</span><span><b>02</b> Build a shortlist</span><span><b>03</b> Compare the details</span></div>
<section class="panel requirements-panel" aria-labelledby="requirements-title"><div class="section-heading"><div><p class="eyebrow">THE RIGHT FIT</p><h2 id="requirements-title">What matters to you?</h2></div><button class="text-button" id="reset-requirements">Reset requirements</button></div><p class="compare-note">All requirements apply together. Budgets use recorded catalog prices in the chosen currency. Missing specifications remain unknown.</p><div id="requirement-rules"></div><div class="requirement-actions"><button class="button" id="add-requirement">+ Add a requirement</button><label class="check-label"><input id="include-unknown" type="checkbox" ${unknown?'checked':''}> Include watches with unrecorded values</label></div><div id="requirement-errors" role="status"></div><div class="filters compare-search"><label class="search-wrap"><span aria-hidden="true">⌕</span><input id="compare-search" type="search" aria-label="Search matching watches" placeholder="Search a watchmaker, model, reference or material…" value="${escape(query)}"></label></div><div id="compare-matches" aria-live="polite"></div></section>
<section class="panel comparison-panel" aria-labelledby="shortlist-title"><div class="section-heading"><div><p class="eyebrow">SIDE BY SIDE</p><h2 id="shortlist-title">Your shortlist</h2></div><div class="comparison-tools"><button class="text-button" id="share-comparison">Copy comparison link</button><button class="text-button" id="export-comparison">Export CSV</button><button class="text-button" id="clear-comparison">Clear shortlist</button></div></div><details class="parameter-picker"><summary id="parameter-summary">Choose comparison parameters</summary><div class="parameter-actions"><button class="text-button" id="default-parameters">Essentials</button><button class="text-button" id="all-parameters">Select all</button><button class="text-button" id="clear-parameters">Clear all</button></div><div class="parameter-groups">${[...new Set(fields.map(f=>f.group))].map(group=>`<fieldset><legend>${escape(group)}</legend>${fields.filter(f=>f.group===group).map(f=>`<label class="check-label"><input type="checkbox" data-parameter="${escape(f.id)}" ${selected.includes(f.id)?'checked':''}>${escape(f.label)}</label>`).join('')}</fieldset>`).join('')}</div></details><div class="comparison-options"><label class="check-label"><input id="differences-only" type="checkbox" ${differences?'checked':''}> Only differences</label><label class="check-label"><input id="hide-empty" type="checkbox" ${hideEmpty?'checked':''}> Hide rows with no recorded values</label>${root.AtlasPrices.countrySelector()}</div><div id="comparison-table"></div><p class="compare-note">Specifications and catalog prices describe the stored snapshot. Web prices are shown separately with source links. Water resistance is a stated rating; bar / ATM values use 10 m per unit for comparison. Ranges and ambiguous dimensions are not reduced to a single number. No currency conversion is applied.</p></section>`;}
function renderRules(){
 $('#requirement-rules').innerHTML=rules.map((r,i)=>{const f=fields.find(f=>f.id===r.field),numeric=['number','price'].includes(f.type);return `<div class="requirement-row" data-rule="${i}"><label><span class="skip-label">Requirement ${i+1} parameter</span><select data-rule-field>${fieldOptions(r.field)}</select></label><label><span class="skip-label">Requirement ${i+1} condition</span><select data-rule-op>${M.operators(f).map(op=>`<option value="${op}" ${op===r.op?'selected':''}>${labels[op]}</option>`).join('')}</select></label>${r.op!=='known'?`<label><span class="skip-label">Requirement ${i+1} value</span><input data-rule-value type="${numeric?'number':'text'}" ${numeric?'min="0" step="any"':''} value="${escape(r.value)}" placeholder="${numeric?(f.unit||'Amount'):'Enter a value'}"></label>${r.op==='between'?`<label><span class="skip-label">Requirement ${i+1} upper value</span><input data-rule-value2 type="number" min="0" step="any" value="${escape(r.value2)}" placeholder="Upper value"></label>`:''}${f.type==='price'?`<label><span class="skip-label">Requirement ${i+1} currency</span><select data-rule-currency>${[...new Set(['USD','INR','EUR','GBP','CHF',...rows.map(r=>r.currency).filter(c=>/^[A-Z]{3}$/.test(c))])].sort().map(c=>`<option ${c===r.currency?'selected':''}>${escape(c)}</option>`).join('')}</select></label>`:''}`:''}<button class="remove-rule" data-remove-rule="${i}" aria-label="Remove requirement ${i+1}">×</button></div>`;}).join('');
 $('#add-requirement').disabled=rules.length>=12;
 document.querySelectorAll('[data-rule]').forEach(el=>{
  const i=Number(el.dataset.rule);
  el.querySelector('[data-rule-field]').onchange=e=>{const f=fields.find(f=>f.id===e.target.value);rules[i]={field:f.id,op:M.operators(f)[0],value:'',value2:'',currency:'USD'};persist();renderRules();renderMatches();renderTable();};
  el.querySelector('[data-rule-op]').onchange=e=>{rules[i].op=e.target.value;persist();renderRules();renderMatches();renderTable();};
  for(const [selector,key] of [['[data-rule-value]','value'],['[data-rule-value2]','value2'],['[data-rule-currency]','currency']]){const input=el.querySelector(selector);if(input)input.addEventListener('input',e=>{rules[i][key]=e.target.value;shown=12;persist();renderMatches();renderTable();});}
 });
 document.querySelectorAll('[data-remove-rule]').forEach(b=>b.onclick=()=>{rules.splice(Number(b.dataset.removeRule),1);persist();renderRules();renderMatches();renderTable();});
}
function matches(){const q=query.trim().toLocaleLowerCase();return rows.map(r=>({r,...M.match(r,rules,fields,unknown)})).filter(x=>x.pass&&(!q||[x.r.brand,x.r.specific_model,x.r.reference_number,x.r.case_material,x.r.dial_color,x.r.caliber,x.r.features].some(v=>String(v||'').toLocaleLowerCase().includes(q)))).sort((a,b)=>a.unknown-b.unknown);}
function renderMatches(){
 const errors=rules.map((r,i)=>{const e=M.validateRule(r,fields.find(f=>f.id===r.field));return e?`Requirement ${i+1}: ${e}`:'';}).filter(Boolean);
 $('#requirement-errors').innerHTML=errors.map(e=>`<p class="requirement-error">${escape(e)}</p>`).join('');
 const matched=errors.length?[]:matches();
 $('#compare-matches').innerHTML=`<div class="results-info"><span>${matched.length.toLocaleString('en-US')} matching watches</span><span>Shortlist ${ids.length} / ${maxWatches}</span></div>${matched.length?`<div class="match-list">${matched.slice(0,shown).map(({r,unknown:n})=>`<article class="match-watch"><button class="match-name" data-match-record="${escape(r.id)}"><small>${escape(r.brand)} · ${escape(r.reference_number)}</small><strong>${escape(r.specific_model)}</strong><span>${escape(M.display(r,fields.find(f=>f.id==='diameter')))} · ${escape(r.movement_family||'Movement not recorded')}${n?' · '+n+' unrecorded requirement'+(n===1?'':'s'):''}</span></button>${selectionButton(r)}</article>`).join('')}</div>${matched.length>shown?'<button class="button show-more" id="more-matches">Show more matches</button>':''}`:`<div class="empty compare-empty"><h3>${errors.length?'Finish setting your requirements':'No matching watches'}</h3><p>${errors.length?'Each active requirement needs a value.':'Try broader requirements or include watches with unrecorded values.'}</p></div>`}`;
 $('#more-matches')?.addEventListener('click',()=>{shown+=12;renderMatches();});
 document.querySelectorAll('[data-match-record]').forEach(b=>b.onclick=()=>callbacks.openRecord?.(b.dataset.matchRecord));bindSelection();
}
function activeFields(watches){return fields.filter(f=>selected.includes(f.id)&&(!differences||M.difference(watches,f))&&(!hideEmpty||watches.some(r=>M.known(f.read(r)))));}
function renderTable(){
 const watches=ids.map(id=>index.get(id)).filter(Boolean),active=activeFields(watches);
 const summary=$('#parameter-summary');if(summary)summary.textContent=`Choose comparison parameters · ${selected.length} of ${fields.length} selected`;
 const csv=$('#export-comparison');if(csv)csv.disabled=watches.length<2||!active.length;
 const share=$('#share-comparison');if(share)share.disabled=!watches.length;
 if(!watches.length){$('#comparison-table').innerHTML='<div class="empty compare-empty"><h3>Your comparison starts here.</h3><p>Add watches from the matches above or from the catalog.</p><button class="button" id="browse-for-compare">Browse the watch catalog</button></div>';$('#browse-for-compare').onclick=()=>callbacks.navigate?.('catalog');return;}
 const errors=rules.some(r=>M.validateRule(r,fields.find(f=>f.id===r.field)));
 const cell=(r,f)=>{const v=M.display(r,f);if(f.type==='url'&&safe(f.read(r)))return `<a href="${escape(safe(f.read(r)))}" target="_blank" rel="noopener noreferrer">View watchmaker source ↗</a>`;return escape(v);};
 $('#comparison-table').innerHTML=`${watches.length===1?'<p class="comparison-hint">Add one more watch to compare side by side.</p>':''}<div class="table-wrap compare-table-wrap" tabindex="0" role="region" aria-label="Watch comparison; scroll horizontally to see all watches"><table class="compare-table"><caption class="skip-label">Watch specifications for your selected parameters</caption><thead><tr><th scope="col">${active.length} parameter${active.length===1?'':'s'}</th>${watches.map(r=>`<th scope="col"><small>${escape(r.brand)}</small><button class="compare-watch-name" data-match-record="${escape(r.id)}">${escape(r.specific_model)}</button><span class="compare-reference">${escape(r.reference_number)}</span><button class="text-button" data-remove-watch="${escape(r.id)}" aria-label="Remove ${escape(r.brand+' '+r.reference_number)} from comparison">Remove</button></th>`).join('')}</tr></thead><tbody>${rules.length?`<tr class="requirements-check"><th scope="row">Your requirements</th>${watches.map(r=>{const result=M.match(r,rules,fields,unknown);return `<td>${errors?'Finish setting requirements':result.pass?(result.unknown?result.unknown+' unrecorded requirement'+(result.unknown===1?'':'s'):'Meets all requirements'):'Outside your requirements'}</td>`;}).join('')}</tr>`:''}${active.map(f=>`<tr class="${M.difference(watches,f)?'has-difference':''}"><th scope="row">${escape(f.label)}${f.unit?`<small>${escape(f.unit)}</small>`:''}</th>${watches.map(r=>`<td class="${M.known(f.read(r))?'':'unrecorded'}">${cell(r,f)}</td>`).join('')}</tr>`).join('')}${active.some(f=>f.id==='price_value')&&watches.some(r=>r.price_value==null)?`<tr class="reported-price-row"><th scope="row">Reported web price<small>Unverified internet reports</small></th>${watches.map(r=>`<td>${r.price_value==null?root.AtlasPrices.controls(r):'<span class="muted">Catalog price available</span>'}</td>`).join('')}</tr>`:''}</tbody></table></div>${!active.length?'<p class="comparison-hint">No rows to show. Choose more parameters or turn off the row filters.</p>':''}`;
 document.querySelectorAll('[data-remove-watch]').forEach(b=>b.onclick=()=>{toggle(b.dataset.removeWatch);if($('#compare-matches'))renderMatches();});
 document.querySelectorAll('#comparison-table [data-match-record]').forEach(b=>b.onclick=()=>callbacks.openRecord?.(b.dataset.matchRecord));root.AtlasPrices.bind(rows);
}
async function share(){
 const p=new URLSearchParams({ids:ids.join(','),fields:JSON.stringify(selected),rules:JSON.stringify(rules),unknown:unknown?'1':'0',diff:differences?'1':'0',hide:hideEmpty?'1':'0'});
 const url=location.origin+location.pathname+'#compare?'+p;
 try{await navigator.clipboard.writeText(url);notify('Comparison link copied.');}
 catch{const el=$('#share-link-fallback');if(el)el.remove();const label=document.createElement('label');label.id='share-link-fallback';label.className='share-link-fallback';label.textContent='Copy your comparison link';const input=document.createElement('input');input.readOnly=true;input.value=url;label.append(input);$('#comparison-table').before(label);input.focus();input.select();notify('Select and copy the comparison link.');}
}
function exportCsv(){
 const watches=ids.map(id=>index.get(id)),active=activeFields(watches);if(watches.length<2)return;
 const blob=new Blob([M.toCsv(watches,active)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='watch-atlas-comparison.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Comparison exported as CSV.');
}
function bind(nextCallbacks){
 callbacks=nextCallbacks;renderRules();renderMatches();renderTable();
 $('#add-requirement').onclick=()=>{if(rules.length>=12)return;rules.push({field:'diameter',op:'lte',value:'40',value2:'',currency:'USD'});shown=12;persist();renderRules();renderMatches();renderTable();};
 $('#reset-requirements').onclick=()=>{rules=[];unknown=false;query='';shown=12;persist();$('#include-unknown').checked=false;$('#compare-search').value='';renderRules();renderMatches();renderTable();};
 $('#include-unknown').onchange=e=>{unknown=e.target.checked;shown=12;persist();renderMatches();renderTable();};
 $('#compare-search').oninput=e=>{query=e.target.value;shown=12;renderMatches();};
 document.querySelectorAll('[data-parameter]').forEach(el=>el.onchange=()=>{selected=[...document.querySelectorAll('[data-parameter]:checked')].map(x=>x.dataset.parameter);persist();renderTable();});
 for(const [id,value] of [['default-parameters',M.defaults],['all-parameters',fields.map(f=>f.id)],['clear-parameters',[]]])$('#'+id).onclick=()=>{selected=[...value];document.querySelectorAll('[data-parameter]').forEach(el=>el.checked=selected.includes(el.dataset.parameter));persist();renderTable();};
 $('#differences-only').onchange=e=>{differences=e.target.checked;persist();renderTable();};$('#hide-empty').onchange=e=>{hideEmpty=e.target.checked;persist();renderTable();};
 $('#price-country').onchange=e=>{root.AtlasPrices.setCountry(e.target.value);renderTable();};
 $('#clear-comparison').onclick=()=>{clear();renderMatches();};$('#share-comparison').onclick=share;$('#export-comparison').onclick=exportCsv;
 refreshSelection();
}
function configure(nextCallbacks){callbacks=nextCallbacks;}
root.AtlasWorkspace={initialize,configure,render,bind,bindSelection,selectionButton,refreshSelection,isSelected,toggle};
})(globalThis);
