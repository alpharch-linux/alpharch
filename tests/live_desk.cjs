const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'../share/desk.html'),'utf8');const js=html.split('<script>')[1].split('</script>')[0];new vm.Script(js);const pure=js.split('function starter()')[0];const context={document:{getElementById:()=>({})},location:{hash:''},URLSearchParams,assert};vm.createContext(context);
vm.runInContext(pure+`
liveMarkets['coinbase:BTC']={tick:.01,bars:[{t:120,o:100,h:101,l:100,c:101,v:3,buy:2,sell:1,pv:302,footprint:[[100,1,0],[101,0,2]]},{t:135,o:101,h:102,l:101,c:102,v:1,buy:1,sell:0,pv:102,footprint:[[102,0,1]]}],historical:[{t:60,o:99,h:100,l:98,c:99,v:10,buy:null,sell:null,historical:true}]};
const c={asset:'BTC',feed:'coinbase',tf:60},bars=barsFor(c);assert.equal(bars.length,2);assert.equal(bars[0].buy,null);assert.equal(bars[1].v,4);assert.equal(bars[1].buy,3);assert.equal(bars[1].sell,1);assert.equal(bars[1].pv,404);assert.deepEqual(bars[1].footprint,[[100,1,0],[101,0,2],[102,0,1]]);
assert.deepEqual(calculate(study('delta'),bars)[0],[null,2]);assert.deepEqual(calculate(study('cvd'),bars)[0],[null,2]);assert.deepEqual(calculate(study('vwap'),bars)[0],[null,101]);assert.equal(price(100.01,c),'100.01');assert.equal(snap(100.006,.01),100.01);assert.equal(String(snap(2474.45,.01)),'2474.45');assert.equal(String(snap(1.00026,.00025)),'1.00025');
assert.equal(barsFor({...c,tf:15}).length,2);assert(barsFor({...c,tf:15}).every(b=>!b.historical));assert.equal(barsFor({asset:'SOL',feed:'coinbase',tf:60}).length,0);

const grouped=groupFootprint([[100.01,.00000015,2],[100.02,3,.00000025],[100.11,4,5]],.01,10);assert.equal(grouped.length,2);assert(Math.abs(grouped.reduce((n,r)=>n+r[1]+r[2],0)-14.0000004)<1e-10,'grouping conserves every quantity');assert.equal(niceGrouping(1066),2000);assert(crossing(99,100,100,'above'));assert(!crossing(100,101,100,'above'));assert(crossing(101,100,100,'below'));assert(!crossing(99,99,100,'above'));
const nav={...c,count:20,until:null},history=Array.from({length:100},(_,i)=>({t:i*60}));
const before=timeWindow(nav,history),anchor=before.from+before.span*.3;zoomTime(nav,history,.5,.3);const after=timeWindow(nav,history);assert(Math.abs(after.from+after.span*.3-anchor)<1e-8,'time zoom keeps cursor timestamp');assert.equal(nav.count,10);
const held=nav.until;history.push({t:6000});assert.equal(timeWindow(nav,history).to,held,'new bars do not move history');
nav.until=null;assert.equal(timeWindow(nav,history).to,6060,'live follows latest');
zoomPrice(nav,{low:100,high:200},.5,.25);assert.equal(nav.priceRange.high,187.5);assert.equal(nav.priceRange.low,137.5);assert.equal(nav.priceRange.high-(nav.priceRange.high-nav.priceRange.low)*.25,175);
liveMarkets['coinbase:BTC'].tick=.00025;assert.equal(price(1.23425,c),'1.23425');
nav.count=1;zoomTime(nav,history,.01);assert.equal(nav.count,1);nav.count=2000;zoomTime(nav,history,10);assert.equal(nav.count,2000);
const gap=timeWindow({...c,count:5,until:null},[{t:60},{t:300}]);assert.equal(gap.span,300);assert.equal(gap.from,60,'missing intervals retain their elapsed time');

// SPECIMEN calculation vectors remain confined to this test VM.
const sample=[1,2,3,4,5,6,7,8].map((v,i)=>({t:100+i,o:v-.5,h:v+1,l:v-1,c:v,v:1}));
const bb={...study('bollinger'),period:3,deviations:2};
const band=calculate(bb,sample);assert.deepEqual(band[0].slice(0,4),[null,null,2,3]);
assert(Math.abs(band[1][2]-(2+2*Math.sqrt(2/3)))<1e-12);assert(Math.abs(band[2][2]-(2-2*Math.sqrt(2/3)))<1e-12);
bb.deviations=1;assert(Math.abs(calculate(bb,sample)[1][2]-(2+Math.sqrt(2/3)))<1e-12,'deviation edit invalidates cache');
bb.source='o';assert.equal(calculate(bb,sample)[0][2],1.5,'Bollinger source selection');
const flat=sample.map(b=>({...b,o:10,h:10,l:10,c:10}));assert.deepEqual(calculate(bb,flat).map(v=>v.at(-1)),[10,10,10]);
const st={...study('stochastic'),period:3,smoothK:2,smoothD:2};
const varied=[0,10,20,30,40,50].map((c,i)=>({t:i+1,o:c,h:100,l:0,c,v:1}));
assert.deepEqual(calculate(st,varied),[[null,null,null,25,35,45],[null,null,null,null,30,40]]);
st.smoothK=1;assert.deepEqual(calculate(st,varied)[0],[null,null,20,30,40,50],'smoothing edit invalidates cache');
assert.equal(calculate(st,flat)[0].at(-1),50,'zero-range stochastic neutral');
assert.deepEqual(calculate(st,[]),[[],[]]);assert.deepEqual(calculate(bb,[]),[[],[],[]]);
for(const studyConfig of[bb,st])assert.deepEqual(calculate(studyConfig,sample).map(v=>v.slice(0,5)),calculate(studyConfig,sample.slice(0,5)),'prefix consistency without lookahead');
const eventChart={...c,aggregation:{kind:'ticks',size:1},count:4,until:null};
const equalTimes=[0,1,2,3].map(i=>({...sample[i],t:1700000000.123456,end:1700000000.123456,startId:'trade-'+i,complete:true}));
eventBarData.set('coinbase:BTC:ticks:1',equalTimes);
const slots=barsFor(eventChart);assert.deepEqual(slots.map(b=>b.t),[1,2,3,4]);assert(slots.every((b,i)=>!i||b.t>=slots[i-1].end),'equal timestamps never overlap');
assert(slots.every(b=>b.exchangeT===1700000000.123456));assert.equal(timeWindow(eventChart,slots).span,4);assert.equal(timeWindow(eventChart,slots).to,5);
assert.equal(candleDirection(eventChart,{o:100,c:100,trades:1},{c:101}),-1,'one-trade drop uses previous close');assert.equal(candleDirection(eventChart,{o:100,c:100,trades:1},{c:99}),1);assert.equal(candleDirection(eventChart,{o:100,c:100,trades:1},{c:100}),0);assert.equal(candleDirection(eventChart,{o:100,c:100,trades:1}),0);assert.equal(candleDirection(eventChart,{o:99,c:100,trades:2},{c:101}),1,'multi-trade candle keeps open/close semantics');assert.equal(candleDirection(c,{o:99,c:100,trades:1},{c:101}),1,'time candles keep open/close semantics');
const second=axisPoint(eventChart,2.5);assert.equal(second.t,1700000000.123456);assert.equal(second.eventId,'trade-1');assert.equal(timeAxis(eventChart,second.t,second),2.5,'duplicate-time drawing keeps its particular bar');
zoomTime(eventChart,slots,.5,.25);const eventWin=timeWindow(eventChart,slots);assert.equal(eventWin.from+eventWin.span*.25,2,'event zoom keeps cursor slot');
const pinned=eventChart.until;equalTimes.push({...equalTimes[0],startId:'trade-4'});eventBarData.set('coinbase:BTC:ticks:1',[...equalTimes]);assert.equal(timeWindow(eventChart,barsFor(eventChart)).to,pinned,'live event append preserves pinned viewport');
for(const kind of['volume','range']){const chart={...eventChart,aggregation:{kind,size:1},until:null};eventBarData.set('coinbase:BTC:'+kind+':1',equalTimes);const rows=barsFor(chart);assert.equal(new Set(rows.map(b=>b.t)).size,rows.length);assert.equal(axisTime(chart,2.5),equalTimes[1].t)}
assert.equal(timeAxis(c,120),120);assert.equal(axisTime(c,120),120,'time chart axis unchanged');
const shifted=equalTimes.slice(1);eventChart.until=3;eventBarData.set('coinbase:BTC:ticks:1',shifted);barsFor(eventChart);assert.equal(eventChart.until,null,'retained history rollover resets stale viewport');assert.equal(timeAxis(eventChart,second.t,second),1.5,'drawing anchors follow retained trade identity');
`,context);
assert(!js.includes('function fixture('));assert(!js.includes('Math.random'));
console.log('Live desk: source isolation, timeframe aggregation, exact footprints, historical unknown-side handling, true trade-weighted VWAP, price formatting, cursor-anchored zoom, live/history anchoring, price zoom and elapsed-time gaps passed.');

vm.runInContext(js.slice(js.indexOf('function validLayout('),js.indexOf('function restore('))+`
const savedChart={...makeChart({w:1}),studies:[{...study('bollinger'),deviations:2.5,upperColor:'#123456',lowerColor:'#654321'},{...study('stochastic'),smoothK:4,smoothD:5,signalColor:'#abcdef',pane:true}]};const saved={name:'SPECIMEN layout',palette:'pit',charts:[savedChart]};const roundtrip=JSON.parse(JSON.stringify(saved));assert(validLayout(roundtrip));assert.deepEqual(roundtrip,saved);roundtrip.charts[0].studies[1].smoothD=0;assert(!validLayout(roundtrip),'reject malformed smoothing');roundtrip.charts[0].studies[1].smoothD=5;roundtrip.charts[0].studies[0].deviations=Infinity;assert(!validLayout(roundtrip),'reject malformed deviations');
`,context);
console.log('Bollinger/stochastic calculations, warm-up, cache edits, saved settings, sequential event slots and exact exchange-time mapping passed.');
