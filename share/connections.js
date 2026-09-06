/* Account data stays outside desk state and exported layouts. */
(() => {
 const dialog=document.createElement('dialog');dialog.id='connectionsDialog';
 dialog.innerHTML=`<div class="modal-head"><div><div class="eyebrow">YOUR ACCOUNTS · YOUR DATA</div><h1>Connections</h1></div><button class="close" aria-label="Close connections">×</button></div><div class="connection-body"><aside><input id="connectionSearch" aria-label="Find a broker or exchange" placeholder="Find broker, exchange or feed…"><div id="connectionList"></div></aside><section id="connectionDetail" aria-live="polite"><p>Select a provider to see available connections.</p></section></div><div class="modal-foot">Public feeds need no login. Account access and exchange data permissions are separate.</div>`;
 document.body.append(dialog);
 let snapshot={providers:[],states:{}},selected='coinbase';
 const byId=id=>document.getElementById(id);
 function send(action,extra={}){if(liveSocket?.readyState===1)liveSocket.send(JSON.stringify({connections:{action,provider:selected,...extra}}));else notify('Local connection service is offline.');}
 function node(tag,text,cls){const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;}
 function renderList(){const list=byId('connectionList');list.replaceChildren();const query=byId('connectionSearch').value.toLowerCase();for(const p of snapshot.providers){if(!(p.name+' '+p.id+' '+(p.id==='interactive-brokers'?'IBKR TWS IB Gateway ':'')+p.category+' '+p.detail).toLowerCase().includes(query))continue;const b=node('button',null,'connection-provider'+(selected===p.id?' selected':''));b.append(node('strong',p.name),node('small',p.category+' · '+(snapshot.states[p.id]?.state||(p.method==='public'?'Public feed':p.method==='setup'||p.method==='route'?'Setup required':'Read-only API'))));b.onclick=()=>{selected=p.id;renderList();renderDetail();};list.append(b);}}
 function renderDetail(){const p=snapshot.providers.find(p=>p.id===selected),target=byId('connectionDetail');target.replaceChildren();if(!p)return;const current=snapshot.states[p.id];target.append(node('div',p.category,'eyebrow'),node('h2',p.name),node('p',p.detail,'connection-copy'));
 const status=node('div',current?.state||(p.method==='public'?'No account required':['setup','route'].includes(p.method)?'Setup required':'disconnected'),'connection-state');status.dataset.state=current?.state||'disconnected';target.append(status);if(current){target.append(node('p',current.message,'connection-copy'));if(current.checkedAt)target.append(node('p','Verified '+new Date(current.checkedAt*1000).toISOString().replace('T',' ').slice(0,19)+' UTC · '+current.environment+' · '+current.permission,'connection-meta'));}
 if(p.chartFeed){const charts=node('div',null,'connection-symbols');charts.append(node('p','Public charts · independent of account login'));for(const asset of ['BTC','ETH','SOL']){const b=node('button',asset+' '+(p.id==='hyperliquid'?'perpetual':'/ USD'),'primary');b.onclick=()=>{if(state.charts.length>=8){notify('This desk has eight charts. Remove one before adding another.');return;}const c=makeChart({asset,feed:p.chartFeed,contract:p.id==='hyperliquid'?'perp':'spot',w:1,h:1});if(NativeDesk.enabled&&state.charts.length){NativeDesk.add(c);dialog.close();return;}state.charts.push(c);dialog.close();render();arrange();saveSoon();};charts.append(b);}target.append(charts);}
 if(['kraken','deribit','binance'].includes(p.method)&&current?.state!=='connected'&&current?.state!=='connecting'){
 target.append(node('p','Development account adapter · protocol and error handling tested; no funded account has been used for verification.','connection-meta'));
 const form=document.createElement('form');form.autocomplete='off';
 const field=(label,id,type='password')=>{const wrap=node('label',label,'field');const input=document.createElement('input');input.id=id;input.type=type;input.autocomplete='off';input.spellcheck=false;input.maxLength=4096;input.required=true;wrap.append(input);form.append(wrap);return input;};
 const key=field(p.id==='deribit'?'Client ID':'API key','connectionKey');const secret=field(p.id==='deribit'?'Client secret':'Private API secret','connectionSecret');let otp=null;if(p.id==='kraken'){otp=field('API one-time code (only if enabled)','connectionOtp','password');otp.required=false;otp.maxLength=10;otp.inputMode='numeric';}
 const label=node('label','Environment','field'),env=document.createElement('select');env.id='connectionEnvironment';for(const e of p.environments){const o=node('option',e==='test'?'Testnet':'Live account · read only');o.value=e;env.append(o);}label.append(env);form.append(label);
 form.append(node('p','Use a dedicated read-only key. Secrets are held in this local service’s memory only, sent over TLS to this provider, and discarded when this page disconnects. They are never saved with a desk.','connection-copy'));
 const submit=node('button','Connect read only','primary');submit.type='submit';form.append(submit);form.onsubmit=e=>{e.preventDefault();const credentials={key:key.value.trim(),secret:secret.value.trim()};if(otp?.value)credentials.otp=otp.value;send('connect',{environment:env.value,credentials});key.value=secret.value='';if(otp)otp.value='';submit.disabled=true;};target.append(form);
 }
 if(current&&['connected','connecting','stale'].includes(current.state)){const b=node('button','Disconnect and discard credentials');b.onclick=()=>send('disconnect');target.append(b);}
 if(p.method==='ibkr')window.renderBrokerConnection?.(target);
 const guide=node('a','How to connect ↗','connection-guide');guide.href=p.guide;guide.target='_blank';guide.rel='noopener noreferrer';target.append(guide);
 if(['setup','route'].includes(p.method))target.append(node('p','This entry describes the required route. It does not claim an active Alpharch integration or ask for credentials it cannot use.','connection-meta'));
 }
 window.receiveConnections=data=>{snapshot=data;renderList();renderDetail();};
 byId('connectionSearch').oninput=renderList;
 dialog.querySelector('.close').onclick=()=>dialog.close();
 dialog.addEventListener('close',()=>{byId('connectionDetail').replaceChildren();});
 byId('connections').onclick=()=>{dialog.showModal();send('catalog');};
})();
