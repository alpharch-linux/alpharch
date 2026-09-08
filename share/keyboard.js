/* Keyboard commands use the same chart operations as the visible controls. */
window.ChartKeyboard=(()=>{
 'use strict';
 let dialog=null,search=null,list=null,resultRows=[],index=0,returnFocus=null;
 const cursors=new WeakMap();
 const c=()=>active()||state.charts[0];
 const frame=chart=>$('chart-'+chart.id)?.querySelector('canvas');
 const textTarget=target=>target?.closest('input,select,textarea,[contenteditable="true"]');
 function chart(){const value=c();if(!value)throw Error('Add a chart first.');focus(value);return value;}
 const entries=[
  ['new','New chart window','N',()=>{openNew();$('instrument').focus();}],
  ['indicators','Indicators · search and edit','I',()=>openStudies(chart())],
  ['interval','Timeframe · type any interval','T',()=>IntervalUI.open(chart())],
  ['history','Chart history / data','H',()=>IntervalUI.openHistory(chart())],
  ['drawings','Drawing objects · edit exact anchors','D',()=>DrawingUI.objects(chart())],
  ['style','Chart themes and window colors','P',()=>ThemeUI.open(c())],
  ['save','Save desk layout','S',()=>NativeDesk.enabled?NativeDesk.openSave():openName('save')],
  ['layouts','Restore or export a saved layout','O',()=>{$('layouts').click();}],
  ['connections','Connect a data feed','C',()=>{$('connections').click();}],
  ['review','Recording and replay','R',()=>window.openSessions()],
  ['live','Return chart to latest bars','L',()=>{const v=chart();v.until=null;changed(v);frame(v)?.focus();}],
  ['fit','Fit and recenter chart','Z',()=>{const v=chart();fitChart(v);frame(v)?.focus();}],
  ['tools','Chart tools · price scale and alerts','',()=>openTools(chart())],
  ['grid','Chart grid settings','',()=>IntervalUI.openGrid(chart())],
  ['ticket','Show / hide trading panel','',()=>{$('chart-'+chart().id).querySelector('.trade-toggle').click();}],
  ['starters','Choose a starting desk','',()=>openStarters()],
  ['zoom-in','Zoom in','',()=>{const v=chart();zoomTime(v,barsFor(v),.8);changed(v);}],
  ['zoom-out','Zoom out','',()=>{const v=chart();zoomTime(v,barsFor(v),1.25);changed(v);}],
  ['crosshair','Toggle crosshair','',()=>{$('chart-'+chart().id).querySelector('[data-control="cross"]').click();}],
  ['undo','Undo drawing','',()=>undoDrawing(chart())],
  ['redo','Redo drawing','',()=>undoDrawing(chart(),true)],
  ['play','Replay · play / pause','',()=>{if(!window.deskReplay)throw Error('Open a recording first.');$('sessionPlay').click();}],
  ['step','Replay · next event','',()=>{if(!window.deskReplay)throw Error('Open a recording first.');$('sessionStep').click();}],
  ['help','Keyboard reference','',()=>help()]
 ];
 function choices(){return [...entries,...DrawingTools.catalog.map(d=>['draw:'+d.id,'Draw · '+d.name,'',()=>{const v=chart();if(['ladder','tape'].includes(v.view))throw Error('Choose a chart view before drawing.');DrawingUI.choose(v,d.id);moveCursor(v,0,0);notify(d.name+' · Alt+arrows move · Enter places anchor · Escape cancels.');}]),...state.charts.map(v=>['focus:'+v.id,'Focus · '+chartName(v)+' · '+Intervals.label(v)+' · '+views[v.view],'',()=>{focus(v);frame(v)?.focus();}])];}
 function close(){dialog?.close();returnFocus?.isConnected&&returnFocus.focus();}
 function run(action){
  try{
   if(action==='commands'){open();return {ok:true};}
   const entry=choices().find(item=>item[0]===action);if(!entry)throw Error('Unknown chart command.');
   if(dialog?.open)close();
   if(document.querySelector('dialog[open]'))throw Error('Close the current panel with Escape before opening another.');
   if(NativeDesk.enabled&&!NativeDesk.ready)throw Error('Wait for the chart to finish loading.');
   entry[3]();saveSoon();return {ok:true};
  }catch(error){notify(error.message);return {ok:false,note:error.message};}
 }
 function render(){
  const terms=search.value.toLowerCase().trim().split(/\s+/);resultRows=choices().filter(item=>terms.every(t=>item[1].toLowerCase().includes(t)));index=0;list.replaceChildren();
  for(const [id,label,key]of resultRows){const b=document.createElement('button');b.type='button';b.setAttribute('role','option');b.id='chart-command-'+id.replace(':','-');const name=document.createElement('span');name.textContent=label;b.append(name);if(key){const k=document.createElement('kbd');k.textContent='Super Alt Shift '+key;b.append(k);}b.onclick=()=>run(id);list.append(b);}
  if(!resultRows.length){const p=document.createElement('p');p.textContent='No matching commands.';list.append(p);}select(0);
 }
 function select(next){index=Math.max(0,Math.min(resultRows.length-1,next));for(const [i,b]of [...list.querySelectorAll('button')].entries())b.setAttribute('aria-selected',String(i===index));const row=list.querySelectorAll('button')[index];if(row){search.setAttribute('aria-activedescendant',row.id);row.scrollIntoView({block:'nearest'});}else search.removeAttribute('aria-activedescendant');}
 function open(){
  if(dialog?.open){search.focus();return;}
  if(document.querySelector('dialog[open]')){notify('Press Escape to close the current panel, then open Commands.');return;}
  returnFocus=document.activeElement;
  if(!dialog){dialog=document.createElement('dialog');dialog.id='commandDialog';dialog.setAttribute('aria-label','Chart commands');dialog.innerHTML='<div class="command-head"><span>ALPHARCH / COMMANDS</span><button type="button" aria-label="Close commands">Esc</button></div><input id="commandSearch" type="text" role="combobox" aria-label="Search chart commands" aria-autocomplete="list" aria-expanded="true" aria-controls="commandResults" autocomplete="off" placeholder="What do you want to do?"><div id="commandResults" role="listbox" aria-label="Matching commands"></div><p class="command-foot">↑ ↓ Choose &nbsp; Enter Run &nbsp; Esc Close <span>Super+Alt+U · Ctrl+K</span></p>';document.body.append(dialog);search=$('commandSearch');list=$('commandResults');dialog.querySelector('button').onclick=close;search.oninput=render;search.onkeydown=e=>{if(['ArrowDown','ArrowUp','Enter'].includes(e.key)){e.preventDefault();if(e.key==='Enter'){if(resultRows[index])run(resultRows[index][0]);}else select(index+(e.key==='ArrowDown'?1:-1));}};}
  search.value='';dialog.showModal();render();search.focus();
 }
 function moveCursor(v,dx,dy,fast=false){
  const r=geometry.get(v);if(!r)throw Error('Wait for chart data before moving the cursor.');
  let point=cursors.get(v);if(!point||point.axis<r.from||point.axis>r.to||point.p<r.low||point.p>r.high)point={axis:r.from+r.span*.6,p:snap((r.low+r.high)/2,+marketTick(v))};
  const tick=+marketTick(v),priceSteps=fast?Math.max(10,Math.ceil((r.high-r.low)/tick/40)):1;
  point.axis=clamp(point.axis+dx*r.unit*(fast?10:1),r.from+.01*r.unit,r.to-.01*r.unit);
  point.p=snap(clamp(point.p+dy*tick*priceSteps,Math.ceil(r.low/tick)*tick,Math.floor(r.high/tick)*tick),tick);cursors.set(v,point);v.crosshair=true;
  v.mouse={x:r.L+(point.axis-r.from)/r.span*r.plotW,y:r.T+(r.high-point.p)/(r.high-r.low)*(r.B-r.T)};
  DrawingUI.keyboardMove(v,v.mouse,r);DrawingUI.refresh(v);draw(v);frame(v)?.focus();
 }
 function help(){
  let panel=$('keyboardHelp');if(!panel){panel=document.createElement('dialog');panel.id='keyboardHelp';panel.setAttribute('aria-label','Keyboard reference');const heading=document.createElement('h2');heading.textContent='Your desk, from the keyboard.';panel.append(heading);const pairs=[['Super + Alt + U / Ctrl + K','Search every chart command'],['Super + Alt + Shift + N / I / T','New chart / indicators / interval'],['Super + Alt + Shift + D / P / S','Drawing objects / style / save desk'],['Super + Alt + Shift + C / R / H','Connections / replay / history'],['Super + Alt + Shift + L / Z / O','Latest bars / fit / layouts'],['Super + arrows','Focus another native window'],['Super + Shift + arrows','Swap native windows'],['Super + 1…9','Switch workspace'],['Alt + arrows on chart','Move drawing cursor: one bar / one native tick'],['Alt + Shift + arrows','Move cursor faster'],['Enter on chart','Place drawing anchor; start / finish a freehand path'],['H / T / R / F / B on chart','Level / trend / rectangle / Fibonacci / brush'],['+ / − / Left / Right / Home','Zoom / pan / latest bars'],['Ctrl + Z / Ctrl + Shift + Z','Undo / redo drawing'],['Tab / Shift + Tab / Enter / Escape','Move between controls / activate / close']];const dl=document.createElement('dl');for(const [keys,detail]of pairs){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=keys;dd.textContent=detail;dl.append(dt,dd);}panel.append(dl);const note=document.createElement('p');note.textContent='Choose a drawing through Commands, then use Alt+arrows and Enter. Edit exact prices and times in Drawing objects. Desktop shortcuts act only on the focused Alpharch window. Your own Omarchy bindings take precedence.';panel.append(note);const done=document.createElement('button');done.textContent='Done';done.onclick=()=>panel.close();panel.append(done);document.body.append(panel);}panel.showModal();
 }
 function connected(){if(liveSocket?.readyState===1)liveSocket.send(JSON.stringify({chartKeys:{register:windowName||'default'}}));}
 function receive(msg){const result=run(msg.action);if(liveSocket?.readyState===1)liveSocket.send(JSON.stringify({chartKeys:{ack:msg.id,...result}}));}
 document.addEventListener('keydown',e=>{
  if(e.ctrlKey&&!e.altKey&&!e.metaKey&&e.key.toLowerCase()==='k'){e.preventDefault();e.stopImmediatePropagation();open();return;}
  if(e.metaKey||document.querySelector('dialog[open]')||textTarget(e.target))return;
  const v=state.charts.find(v=>frame(v)===e.target);if(!v)return;
  if(e.altKey&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();try{moveCursor(v,e.key==='ArrowLeft'?-1:e.key==='ArrowRight'?1:0,e.key==='ArrowDown'?-1:e.key==='ArrowUp'?1:0,e.shiftKey);}catch(err){notify(err.message);}}
  else if(e.key==='Enter'&&!e.ctrlKey){e.preventDefault();e.stopImmediatePropagation();try{if(!v.tool||v.tool==='cursor'){open();return;}if(!v.mouse)moveCursor(v,0,0);DrawingUI.keyboardEnter(v,v.mouse,geometry.get(v));saveSoon();}catch(err){notify(err.message);}}
  else if(!e.altKey&&!e.ctrlKey&&['h','t','r','f','b'].includes(e.key.toLowerCase())){queueMicrotask(()=>{try{moveCursor(v,0,0);}catch{}});}
 },true);
 const button=document.createElement('button');button.id='chartCommands';button.textContent='Commands';button.title='Chart commands · Super+Alt+U / Ctrl+K';button.onclick=open;$('palette').after(button);
 $('help').textContent='Keys';$('help').onclick=help;
 new MutationObserver(()=>{if((document.activeElement===document.body||!document.activeElement)&&!document.querySelector('dialog[open]')&&state.charts.length){frame(c())?.focus();}}).observe(stage,{childList:true});
 connected();
 return {open,run,connected,receive,moveCursor,help};
})();
