// SPECIMEN geometry and interval vectors only; no fabricated data enters the desk.
const assert=require('node:assert/strict'),D=require('../share/drawing-tools.js'),I=require('../share/intervals.js'),G=require('../share/chart-grid.js');
const point=(p,t=100)=>({p,t}),drawing=(type,points,extra={})=>({type,text:'',points,...extra});
const r={L:0,R:200,T:0,B:200},env={r,x:p=>p.t,y:p=>200-p,format:p=>String(p),tick:.25,snap:p=>Math.round(p*4)/4};
for(const tool of D.catalog){const points=tool.id==='shortposition'?[point(100),point(110,110),point(80,150)]:[point(100),point(90,110),point(120,150)];const d=drawing(tool.id,points.slice(0,tool.anchors||2),{style:{...D.defaults}});assert(D.valid(d),tool.id+' accepts its anchors');assert(D.valid(JSON.parse(JSON.stringify(d))),tool.id+' roundtrip');assert.doesNotThrow(()=>D.primitives(d,env),tool.id+' renders');assert(!D.valid({...d,points:[]}),tool.id+' requires anchors')}
assert(!D.valid(null));assert(!D.valid(drawing('hline',[point(NaN)])));assert(!D.valid(drawing('hline',[point(1,Infinity)])));assert(!D.valid(drawing('hline',[point(-3)])));assert(D.valid(drawing('hline',[point(-3)]),true));
assert(!D.valid(drawing('fibonacci',[point(100),point(120)],{ratios:[NaN]})));assert(!D.valid(drawing('hline',[point(100)],{style:{color:'url(x)'}})));assert(!D.valid(drawing('longposition',[point(100),point(110),point(120)])));
const fib=drawing('fibextension',[point(100,30),point(120,80),point(110,110)],{ratios:[0,1,1.618]});assert.deepEqual(D.levelValues(fib).map(v=>v.value),[110,130,142.36]);const fibLines=D.primitives(fib,env).filter(v=>v.kind==='line');assert(fibLines.every(v=>v.b.x===200),'extension projects right of third anchor');assert(fibLines.every(v=>Number.isInteger((200-v.a.y)*4)),'computed levels snap to native ticks');
const offplot=drawing('hline',[point(500)]);assert.equal(D.primitives(offplot,env).length,0,'offscreen price does not stick a label to the plot edge');
assert.deepEqual(D.lineClip({x:50,y:100},{x:50,y:90},r,'ray'),[{x:50,y:100},{x:50,y:0}]);assert.deepEqual(D.lineClip({x:80,y:60},{x:40,y:60},r,'ray'),[{x:80,y:60},{x:0,y:60}]);
const channel=D.primitives(drawing('channel',[point(100,20),point(140,100),point(60,60)]),env).filter(v=>v.kind==='line');assert.equal(channel.length,3);assert(channel.every(v=>Math.abs((v.b.y-v.a.y)/(v.b.x-v.a.x)+.5)<1e-8),'channel borders and median parallel');
assert.deepEqual(D.planValues(drawing('longposition',[point(100),point(99),point(103)]),.25),{riskTicks:4,rewardTicks:12,ratio:3});
const level=drawing('hline',[point(100,100)]);assert(D.hit(level,env,{x:140,y:100}));assert(!D.hit({...level,hidden:true},env,{x:100,y:100}));assert(!D.hit({...level,locked:true},env,{x:100,y:100}));
for(const interval of ['1s','5m','30m','1h','3hr','4h','1day','1week','1M','3M','12M','40R','1000T','500V','150m']){const c=I.parse(interval,.25);assert(I.valid(c));assert(I.valid(JSON.parse(JSON.stringify(c))));assert.equal(I.label(I.parse(I.label(c),.25)),I.label(c))}
assert.equal(I.parse('40R',.25).aggregation.size,40);assert.equal(I.parse('10P',.25).aggregation.size,40);assert.equal(I.parse('4h').tf,14400);assert.equal(I.parse('3hr').tf,10800);assert.equal(I.parse('125').tf,7500);
for(const value of ['0m','1.2R','3.1P','-4h','Infinity','999999999m','3Ms','1m;exit'])assert.throws(()=>I.parse(value,.25),value);
const month=I.parse('1M'),leap=Date.UTC(2024,1,19)/1000;assert.equal(I.bucket(leap,month),Date.UTC(2024,1,1)/1000);assert.equal(I.end(I.bucket(leap,month),month),Date.UTC(2024,2,1)/1000);
const week=I.parse('1w');assert.equal(new Date(I.bucket(Date.UTC(2026,8,6)/1000,week)*1000).getUTCDay(),1,'weeks start Monday');
for(const tick of [.25,.01,.00025])for(const low of [-10,0,100]){const normal=G.plan({low,high:low+100*tick,tick,height:400,width:800,from:0,to:3600}),dense=G.plan({low,high:low+100*tick,tick,height:400,width:800,from:0,to:3600,density:'dense'});assert(normal.prices.every(v=>Math.abs(v.price/tick-Math.round(v.price/tick))<1e-7),'grid on exact ticks');assert(dense.prices.filter(v=>v.major).length>=normal.prices.filter(v=>v.major).length);assert(normal.times.some(v=>v.major)&&normal.times.some(v=>!v.major));}
console.log('22 drawing tools: validation, geometry, clipping, precision, selection and save roundtrips passed. Standard/custom intervals, calendar boundaries and native-tick grids passed.');
const F=require('../share/flow-overlays.js'),Depth=require('../share/depth-views.js'),Ticket=require('../share/trade-panel.js');
const prints=[{p:'100.25',q:'.5',side:'buy'},{p:'100.5',q:'10',side:'sell'},{p:'100.75',q:'20',side:null}];
assert.deepEqual(F.filter(prints,{id:'largetrades',minimum:5,direction:'all'}),prints.slice(1));assert.deepEqual(F.filter(prints,{id:'bubbles',minimum:0,direction:'unknown'}),[prints[2]]);assert(!F.valid({id:'bubbles',pane:true}));assert(!F.valid({id:'bubbles',minimum:NaN}));
const dom=Depth.ladderRows({last:100.25,book:{bids:[['100','4'],['99.5','6']],asks:[['100.5','3'],['100.75','8']]}},.25,7,100.25);assert(dom.every((r,i)=>!i||Math.abs(dom[i-1].price-r.price-.25)<1e-9));assert.equal(dom.find(r=>r.price===99.75).bid,null,'unsupplied size remains unknown');assert.equal(dom.find(r=>r.price===100).bid,4);assert.equal(dom.filter(r=>r.last).length,1);
assert(!Ticket.valid({mode:'LIVE'}));assert(Ticket.valid({mode:'LOCAL_DRAFT',symbol:'ES SPECIMEN',source:'ibkr:123',side:'buy',kind:'limit',tif:'DAY',quantity:1,created:1,limit:6000.25,stop:null,stopLoss:5999,target:6002}));
console.log('Trade-size filters, unknown-side handling, exact DOM tick rows, missing depth and local-only ticket validation passed.');

// SPECIMEN BBO: all four shortcuts must preserve buy/sell and bid/ask independently.
const bbo={fresh:true,bid:['6000.25','3'],ask:['6000.50','8']};
for(const side of ['buy','sell'])for(const at of ['bid','ask'])assert.deepEqual(Ticket.quoteChoice(side,at,bbo),{side,kind:'limit',price:at==='bid'?6000.25:6000.5});
assert.equal(Ticket.quoteChoice('buy','bid',{...bbo,fresh:false}),null);
assert.equal(Ticket.quoteChoice('sell','ask',{...bbo,ask:[null]}),null);
assert.equal(Ticket.referencePrice('limit',{limit:''},bbo,'buy'),null,'an empty limit never becomes zero');
assert.equal(Ticket.referencePrice('stop',{stop:'6002.25'},bbo,'buy'),6002.25);
assert.equal(Ticket.referencePrice('stop-limit',{stop:'6002',limit:'6002.25'},bbo,'buy'),6002.25);
assert.equal(Ticket.referencePrice('limit',{limit:'-1.25'},bbo,'sell'),-1.25,'negative futures prices retain their sign');
assert.equal(Ticket.referencePrice('market',{},bbo,'buy'),6000.5);
assert.equal(Ticket.referencePrice('market',{},bbo,'sell'),6000.25);
console.log('Bid/ask side selection, stale quote rejection and market/limit/stop reference prices passed.');
