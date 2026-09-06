/* Price/time drawing geometry. No feed subscriptions, DOM or account access. */
(function(root){
'use strict';
const catalog=[
 ['hline','Horizontal level','Lines',1,'─','Support, resistance, previous high/low'],
 ['hray','Horizontal ray','Lines',1,'⟶','A price level extending right from an anchor'],
 ['trend','Trend line','Lines',2,'╱','Connect two price/time anchors'],
 ['ray','Ray','Lines',2,'↗','A trend extending beyond its second anchor'],
 ['extended','Extended line','Lines',2,'⤢','Extend a trend in both directions'],
 ['vline','Vertical line','Lines',1,'│','Mark a time across the chart'],
 ['crossline','Cross line','Lines',1,'＋','Mark one exact price and time'],
 ['zone','Support / resistance zone','Zones & channels',2,'▰','Two prices, shaded across the chart'],
 ['rectangle','Rectangle','Zones & channels',2,'▭','A bounded price/time area'],
 ['channel','Parallel channel','Zones & channels',3,'⫽','Two anchors set the slope; a third sets the width'],
 ['pitchfork','Pitchfork','Zones & channels',3,'⋔','Origin, then two pivots for the median and parallels'],
 ['ellipse','Ellipse','Zones & channels',2,'◯','Circle a price/time area'],
 ['fibonacci','Fibonacci retracement','Fibonacci',2,'≋','Levels between two prices; editable ratios'],
 ['fibextension','Fibonacci extension','Fibonacci',3,'≋','Measure the first leg and project from a third anchor'],
 ['fibtime','Fibonacci time zones','Fibonacci',2,'╫','Project time intervals from two anchors'],
 ['note','Text note','Markup',1,'T','Place a label or session note'],
 ['arrow','Arrow','Markup',2,'➚','Point to a move or chart event'],
 ['brush','Freehand brush','Markup',0,'∿','Press and drag to draw a freehand path'],
 ['highlighter','Highlighter','Markup',0,'▱','Press and drag for a translucent broad stroke'],
 ['measure','Price / time measure','Planning',2,'↔','Price difference, native ticks and elapsed time'],
 ['longposition','Long position plan','Planning',3,'↑','Click entry, stop, target; shows ticks and reward/risk'],
 ['shortposition','Short position plan','Planning',3,'↓','Click entry, stop, target; shows ticks and reward/risk']
].map(([id,name,group,anchors,glyph,description])=>({id,name,group,anchors,glyph,description}));
const byId=Object.fromEntries(catalog.map(d=>[d.id,d]));
const defaults={color:'#e7c990',width:1.5,dash:'solid',fill:.12,fontSize:12,extend:false,magnet:false,repeat:false};
const ratios={fibonacci:[0,.236,.382,.5,.618,.786,1],fibextension:[0,.618,1,1.272,1.618,2,2.618],fibtime:[0,1,2,3,5,8,13]};
const finite=Number.isFinite, clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const styleValid=s=>s&&typeof s==='object'&&['color'].every(k=>s[k]===undefined||/^#[0-9a-f]{6}$/i.test(s[k]))&&['width','fill','fontSize'].every(k=>s[k]===undefined||finite(s[k])&&s[k]>=(k==='width'?.5:k==='fontSize'?9:0)&&s[k]<=(k==='width'?6:k==='fontSize'?24:.6))&&(s.dash===undefined||['solid','dashed','dotted'].includes(s.dash))&&['extend','magnet','repeat'].every(k=>s[k]===undefined||typeof s[k]==='boolean');
function valid(d,allowNegative=false){
 const def=d&&byId[d.type];if(!def||typeof d.text!=='string'||d.text.length>80||!Array.isArray(d.points))return false;
 if(def.anchors?d.points.length!==def.anchors:d.points.length<2||d.points.length>128)return false;
 if(!d.points.every(p=>p&&finite(p.t)&&p.t>0&&finite(p.p)&&(allowNegative||p.p>0)&&(p.eventId===undefined||typeof p.eventId==='string'&&p.eventId.length<=256)&&(p.eventOffset===undefined||finite(p.eventOffset)&&p.eventOffset>=0&&p.eventOffset<=1)))return false;
 if(!['locked','hidden'].every(k=>d[k]===undefined||typeof d[k]==='boolean')||(d.style!==undefined&&!styleValid(d.style)))return false;
 if(d.ratios!==undefined&&(!ratios[d.type]||!Array.isArray(d.ratios)||!d.ratios.length||d.ratios.length>16||!d.ratios.every(n=>finite(n)&&n>=-10&&n<=30)))return false;
 if(d.type==='longposition'||d.type==='shortposition'){const [entry,stop,target]=d.points.map(p=>p.p);return d.type==='longposition'?stop<entry&&target>entry:stop>entry&&target<entry}
 return true;
}
function lineClip(a,b,r,mode='segment'){
 const dx=b.x-a.x,dy=b.y-a.y;if(![a.x,a.y,b.x,b.y].every(finite)||(!dx&&!dy))return null;
 let lo=mode==='line'?-Infinity:0,hi=mode==='segment'?1:Infinity;
 for(const [p,q]of [[-dx,a.x-r.L],[dx,r.R-a.x],[-dy,a.y-r.T],[dy,r.B-a.y]]){
  if(!p){if(q<0)return null;continue}const t=q/p;
  if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);if(lo>hi)return null;
 }
 if(!finite(lo)||!finite(hi))return null;
 return [{x:a.x+lo*dx,y:a.y+lo*dy},{x:a.x+hi*dx,y:a.y+hi*dy}];
}
function levelValues(d){const [a,b,c]=d.points;return(d.ratios||ratios[d.type]||[]).map(ratio=>({ratio,value:d.type==='fibextension'?c.p+(b.p-a.p)*ratio:a.p+(b.p-a.p)*ratio}))}
function planValues(d,tick){const [a,b,c]=d.points,risk=Math.abs(a.p-b.p),reward=Math.abs(c.p-a.p);return{riskTicks:Math.round(risk/tick),rewardTicks:Math.round(reward/tick),ratio:risk?reward/risk:null}}
function primitives(d,env){
 const {r,x,y,format,tick}=env,p=d.points.map(a=>({x:x(a),y:y(a.p)})),[a,b,c]=p,style={...defaults,...d.style},out=[];
 const label=(text,xx,yy)=>{if(yy<r.T-12||yy>r.B||xx>r.R)return;out.push({kind:'text',text,x:clamp(xx,r.L+5,r.R-20),y:clamp(yy,r.T+14,r.B-5)})};
 const line=(a,b,mode='segment',extra={})=>{const clipped=lineClip(a,b,r,mode);if(clipped)out.push({kind:'line',a:clipped[0],b:clipped[1],...extra})};
 const horizontal=(yy,start=r.L,end=r.R)=>line({x:start,y:yy},{x:end,y:yy});
 const rect=(a,b,extra={})=>out.push({kind:'rect',x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(b.x-a.x),h:Math.abs(b.y-a.y),...extra});
 switch(d.type){
 case'hline':case'hray':case'crossline':horizontal(a.y,d.type==='hray'?a.x:r.L);label((d.text||'Level')+' '+format(d.points[0].p),d.type==='hray'?a.x+5:r.L+5,a.y-5);if(d.type!=='crossline')break;
 case'vline':line({x:a.x,y:r.T},{x:a.x,y:r.B});if(d.type==='vline'&&d.text)label(d.text,a.x+5,r.T+15);break;
 case'zone':rect({x:r.L,y:a.y},{x:r.R,y:b.y});label(d.text||'Zone',r.L+5,Math.min(a.y,b.y)-5);break;
 case'rectangle':rect(a,b);if(d.text)label(d.text,Math.min(a.x,b.x)+5,Math.min(a.y,b.y)-5);break;
 case'ellipse':out.push({kind:'ellipse',x:(a.x+b.x)/2,y:(a.y+b.y)/2,rx:Math.abs(b.x-a.x)/2,ry:Math.abs(b.y-a.y)/2});if(d.text)label(d.text,Math.min(a.x,b.x),Math.min(a.y,b.y)-5);break;
 case'channel':{if(Math.abs(b.x-a.x)<.001)break;const offset=c.y-(a.y+(c.x-a.x)*(b.y-a.y)/(b.x-a.x)),aa={x:a.x,y:a.y+offset},bb={x:b.x,y:b.y+offset};line(a,b,style.extend?'line':'segment');line(aa,bb,style.extend?'line':'segment');line({x:a.x,y:a.y+offset/2},{x:b.x,y:b.y+offset/2},style.extend?'line':'segment',{dash:'dashed'});out.push({kind:'polygon',points:[a,b,bb,aa]});if(d.text)label(d.text,a.x,a.y-8);break}
 case'pitchfork':{const mid={x:(b.x+c.x)/2,y:(b.y+c.y)/2},dx=mid.x-a.x,dy=mid.y-a.y;line(a,mid,'ray');line(b,{x:b.x+dx,y:b.y+dy},'ray');line(c,{x:c.x+dx,y:c.y+dy},'ray');line(b,c,'segment',{dash:'dashed'});break}
 case'fibonacci':case'fibextension':{for(const level of levelValues(d)){const xx=d.type==='fibextension'?c.x:Math.min(a.x,b.x),end=style.extend||d.type==='fibextension'?r.R:Math.max(...p.map(v=>v.x)),value=env.snap?env.snap(level.value):level.value,yy=y(value);horizontal(yy,xx,Math.max(xx+1,end));label(level.ratio+' · '+format(value),xx+5,yy-4)}break}
 case'fibtime':{for(const ratio of d.ratios||ratios.fibtime){const xx=a.x+(b.x-a.x)*ratio;line({x:xx,y:r.T},{x:xx,y:r.B});if(xx>=r.L&&xx<=r.R)label(String(ratio),xx+4,r.T+15)}break}
 case'note':label(d.text||'Note',a.x,a.y);break;
 case'brush':case'highlighter':for(let i=1;i<p.length;i++)line(p[i-1],p[i]);break;
 case'longposition':case'shortposition':{const end=Math.max(a.x+30,c.x),v=planValues(d,tick);rect(a,{x:end,y:b.y},{color:'#fa7294'});rect(a,{x:end,y:c.y},{color:'#59e5bf'});horizontal(a.y,a.x,end);label('Entry '+format(d.points[0].p),a.x+5,a.y-5);label('Stop '+format(d.points[1].p)+' · '+v.riskTicks+' ticks',a.x+5,b.y-5);label('Target '+format(d.points[2].p)+' · '+v.rewardTicks+' ticks · '+(v.ratio?.toFixed(2)||'—')+'R',a.x+5,c.y-5);break}
 default:{line(a,b,d.type==='extended'?'line':d.type==='ray'?'ray':'segment');if(d.type==='arrow'){const angle=Math.atan2(b.y-a.y,b.x-a.x);line(b,{x:b.x-12*Math.cos(angle-.45),y:b.y-12*Math.sin(angle-.45)});line(b,{x:b.x-12*Math.cos(angle+.45),y:b.y-12*Math.sin(angle+.45)})}if(d.type==='measure'){const delta=d.points[1].p-d.points[0].p,percent=d.points[0].p?delta/Math.abs(d.points[0].p)*100:null;label(format(delta)+' · '+Math.round(delta/tick)+' ticks'+(percent===null?'':' · '+percent.toFixed(3)+'%')+' · '+Math.abs(d.points[1].t-d.points[0].t).toFixed(0)+'s',a.x,a.y-8)}else if(d.text)label(d.text,a.x,a.y-8)}
 }
 return out;
}
function distance(point,a,b){const dx=b.x-a.x,dy=b.y-a.y,t=clamp(((point.x-a.x)*dx+(point.y-a.y)*dy)/(dx*dx+dy*dy||1),0,1);return Math.hypot(point.x-a.x-t*dx,point.y-a.y-t*dy)}
function hit(d,env,p){
 if(d.hidden||d.locked)return null;
 for(let i=0;i<d.points.length;i++){const a=d.points[i];if(Math.hypot(env.x(a)-p.x,env.y(a.p)-p.y)<9)return{anchor:i}}
 for(const s of primitives(d,env)){
  if(s.kind==='line'&&distance(p,s.a,s.b)<7)return{anchor:null};
  if(s.kind==='text'&&p.x>=s.x&&p.x<=s.x+s.text.length*(d.style?.fontSize||12)*.64&&p.y>=s.y-14&&p.y<=s.y+4)return{anchor:null};
  if(s.kind==='rect'&&p.x>=s.x-5&&p.x<=s.x+s.w+5&&p.y>=s.y-5&&p.y<=s.y+s.h+5&&Math.min(Math.abs(p.x-s.x),Math.abs(p.x-s.x-s.w),Math.abs(p.y-s.y),Math.abs(p.y-s.y-s.h))<7)return{anchor:null};
  if(s.kind==='ellipse'&&s.rx&&s.ry&&Math.abs(Math.hypot((p.x-s.x)/s.rx,(p.y-s.y)/s.ry)-1)<7/Math.max(1,Math.min(s.rx,s.ry)))return{anchor:null};
 }
 return null;
}
function paint(g,d,env,selected=false,preview=false){
 if(d.hidden)return;const style={...defaults,...d.style},r=env.r;g.save();g.beginPath();g.rect(r.L,r.T,r.R-r.L,r.B-r.T);g.clip();
 g.strokeStyle=style.color;g.fillStyle=style.color;g.lineWidth=d.type==='highlighter'?18:style.width;g.font=style.fontSize+'px ui-monospace';g.lineCap='round';g.lineJoin='round';
 const baseAlpha=preview ? .55 : d.type==='highlighter' ? .28 : 1;
 for(const s of primitives(d,env)){g.globalAlpha=baseAlpha;g.strokeStyle=s.color||style.color;g.fillStyle=s.color||style.color;g.setLineDash((s.dash||style.dash)==='dashed'?[7,5]:(s.dash||style.dash)==='dotted'?[2,4]:[]);g.beginPath();
  if(s.kind==='line'){g.moveTo(s.a.x,s.a.y);g.lineTo(s.b.x,s.b.y);g.stroke()}
  if(s.kind==='text'){g.globalAlpha=preview ? .65 : 1;g.fillText(s.text,s.x,s.y)}
  if(s.kind==='rect'){g.globalAlpha=style.fill*baseAlpha;g.fillRect(s.x,s.y,s.w,s.h);g.globalAlpha=baseAlpha;g.strokeRect(s.x,s.y,s.w,s.h)}
  if(s.kind==='ellipse'){g.ellipse(s.x,s.y,s.rx,s.ry,0,0,Math.PI*2);g.globalAlpha=style.fill*baseAlpha;g.fill();g.globalAlpha=baseAlpha;g.stroke()}
  if(s.kind==='polygon'){s.points.forEach((p,i)=>i?g.lineTo(p.x,p.y):g.moveTo(p.x,p.y));g.closePath();g.globalAlpha=style.fill*baseAlpha;g.fill()}
 }
 if(selected||preview){g.globalAlpha=1;g.setLineDash([]);for(const p of (d.points.length>3?[d.points[0],d.points.at(-1)]:d.points)){g.beginPath();g.arc(env.x(p),env.y(p.p),4,0,Math.PI*2);g.fillStyle=d.locked?'#718095':'#101923';g.fill();g.strokeStyle=style.color;g.lineWidth=1.5;g.stroke()}}
 g.restore();
}
const api={catalog,byId,defaults,ratios,styleValid,valid,lineClip,levelValues,planValues,primitives,hit,paint};
if(typeof module!=='undefined'&&module.exports)module.exports=api;root.DrawingTools=api;
})(globalThis);
