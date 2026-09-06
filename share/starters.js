/* Starting desks contain layout and study settings only, never sample market data. */
(function (root) {
  'use strict';
  const templates = [
    {id:'bitcoin', name:'Bitcoin desk', tag:'A good first desk', description:'Price, resting liquidity and the trades going through. All on the same BTC/USD feed.', detail:'Coinbase spot · 1m candles · 15s heatmap · tape',
      panels:[
        {label:'BTC · price + volume', view:'candles', tf:60, x:0, y:0, w:.598, h:1, studies:['vwap','volume'], link:'A'},
        {label:'Liquidity heatmap', view:'heat', tf:15, x:.602, y:0, w:.398, h:.568, count:16, studies:[], link:'A'},
        {label:'Time & sales', view:'tape', tf:60, x:.602, y:.575, w:.398, h:.425, studies:[], link:'A'}]},
    {id:'overview', name:'Crypto overview', tag:'Three markets, one glance', description:'BTC, ETH and SOL side by side, with matching timeframes. Each chart stays independent.', detail:'Coinbase spot · three 5m charts · EMA 20 + volume',
      panels:['BTC','ETH','SOL'].map((asset,i)=>({label:asset+' · 5m',asset,view:'candles',tf:300,x:i/3,y:0,w:1/3-.004,h:1,studies:['ema','volume'],emaPeriod:20}))},
    {id:'single', name:'Single chart', tag:'Keep it simple', description:'One large Bitcoin chart and volume below. Add your own studies, levels and extra charts when you need them.', detail:'Coinbase spot · 1m candles · volume',
      panels:[{label:'BTC · price + volume',view:'candles',tf:60,x:0,y:0,w:1,h:1,studies:['volume']}]},
    {id:'blank', name:'Blank desk', tag:'Start from scratch', description:'An empty workspace. Choose each market and tool yourself.', detail:'No charts or market subscriptions', panels:[]}
  ];
  function layout(id, makeChart, study, width=1440, height=850) {
    const template=templates.find(t=>t.id===id);
    if(!template)throw new RangeError('Unknown starting desk');
    const charts=template.panels.map(({label,studies,emaPeriod,...panel})=>makeChart({...panel,asset:panel.asset||'BTC',feed:'coinbase',contract:'spot',studies:studies.map(id=>({...study(id),...(id==='ema'&&emaPeriod?{period:emaPeriod}:{})}))}));
    // Keep usable tiles on shorter laptops; never move a user's edited layout.
    if(charts.length>1&&(width<900||height<600)){
      const cols=Math.max(1,Math.min(charts.length,Math.floor(width/300))),rows=Math.ceil(charts.length/cols);
      charts.forEach((c,i)=>Object.assign(c,{x:(i%cols)/cols,y:Math.floor(i/cols)/rows,w:(i===charts.length-1&&charts.length%cols===1?1:1/cols)-.004,h:1/rows-.006}));
    }
    return {name:template.name,charts};
  }
  function freeze(value){Object.freeze(value);for(const v of Object.values(value))if(v&&typeof v==='object'&&!Object.isFrozen(v))freeze(v);return value;}
  const api=Object.freeze({templates:freeze(templates),layout});
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.AlpharchStarters=api;
})(globalThis);
