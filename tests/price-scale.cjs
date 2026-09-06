const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const page=fs.readFileSync('share/canvas.html','utf8');
const source=page.split('/* PRICE_SCALE_START */')[1].split('/* PRICE_SCALE_END */')[0];
const scale=vm.runInNewContext(source+';PriceScale');
for(const [low,high,tick] of [[23175.21,23242.79,.25],[5998.12,6010.91,.25],[-3.11,2.23,.25],[.01313,.01411,.00001]]){
 const labels=scale.axis(low,high,tick);
 assert(labels.length>0);
 for(const price of labels)assert(Math.abs(price/tick-Math.round(price/tick))<1e-8);
 assert(labels.every(p=>p>=low&&p<=high));
}
assert.equal(scale.snap(23231.53,.25),23231.5);
assert.equal(scale.snap(23231.65,.25),23231.75);
assert.equal(scale.snap(-3.13,.25),-3.25);
assert.equal(scale.snap(.0000146,.000001),.000015);
assert.equal(scale.snap(.000000146,.00000001),.00000015);
console.log('Price scales, crosshair and drawing snapping: tick precision checks passed');
