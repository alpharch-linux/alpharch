/* Grid positions are integer native ticks. Density changes spacing, never prices. */
(function(root){
'use strict';
function nice(n){const base=10**Math.floor(Math.log10(Math.max(1,n)));return [1,2,5,10].map(v=>v*base).find(v=>v>=n)||base*10}
function plan({low,high,tick,height,from,to,width,density='normal',event=false}){
 if(![low,high,tick,height,from,to,width].every(Number.isFinite)||high<=low||tick<=0||height<=0||to<=from||width<=0)return{prices:[],times:[]};
 const spacing={sparse:65,normal:40,dense:26}[density]||40,major=nice((high-low)/tick/Math.max(2,height/spacing)),minor=Math.max(1,[5,4,2].map(n=>major/n).find(n=>Number.isInteger(n)&&n*tick/(high-low)*height>=7)||major);
 const prices=[];for(let i=Math.ceil(low/tick/minor)*minor,limit=0;i*tick<=high&&limit<1000;i+=minor,limit++)prices.push({price:Number((i*tick).toPrecision(14)),major:i%major===0});
 const span=to-from,needed=span/(width/(density==='dense'?70:density==='sparse'?150:100)),steps=event?[1,2,5,10,20,50,100,200,500,1000]:[1,5,10,15,30,60,120,300,600,900,1800,3600,7200,14400,21600,43200,86400,172800,604800,2592000,7776000,31536000],timeMajor=steps.find(n=>n>=needed)||nice(needed),timeMinor=event?Math.max(1,Math.floor(timeMajor/4)):Math.max(1,timeMajor/4),times=[];
 for(let t=Math.ceil(from/timeMinor)*timeMinor,limit=0;t<=to&&limit<1000;t+=timeMinor,limit++)times.push({time:t,major:Math.abs(t/timeMajor-Math.round(t/timeMajor))<1e-6});
 return{prices,times,majorTicks:major,minorTicks:minor};
}
const api={plan};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.ChartGrid=api;
})(globalThis);
