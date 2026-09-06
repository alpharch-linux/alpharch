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
