/* Local order-ticket planning. No order transport, account secrets, or simulated balances. */
(function(root){
'use strict';
const panels=new WeakMap(),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
function quote(c){const m=marketFor(c),fresh=m?.connected&&m.status==='receiving'&&Number.isFinite(m.bookAge)&&m.bookAge+(Number.isFinite(m.clientReceived)?Math.max(0,Date.now()-m.clientReceived)/1000:0)<=15;const bid=fresh?m.book?.bids?.[0]:null,ask=fresh?m.book?.asks?.[0]:null;return{m,bid,ask,fresh:!!bid&&!!ask}}
// Quote shortcuts take a price snapshot. They never submit or chase an order.
function quoteChoice(side,at,q){if(!['buy','sell'].includes(side)||!['bid','ask'].includes(at)||!q?.fresh)return null;const raw=q[at]?.[0];if(raw==null||String(raw).trim()==='')return null;const value=Number(raw);return Number.isFinite(value)?{side,kind:'limit',price:value}:null}
function referencePrice(kind,fields,q,side){if(['limit','stop-limit','stop'].includes(kind)){const raw=kind==='stop'?fields.stop:fields.limit;if(raw==null||String(raw).trim()==='')return null;const value=Number(raw);return Number.isFinite(value)?value:null}return quoteChoice(side,side==='buy'?'ask':'bid',q)?.price??null}
const orderKinds=['market','limit','stop','stop-limit'],timeInForce=['DAY','GTC','IOC','FOK'];
function legValid(o){return !!o&&['buy','sell'].includes(o.side)&&orderKinds.includes(o.kind)&&timeInForce.includes(o.tif)&&Number.isFinite(o.quantity)&&o.quantity>0&&o.quantity<=10000000&&['limit','stop'].every(k=>o[k]===null||Number.isFinite(o[k]))&&(['limit','stop-limit'].includes(o.kind)?o.limit!==null:o.limit===null)&&(['stop','stop-limit'].includes(o.kind)?o.stop!==null:o.stop===null)}
function valid(d){
 if(!d||d.mode!=='LOCAL_DRAFT'||typeof d.symbol!=='string'||d.symbol.length>80||typeof d.source!=='string'||d.source.length>100||!['buy','sell'].includes(d.side)||!orderKinds.includes(d.kind)||!timeInForce.includes(d.tif)||!Number.isFinite(d.quantity)||d.quantity<=0||d.quantity>10000000||!Number.isFinite(d.created)||d.created<=0||!['limit','stop','stopLoss','target'].every(k=>d[k]===null||Number.isFinite(d[k])))return false;
 // Pre-linked-ticket drafts remain readable; they never become executable orders.
 if(d.setup===undefined)return d.linked===undefined;
 if(!['single','oco','bracket','oto'].includes(d.setup)||!legValid(d))return false;
 if(d.setup==='single')return d.linked===null&&d.stopLoss===null&&d.target===null;
 const link=d.linked;
 if(!link||link.type!==d.setup||link.partialFill!=='unverified'||link.hosting!=='unverified'||!Array.isArray(link.legs)||link.legs.length!==(d.setup==='bracket'?2:1)||!link.legs.every(legValid))return false;
 if(d.setup!=='bracket')return d.stopLoss===null&&d.target===null;
 const [target,stop]=link.legs,opposite=d.side==='buy'?'sell':'buy';
 return target.kind==='limit'&&target.stop===null&&target.limit===d.target&&['stop','stop-limit'].includes(stop.kind)&&stop.stop===d.stopLoss&&[target,stop].every(o=>o.side===opposite&&o.quantity===d.quantity);
}
function validateDraft(d,tick,futures){
 if(!valid(d)||!Number.isFinite(tick)||tick<=0)throw Error('Check the order setup, quantity and linked order fields.');
 for(const [i,leg]of [d,...(d.linked?.legs||[])].entries()){
  if(futures&&!Number.isInteger(leg.quantity))throw Error('Order '+(i+1)+': quantity must be whole contracts.');
  for(const key of ['limit','stop',...(i===0?['stopLoss','target']:[])]){
   const value=leg[key];
   if(value!==null&&(!Number.isFinite(value)||!futures&&value<=0||Math.abs(value-Math.round(value/tick)*tick)>tick*1e-6))throw Error('Order '+(i+1)+': prices must align with the native tick: '+tick);
  }
 }
 if(d.setup==='bracket'){
  const entry=referencePrice(d.kind,d,null,d.side),long=d.side==='buy';
  if(long?d.stopLoss>=d.target:d.stopLoss<=d.target)throw Error('Put the bracket stop and target on opposite sides of the planned position.');
  if(entry!==null&&(long?d.stopLoss>=entry||d.target<=entry:d.stopLoss<=entry||d.target>=entry))throw Error('A long bracket needs stop < entry < target; a short bracket needs target < entry < stop.');
 }
 return d;
}
// Relationships describe a saved plan, not an order-routing or cancellation engine.
function orderPlan(d){
 if(!valid(d))throw Error('Invalid local ticket.');
 const leg=o=>({side:o.side,kind:o.kind,quantity:o.quantity,tif:o.tif,limit:o.limit,stop:o.stop});
 const first={id:'entry',...leg(d)},setup=d.setup||'legacy';
 if(setup==='single'||setup==='legacy')return{setup,orders:[first],activateAfter:[],cancelOnFullFill:[]};
 if(setup==='oco')return{setup,orders:[first,{id:'peer',...leg(d.linked.legs[0])}],activateAfter:[],cancelOnFullFill:[['entry','peer']]};
 if(setup==='oto')return{setup,orders:[first,{id:'child',...leg(d.linked.legs[0])}],activateAfter:[{parent:'entry',children:['child']}],cancelOnFullFill:[]};
 return{setup,orders:[first,{id:'target',...leg(d.linked.legs[0])},{id:'stop',...leg(d.linked.legs[1])}],activateAfter:[{parent:'entry',children:['target','stop']}],cancelOnFullFill:[['target','stop']]};
}
function setupDescription(setup){return{single:'One order.',oco:'Plan: two linked orders. A full fill cancels the other.',bracket:'Plan: entry activates target + stop, linked by OCO.',oto:'Plan: entry fill activates the second order.'}[setup]||'Legacy draft · bracket prices were not linked.'}
function legText(o){return o.side.toUpperCase()+' '+o.quantity+' · '+o.kind+(o.limit!==null?' @ '+o.limit:'')+(o.stop!==null?' · trigger '+o.stop:'')+' · '+o.tif}

function toggle(c){c.tradePanelOpen=!c.tradePanelOpen;const tile=$('chart-'+c.id);tile?.classList.toggle('trade-open',c.tradePanelOpen);tile?.querySelector('.trade-toggle')?.setAttribute('aria-pressed',String(c.tradePanelOpen));if(c.tradePanelOpen)refresh(c);changed(c)}
function mount(c,tile){
 const toggleButton=el('button','Trade');toggleButton.className='trade-toggle';toggleButton.title='Show / hide trading panel';toggleButton.setAttribute('aria-label','Trading panel for '+chartName(c));toggleButton.setAttribute('aria-pressed',String(!!c.tradePanelOpen));toggleButton.onclick=()=>{focus(c);toggle(c)};tile.querySelector('.actions').prepend(toggleButton);
 const panel=el('aside');panel.className='trade-panel';panel.setAttribute('aria-label','Trading panel · '+chartName(c));const head=el('div');head.className='trade-panel-head';head.append(el('strong','Trading'));const exit=el('button','×');exit.setAttribute('aria-label','Close trading panel');exit.onclick=()=>toggle(c);head.append(exit);panel.append(head);
 const badge=el('span','DRAFT ONLY');badge.className='trade-mode';badge.title='Local tickets only · broker execution is not connected';head.insertBefore(badge,exit);const accountLabel=el('label');accountLabel.className='ticket-account';const account=el('select');account.setAttribute('aria-label','Trading account');account.add(new Option('Local draft','draft'));account.add(Object.assign(new Option('Live broker execution · unavailable','live'),{disabled:true}));account.add(Object.assign(new Option('Paper broker account · unavailable','paper'),{disabled:true}));accountLabel.append(account);panel.append(accountLabel);
 const metrics=el('dl');metrics.className='trade-metrics';for(const label of ['Equity','Buying power','Available margin','Realized P&L','Unrealized P&L','Position']){metrics.append(el('dt',label),el('dd','—'))}panel.append(metrics);const accountNote=el('p','Account balances and positions require an execution/account adapter. The current IBKR integration is read-only market data.');accountNote.className='trade-note';panel.append(accountNote);
 const book=el('div');book.className='ticket-book';const bid=el('div'),ask=el('div');bid.className='ticket-bid';ask.className='ticket-ask';bid.append(el('small','BID'));ask.append(el('small','ASK'));const bidValue=el('strong','—'),askValue=el('strong','—');bid.append(bidValue);ask.append(askValue);book.append(bid,ask);panel.append(book);const spread=el('p');spread.className='trade-note ticket-spread';panel.append(spread);
 const tabs=el('div');tabs.className='trade-tabs';tabs.setAttribute('role','tablist');const ticketTab=el('section'),accountTab=el('section'),activityTab=el('section');const sections=[ticketTab,accountTab,activityTab];for(const [i,label] of ['Ticket','Account','Activity'].entries()){const b=el('button',label);b.type='button';b.setAttribute('role','tab');b.id='ticket-tab-'+c.id+'-'+i;b.tabIndex=i===0?0:-1;b.setAttribute('aria-controls','ticket-pane-'+c.id+'-'+i);sections[i].id='ticket-pane-'+c.id+'-'+i;sections[i].setAttribute('role','tabpanel');sections[i].setAttribute('aria-labelledby',b.id);b.setAttribute('aria-selected',String(i===0));b.onclick=()=>{sections.forEach((section,j)=>section.hidden=j!==i);for(const [j,button]of [...tabs.children].entries()){button.setAttribute('aria-selected',String(j===i));button.tabIndex=j===i?0:-1}};b.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;tabs.children[next].click();tabs.children[next].focus()};tabs.append(b)}panel.insertBefore(tabs,accountLabel);accountTab.append(metrics,accountNote);accountTab.hidden=true;activityTab.hidden=true;ticketTab.append(book,spread);panel.append(ticketTab,accountTab,activityTab);
 const shortcuts=el('div');shortcuts.className='ticket-shortcuts';shortcuts.setAttribute('role','group');shortcuts.setAttribute('aria-label','Prepare a limit ticket at bid or ask');ticketTab.append(shortcuts);const quoteButtons=[];
 const form=el('form');form.className='ticket-form';const inputs={};function field(label,input){const l=el('label',label);input.setAttribute('aria-label',label);l.append(input);form.append(l);return input}function select(label,values){const n=el('select');for(const [v,t]of values)n.add(new Option(t,v));return field(label,n)}
 inputs.side=select('Side',[['buy','Buy / long'],['sell','Sell / short']]);inputs.kind=select('Order type',[['market','Market'],['limit','Limit'],['stop','Stop market'],['stop-limit','Stop limit']]);inputs.quantity=field(c.feed==='ibkr'?'Contracts':'Quantity',Object.assign(el('input'),{type:'number',min:c.feed==='ibkr'?1:.00000001,max:10000000,step:c.feed==='ibkr'?1:'any',value:c.feed==='ibkr'?1:.01}));inputs.tif=select('Time in force',[['DAY','Day'],['GTC','Good till cancelled'],['IOC','Immediate or cancel'],['FOK','Fill or kill']]);
 for(const [key,name]of [['limit','Limit price'],['stop','Trigger price'],['stopLoss','Bracket stop loss'],['target','Bracket take profit']])inputs[key]=field(name,Object.assign(el('input'),{type:'text',inputMode:'decimal',placeholder:key==='stopLoss'||key==='target'?'Optional':'Exact price'}));
 inputs.setup=select('Order setup',[['single','Single order'],['oco','OCO · two orders'],['bracket','Bracket · target + stop'],['oto','OTO · entry → order']]);inputs.setup.parentElement.className='ticket-setup';form.prepend(inputs.setup.parentElement);
 const advanced=el('details');advanced.className='ticket-advanced';const advancedSummary=el('summary','Time in force');advanced.append(advancedSummary);const advancedFields=el('div');advancedFields.className='ticket-advanced-fields';
 const linkNote=el('p');linkNote.className='trade-note ticket-link-note';
 const bracketFields=el('div');bracketFields.className='ticket-linked-fields';
 inputs.stopKind=select('Bracket stop type',[['stop','Stop market'],['stop-limit','Stop limit']]);inputs.stopLimit=field('Bracket stop limit',Object.assign(el('input'),{type:'text',inputMode:'decimal',placeholder:'Exact price'}));
 inputs.stopLoss.placeholder=inputs.target.placeholder='Exact price';bracketFields.append(inputs.target.parentElement,inputs.stopLoss.parentElement,inputs.stopKind.parentElement,inputs.stopLimit.parentElement);
 const peerFields=el('div');peerFields.className='ticket-linked-fields';const peerHeading=el('strong','Order 2');peerHeading.className='ticket-leg-heading';peerFields.append(peerHeading);
 inputs.peerSide=select('Order 2 side',[['buy','Buy'],['sell','Sell']]);inputs.peerKind=select('Order 2 type',[['limit','Limit'],['stop','Stop market'],['stop-limit','Stop limit'],['market','Market']]);
 inputs.peerQuantity=field('Order 2 quantity',Object.assign(el('input'),{type:'number',min:c.feed==='ibkr'?1:.00000001,max:10000000,step:c.feed==='ibkr'?1:'any',value:c.feed==='ibkr'?1:.01}));
 for(const [key,label]of [['peerLimit','Order 2 limit price'],['peerStop','Order 2 trigger price']])inputs[key]=field(label,Object.assign(el('input'),{type:'text',inputMode:'decimal',placeholder:'Exact price'}));
 peerFields.append(...['peerSide','peerKind','peerQuantity','peerLimit','peerStop'].map(k=>inputs[k].parentElement));
 const linkLimits=el('p','Partial fills and protection during disconnects still need broker testing.');linkLimits.className='trade-note ticket-link-note';
 advancedFields.append(linkNote,bracketFields,peerFields,inputs.tif.parentElement,linkLimits);advanced.append(advancedFields);form.append(advanced);
 const notional=el('p');notional.className='ticket-notional';form.append(notional);const save=el('button','Save draft');save.className='primary';save.type='submit';form.append(save);const status=el('p');status.className='trade-note';status.setAttribute('role','status');form.append(status);ticketTab.append(form);
 const orders=el('details');orders.open=true;orders.append(el('summary','Saved local tickets'));const drafts=el('div');orders.append(drafts);activityTab.append(orders);const positions=el('details');positions.append(el('summary','Broker orders & positions'),el('p','Unavailable until an account/execution adapter is connected. Saved tickets above are local drafts, not submitted orders.'));activityTab.append(positions);
 const foot=el('p','Broker execution not connected. No orders are sent.');foot.className='trade-note ticket-footer';ticketTab.append(foot);tile.append(panel);tile.classList.toggle('trade-open',!!c.tradePanelOpen);
 const item={panel,inputs,bidValue,askValue,quoteButtons,spread,notional,drafts,status};panels.set(c,item);
 function priceState(input,show){input.parentElement.hidden=!show;input.disabled=!show}
 function kindState(){priceState(inputs.limit,['limit','stop-limit'].includes(inputs.kind.value));priceState(inputs.stop,['stop','stop-limit'].includes(inputs.kind.value));refresh(c)}
 function linkedState(){
  const setup=inputs.setup.value,bracket=setup==='bracket',pair=['oco','oto'].includes(setup);
  bracketFields.hidden=!bracket;peerFields.hidden=!pair;linkNote.hidden=linkLimits.hidden=setup==='single';linkNote.textContent=setupDescription(setup);
  advancedSummary.textContent={single:'Time in force',oco:'OCO · linked order / TIF',bracket:'Bracket · exits / TIF',oto:'OTO · linked order / TIF'}[setup];
  for(const key of ['stopLoss','target','stopKind','stopLimit'])inputs[key].disabled=!bracket;
  for(const key of ['peerSide','peerKind','peerQuantity','peerLimit','peerStop'])inputs[key].disabled=!pair;
  priceState(inputs.stopLimit,bracket&&inputs.stopKind.value==='stop-limit');
  priceState(inputs.peerLimit,pair&&['limit','stop-limit'].includes(inputs.peerKind.value));priceState(inputs.peerStop,pair&&['stop','stop-limit'].includes(inputs.peerKind.value));
  peerHeading.textContent=setup==='oto'?'After entry fills':'Order 2 · OCO partner';refresh(c);
 }
 inputs.setup.onchange=()=>{status.textContent='';advanced.open=inputs.setup.value!=='single';inputs.peerSide.value=inputs.setup.value==='oto'?(inputs.side.value==='buy'?'sell':'buy'):inputs.side.value;linkedState()};
 inputs.peerKind.onchange=inputs.stopKind.onchange=()=>{status.textContent='';linkedState()};
 inputs.kind.onchange=()=>{status.textContent='';kindState()};inputs.side.onchange=()=>{status.textContent='';refresh(c)};inputs.quantity.oninput=()=>refresh(c);inputs.limit.oninput=()=>refresh(c);inputs.stop.oninput=()=>refresh(c);
 for(const [side,at,label]of [['buy','bid','Buy Bid'],['sell','ask','Sell Ask'],['buy','ask','Buy Ask'],['sell','bid','Sell Bid']]){const button=el('button',label);button.type='button';button.className='ticket-'+side;button.title='Prepare '+side+' limit at the current '+at+' · does not submit';button.onclick=()=>{const choice=quoteChoice(side,at,quote(c));if(!choice){status.textContent='Wait for a fresh bid and ask.';return}inputs.side.value=choice.side;inputs.kind.value=choice.kind;inputs.limit.value=String(snap(choice.price,+marketTick(c)));status.textContent=label+' selected · local limit ticket.';kindState()};quoteButtons.push(button);shortcuts.append(button)}
 form.onsubmit=e=>{
  e.preventDefault();
  try{
   const readPrice=key=>{const f=inputs[key];if(f.disabled)return null;if(!f.value.trim())throw Error('Enter '+f.getAttribute('aria-label').toLowerCase()+'.');const value=Number(f.value);if(!Number.isFinite(value))throw Error('Enter a valid price.');return value};
   const draft={mode:'LOCAL_DRAFT',symbol:chartName(c),source:c.feed+':'+c.asset,created:Date.now(),setup:inputs.setup.value,side:inputs.side.value,kind:inputs.kind.value,tif:inputs.tif.value,quantity:Number(inputs.quantity.value),limit:readPrice('limit'),stop:readPrice('stop'),stopLoss:null,target:null,linked:null};
   if(draft.setup!=='single'){
    let legs;
    if(draft.setup==='bracket'){
     draft.stopLoss=readPrice('stopLoss');draft.target=readPrice('target');const side=draft.side==='buy'?'sell':'buy',common={side,quantity:draft.quantity,tif:draft.tif};
     legs=[{...common,kind:'limit',limit:draft.target,stop:null},{...common,kind:inputs.stopKind.value,limit:readPrice('stopLimit'),stop:draft.stopLoss}];
    }else legs=[{side:inputs.peerSide.value,kind:inputs.peerKind.value,quantity:Number(inputs.peerQuantity.value),tif:draft.tif,limit:readPrice('peerLimit'),stop:readPrice('peerStop')}];
    draft.linked={type:draft.setup,legs,partialFill:'unverified',hosting:'unverified'};
   }
   validateDraft(draft,+marketTick(c),c.feed==='ibkr');
   if((c.orderDrafts||[]).length>=20)throw Error('Keep up to 20 local tickets per chart; remove an older draft first.');
   (c.orderDrafts??=[]).push(draft);status.textContent=(draft.setup==='single'?'Ticket':draft.setup.toUpperCase()+' plan')+' saved locally. No orders sent.';list(c);saveSoon();
  }catch(error){status.textContent=error.message}
 };

 kindState();linkedState();list(c);refresh(c);
}
function list(c){
 const area=panels.get(c)?.drafts;if(!area)return;area.replaceChildren();if(!c.orderDrafts?.length){area.append(el('p','No local tickets saved.'));return}
 for(const d of [...c.orderDrafts].reverse()){
  const row=el('div');row.className='ticket-draft';const plan=orderPlan(d);
  row.append(el('strong',(d.setup||'Legacy').toUpperCase()+' · '+d.symbol));
  for(const o of plan.orders)row.append(el('small',(o.id==='entry'&&d.setup==='oco'?'Order 1':o.id[0].toUpperCase()+o.id.slice(1))+': '+legText(o)));
  if(d.setup&&d.setup!=='single')row.append(el('p',setupDescription(d.setup)));
  if(!d.setup&&(d.stopLoss!==null||d.target!==null))row.append(el('small','Unlinked bracket prices · stop '+(d.stopLoss??'—')+' · target '+(d.target??'—')));
  row.append(el('small',d.source+' · local draft'));
  const remove=el('button','Remove draft');remove.onclick=()=>{c.orderDrafts=c.orderDrafts.filter(v=>v!==d);list(c);saveSoon()};row.append(remove);area.append(row);
 }
}
function refresh(c){const p=panels.get(c);if(!p||!c.tradePanelOpen)return;const q=quote(c),tick=+marketTick(c);p.bidValue.textContent=q.bid?price(Number(q.bid[0]),c):'—';p.askValue.textContent=q.ask?price(Number(q.ask[0]),c):'—';for(const button of p.quoteButtons)button.disabled=!q.fresh;p.spread.textContent=q.fresh?'Spread '+price(Number(q.ask[0])-Number(q.bid[0]),c)+' · '+Math.round((Number(q.ask[0])-Number(q.bid[0]))/tick)+' ticks':'Fresh bid / ask unavailable';const qty=Number(p.inputs.quantity.value),reference=referencePrice(p.inputs.kind.value,{limit:p.inputs.limit.value,stop:p.inputs.stop.value},q,p.inputs.side.value),multiplier=c.feed==='ibkr'?Number(c.ibContract?.multiplier):1;const total=Number.isFinite(reference)&&qty>0&&multiplier>0?Math.abs(reference*qty*multiplier):null;p.notional.textContent=total!==null?(p.inputs.setup.value==='oco'?'Order 1 ≈ ':'Notional ≈ ')+total.toLocaleString('en-US',{maximumFractionDigits:2})+' '+(c.ibContract?.currency||'USD')+' · before fees':'Notional —';}
root.TradePanel={mount,refresh,valid};if(typeof module!=='undefined'&&module.exports)module.exports={valid,quoteChoice,referencePrice,validateDraft,orderPlan};
})(globalThis);
