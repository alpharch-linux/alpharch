/* Chart colors never depend on a desktop theme. This module is also used by
 * import/layout validation and calculation-only tests. */
(function(root){
  'use strict';
  const hex=/^#[0-9a-f]{6}$/i;
  const keys=['background','panel','text','muted','grid','buy','sell','crosshair','accent','heatLow','heatMid','heatHigh'];
  const dark={background:'#0a111c',panel:'#121e2c',text:'#cad7e8',muted:'#8fa4bf',grid:'#7893b7',buy:'#a2ef75',sell:'#fc63a7',crosshair:'#cddbeb',accent:'#d8b77c',heatLow:'#415387',heatMid:'#936ac1',heatHigh:'#e7a064'};
  const light={background:'#f7f8fa',panel:'#e8edf3',text:'#253448',muted:'#536780',grid:'#63758b',buy:'#147a58',sell:'#bc3566',crosshair:'#324968',accent:'#806127',heatLow:'#7d99c3',heatMid:'#9974bb',heatHigh:'#b96929'};
  function colorsValid(value,allowed=keys){return !!value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(k=>allowed.includes(k)&&typeof value[k]==='string'&&hex.test(value[k]));}
  function valid(value){return value===undefined||!!value&&typeof value==='object'&&!Array.isArray(value)&&['dark','light','custom'].includes(value.mode)&&(value.base===undefined||['dark','light'].includes(value.base))&&(value.colors===undefined||colorsValid(value.colors))&&Object.keys(value).every(k=>['mode','base','colors'].includes(k));}
  function rgb(color){return [1,3,5].map(i=>parseInt(color.slice(i,i+2),16));}
  function luminance(color){return rgb(color).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);}
  function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
  function ink(background){return contrast(background,'#15202d')>contrast(background,'#ffffff')?'#15202d':'#ffffff';}
  function mix(a,b,t){return '#'+rgb(a).map((v,i)=>Math.round(v+(rgb(b)[i]-v)*t).toString(16).padStart(2,'0')).join('');}
  function rgba(color,alpha){return 'rgba('+rgb(color).join(',')+','+Math.max(0,Math.min(1,alpha))+')';}
  function resolve(value,palette={},legacy={}){
    const config=valid(value)&&value?value:{mode:'dark'},base=config.mode==='custom'?(config.base||'dark'):config.mode;
    const result={...(base==='light'?light:dark),...(base==='dark'?Object.fromEntries(['buy','sell','accent'].filter(k=>hex.test(palette[k]||'')).map(k=>[k,palette[k]])):{}),...Object.fromEntries(['buy','sell'].filter(k=>hex.test(legacy[k]||'')).map(k=>[k,legacy[k]])),...(config.colors||{})};
    return {...result,base,axis:result.panel,backgroundEnd:mix(result.background,result.panel,.25),row:mix(result.background,result.panel,.55),tagText:ink(result.accent)};
  }
  function presetValid(value){return !!value&&typeof value==='object'&&value.schema===1&&typeof value.name==='string'&&value.name.trim().length>0&&value.name.length<=60&&value.theme!==undefined&&valid(value.theme)&&Object.keys(value).every(k=>['schema','name','theme'].includes(k));}
  function snapshot(colors){return {mode:'custom',base:colors.base,colors:Object.fromEntries(keys.map(k=>[k,colors[k]]))};}
  const api={keys,dark,light,valid,colorsValid,resolve,snapshot,presetValid,contrast,ink,mix,rgba};
  root.ChartThemes=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
