/* Interval parsing and calendar boundaries. Time bars use UTC, weeks start Monday. */
(function(root){
'use strict';
const units={s:1,m:60,h:3600,d:86400,w:604800,M:2592000};
const presets=['1s','5s','15s','30s','1m','2m','3m','5m','10m','15m','30m','1h','2h','3h','4h','6h','8h','12h','1d','1w','1M','40R','100R','100T','1000T','100V'];
function parse(input,tick=.01){
 const match=String(input).trim().match(/^(\d+(?:\.\d+)?)\s*(s|S|sec(?:onds?)?|m|min(?:utes?)?|h|H|hrs?|hours?|d|D|days?|w|W|weeks?|M|months?|R|r|range|T|t|ticks?|trades?|V|v|vol(?:ume)?|P|p|points?)?$/);
 if(!match)throw Error('Try 30s, 5m, 4h, 1d, 1w, 1M, 40R (range ticks), 10P (range points), 1000T (trades), or 100V (volume).');
 const n=Number(match[1]),raw=match[2]||'m';let unit=raw==='M'||raw.startsWith('month')?'M':raw.toLowerCase();
 unit=unit.startsWith('sec')?'s':unit.startsWith('min')?'m':unit.startsWith('hour')||unit.startsWith('hr')?'h':unit.startsWith('day')?'d':unit.startsWith('week')?'w':unit==='range'?'r':unit.startsWith('point')?'p':unit.startsWith('tick')||unit.startsWith('trade')?'t':unit.startsWith('vol')?'v':unit;
 if(!(n>0))throw Error('Use a positive interval.');
 if(['r','t','v','p'].includes(unit)){
  const size=unit==='p'?Math.round(n/tick):n;
  if(size<1e-9||size>1000000||unit!=='v'&&(!Number.isInteger(size)||unit==='p'&&Math.abs(size*tick-n)>tick*1e-6))throw Error('Use whole native ticks or trades, up to 1,000,000. A point range must fit the instrument’s tick size.');
  return {tf:60,interval:undefined,aggregation:{kind:unit==='t'?'ticks':unit==='v'?'volume':'range',size}};
 }
 if(!units[unit]||!Number.isInteger(n)||n*units[unit]>31622400)throw Error('Use whole time units between 1 second and 12 months (366 days).');
 return {tf:n*units[unit],interval:{unit,value:n},aggregation:undefined};
}
function label(c){if(c.aggregation&&c.aggregation.kind!=='time')return c.aggregation.size+({range:'R',ticks:'T',volume:'V'}[c.aggregation.kind]);if(c.interval)return c.interval.value+c.interval.unit;const n=c.tf;for(const unit of ['w','d','h','m'])if(n%units[unit]===0)return n/units[unit]+unit;return n+'s'}
function valid(c){if(!Number.isInteger(c.tf)||c.tf<1||c.tf>31622400)return false;if(c.interval===undefined)return true;const i=c.interval;return !!i&&Object.hasOwn(units,i.unit)&&Number.isInteger(i.value)&&i.value>0&&i.value*units[i.unit]===c.tf}
function bucket(t,c){const i=c.interval;if(i?.unit==='M'){const d=new Date(t*1000),m=d.getUTCFullYear()*12+d.getUTCMonth(),b=Math.floor(m/i.value)*i.value;return Date.UTC(Math.floor(b/12),b%12,1)/1000}const offset=i?.unit==='w'?345600:0;return Math.floor((t-offset)/c.tf)*c.tf+offset}
function end(t,c){if(c.interval?.unit==='M'){const d=new Date(t*1000);return Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+c.interval.value,1)/1000}return t+c.tf}
const api={units,presets,parse,label,valid,bucket,end};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.Intervals=api;
})(globalThis);
