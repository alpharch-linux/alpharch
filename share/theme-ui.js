/* Window chrome follows Omarchy independently of each chart's saved theme. */
window.ThemeUI=(() => {
  'use strict';
  const libraryKey='alpharch.chart-themes.v1';
  let desktop=null,watchSocket=null,watchValue=null,dialog=null,target=null,scope='chart',nameInput,presetSelect,preview,status;
  const fields=new Map();
  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  function library(){try{const value=JSON.parse(localStorage.getItem(libraryKey)||'[]');return Array.isArray(value)?value.filter(ChartThemes.presetValid).slice(0,50):[];}catch{return [];}}
  function setStatus(text){if(status)status.textContent=text;}
  function saveLibrary(value){try{localStorage.setItem(libraryKey,JSON.stringify(value));return true;}catch{setStatus('Browser storage is unavailable. Export your theme to keep a copy.');return false;}}
  function current(){return target&&state.charts.includes(target)?target:null;}
  function config(){return structuredClone(current()?.chartTheme||appearance().chartTheme||{mode:'dark'});}
  function apply(value){
    if(!ChartThemes.valid(value))return;
    if(scope==='all'||!current()){state.appearance={...appearance(),chartTheme:structuredClone(value)};for(const c of state.charts)delete c.chartTheme;}
    else current().chartTheme=structuredClone(value);
    theme();saveSoon();refresh();
  }
  function watch(){
    const enabled=(appearance().chrome||'omarchy')==='omarchy';
    if(liveSocket?.readyState===1&&(liveSocket!==watchSocket||watchValue!==enabled)){
      liveSocket.send(JSON.stringify({omarchyTheme:{watch:enabled}}));watchSocket=liveSocket;watchValue=enabled;
    }
  }
  function chrome(){
    const a=appearance(),mode=a.chrome||'omarchy';
    const available=mode==='omarchy'&&desktop?.available;
    const custom=mode==='custom'&&ChartThemes.colorsValid(a.chromeColors||{},['background','foreground','accent']);
    const colors=available?desktop.colors:custom?a.chromeColors:null;
    document.body.classList.toggle('themed-chrome',!!colors);
    if(colors){
      const bg=colors.background||'#151f2c',accent=colors.accent||'#d9bc81';
      let fg=colors.foreground||ChartThemes.ink(bg);if(ChartThemes.contrast(bg,fg)<4.5)fg=ChartThemes.ink(bg);
      const values={bg,text:fg,accent,soft:ChartThemes.mix(bg,fg,.075),edge:ChartThemes.mix(bg,fg,.22),muted:ChartThemes.mix(bg,fg,.75),selected:ChartThemes.mix(bg,accent,.15),onAccent:ChartThemes.ink(accent)};
      for(const [k,v]of Object.entries(values))document.body.style.setProperty('--chrome-'+k,v);
    }
    const label=document.getElementById('desktopThemeStatus');
    if(label)label.textContent=mode==='omarchy'?(available?'Following '+desktop.name+' · window bars only':'Omarchy theme unavailable · using Alpharch window bars'):mode==='custom'?'Your window-bar colors':'Alpharch window bars';
  }
  function sync(){chrome();watch();}
  function receive(value){
    if(value?.available&&ChartThemes.colorsValid(value.colors,['background','foreground','accent','lighter_background'])&&['background','foreground','accent'].every(k=>value.colors[k]))desktop={...value,name:typeof value.name==='string'?value.name.slice(0,80):'Omarchy'};
    else desktop={available:false};
    chrome(); // Deliberately no chart-state edits, redraw, layout reset or reload.
  }
  function fillPresets(selected=''){
    presetSelect.replaceChildren(new Option('Choose a saved theme…',''));
    for(const [i,p]of library().entries())presetSelect.add(new Option(p.name,String(i)));
    presetSelect.value=selected;
    const remove=dialog.querySelector('[data-theme-delete]');if(remove)remove.disabled=selected==='';
  }
  function refresh(){
    if(!dialog)return;const colors=chartColors(current()),value=config();
    for(const [key,input]of fields)input.value=colors[key];
    for(const b of dialog.querySelectorAll('[data-chart-mode]'))b.setAttribute('aria-pressed',String(value.mode===b.dataset.chartMode));
    preview.style.setProperty('--preview-bg',colors.background);preview.style.setProperty('--preview-panel',colors.panel);preview.style.setProperty('--preview-text',colors.text);preview.style.setProperty('--preview-buy',colors.buy);preview.style.setProperty('--preview-sell',colors.sell);preview.style.setProperty('--preview-grid',ChartThemes.rgba(colors.grid,.25));
    const weak=['text','muted','buy','sell'].filter(k=>ChartThemes.contrast(colors.background,colors[k])<(k==='text'?4.5:3));
    dialog.querySelector('.theme-contrast').textContent=weak.length?'Low contrast against the chart background: '+weak.map(k=>({text:'labels',muted:'secondary labels',buy:'up / buy',sell:'down / sell'}[k])).join(', ')+'. You can adjust these below.':'';
    chrome();
  }
  function colorField(key,label,parent,callback,value){
    const row=el('label'),text=el('span',label),input=el('input');input.type='color';input.value=value;input.setAttribute('aria-label',label);row.append(text,input);parent.append(row);input.addEventListener('input',()=>callback(input.value));return input;
  }
  function open(c=active()){
    dialog?.remove();target=c||null;scope=c?'chart':'all';fields.clear();
    dialog=el('dialog');dialog.id='appearanceDialog';dialog.setAttribute('aria-label','Chart and window appearance');
    const head=el('div');head.className='modal-head';head.append(el('h1','Make it yours.'));const close=el('button','×');close.className='close';close.setAttribute('aria-label','Close appearance');close.onclick=()=>dialog.close();head.append(close);dialog.append(head);
    const body=el('div');body.className='theme-editor';dialog.append(body);
    const windowSection=el('section');windowSection.className='theme-window';body.append(windowSection);
    const windowLabel=el('label','Window bars'),windowSelect=el('select');windowSelect.setAttribute('aria-label','Window bar theme');for(const [value,label]of [['omarchy','Follow Omarchy'],['alpharch','Alpharch'],['custom','Custom colors']])windowSelect.add(new Option(label,value));windowSelect.value=appearance().chrome||'omarchy';windowLabel.append(windowSelect);windowSection.append(windowLabel);
    const desktopStatus=el('p');desktopStatus.id='desktopThemeStatus';windowSection.append(desktopStatus);
    const customWindow=el('div');customWindow.className='theme-color-grid';customWindow.hidden=windowSelect.value!=='custom';windowSection.append(customWindow);
    for(const [key,label,fallback]of [['background','Window bar background','#151f2c'],['foreground','Window bar text','#dce6f2'],['accent','Window bar accent','#d9bc81']])colorField(key,label,customWindow,value=>{state.appearance={...appearance(),chromeColors:{...appearance().chromeColors,[key]:value}};sync();saveSoon();},appearance().chromeColors?.[key]||fallback);
    windowSelect.onchange=()=>{state.appearance={...appearance(),chrome:windowSelect.value};customWindow.hidden=windowSelect.value!=='custom';if(windowSelect.value==='custom'&&!state.appearance.chromeColors)state.appearance.chromeColors={background:'#151f2c',foreground:'#dce6f2',accent:'#d9bc81'};sync();saveSoon();};
    const chartSection=el('section');body.append(chartSection);const heading=el('div');heading.className='theme-section-heading';heading.append(el('h2','Chart theme'));const scopeSelect=el('select');scopeSelect.setAttribute('aria-label','Apply chart appearance to');if(c)scopeSelect.add(new Option('This chart · '+chartName(c),'chart'));scopeSelect.add(new Option('All charts in this window + new charts','all'));scopeSelect.value=scope;scopeSelect.onchange=()=>{scope=scopeSelect.value;};heading.append(scopeSelect);chartSection.append(heading);
    const modes=el('div');modes.className='theme-mode-buttons';modes.setAttribute('role','group');modes.setAttribute('aria-label','Chart light or dark theme');for(const [value,label]of [['dark','Dark chart'],['light','Light chart']]){const b=el('button',label);b.dataset.chartMode=value;b.onclick=()=>{apply({mode:value});setStatus(label+' applied. Your indicators and drawings keep their own colors.');};modes.append(b);}chartSection.append(modes);
    preview=el('div');preview.className='theme-preview';preview.setAttribute('aria-label','Chart color preview');preview.append(el('span','Aa · 0123456789'));const buys=el('b','UP / BUY'),sells=el('b','DOWN / SELL');buys.className='preview-buy';sells.className='preview-sell';preview.append(buys,sells);chartSection.append(preview);const contrast=el('p');contrast.className='theme-contrast';contrast.setAttribute('role','status');chartSection.append(contrast);
    const colors=el('div');colors.className='theme-color-grid';chartSection.append(colors);
    const labels={background:'Chart background',panel:'Price scale & study backgrounds',text:'Price & axis labels',muted:'Secondary labels',grid:'Grid lines',buy:'Up candle / buy',sell:'Down candle / sell',crosshair:'Crosshair',accent:'Chart highlights',heatLow:'Heatmap · low depth',heatMid:'Heatmap · medium depth',heatHigh:'Heatmap · high depth'};
    for(const key of ChartThemes.keys){const input=colorField(key,labels[key],colors,value=>{const now=chartColors(current());apply({mode:'custom',base:now.base,colors:{...Object.fromEntries(ChartThemes.keys.map(k=>[k,now[k]])),[key]:value}});},chartColors(c)[key]);fields.set(key,input);}
    const note=el('p','Omarchy changes window bars only. Chart colors stay saved with your layout. Edit individual indicator and drawing colors in their own tools.');note.className='theme-note';chartSection.append(note);
    const rendering=el('details');rendering.className='theme-rendering';rendering.append(el('summary','Rendering, color palettes & motion'));
    const paletteLabel=el('label','Candle color palette'),paletteSelect=el('select');paletteSelect.setAttribute('aria-label','Candle color palette');paletteSelect.add(new Option('Choose colors…',''));for(const [key,p]of Object.entries(palettes))paletteSelect.add(new Option(p.label+' · '+p.detail,key));paletteSelect.onchange=()=>{const p=palettes[paletteSelect.value];if(!p)return;const now=chartColors(current());apply({mode:'custom',base:now.base,colors:{...Object.fromEntries(ChartThemes.keys.map(k=>[k,now[k]])),buy:p.buy,sell:p.sell,accent:p.accent}});};paletteLabel.append(paletteSelect);rendering.append(paletteLabel);
    for(const [key,label,min,max,step]of [['heat','Heat intensity',.3,2,.1],['grid','Default grid contrast',0,1,.05],['glow','Candle glow',0,1,.1]]){const row=el('label',label),input=el('input');Object.assign(input,{type:'range',min,max,step,value:appearance()[key]});input.setAttribute('aria-label',label);input.oninput=()=>{state.appearance={...appearance(),[key]:+input.value};theme();saveSoon();};row.append(input);rendering.append(row);}
    const candleLabel=el('label','Candle style'),candleSelect=el('select');candleSelect.setAttribute('aria-label','Candle style');candleSelect.add(new Option('Filled','filled'));candleSelect.add(new Option('Hollow up','hollow'));candleSelect.value=appearance().candles;candleSelect.onchange=()=>{state.appearance={...appearance(),candles:candleSelect.value};theme();saveSoon();};candleLabel.append(candleSelect);rendering.append(candleLabel);
    const motionLabel=el('label','Interface motion'),motion=el('input');motion.type='checkbox';motion.checked=appearance().motion;motion.setAttribute('aria-label','Interface motion');motion.onchange=()=>{state.appearance={...appearance(),motion:motion.checked};theme();saveSoon();};motionLabel.append(motion);rendering.append(motionLabel,el('p','Rendering and motion apply throughout this window. Individual chart grid settings take precedence.'));chartSection.append(rendering);
    const presets=el('section');presets.className='theme-library';presets.append(el('h2','Your saved themes'));presetSelect=el('select');presetSelect.setAttribute('aria-label','Saved chart themes');presets.append(presetSelect);presetSelect.onchange=()=>{const chosen=library()[+presetSelect.value];if(presetSelect.value!==''&&chosen){nameInput.value=chosen.name;apply(chosen.theme);setStatus('Applied '+chosen.name+'.');}dialog.querySelector('[data-theme-delete]').disabled=presetSelect.value==='';};
    const nameRow=el('div');nameRow.className='theme-save-row';nameInput=el('input');nameInput.type='text';nameInput.maxLength=60;nameInput.placeholder='Name your theme';nameInput.setAttribute('aria-label','Theme name');const save=el('button','Save theme');save.className='primary';save.onclick=()=>{const name=nameInput.value.trim();if(!name){setStatus('Give your theme a name first.');nameInput.focus();return;}const list=library(),item={schema:1,name,theme:ChartThemes.snapshot(chartColors(current()))},i=list.findIndex(p=>p.name===name);if(i<0&&list.length>=50){setStatus('You have 50 saved themes. Delete one or reuse an existing name.');return;}if(i<0)list.push(item);else list[i]=item;if(saveLibrary(list)){fillPresets(String(i<0?list.length-1:i));setStatus('Saved “'+name+'”'+(i<0?'':' · replaced the previous version')+'.');}};nameRow.append(nameInput,save);presets.append(nameRow);
    const actions=el('div');actions.className='theme-file-actions';const remove=el('button','Delete saved theme');remove.dataset.themeDelete='';remove.disabled=true;remove.onclick=()=>{if(presetSelect.value==='')return;const list=library(),removed=list.splice(+presetSelect.value,1)[0];if(removed&&saveLibrary(list)){fillPresets();setStatus('Deleted “'+removed.name+'” from saved themes. Its colors stay on this chart.');}};
    const exportButton=el('button','Export theme');exportButton.onclick=()=>{const data={schema:1,name:nameInput.value.trim()||'My chart theme',theme:ChartThemes.snapshot(chartColors(current()))},url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=el('a');a.href=url;a.download='alpharch-chart-theme.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    const file=el('input');file.type='file';file.accept='.json,application/json';file.hidden=true;file.setAttribute('aria-label','Import chart theme file');const importButton=el('button','Import theme');importButton.onclick=()=>file.click();file.onchange=async()=>{const f=file.files?.[0];if(!f)return;try{if(f.size>16384)throw Error();const item=JSON.parse(await f.text());if(!ChartThemes.presetValid(item))throw Error();apply(item.theme);nameInput.value=item.name;presetSelect.value='';remove.disabled=true;setStatus('Imported “'+item.name+'”. Save theme to add it to your library.');}catch{setStatus('Could not read that theme. Choose an Alpharch chart-theme JSON file under 16 KB.');}file.value='';};actions.append(importButton,exportButton,remove,file);presets.append(actions);body.append(presets);
    status=el('p');status.className='theme-status';status.setAttribute('role','status');body.append(status);
    const footer=el('div');footer.className='theme-footer';footer.append(el('span','Changes save automatically with your chart.'));const done=el('button','Done');done.className='primary';done.onclick=()=>dialog.close();footer.append(done);dialog.append(footer);
    document.body.append(dialog);fillPresets();refresh();dialog.showModal();
  }
  $('palette').textContent='Style';$('palette').title='Chart themes and window appearance';$('palette').setAttribute('aria-label','Chart themes and window appearance');$('palette').onclick=()=>open();
  window.addEventListener('storage',event=>{if(event.key===libraryKey&&dialog?.open)fillPresets();});
  sync();
  return {open,sync,receive};
})();
