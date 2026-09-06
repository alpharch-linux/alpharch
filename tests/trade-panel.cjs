// SPECIMEN tickets. These tests have no network access or order transport.
const assert=require('node:assert/strict');
const Ticket=require('../share/trade-panel.js');
const main={mode:'LOCAL_DRAFT',symbol:'ES SPECIMEN',source:'ibkr:123',created:1,side:'buy',kind:'limit',quantity:2,tif:'DAY',limit:6000,stop:null,stopLoss:null,target:null,setup:'single',linked:null};
const leg=(side,kind,quantity,limit,stop)=>({side,kind,quantity,tif:'DAY',limit,stop});
const linked=(type,legs,extra={})=>({...main,...extra,setup:type,linked:{type,legs,partialFill:'unverified',hosting:'unverified'}});
const target=leg('sell','limit',2,6002,null),stop=leg('sell','stop-limit',2,5998.75,5999);
const bracket=linked('bracket',[target,stop],{target:6002,stopLoss:5999});
assert.equal(Ticket.validateDraft(bracket,.25,true),bracket);
assert.deepEqual(Ticket.orderPlan(bracket),{
 setup:'bracket',
 orders:[{id:'entry',...leg('buy','limit',2,6000,null)},{id:'target',...target},{id:'stop',...stop}],
 activateAfter:[{parent:'entry',children:['target','stop']}],
 cancelOnFullFill:[['target','stop']]
},'a bracket links the two exits, never the entry and an exit');
const oco=linked('oco',[leg('sell','stop',2,null,5999)],{side:'sell',limit:6002});
assert.equal(Ticket.validateDraft(oco,.25,true),oco,'two same-side exit orders are valid OCO drafts');
assert.deepEqual(Ticket.orderPlan(oco).cancelOnFullFill,[['entry','peer']]);
assert.deepEqual(Ticket.orderPlan(oco).activateAfter,[],'neither standalone OCO leg waits for the other');
const breakout=linked('oco',[leg('sell','stop',2,null,5999)],{kind:'stop',limit:null,stop:6002});
assert.equal(Ticket.validateDraft(breakout,.25,true),breakout,'opposite-side OCO entries remain possible');
const oto=linked('oto',[target]);
assert.deepEqual(Ticket.orderPlan(oto).activateAfter,[{parent:'entry',children:['child']}]);
assert.deepEqual(Ticket.orderPlan(oto).cancelOnFullFill,[],'OTO is not an OCO pair');
for(const draft of [main,oco,breakout,bracket,oto]){
 const restored=JSON.parse(JSON.stringify(draft));
 assert(Ticket.valid(restored));
 assert.deepEqual(Ticket.orderPlan(restored),Ticket.orderPlan(draft),'links and all leg prices survive a saved layout');
}
for(const broken of [
 {...oco,linked:{...oco.linked,legs:[]}},
 {...oco,linked:{...oco.linked,type:'oto'}},
 {...oco,linked:{...oco.linked,hosting:'exchange'}},
 {...oco,linked:{...oco.linked,partialFill:'guaranteed'}},
 {...oco,linked:{...oco.linked,legs:[{...oco.linked.legs[0],stop:null}]}},
 {...bracket,linked:{...bracket.linked,legs:[target,{...stop,quantity:1}]}},
 {...bracket,linked:{...bracket.linked,legs:[target,{...stop,side:'buy'}]}},
 {...main,linked:oco.linked},
 {...main,mode:'LIVE'}
])assert(!Ticket.valid(broken),'malformed or falsely verified linked tickets are rejected');
assert.throws(()=>Ticket.validateDraft(linked('oco',[{...target,limit:6002.1}]),.25,true),/native tick/);
assert.throws(()=>Ticket.validateDraft(linked('oto',[{...target,quantity:.5}]),.25,true),/whole contracts/);
assert.throws(()=>Ticket.validateDraft(linked('bracket',[{...target,limit:5998},stop],{target:5998,stopLoss:5999}),.25,true),/opposite sides/);
assert.throws(()=>Ticket.validateDraft({...bracket,limit:6003},.25,true),/entry/);
const short=linked('bracket',[leg('buy','limit',2,5998,null),leg('buy','stop',2,null,6001)],{side:'sell',target:5998,stopLoss:6001});
assert.equal(Ticket.validateDraft(short,.25,true),short);
const negative=linked('oco',[leg('sell','stop',2,null,-2)],{limit:-1});
assert.equal(Ticket.validateDraft(negative,.25,true),negative);
assert.throws(()=>Ticket.validateDraft(negative,.25,false),/native tick/);
const crypto=linked('oto',[leg('sell','limit',.005,6001.01,null)],{quantity:.01});
assert.equal(Ticket.validateDraft(crypto,.01,false),crypto);
const legacy={...main,stopLoss:5999,target:6002};delete legacy.setup;delete legacy.linked;
assert(Ticket.valid(legacy),'old drafts remain readable');
assert.deepEqual(Ticket.orderPlan(legacy).cancelOnFullFill,[],'old unlinked price fields do not silently acquire OCO semantics');
console.log('Linked tickets: OCO/OTO/bracket relationships, save/restore, leg quantities, native ticks, malformed plans and legacy compatibility passed.');
