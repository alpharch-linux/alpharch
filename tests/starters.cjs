const assert=require('node:assert/strict');
const {templates,layout}=require('../share/starters.js');
let uid=0;
const study=id=>({id,period:9,visible:true});
const chart=opts=>({id:++uid,...opts});
for(const t of templates){
 for(const [width,height] of [[1440,850],[1280,660],[800,650],[1200,550]]){
  const desk=layout(t.id,chart,study,width,height);
  assert.equal(desk.name,t.name);
  assert.equal(desk.charts.length,t.panels.length);
  assert.equal(new Set(desk.charts.map(c=>c.id)).size,desk.charts.length);
  for(const c of desk.charts){
   assert.equal(c.feed,'coinbase');assert.equal(c.contract,'spot');
   assert(c.x>=0&&c.y>=0&&c.x+c.w<=1.001&&c.y+c.h<=1.001);
   assert(c.w*width>=250&&c.h*height>=250,'usable desktop tile dimensions');
   assert(!('bars' in c)&&!('last' in c),'templates never contain market data');
   for(const other of desk.charts.filter(x=>x.id!==c.id))assert(c.x+c.w<=other.x+.001||other.x+other.w<=c.x+.001||c.y+c.h<=other.y+.001||other.y+other.h<=c.y+.001,'tiles must not overlap');
  }
 }
}
const btc=layout('bitcoin',chart,study);assert.deepEqual(btc.charts.map(c=>c.view),['candles','heat','tape']);assert(btc.charts.every(c=>c.asset==='BTC'&&c.link==='A'));
const overview=layout('overview',chart,study);assert.deepEqual(overview.charts.map(c=>c.asset),['BTC','ETH','SOL']);assert(overview.charts.every(c=>c.tf===300&&!c.link));assert(overview.charts.every(c=>c.studies.find(s=>s.id==='ema').period===20));
const changed=layout('single',chart,study);changed.charts[0].studies[0].visible=false;assert.equal(layout('single',chart,study).charts[0].studies[0].visible,true,'each desk owns independent studies');
assert.equal(layout('blank',chart,study).charts.length,0);assert.throws(()=>layout('missing',chart,study),RangeError);
console.log('Starting desks: exact feed identity, independent studies, matching overview timeframes, blank/no data and non-overlapping desktop layouts passed.');

// Exercise the page's launch path with saved desks and dedicated chart URLs.
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require('node:path').join(__dirname,'../share/desk.html'),'utf8');
const startup=html.slice(html.indexOf('function initializeDesk(){'),html.indexOf('function selectStarter('));
const dismissal=html.slice(html.indexOf('function finishStarterDismissal(){'),html.indexOf("$('resumeStarter').onclick"));
function launch(saved,hash='',native=false){
 const calls=[];
 const context={
  localStorage:{getItem:()=>saved,setItem:()=>assert.fail('Launch must not replace stored charts')},storageKey:'test',
  windowName:new URLSearchParams(hash).get('window'),launchParams:new URLSearchParams(hash),
  instruments:{BTC:{}},views:{candles:'Candles'},Intervals:require('../share/intervals.js'),
  NativeDesk:{enabled:native},starterPending:false,state:{name:'Initial',charts:[]},
  validLayout:value=>!!value&&typeof value.name==='string'&&Array.isArray(value.charts),
  restore(value){context.state=structuredClone(value);calls.push('restore')},
  render:()=>calls.push('render'),notify:()=>{},openStarters:()=>calls.push('chooser'),
  starter:()=>calls.push('first-desk'),makeChart:value=>value,saveSoon:()=>calls.push('save')
 };
 vm.runInNewContext(startup+'\n'+dismissal+'\ninitializeDesk();finishStarterDismissal();',context);
 return {calls,state:context.state};
}
const previous={name:'My morning desk',charts:[{id:7,tf:14400,drawings:[{type:'hline',price:6500.25}]}]};
for(const hash of ['', 'window=desk']){
 const result=launch(JSON.stringify(previous),hash);
 assert.deepEqual(result.calls,['restore','chooser']);
 assert.deepEqual(result.state,previous,'Opening or dismissing the chooser preserves the saved desk');
}
assert.deepEqual(launch(JSON.stringify({name:'My blank desk',charts:[]})).calls,['restore','chooser']);
assert.deepEqual(launch(null).calls,['first-desk']);
assert.deepEqual(launch('{broken').calls,['first-desk']);
const chartLaunch='window=btc&asset=BTC&feed=coinbase&view=candles&tf=60';
assert.deepEqual(launch(JSON.stringify(previous),chartLaunch).calls,['restore']);
assert.deepEqual(launch(null,chartLaunch).calls,['render']);
assert.deepEqual(launch(null,'window=desk&asset=missing').calls,['first-desk']);
// Native documents load independently; do not simulate dismissing a nonexistent chooser.
const nativeCalls=[];
vm.runInNewContext(startup+'\ninitializeDesk();',{
 localStorage:{getItem:()=>JSON.stringify(previous)},storageKey:'native',windowName:'native-chart',
 launchParams:new URLSearchParams('edition=hyprland&window=native-chart'),instruments:{},views:{},Intervals:{},
 NativeDesk:{enabled:true},starterPending:false,render:()=>nativeCalls.push('render'),notify:()=>{},
 validLayout:()=>assert.fail('Native charts must load their server document'),
 openStarters:()=>assert.fail('No chooser over native chart windows')
});
assert.deepEqual(nativeCalls,['render']);
console.log('Startup chooser: fresh, saved, blank, corrupt and explicit chart launches; saved drawings preserved; native chart windows open directly.');
