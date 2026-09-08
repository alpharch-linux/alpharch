/* Presentation only. Market data, saved chart state and native placement stay in
 * the desk engine. Controls are moved, never duplicated or given new shortcuts. */
const DeskSurface = (() => {
  const icons = {
    'zoom-out':'<path d="M5 10h10"/>',
    'zoom-in':'<path d="M5 10h10M10 5v10"/>',
    fit:'<path d="M7 3H3v4m10-4h4v4M3 13v4h4m10-4v4h-4"/><path d="m6 12 3-5 3 6 2-4"/>',
  };
  function mount(tile) {
    const toolbar = tile.querySelector('.chart-tools');
    for (const [name, paths] of Object.entries(icons)) {
      const button = toolbar.querySelector('.'+name);
      button.innerHTML = '<svg viewBox="0 0 20 20" aria-hidden="true">'+paths+'</svg>';
      button.classList.add('chart-icon');
    }
    const more = document.createElement('details'); more.className='chart-more';
    const summary = document.createElement('summary');
    summary.title='Chart settings and history'; summary.setAttribute('aria-label','Chart settings and history');
    summary.innerHTML='<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="4" cy="10" r="1"/><circle cx="10" cy="10" r="1"/><circle cx="16" cy="10" r="1"/></svg>';
    const menu = document.createElement('div'); menu.className='chart-more-menu';
    for (const selector of ['.tools','.history-control']) {
      const button = toolbar.querySelector(selector);
      if (button) { menu.append(button); button.addEventListener('click',()=>{more.open=false;}); }
    }
    const appearance=document.createElement('button');appearance.textContent='Chart theme & colors';appearance.type='button';appearance.setAttribute('aria-label','Theme and colors for this chart');appearance.onclick=()=>{more.open=false;window.ThemeUI?.open(state.charts.find(c=>c.id===Number(tile.dataset.id)));};menu.append(appearance);
    more.append(summary,menu); toolbar.append(more);
    more.addEventListener('keydown',event=>{if(event.key==='Escape'){more.open=false;summary.focus();event.stopPropagation();}});
    more.addEventListener('focusout',event=>{if(event.relatedTarget&&!more.contains(event.relatedTarget))more.open=false;});
    const study = tile.querySelector('.studies');
    study.innerHTML='<span aria-hidden="true">ƒ</span><span class="control-label">Indicators</span>';
    const instrument = tile.querySelector('.instrument');
    instrument.classList.add('instrument-picker');
  }
  function tint(tile,colors){
    const signature=['background','panel','text','muted','grid','buy','sell','accent'].map(k=>colors[k]).join(',');
    if(tile.dataset.chartColors===signature)return;
    tile.dataset.chartColors=signature;
    for(const key of ['background','panel','text','muted','grid','accent'])tile.style.setProperty('--chart-'+key,colors[key]);
    tile.style.setProperty('--buy',colors.buy);tile.style.setProperty('--sell',colors.sell);
  }
  function context(tile,c,market,source,partial){
    const table=['ladder','tape'].includes(c.view);
    if(tile.dataset.view!==c.view){
      tile.dataset.view=c.view;
      const toolbar=tile.querySelector('.chart-tools'),actions=tile.querySelector('.titlebar .actions'),more=tile.querySelector('.chart-more'),fit=tile.querySelector('.fit');
      if(table){actions.append(fit,more);}
      else{toolbar.insertBefore(fit,toolbar.querySelector('.auto-price'));toolbar.append(more);}
    }
    let strip=tile.querySelector('.chart-context');
    if(!strip){
      strip=document.createElement('div');strip.className='chart-context';
      const details=document.createElement('button');details.className='chart-data';details.type='button';
      details.innerHTML='<i aria-hidden="true"></i><span class="data-feed"></span><span class="data-state"></span><span class="data-coverage"></span>';
      details.onclick=()=>IntervalUI.openHistory(c);
      const tick=document.createElement('span');tick.className='chart-tick';
      strip.append(details,tick);tile.querySelector('.tile-body').append(strip);
    }
    const live=market.connected&&market.status==='receiving';
    const mode=market.replay?'Replay':!market.connected?'Disconnected':live?'Live':market.status||'Waiting';
    const warning=market.incomplete?'Capture gaps':partial&&!table?'Partial history':'';
    const signature=[c.feed,mode,warning,market.tick,source].join('|');
    if(strip.dataset.signature===signature)return;
    strip.dataset.signature=signature;strip.dataset.condition=market.replay?'replay':live?'live':'waiting';
    strip.querySelector('.data-feed').textContent=({coinbase:'Coinbase',hyperliquid:'Hyperliquid',kraken:'Kraken',ibkr:'IBKR'})[c.feed]||c.feed;
    strip.querySelector('.data-state').textContent=mode;
    strip.querySelector('.data-coverage').textContent=warning;
    strip.querySelector('.chart-data').title=source;
    strip.querySelector('.chart-data').setAttribute('aria-label','Data source and coverage for '+chartName(c)+' · '+mode+(warning?' · '+warning:''));
    strip.querySelector('.chart-tick').textContent='Tick '+marketTick(c);
  }
  function compact(value){return Number.isFinite(value)?value.toLocaleString('en-US',{maximumSignificantDigits:4,useGrouping:false}):'—';}
  return {mount,tint,context,compact};
})();
