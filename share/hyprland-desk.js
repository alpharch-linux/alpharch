/* Two editions share the chart engine. Only Hyprland owns native window placement. */
const NativeDesk = (() => {
  'use strict';
  const enabled = new URLSearchParams(location.hash.slice(1)).get('edition') === 'hyprland';
  let ready = !enabled, counter = 0, selectedEdition = enabled ? 'hyprland' : 'classic';
  const pending = new Map();
  let availabilityTimer=null;
  function request(action, extra = {}) {
    if (liveSocket?.readyState !== 1) return Promise.reject(Error('The local service is disconnected.'));
    const id = ++counter, data = JSON.stringify({native:{id, action, ...extra}});
    if (new TextEncoder().encode(data).length > 65000) return Promise.reject(Error('This chart is too large to transfer. Export a layout to keep a backup.'));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(Error('The desktop did not respond. Check for an opened window before retrying.')); }, 120000);
      pending.set(id, {resolve, reject, timer});
      liveSocket.send(data);
    });
  }
  function receive(reply) {
    const task = pending.get(reply.id);
    if (!task) return;
    pending.delete(reply.id); clearTimeout(task.timer);
    if (reply.error) task.reject(Error(reply.error)); else task.resolve(reply.result);
  }
  function disconnected() {
    for (const p of pending.values()) { clearTimeout(p.timer); p.reject(Error('The local service disconnected.')); }
    pending.clear();
  }
  async function connected() {
    if($('starterDialog').open)chooser();
    if (!enabled || ready) return;
    try {
      const result = await request('read', {window:windowName});
      if (!validLayout(result.document) || result.document.charts.length > 1) throw Error('This Hyprland chart file could not be read. Your saved file is unchanged.');
      ready = true; starterPending = false; restore(result.document); syncMarkets();
      notify('Hyprland desk · New chart opens another tiled window.');
    } catch (error) { notify(error.message); }
  }
  async function save() {
    if (!enabled || !ready || starterPending || window.deskReplay) return;
    try { await request('write', {window:windowName, document:cleanState()}); }
    catch (error) { notify('Native chart not saved: '+error.message); }
  }
  async function open(value) {
    if (!validLayout(value)) throw Error('The chart settings could not be read.');
    return request('open', {document:value, ...(enabled ? {source:windowName} : {})});
  }
  async function add(chart) {
    try {
      $('submitChart').disabled = true;
      const result = await open({...cleanState(), charts:[chart]});
      $('newDialog').close(); notify(result.note);
    } catch (error) { notify(error.message); }
    finally { $('submitChart').disabled = false; }
  }
  function updateChoice() {
    if (!$('editionNote')) return;
    for (const b of document.querySelectorAll('[data-edition]')) b.setAttribute('aria-pressed', String(b.dataset.edition === selectedEdition));
    $('editionNote').textContent = selectedEdition === 'hyprland'
      ? 'One chart per real window. Omarchy handles tiling, shortcuts and monitors. Your Classic desk stays saved separately.'
      : enabled ? 'Return to your saved Classic desk. This Hyprland window stays open.' : 'Charts live together inside one window. Drag and resize them within the desk.';
    $('openStarter').textContent = enabled && selectedEdition === 'classic' ? 'Open Classic desk' : 'Open '+AlpharchStarters.templates.find(t=>t.id===chosenStarter).name+(selectedEdition==='hyprland'?' in Hyprland':'');
    $('starterChoices').hidden = enabled && selectedEdition === 'classic';
    $('starterFootnote').textContent=selectedEdition==='hyprland'?'Public crypto templates. These open a separate Hyprland desk; the current window stays as it is. Connect your futures data through Connect.':enabled?'Your existing Classic layout will open with its own saved charts.':'Your current desk is kept under Desk → Restore previous desk. Named layouts and your colors stay as they are.';
  }
  function chooser() {
    if (!$('editionChoices')) {
      const group = document.createElement('div'); group.id='editionChoices'; group.setAttribute('role','group'); group.setAttribute('aria-label','Desk style');
      group.innerHTML='<button type="button" data-edition="classic"><span class="edition-mark">▣</span><strong>Classic desk</strong><small>All your charts in one window</small></button><button type="button" data-edition="hyprland"><span class="edition-mark">▥</span><strong>Hyprland desk</strong><small>Separate windows · Omarchy tiling</small></button>';
      const note=document.createElement('p'); note.id='editionNote'; note.className='starter-intro';
      $('starterChoices').before(group,note);
      for (const b of group.querySelectorAll('button')) b.onclick=()=>{selectedEdition=b.dataset.edition;updateChoice();};
    }
    updateChoice();
    clearTimeout(availabilityTimer);
    request('catalog').then(result=>{
      const choice=document.querySelector('[data-edition="hyprland"]');
      choice.disabled=!result.available;
      choice.querySelector('small').textContent=result.available?'Separate windows · Omarchy tiling':'Waiting for your Hyprland desktop…';
      if(!result.available){if(!enabled){selectedEdition='classic';updateChoice();}retryAvailability();}
    }).catch(()=>{retryAvailability();});
  }
  function retryAvailability(){
    clearTimeout(availabilityTimer);
    if($('starterDialog').open)availabilityTimer=setTimeout(()=>{if($('starterDialog').open)chooser();},3000);
  }
  async function template() {
    $('openStarter').disabled = true;
    try {
      const result = selectedEdition === 'classic'
        ? await request('classic')
        : await open({...cleanState(), ...AlpharchStarters.layout(chosenStarter,makeChart,study,stage.clientWidth,stage.clientHeight)});
      $('starterStatus').textContent=result.note;window.dispatchEvent(new Event('alpharch:desk-opened'));
      // Keep the Classic desk and its opening chooser intact. It remains the
      // easy way back while the compositor switches to the separate workspace.
      notify(result.note);
    } catch(error){$('starterStatus').textContent=error.message;}
    finally{$('openStarter').disabled=false;}
  }
  async function menu() {
    try {
      const data=await request('catalog');
      popup([
        {label:'Choose a starting desk…',action:()=>openStarters()},
        {label:'Save Hyprland desk…',action:openSave},
        ...data.layouts.map(name=>({label:'Restore · '+name,action:async()=>{try{notify((await request('load',{name})).note);}catch(e){notify(e.message);}}})),
        {label:'Export this chart',action:exportLayout},
        {label:'Import charts as windows…',action:()=>$('importLayoutFile').click()},
        {label:'Omarchy window controls',action:()=>$('nativeHelp').showModal()}
      ]);
    }catch(error){notify(error.message);}
  }
  function openSave(){ $('nativeName').value='my-desk';$('nativeSaveStatus').textContent='';$('nativeSaveDialog').showModal();$('nativeName').focus(); }
  function mount() {
    if(!enabled)return;
    document.body.classList.add('hyprland-edition');
    $('newChart').title='New chart window (Ctrl+N)';
    $('arrange').hidden=true;
    $('help').textContent='Keys';$('help').onclick=()=>$('nativeHelp').showModal();
    $('layouts').textContent='Desk';$('layouts').onclick=e=>{e.stopPropagation();menu();};
    const badge=document.createElement('span');badge.className='native-badge';badge.textContent='HYPRLAND';document.querySelector('header .brand').after(badge);
    const help=document.createElement('dialog');help.id='nativeHelp';help.innerHTML='<div class="modal-head"><h2>Your desktop is the workspace.</h2><button class="close" aria-label="Close window controls">×</button></div><div class="native-help-content"><p>Each chart is a separate app window. Use your existing Omarchy bindings to focus, tile, group and move it between monitors.</p><dl><dt>Super + arrows</dt><dd>Focus another window</dd><dt>Super + Shift + arrows</dt><dd>Swap tiled windows</dd><dt>Super + right-drag</dt><dd>Resize a window</dd><dt>Super + left-drag</dt><dd>Move a window</dd><dt>Super + F</dt><dd>Fullscreen the focused chart</dd><dt>Ctrl + N</dt><dd>New chart window</dd><dt>Ctrl + Shift + S</dt><dd>Save Hyprland desk</dd></dl><p>These are Omarchy’s usual bindings; your own custom bindings take precedence. The chart toolbar controls zoom, drawings and studies.</p><p>Save a Hyprland desk to keep charts, drawings, indicators and workspace/monitor assignments. Hyprland determines the tile proportions when windows reopen.</p></div>';
    const saveDialog=document.createElement('dialog');saveDialog.id='nativeSaveDialog';saveDialog.innerHTML='<form id="nativeSaveForm"><div class="modal-head"><h2>Save Hyprland desk</h2><button type="button" class="close" aria-label="Close save desk">×</button></div><div class="native-help-content"><label>Desk name <input id="nativeName" required maxlength="48" pattern="[A-Za-z0-9_-]+" placeholder="my-desk"></label><p>All open Hyprland charts, including their drawings, indicators and display assignments. Existing desks with the same name are updated.</p><p id="nativeSaveStatus" role="status"></p><button class="primary" type="submit">Save desk</button></div></form>';
    document.body.append(help,saveDialog);for(const d of[help,saveDialog])d.querySelector('.close').onclick=()=>d.close();
    // Ask sibling windows to flush first; replies form a barrier before the
    // server snapshots all documents. An unresponsive window is reported.
    $('nativeSaveForm').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await flushAll();const result=await request('save',{name:$('nativeName').value});notify(result.note);saveDialog.close();}catch(error){$('nativeSaveStatus').textContent=error.message;}finally{button.disabled=false;}};
    document.addEventListener('keydown',e=>{if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key.toLowerCase()==='n'||e.shiftKey&&e.key.toLowerCase()==='s')){e.preventDefault();if(!document.querySelector('dialog[open]')){if(e.key.toLowerCase()==='n')openNew();else openSave();}}});
    $('importLayoutFile').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>60000)throw Error('Open chart files of 60 KB or less.');notify((await open(JSON.parse(await file.text()))).note);}catch(error){notify(error.message);}e.target.value='';};
  }
  const channel=typeof BroadcastChannel==='function'?new BroadcastChannel('alpharch.hyprland.save.v1'):null;
  const flushes=new Map();
  if(channel)channel.onmessage=async e=>{
    if(!enabled||!ready)return;
    const m=e.data;
    if(m?.type==='flush'&&m.sender!==windowName&&!window.deskReplay){try{await request('write',{window:windowName,document:cleanState()});channel.postMessage({type:'flushed',id:m.id,window:windowName});}catch{}}
    if(m?.type==='flushed')flushes.get(m.id)?.delete(m.window);
  };
  async function flushAll(){
    if(window.deskReplay)throw Error('Return to live before saving the Hyprland desk.');
    await request('write',{window:windowName,document:cleanState()});
    const data=await request('catalog'), waiting=new Set(data.windows.filter(w=>w!==windowName)), id=Date.now();
    flushes.set(id,waiting);
    try {
      channel?.postMessage({type:'flush',sender:windowName,id});
      for(let i=0;i<40&&waiting.size;i++)await new Promise(resolve=>setTimeout(resolve,100));
      if(waiting.size)throw Error('Some charts could not confirm their latest changes. Keep this desk’s windows on the same local service and try again.');
    }finally{flushes.delete(id);}
  }
  function replayCharts(charts){
    $('nativeReplayStream')?.remove();
    if(charts.length<2)return charts;
    const select=document.createElement('select');select.id='nativeReplayStream';select.setAttribute('aria-label','Replay chart stream');
    charts.forEach((c,i)=>select.add(new Option(chartName(c),String(i))));
    select.onchange=()=>{state.charts=[charts[+select.value]];selected=null;render();};
    $('sessionBar').prepend(select);
    notify('This window shows one replay stream. Choose another in the replay bar. Other windows keep their own sessions.');
    return [charts[0]];
  }
  return {enabled,get ready(){return ready;},get interceptTemplate(){return enabled||selectedEdition==='hyprland';},receive,disconnected,connected,save,open,add,chooser,updateChoice,template,mount,replayCharts,openSave,menu};
})();
